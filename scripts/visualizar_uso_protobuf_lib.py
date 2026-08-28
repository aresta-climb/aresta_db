# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Dict, List, Set, Any
from dataclasses import dataclass, field

@dataclass
class FieldInfo:
    name: str
    is_message: bool
    message_full_name: str | None = None
    is_enum: bool = False
    enum_full_name: str | None = None

@dataclass
class MessageInfo:
    name: str
    full_name: str
    fields: List[FieldInfo] = field(default_factory=list)

class DescriptorParser:
    """Faz o parse de um google.protobuf.descriptor.Descriptor para extrair os metadados do schema."""
    
    def __init__(self):
        self.visited_messages: Set[str] = set()
        self.messages: Dict[str, MessageInfo] = {}

    def parse(self, descriptor: Any) -> Dict[str, MessageInfo]:
        """Inicia a travessia a partir de um descriptor raiz e retorna as mensagens encontradas."""
        self._traverse(descriptor)
        return self.messages

    def _traverse(self, descriptor: Any) -> None:
        if descriptor.full_name in self.visited_messages:
            return
        
        self.visited_messages.add(descriptor.full_name)
        
        msg_info = MessageInfo(name=descriptor.name, full_name=descriptor.full_name)
        self.messages[descriptor.full_name] = msg_info

        # type=11 is TYPE_MESSAGE
        for f in descriptor.fields:
            is_msg = f.type == 11
            msg_full_name = f.message_type.full_name if (is_msg and f.message_type) else None
            
            is_enum = f.type == 14
            enum_full_name = f.enum_type.full_name if (is_enum and f.enum_type) else None
            
            field_info = FieldInfo(
                name=f.name,
                is_message=is_msg,
                message_full_name=msg_full_name,
                is_enum=is_enum,
                enum_full_name=enum_full_name
            )
            msg_info.fields.append(field_info)
            
            if is_msg and f.message_type:
                self._traverse(f.message_type)

class BinaryPbCounter:
    """Contador de preenchimento de campos de mensagens Protobuf lidas em runtime."""
    
    def __init__(self):
        # self.counts[message_full_name][field_name] = {"all": int, "published": int}
        self.counts: Dict[str, Dict[str, Dict[str, int]]] = {}
        self.message_totals: Dict[str, Dict[str, int]] = {}
        self.total_all = 0
        self.total_published = 0

    def process_file_message(self, message: Any, is_published: bool) -> None:
        """Processa um arquivo (ex: croqui ou indice) como uma unidade atômica."""
        present_fields: Set[tuple[str, str]] = set()
        self._traverse(message, present_fields)
        
        self.total_all += 1
        if is_published:
            self.total_published += 1
            
        touched_messages = {full_name for full_name, _ in present_fields}
        touched_messages.add(message.DESCRIPTOR.full_name)
        
        for full_name in touched_messages:
            if full_name not in self.message_totals:
                self.message_totals[full_name] = {"all": 0, "published": 0}
            self.message_totals[full_name]["all"] += 1
            if is_published:
                self.message_totals[full_name]["published"] += 1
            
        for full_name, field_name in present_fields:
            if full_name not in self.counts:
                self.counts[full_name] = {}
            if field_name not in self.counts[full_name]:
                self.counts[full_name][field_name] = {"all": 0, "published": 0}
            
            self.counts[full_name][field_name]["all"] += 1
            if is_published:
                self.counts[full_name][field_name]["published"] += 1

    def _traverse(self, message: Any, present_fields: Set[tuple[str, str]]) -> None:
        full_name = message.DESCRIPTOR.full_name
        for field_desc, value in message.ListFields():
            present_fields.add((full_name, field_desc.name))
            
            if field_desc.type == 11: # TYPE_MESSAGE
                if field_desc.label == 3: # LABEL_REPEATED
                    for item in value:
                        self._traverse(item, present_fields)
                else:
                    self._traverse(value, present_fields)

class HeatmapCalculator:
    @staticmethod
    def get_color(count: int, total: int) -> tuple[str, str]:
        """Retorna uma tupla (bgcolor, fontcolor) baseada no uso."""
        if total == 0 or count == 0:
            return ("#cccccc", "black")
        
        ratio = count / total
        r = int(ratio * 255)
        b = int((1 - ratio) * 255)
        
        bgcolor = f"#{r:02x}00{b:02x}"
        fontcolor = "white"
        return (bgcolor, fontcolor)

class GraphvizRenderer:
    def __init__(self, messages: Dict[str, MessageInfo], counter: BinaryPbCounter, single_column: bool = False, custom_totals: Dict[str, int] = None, filter_unused: bool = False, comments: Dict[Any, str] = None):
        self.messages = messages
        self.counter = counter
        self.single_column = single_column
        self.custom_totals = custom_totals or {}
        self.filter_unused = filter_unused
        self.comments = comments or {}

    def render(self) -> str:
        used_message_names = set()
        if self.filter_unused:
            for full_name, msg_info in self.messages.items():
                for field in msg_info.fields:
                    counts = self.counter.counts.get(full_name, {}).get(field.name, {"all": 0, "published": 0})
                    if counts["all"] > 0:
                        used_message_names.add(full_name)
                        if field.is_message and field.message_full_name in self.messages:
                            used_message_names.add(field.message_full_name)
        else:
            used_message_names = set(self.messages.keys())
            
        lines = []
        lines.append('digraph G {')
        lines.append('    fontname="Arial";')
        lines.append('    rankdir=LR;')
        lines.append('    node [shape=none, fontname=Arial];')
        legend_cols = 3 if self.single_column else 5
        lines.append('    labelloc="t";')
        lines.append('    labeljust="l";')
        lines.append('    label=<')
        lines.append('        <table border="0" cellborder="1" cellspacing="0">')
        lines.append(f'            <tr><td colspan="{legend_cols}"><b>Legenda de Colunas</b>&nbsp;&nbsp;</td></tr>')
        if self.single_column:
            lines.append('            <tr><td align="left"><b>Relativo</b>&nbsp;&nbsp;</td><td colspan="2" align="left">Dentre as instâncias criadas desta mensagem, em quantas o campo foi preenchido.&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
            lines.append('            <tr><td align="left"><b>Absoluto</b>&nbsp;&nbsp;</td><td colspan="2" align="left">No total de croquis processados, em quantos o campo foi preenchido.&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
        else:
            lines.append('            <tr><td align="left"><b>Relativo Pub.</b>&nbsp;&nbsp;</td><td colspan="4" align="left">Dentre os croquis publicados que criaram esta mensagem, quantos preencheram o campo.&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
            lines.append('            <tr><td align="left"><b>Em Publicados</b>&nbsp;&nbsp;</td><td colspan="4" align="left">No total de croquis publicados no banco, quantos preencheram o campo.&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
            lines.append('            <tr><td align="left"><b>Relativo Todos</b>&nbsp;&nbsp;</td><td colspan="4" align="left">Dentre todos os croquis que criaram esta mensagem, quantos preencheram o campo.&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
            lines.append('            <tr><td align="left"><b>Em Todos</b>&nbsp;&nbsp;</td><td colspan="4" align="left">No total global de croquis no banco, quantos preencheram o campo.&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
        lines.append('        </table>')
        lines.append('    >;')
        lines.append('')
        
        # Render nodes
        import html
        for full_name, msg_info in self.messages.items():
            if full_name not in used_message_names:
                continue
                
            msg_tooltip = html.escape(self.comments.get((msg_info.name, "__message__"), ""))
            msg_tooltip_attr = f' tooltip="{msg_tooltip}"' if msg_tooltip else ""
                
            lines.append(f'    "{full_name}" [label=<')
            lines.append('        <table border="0" cellborder="1" cellspacing="0">')
            if self.single_column:
                lines.append(f'            <tr><td colspan="3"{msg_tooltip_attr}><b>{msg_info.name}</b>&nbsp;&nbsp;</td></tr>')
                lines.append('            <tr><td><b>Campo</b>&nbsp;&nbsp;</td><td><b>Relativo</b>&nbsp;&nbsp;</td><td><b>Absoluto</b>&nbsp;&nbsp;</td></tr>')
            else:
                lines.append(f'            <tr><td colspan="5"{msg_tooltip_attr}><b>{msg_info.name}</b>&nbsp;&nbsp;</td></tr>')
                lines.append('            <tr><td><b>Campo</b>&nbsp;&nbsp;</td><td><b>Relativo Pub.</b>&nbsp;&nbsp;</td><td><b>Em Publicados</b>&nbsp;&nbsp;</td><td><b>Relativo Todos</b>&nbsp;&nbsp;</td><td><b>Em Todos</b>&nbsp;&nbsp;</td></tr>')
            
            has_rendered_field = False
            for field in msg_info.fields:
                counts = self.counter.counts.get(full_name, {}).get(field.name, {"all": 0, "published": 0})
                
                if self.filter_unused and counts["all"] == 0:
                    continue
                    
                has_rendered_field = True
                
                abs_total_all = self.custom_totals.get(full_name, self.counter.total_all)
                abs_total_pub = self.custom_totals.get(full_name, self.counter.total_published)
                
                rel_total_all = self.counter.message_totals.get(full_name, {}).get("all", 0)
                rel_total_pub = self.counter.message_totals.get(full_name, {}).get("published", 0)
                
                # Abs All
                all_cnt = counts["all"]
                all_bg, all_fg = HeatmapCalculator.get_color(all_cnt, abs_total_all)
                all_perc = int((all_cnt / abs_total_all) * 100) if abs_total_all else 0
                all_label = f'{all_perc}% ({all_cnt}/{abs_total_all})&nbsp;&nbsp;'
                
                # Abs Published
                pub_cnt = counts["published"]
                pub_bg, pub_fg = HeatmapCalculator.get_color(pub_cnt, abs_total_pub)
                pub_perc = int((pub_cnt / abs_total_pub) * 100) if abs_total_pub else 0
                pub_label = f'{pub_perc}% ({pub_cnt}/{abs_total_pub})&nbsp;&nbsp;'
                
                # Rel All
                rel_all_bg, rel_all_fg = HeatmapCalculator.get_color(all_cnt, rel_total_all)
                rel_all_perc = int((all_cnt / rel_total_all) * 100) if rel_total_all else 0
                rel_all_label = f'{rel_all_perc}% ({all_cnt}/{rel_total_all})&nbsp;&nbsp;'
                
                # Rel Published
                rel_pub_bg, rel_pub_fg = HeatmapCalculator.get_color(pub_cnt, rel_total_pub)
                rel_pub_perc = int((pub_cnt / rel_total_pub) * 100) if rel_total_pub else 0
                rel_pub_label = f'{rel_pub_perc}% ({pub_cnt}/{rel_total_pub})&nbsp;&nbsp;'
                
                raw_tooltip = self.comments.get((msg_info.name, field.name), "")
                if not raw_tooltip:
                    if field.is_message and field.message_full_name:
                        short_type_name = field.message_full_name.split('.')[-1]
                        raw_tooltip = self.comments.get((short_type_name, "__message__"), "")
                    elif field.is_enum and field.enum_full_name:
                        parts = field.enum_full_name.split('.')
                        short_type_name = parts[-1]
                        if short_type_name == "Enum" and len(parts) >= 2:
                            short_type_name = parts[-2]
                        raw_tooltip = self.comments.get((short_type_name, "__message__"), "")
                        
                field_tooltip = html.escape(raw_tooltip)
                field_tooltip_attr = f' tooltip="{field_tooltip}"' if field_tooltip else ""
                
                lines.append('            <tr>')
                lines.append(f'                <td align="left"{field_tooltip_attr}>{field.name}&nbsp;&nbsp;</td>')
                if self.single_column:
                    lines.append(f'                <td bgcolor="{rel_all_bg}"><font color="{rel_all_fg}">{rel_all_label}</font></td>')
                    lines.append(f'                <td port="{field.name}" bgcolor="{all_bg}"><font color="{all_fg}">{all_label}</font></td>')
                else:
                    lines.append(f'                <td bgcolor="{rel_pub_bg}"><font color="{rel_pub_fg}">{rel_pub_label}</font></td>')
                    lines.append(f'                <td bgcolor="{pub_bg}"><font color="{pub_fg}">{pub_label}</font></td>')
                    lines.append(f'                <td bgcolor="{rel_all_bg}"><font color="{rel_all_fg}">{rel_all_label}</font></td>')
                    lines.append(f'                <td port="{field.name}" bgcolor="{all_bg}"><font color="{all_fg}">{all_label}</font></td>')
                lines.append('            </tr>')
                
            if not has_rendered_field and self.filter_unused:
                colspan = 3 if self.single_column else 5
                lines.append(f'            <tr><td colspan="{colspan}"><i>Nenhum campo utilizado</i></td></tr>')
                
            lines.append('        </table>')
            lines.append('    >];')
            lines.append('')
            
        # Render edges
        for full_name, msg_info in self.messages.items():
            if full_name not in used_message_names:
                continue
            for field in msg_info.fields:
                counts = self.counter.counts.get(full_name, {}).get(field.name, {"all": 0, "published": 0})
                if self.filter_unused and counts["all"] == 0:
                    continue
                if field.is_message and field.message_full_name in used_message_names:
                    lines.append(f'    "{full_name}":"{field.name}":e -> "{field.message_full_name}":w;')
                    
        lines.append('}')
        return "\n".join(lines)
