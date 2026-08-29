# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Any, List
from pathlib import Path
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarRepeatedItem,
)


class MapasController:
    """
    Controller para interações específicas do Editor de Mapas.
    Despacha comandos para o Model através de QUndoCommand / GerenciadorHistorico.
    """
    
    def __init__(self, model: CroquiModel, undo_stack: Any) -> None:
        self.model: CroquiModel = model
        self.undo_stack: Any = undo_stack
        self.caminho_db: Optional[Path] = None
        self.contexto_atual_path: Optional[str] = None
        
    def set_contexto(self, path: Optional[str]) -> None:
        self.contexto_atual_path = path
        
    def set_caminho_db(self, caminho: Any) -> None:
        self.caminho_db = Path(caminho) if caminho else None

    def obter_pilha(self) -> Any:
        """Retorna a QUndoStack subjacente se estiver usando GerenciadorHistorico ou QUndoStack."""
        if hasattr(self.undo_stack, "obter_pilha"):
            return self.undo_stack.obter_pilha()
        return self.undo_stack

    def _executar_comando(self, cmd: Any) -> None:
        """Despacha comando pelo GerenciadorHistorico (persistindo no diário) ou diretamente na pilha."""
        if hasattr(self.undo_stack, "executar"):
            self.undo_stack.executar(cmd)
        elif hasattr(self.undo_stack, "push"):
            self.undo_stack.push(cmd)
        else:
            cmd.redo()

    def iniciar_grupo_undo(self, texto: str) -> None:
        """Inicia um macro de undo/redo para agrupar múltiplos comandos em um só."""
        pilha = self.obter_pilha()
        if pilha is not None:
            pilha.beginMacro(texto)

    def finalizar_grupo_undo(self) -> None:
        """Finaliza o macro atual de undo/redo."""
        pilha = self.obter_pilha()
        if pilha is not None:
            pilha.endMacro()

    def mover_ponto_de_interesse(
        self,
        historico: Any,
        chave_mapa: Any,
        idx_poi: int,
        estado_inicial: Any,
        estado_final: Any,
        widget_editor: Any,
    ) -> None:
        from editor.commands.comandos_mapas import CmdMoverPonto  # type: ignore[attr-defined]
        historico.executar(CmdMoverPonto(chave_mapa, idx_poi, estado_inicial, estado_final, widget_editor))

    def converter_boxes_para_circulos(self, msg_mapa_proxy: Any, indices: List[int]) -> None:
        """Converte múltiplos POIs do tipo box para circular de uma só vez."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import ReadOnlyProxy
        from editor.commands.comandos_protobuf import CmdAlterarMultiplosRepeatedItems
        
        alteracoes = []
        for index in indices:
            poi_antigo = msg_mapa_proxy.pontos_de_interesse[index]
            if not poi_antigo.HasField('retangulo'):
                continue
                
            poi_novo = croqui_pb2.Mapa.PontoDeInteresse()
            if isinstance(poi_antigo, ReadOnlyProxy):
                poi_novo.CopyFrom(poi_antigo._obj)
            else:
                poi_novo.CopyFrom(poi_antigo)
            
            box = poi_antigo.retangulo
            r = (box.comprimento + box.largura) / 4.0
            
            poi_novo.ClearField('tipo_area')
            poi_novo.circulo.x = box.x
            poi_novo.circulo.y = box.y
            poi_novo.circulo.raio = int(round(r))
            
            alteracoes.append((index, poi_antigo, poi_novo))
            
        if alteracoes:
            cmd = CmdAlterarMultiplosRepeatedItems(
                model=self.model,
                msg=msg_mapa_proxy,
                campo_nome="pontos_de_interesse",
                alteracoes=alteracoes,
                context_path=self.contexto_atual_path
            )
            self._executar_comando(cmd)

    def converter_circulos_para_boxes(self, msg_mapa_proxy: Any, indices: List[int]) -> None:
        """Converte múltiplos POIs do tipo circular para box de uma só vez."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import ReadOnlyProxy
        from editor.commands.comandos_protobuf import CmdAlterarMultiplosRepeatedItems
        
        alteracoes = []
        for index in indices:
            poi_antigo = msg_mapa_proxy.pontos_de_interesse[index]
            if not poi_antigo.HasField('circulo'):
                continue
                
            poi_novo = croqui_pb2.Mapa.PontoDeInteresse()
            if isinstance(poi_antigo, ReadOnlyProxy):
                poi_novo.CopyFrom(poi_antigo._obj)
            else:
                poi_novo.CopyFrom(poi_antigo)
            
            circ = poi_antigo.circulo
            r = circ.raio
            
            poi_novo.ClearField('tipo_area')
            poi_novo.retangulo.x = circ.x
            poi_novo.retangulo.y = circ.y
            poi_novo.retangulo.comprimento = r * 2
            poi_novo.retangulo.largura = r * 2
            
            alteracoes.append((index, poi_antigo, poi_novo))
            
        if alteracoes:
            cmd = CmdAlterarMultiplosRepeatedItems(
                model=self.model,
                msg=msg_mapa_proxy,
                campo_nome="pontos_de_interesse",
                alteracoes=alteracoes,
                context_path=self.contexto_atual_path
            )
            self._executar_comando(cmd)

    def adicionar_poi(self, msg_mapa_proxy: Any, poi_novo: Any) -> None:
        """Adiciona um POI ao mapa."""
        index = len(msg_mapa_proxy.pontos_de_interesse)
        cmd = CmdAdicionarRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor=poi_novo,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def deletar_poi(self, msg_mapa_proxy: Any, index: int) -> None:
        """Remove um POI do mapa."""
        poi_removido = msg_mapa_proxy.pontos_de_interesse[index]
        cmd = CmdRemoverRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor_removido=poi_removido,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def mover_poi(self, msg_mapa_proxy: Any, index: int, poi_antigo: Any, poi_novo: Any) -> None:
        """Altera um POI (posição, nome, etc)."""
        cmd = CmdAlterarRepeatedItem(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor_antigo=poi_antigo,
            valor_novo=poi_novo,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def adicionar_referencia(self, msg_mapa_proxy: Any, ref_nova: Any) -> None:
        """Adiciona uma referência ao mapa."""
        index = len(msg_mapa_proxy.referencias)
        cmd = CmdAdicionarRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="referencias",
            index=index,
            valor=ref_nova,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def deletar_referencia(self, msg_mapa_proxy: Any, index: int) -> None:
        """Remove uma referência do mapa."""
        ref_removida = msg_mapa_proxy.referencias[index]
        cmd = CmdRemoverRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="referencias",
            index=index,
            valor_removido=ref_removida,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def alterar_referencia(self, msg_mapa_proxy: Any, index: int, ref_antiga: Any, ref_nova: Any) -> None:
        """Altera uma referência."""
        cmd = CmdAlterarRepeatedItem(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="referencias",
            index=index,
            valor_antigo=ref_antiga,
            valor_novo=ref_nova,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def obter_caminho_imagem_mapa(self, msg_mapa_proxy: Any) -> Optional[Path]:
        """Retorna o caminho absoluto para a imagem do mapa."""
        if not self.caminho_db or not msg_mapa_proxy.caminho_imagem_mapa:
            return None
        return Path(self.caminho_db) / str(msg_mapa_proxy.caminho_imagem_mapa)


    def substituir_imagem(
        self,
        caminho_relativo: str,
        bytes_novo: bytes,
        bytes_antigo: Optional[bytes] = None,
        context_path: Optional[str] = None,
    ) -> None:
        """Despacha comando de substituição de imagem em memória RAM via GerenciadorHistorico / QUndoStack."""
        from editor.commands.comandos_protobuf import CmdSubstituirImagemMemoria
        if bytes_antigo is None:
            bytes_antigo = self.model.obter_bytes_imagem(caminho_relativo)
        ctx = context_path if context_path is not None else self.contexto_atual_path
        cmd = CmdSubstituirImagemMemoria(self.model, caminho_relativo, bytes_antigo, bytes_novo, ctx)
        self._executar_comando(cmd)

