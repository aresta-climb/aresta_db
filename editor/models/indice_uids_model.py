# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Modelo de índice de UIDs universal do Croqui (IndiceUidsModel).
Fornece lookups O(1) de entidades por UID (NanoID 14c) e formatação
hierárquica dinâmica de nomes (Grupo > Setor > Escalada).

Segue rigorosamente os Princípios I, II, III, IV e VII de AGENTS.md:
- Tudo em português
- Library-First
- 100% de unit test coverage
- TDD
- Sincronização com histórico (Undo/Redo)
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from PySide6.QtCore import QObject, Signal


class TipoEntidadeUid(IntEnum):
    """Identificador numérico do tipo de entidade indexada."""

    GRUPO = 1
    SETOR = 2
    ESCALADA = 3
    BOTAO = 4


@dataclass(slots=True)
class RegistroUid:
    """
    Registro plano de metadados de uma entidade indexada por seu UID.
    Armazena o contexto hierárquico necessário para resolução de caminhos O(1).
    """

    uid: str  # NanoID Base62 de 14 caracteres (Chave Primária)
    tipo_id: int  # 1: grupo, 2: setor, 3: escalada, 4: botao
    grupo_uid: str | None = None  # Preenchido se pertencer a um grupo
    nome_grupo: str | None = None  # Preenchido se pertencer ou for um grupo
    setor_uid: str | None = None  # Preenchido para setores e vias
    nome_setor: str | None = None  # Preenchido para setores e vias
    nome_escalada: str | None = None  # Preenchido APENAS para escaladas
    texto_botao: str | None = None  # Preenchido APENAS para botões
    indice_enfiada: int | None = None  # Preenchido se for enfiada de via de múltiplas enfiadas
    escalada_pai_uid: str | None = None  # Preenchido se for enfiada, aponta para a escalada pai

    def obter_caminho_formatado(self) -> str:
        """Retorna o rótulo hierárquico legível pronto para exibição."""
        if self.tipo_id == TipoEntidadeUid.GRUPO:
            return self.nome_grupo or ""
        elif self.tipo_id == TipoEntidadeUid.SETOR:
            if self.nome_grupo:
                return f"{self.nome_grupo} > {self.nome_setor}"
            return self.nome_setor or ""
        elif self.tipo_id == TipoEntidadeUid.ESCALADA:
            prefixo = (
                f"{self.nome_grupo} > {self.nome_setor}"
                if self.nome_grupo
                else (self.nome_setor or "")
            )
            nome = (
                f"{self.nome_escalada} ({self.indice_enfiada}ª Enfiada)"
                if self.indice_enfiada
                else (self.nome_escalada or "")
            )
            if prefixo and nome:
                return f"{prefixo} > {nome}"
            return nome or prefixo
        elif self.tipo_id == TipoEntidadeUid.BOTAO:
            return f"🔘 {self.texto_botao or 'Botão'}"
        return ""


def _extrair_nome_escalada(msg: Any) -> str:
    """Extrai o nome de uma mensagem Escalada ou de suas variantes de tipo."""
    if hasattr(msg, "nome"):
        return str(msg.nome)
    if hasattr(msg, "WhichOneof"):
        tipo = msg.WhichOneof("tipo")
        if tipo:
            sub = getattr(msg, tipo)
            if hasattr(sub, "nome"):
                return str(sub.nome)
    return ""


def _desembrulhar(obj: Any) -> Any:
    """Desembrulha ReadOnlyProxy se o objeto estiver envolvido."""
    from editor.models.readonly_proxy import ReadOnlyProxy

    if isinstance(obj, ReadOnlyProxy):
        return object.__getattribute__(obj, "_obj")
    return obj


class IndiceUidsModel(QObject):
    """
    Modelo de índice em memória de todos os UIDs de um croqui.
    Mantém tabela de hash O(1) de UIDs para RegistroUid e sincroniza
    com mutações de Undo/Redo do CroquiModel.
    """

    indice_alterado = Signal()

    def __init__(self, croqui: Any | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._registros: dict[str, RegistroUid] = {}
        self._obj_id_para_uid: dict[int, str] = {}
        if croqui is not None:
            self.carregar_do_croqui(croqui)

    def __len__(self) -> int:
        return len(self._registros)

    def obter(self, uid: str) -> RegistroUid | None:
        """Retorna o RegistroUid correspondente ao UID ou None se não existir."""
        if not uid:
            return None
        return self._registros.get(str(uid))

    def obter_uid_por_objeto(self, obj: Any) -> str | None:
        """Localiza o UID associado a um objeto Protobuf ou subobjeto de variante."""
        obj = _desembrulhar(obj)
        uid_val = getattr(obj, "uid", None)
        if uid_val:
            return str(uid_val)
        return self._obj_id_para_uid.get(id(obj))

    def obter_caminho(self, uid: str) -> str | None:
        """Retorna o caminho hierárquico legível da entidade ou None se não existir."""
        reg = self.obter(uid)
        return reg.obter_caminho_formatado() if reg is not None else None

    def existe(self, uid: str) -> bool:
        """Verifica se um UID está indexado."""
        if not uid:
            return False
        return str(uid) in self._registros

    def listar(self, tipo_id: int | None = None) -> list[RegistroUid]:
        """Retorna lista de todos os registros indexados, opcionalmente filtrados por tipo_id."""
        if tipo_id is not None:
            return [r for r in self._registros.values() if r.tipo_id == tipo_id]
        return list(self._registros.values())

    def carregar_do_croqui(self, croqui: Any) -> None:
        """Reconstrói completamente o índice a partir do objeto raiz do croqui."""
        self._registros.clear()
        self._obj_id_para_uid.clear()
        croqui = _desembrulhar(croqui)
        if not croqui:
            self.indice_alterado.emit()
            return

        # 1. Botões no Croqui
        if hasattr(croqui, "botoes"):
            for b in croqui.botoes:
                b = _desembrulhar(b)
                uid_b = getattr(b, "uid", "")
                if uid_b:
                    self._registros[uid_b] = RegistroUid(
                        uid=uid_b,
                        tipo_id=TipoEntidadeUid.BOTAO,
                        texto_botao=getattr(b, "texto", ""),
                    )
                    self._obj_id_para_uid[id(b)] = uid_b

        # 2. Picos e suas árvores
        if hasattr(croqui, "picos"):
            for pico in croqui.picos:
                self._carregar_pico(pico)

        self.indice_alterado.emit()

    def _carregar_pico(self, pico: Any) -> None:
        pico = _desembrulhar(pico)
        if not hasattr(pico, "setores_ou_grupos"):
            return

        for sg in pico.setores_ou_grupos:
            sg = _desembrulhar(sg)
            if sg.HasField("grupo"):
                grupo = sg.grupo.conteudo if sg.grupo.HasField("conteudo") else sg.grupo
                self._indexar_grupo(grupo)
            elif sg.HasField("setor"):
                setor = sg.setor.conteudo if sg.setor.HasField("conteudo") else sg.setor
                self._indexar_setor(setor, grupo_uid=None, nome_grupo=None)

    def _indexar_grupo(self, grupo: Any) -> None:
        grupo = _desembrulhar(grupo)
        uid_g = getattr(grupo, "uid", "")
        nome_g = str(getattr(grupo, "nome", ""))
        if uid_g:
            self._registros[uid_g] = RegistroUid(
                uid=uid_g,
                tipo_id=TipoEntidadeUid.GRUPO,
                nome_grupo=nome_g,
            )
            self._obj_id_para_uid[id(grupo)] = uid_g

        if hasattr(grupo, "setores"):
            for s_item in grupo.setores:
                s_item = _desembrulhar(s_item)
                setor = (
                    s_item.conteudo
                    if hasattr(s_item, "conteudo") and s_item.HasField("conteudo")
                    else s_item
                )
                self._indexar_setor(setor, grupo_uid=uid_g, nome_grupo=nome_g)

    def _indexar_setor(self, setor: Any, grupo_uid: str | None, nome_grupo: str | None) -> None:
        setor = _desembrulhar(setor)
        uid_s = getattr(setor, "uid", "")
        nome_s = str(getattr(setor, "nome", ""))
        if uid_s:
            self._registros[uid_s] = RegistroUid(
                uid=uid_s,
                tipo_id=TipoEntidadeUid.SETOR,
                grupo_uid=grupo_uid,
                nome_grupo=nome_grupo,
                setor_uid=uid_s,
                nome_setor=nome_s,
            )
            self._obj_id_para_uid[id(setor)] = uid_s

        if hasattr(setor, "escaladas"):
            for esc in setor.escaladas:
                self._indexar_escalada(
                    esc,
                    setor_uid=uid_s,
                    nome_setor=nome_s,
                    grupo_uid=grupo_uid,
                    nome_grupo=nome_grupo,
                )

    def _indexar_escalada(
        self,
        esc: Any,
        setor_uid: str | None,
        nome_setor: str | None,
        grupo_uid: str | None,
        nome_grupo: str | None,
    ) -> None:
        esc = _desembrulhar(esc)
        uid_e = getattr(esc, "uid", "")
        nome_e = _extrair_nome_escalada(esc)

        if uid_e:
            self._registros[uid_e] = RegistroUid(
                uid=uid_e,
                tipo_id=TipoEntidadeUid.ESCALADA,
                grupo_uid=grupo_uid,
                nome_grupo=nome_grupo,
                setor_uid=setor_uid,
                nome_setor=nome_setor,
                nome_escalada=nome_e,
            )
            self._obj_id_para_uid[id(esc)] = uid_e
            if hasattr(esc, "WhichOneof"):
                tipo = esc.WhichOneof("tipo")
                if tipo:
                    sub = getattr(esc, tipo)
                    self._obj_id_para_uid[id(sub)] = uid_e

        # Enfiadas se for via de múltiplas enfiadas
        if hasattr(esc, "WhichOneof") and esc.WhichOneof("tipo") == "via_multiplas_enfiadas":
            sub = esc.via_multiplas_enfiadas
            for idx_enf, enf in enumerate(sub.enfiadas, 1):
                enf = _desembrulhar(enf)
                uid_enf = getattr(enf, "uid", "")
                if uid_enf:
                    self._registros[uid_enf] = RegistroUid(
                        uid=uid_enf,
                        tipo_id=TipoEntidadeUid.ESCALADA,
                        grupo_uid=grupo_uid,
                        nome_grupo=nome_grupo,
                        setor_uid=setor_uid,
                        nome_setor=nome_setor,
                        nome_escalada=nome_e,
                        indice_enfiada=idx_enf,
                        escalada_pai_uid=uid_e,
                    )
                    self._obj_id_para_uid[id(enf)] = uid_enf
                    if hasattr(enf, "WhichOneof"):
                        tipo_enf = enf.WhichOneof("tipo")
                        if tipo_enf:
                            sub_enf = getattr(enf, tipo_enf)
                            self._obj_id_para_uid[id(sub_enf)] = uid_enf

    # ==========================================================================
    # Mutações Granulares
    # ==========================================================================

    def atualizar_nome_escalada(self, escalada_uid: str, novo_nome: str) -> None:
        """Atualiza o nome da escalada e de todas as suas enfiadas associadas."""
        reg = self.obter(escalada_uid)
        if not reg:
            return
        reg.nome_escalada = novo_nome

        # Atualiza enfiadas vinculadas a esta via
        for r in self._registros.values():
            if r.tipo_id == TipoEntidadeUid.ESCALADA and r.indice_enfiada is not None:
                if r.escalada_pai_uid == escalada_uid:
                    r.nome_escalada = novo_nome
        self.indice_alterado.emit()

    def atualizar_nome_setor(self, setor_uid: str, novo_nome: str) -> None:
        """Atualiza o nome do setor e propaga para todas as suas escaladas filhas."""
        reg = self.obter(setor_uid)
        if not reg:
            return
        reg.nome_setor = novo_nome

        for r in self._registros.values():
            if r.setor_uid == setor_uid:
                r.nome_setor = novo_nome
        self.indice_alterado.emit()

    def atualizar_nome_grupo(self, grupo_uid: str, novo_nome: str) -> None:
        """Atualiza o nome do grupo e propaga para todos os setores e escaladas vinculados."""
        reg = self.obter(grupo_uid)
        if not reg:
            return
        reg.nome_grupo = novo_nome

        for r in self._registros.values():
            if r.grupo_uid == grupo_uid:
                r.nome_grupo = novo_nome
        self.indice_alterado.emit()

    def atualizar_texto_botao(self, botao_uid: str, novo_texto: str) -> None:
        """Atualiza o texto descritivo do botão."""
        reg = self.obter(botao_uid)
        if not reg:
            return
        reg.texto_botao = novo_texto
        self.indice_alterado.emit()

    def mover_setor(
        self,
        setor_uid: str,
        novo_grupo_uid: str | None,
        novo_nome_grupo: str | None,
    ) -> None:
        """Atualiza a associação de grupo de um setor e de todas as suas escaladas."""
        reg = self.obter(setor_uid)
        if not reg:
            return
        reg.grupo_uid = novo_grupo_uid
        reg.nome_grupo = novo_nome_grupo

        for r in self._registros.values():
            if r.setor_uid == setor_uid:
                r.grupo_uid = novo_grupo_uid
                r.nome_grupo = novo_nome_grupo
        self.indice_alterado.emit()

    def mover_escalada(
        self,
        escalada_uid: str,
        novo_setor_uid: str,
        novo_nome_setor: str,
        novo_grupo_uid: str | None = None,
        novo_nome_grupo: str | None = None,
    ) -> None:
        """Atualiza a associação de setor e grupo de uma escalada e suas enfiadas."""
        reg = self.obter(escalada_uid)
        if not reg:
            return
        reg.setor_uid = novo_setor_uid
        reg.nome_setor = novo_nome_setor
        reg.grupo_uid = novo_grupo_uid
        reg.nome_grupo = novo_nome_grupo

        # Atualiza enfiadas filhas se houver
        for r in self._registros.values():
            if r.tipo_id == TipoEntidadeUid.ESCALADA and r.indice_enfiada is not None:
                if r.escalada_pai_uid == escalada_uid:
                    r.setor_uid = novo_setor_uid
                    r.nome_setor = novo_nome_setor
                    r.grupo_uid = novo_grupo_uid
                    r.nome_grupo = novo_nome_grupo
        self.indice_alterado.emit()

    def remover(self, uid: str) -> None:
        """Remove o registro do UID e limpa em cascata entidades filhas."""
        reg = self.obter(uid)
        if not reg:
            return

        if reg.tipo_id == TipoEntidadeUid.GRUPO:
            # Remove o grupo e tudo que estiver vinculado a ele
            uids_remover = [
                r.uid for r in self._registros.values() if r.grupo_uid == uid or r.uid == uid
            ]
            for u in uids_remover:
                self._registros.pop(u, None)
        elif reg.tipo_id == TipoEntidadeUid.SETOR:
            # Remove o setor e todas as escaladas filhas
            uids_remover = [
                r.uid for r in self._registros.values() if r.setor_uid == uid or r.uid == uid
            ]
            for u in uids_remover:
                self._registros.pop(u, None)
        elif reg.tipo_id == TipoEntidadeUid.ESCALADA:
            # Remove a via e suas enfiadas
            uids_remover = [
                r.uid for r in self._registros.values() if r.uid == uid or r.escalada_pai_uid == uid
            ]
            for u in uids_remover:
                self._registros.pop(u, None)
        else:
            self._registros.pop(uid, None)

        self.indice_alterado.emit()
