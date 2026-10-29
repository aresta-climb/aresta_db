# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Módulo de comandos legados descontinuados do histórico.
Mantido EXCLUSIVAMENTE para retrocompatibilidade na deserialização de diários locais
(diario_pendente.bin e diario_salvo.bin) de croquis gravados em versões anteriores.

Nenhum código novo de produção deve instanciar estas classes diretamente.
Consulte `editor/commands/comandos_protobuf.py` para os comandos canônicos ativos.
"""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtGui import QUndoCommand

from editor.commands.comandos_protobuf import (
    ComandoEditor,
    _deserializar_valor,
    _serializar_valor,
    _validar_campo_se_msg_existir,
    resolver_caminho_mensagem,
    validar_pertence_ao_croqui,
)
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import _copia_segura

logger = logging.getLogger(__name__)


class CmdAlterarPrimitivo(ComandoEditor):
    """Comando legado para alterar um campo primitivo de uma mensagem Protobuf via Model."""

    ID_COMANDO = 1001

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        valor_antigo: Any = None,
        valor_novo: Any = None,
        context_path: str | None = None,
        pode_mesclar: bool = False,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdAlterarPrimitivo"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdAlterarPrimitivo"
            )
            self._msg_cache = msg
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarPrimitivo):
            return False
        if self.caminho_msg == outro.caminho_msg and self.campo_nome == outro.campo_nome:
            msg = self.msg
            if msg is None:
                return False
            self.valor_novo = outro.valor_novo
            if hasattr(outro, "context_path") and outro.context_path:
                self.context_path = outro.context_path
            self.model._set_primitivo(msg, self.campo_nome, self.valor_novo)
            return True
        return False

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.valor_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.valor_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAlterarPrimitivo",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarPrimitivo":
        return CmdAlterarPrimitivo(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            valor_antigo=dados.get("valor_antigo"),
            valor_novo=dados.get("valor_novo"),
            context_path=dados.get("context_path"),
        )


class CmdAlterarOneof(ComandoEditor):
    """Comando legado para alterar a escolha ativa de um campo oneof via Model."""

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        oneof_nome: str = "",
        nome_antigo: str | None = None,
        valor_antigo: Any = None,
        nome_novo: str | None = None,
        valor_novo: Any = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.oneof_nome: str = oneof_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, nome_comando="CmdAlterarOneof"
            )
            self._msg_cache = msg
        self.nome_antigo: str | None = nome_antigo
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.nome_novo: str | None = nome_novo
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_oneof(
            msg, self.oneof_nome, self.nome_novo, self.nome_antigo, self.valor_antigo
        )
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_oneof(
            msg, self.oneof_nome, self.nome_antigo, self.nome_novo, self.valor_novo
        )
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAlterarOneof",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "oneof_nome": self.oneof_nome,
            "nome_antigo": self.nome_antigo,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "nome_novo": self.nome_novo,
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarOneof":
        valor_antigo = _deserializar_valor(dados["valor_antigo"], model=model)
        valor_novo = _deserializar_valor(dados["valor_novo"], model=model)
        return CmdAlterarOneof(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            oneof_nome=dados["oneof_nome"],
            nome_antigo=dados["nome_antigo"],
            valor_antigo=valor_antigo,
            nome_novo=dados["nome_novo"],
            valor_novo=valor_novo,
            context_path=dados.get("context_path"),
        )


class CmdAlterarRepeatedItem(ComandoEditor):
    """Comando legado para alterar um item específico em uma coleção repeated via Model."""

    ID_COMANDO = 1002

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor_antigo: Any = None,
        valor_novo: Any = None,
        context_path: str | None = None,
        pode_mesclar: bool = False,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdAlterarRepeatedItem"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdAlterarRepeatedItem"
            )
            self._msg_cache = msg
        self.index: int = index
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarRepeatedItem):
            return False
        if (
            self.caminho_msg == outro.caminho_msg
            and self.campo_nome == outro.campo_nome
            and self.index == outro.index
        ):
            msg = self.msg
            if msg is None:
                return False
            self.valor_novo = outro.valor_novo
            if hasattr(outro, "context_path") and outro.context_path:
                self.context_path = outro.context_path
            self.model._alterar_repeated_item(msg, self.campo_nome, self.index, self.valor_novo)
            return True
        return False

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_repeated_item(msg, self.campo_nome, self.index, self.valor_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_repeated_item(msg, self.campo_nome, self.index, self.valor_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAlterarRepeatedItem",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarRepeatedItem":
        valor_antigo = _deserializar_valor(dados["valor_antigo"], model=model)
        valor_novo = _deserializar_valor(dados["valor_novo"], model=model)
        return CmdAlterarRepeatedItem(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor_antigo=valor_antigo,
            valor_novo=valor_novo,
            context_path=dados.get("context_path"),
        )


class CmdAlterarMultiplosRepeatedItems(ComandoEditor):
    """Comando legado para alterar múltiplos itens em uma coleção repeated simultaneamente via Model."""

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        alteracoes: list[tuple[int, Any, Any]] | None = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdAlterarMultiplosRepeatedItems"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdAlterarMultiplosRepeatedItems"
            )
            self._msg_cache = msg
        self.alteracoes: list[tuple[int, Any, Any]] = []
        if alteracoes:
            for index, valor_antigo, valor_novo in alteracoes:
                self.alteracoes.append(
                    (index, _copia_segura(valor_antigo), _copia_segura(valor_novo))
                )
        self.context_path: str | None = context_path
        self.setText(f"Alterados {len(self.alteracoes)} itens em {self.campo_nome}")

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        for index, valor_antigo, _ in self.alteracoes:
            self.model._alterar_repeated_item(msg, self.campo_nome, index, valor_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        for index, _, valor_novo in self.alteracoes:
            self.model._alterar_repeated_item(msg, self.campo_nome, index, valor_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        alt_serializadas = [
            (
                idx,
                _serializar_valor(v_ant, anonimizado=anonimizado),
                _serializar_valor(v_nov, anonimizado=anonimizado),
            )
            for idx, v_ant, v_nov in self.alteracoes
        ]
        return {
            "classe": "CmdAlterarMultiplosRepeatedItems",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "alteracoes": alt_serializadas,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(
        dados: dict[str, Any], model: CroquiModel
    ) -> "CmdAlterarMultiplosRepeatedItems":
        alt_deserializadas = [
            (idx, _deserializar_valor(v_ant, model=model), _deserializar_valor(v_nov, model=model))
            for idx, v_ant, v_nov in dados["alteracoes"]
        ]
        return CmdAlterarMultiplosRepeatedItems(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            alteracoes=alt_deserializadas,
            context_path=dados.get("context_path"),
        )


class CmdMigrarSetor(ComandoEditor):
    """Comando legado para migrar um setor entre listas repetidas (Pico/Grupo) via Model com Undo/Redo."""

    def __init__(
        self,
        model: Any,
        pai_origem: Any = None,
        campo_origem: str = "",
        indice_origem: int = 0,
        pai_destino: Any = None,
        campo_destino: str = "",
        indice_destino: int = 0,
        caminho_novo: str | None = None,
        caminho_antigo: str | None = None,
        caminho_msg_origem: str | None = None,
        caminho_msg_destino: str | None = None,
        context_path: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_origem: str = campo_origem
        self.indice_origem: int = indice_origem
        self.campo_destino: str = campo_destino
        self.indice_destino: int = indice_destino
        self.caminho_novo: str | None = caminho_novo
        self.caminho_antigo: str | None = caminho_antigo
        self.context_path: str | None = context_path

        self._pai_origem_cache: Any = pai_origem
        self._pai_destino_cache: Any = pai_destino

        if caminho_msg_origem is not None:
            self.caminho_msg_origem: str | None = caminho_msg_origem
        elif pai_origem is not None:
            self.caminho_msg_origem = validar_pertence_ao_croqui(
                self.model, pai_origem, nome_comando="CmdMigrarSetor (origem)"
            )
        else:
            self.caminho_msg_origem = None

        if caminho_msg_destino is not None:
            self.caminho_msg_destino: str | None = caminho_msg_destino
        elif pai_destino is not None:
            self.caminho_msg_destino = validar_pertence_ao_croqui(
                self.model, pai_destino, nome_comando="CmdMigrarSetor (destino)"
            )
        else:
            self.caminho_msg_destino = None

    def _obter_pai(self, caminho_msg: str | None, cache_attr: str) -> Any:
        cache = getattr(self, cache_attr, None)
        if cache is not None:
            return cache

        if self.model is None or caminho_msg is None:
            return None

        from editor.commands.comandos_protobuf import navegar_para_alvo

        root = (
            self.model.obter_croqui_readonly()
            if hasattr(self.model, "obter_croqui_readonly")
            else getattr(self.model, "croqui", None)
        )
        if caminho_msg == "":
            alvo = root
        else:
            alvo = navegar_para_alvo(root, caminho_msg, getattr(self.model, "indice_uids", None))

        if alvo is None:
            logger.error(
                "Falha ao resolver mensagem pai no caminho '%s' para o comando %s",
                caminho_msg,
                type(self).__name__,
            )
            return None

        from editor.models.readonly_proxy import ReadOnlyProxy

        if isinstance(alvo, ReadOnlyProxy):
            alvo = object.__getattribute__(alvo, "_obj")

        setattr(self, cache_attr, alvo)
        return alvo

    @property
    def pai_origem(self) -> Any:
        return self._obter_pai(self.caminho_msg_origem, "_pai_origem_cache")

    @property
    def pai_destino(self) -> Any:
        return self._obter_pai(self.caminho_msg_destino, "_pai_destino_cache")

    def undo(self) -> None:
        origem = self.pai_origem
        destino = self.pai_destino
        if origem is None or destino is None:
            return
        self.model._migrar_setor(
            destino,
            self.campo_destino,
            self.indice_destino,
            origem,
            self.campo_origem,
            self.indice_origem,
            self.caminho_antigo,
        )
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        origem = self.pai_origem
        destino = self.pai_destino
        if origem is None or destino is None:
            return
        self.model._migrar_setor(
            origem,
            self.campo_origem,
            self.indice_origem,
            destino,
            self.campo_destino,
            self.indice_destino,
            self.caminho_novo,
        )
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdMigrarSetor",
            "caminho_msg_origem": self.caminho_msg_origem,
            "campo_origem": self.campo_origem,
            "indice_origem": self.indice_origem,
            "caminho_msg_destino": self.caminho_msg_destino,
            "campo_destino": self.campo_destino,
            "indice_destino": self.indice_destino,
            "caminho_novo": self.caminho_novo,
            "caminho_antigo": self.caminho_antigo,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdMigrarSetor":
        return CmdMigrarSetor(
            model=model,
            caminho_msg_origem=dados.get("caminho_msg_origem"),
            campo_origem=dados.get("campo_origem", ""),
            indice_origem=dados.get("indice_origem", 0),
            caminho_msg_destino=dados.get("caminho_msg_destino"),
            campo_destino=dados.get("campo_destino", ""),
            indice_destino=dados.get("indice_destino", 0),
            caminho_novo=dados.get("caminho_novo"),
            caminho_antigo=dados.get("caminho_antigo"),
            context_path=dados.get("context_path"),
        )


class CmdAlterarMetadadosCaminhoNovo(ComandoEditor):
    """Comando legado para alterar o sub-campo caminho_novo de uma extensão MetadadosArquivoNoEditor via Model."""

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        field_ext: Any = None,
        valor_antigo: Any = None,
        valor_novo: Any = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.field_ext: Any = field_ext
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, nome_comando="CmdAlterarMetadadosCaminhoNovo"
            )
            self._msg_cache = msg
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_metadados_caminho_novo(msg, self.field_ext, self.valor_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_metadados_caminho_novo(msg, self.field_ext, self.valor_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAlterarMetadadosCaminhoNovo",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "containing_type": self.field_ext.containing_type.name
            if self.field_ext and self.field_ext.containing_type
            else None,
            "field_ext_nome": self.field_ext.name if self.field_ext else "",
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarMetadadosCaminhoNovo":
        import aresta_api.proto.generated.croqui_pb2 as croqui_pb2

        containing_type = dados.get("containing_type")
        field_ext_nome = dados["field_ext_nome"]
        if containing_type and hasattr(croqui_pb2, containing_type):
            msg_cls = getattr(croqui_pb2, containing_type)
            field_ext = getattr(msg_cls, field_ext_nome, None)
        else:
            field_ext = getattr(croqui_pb2, field_ext_nome, None)

        return CmdAlterarMetadadosCaminhoNovo(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            field_ext=field_ext,
            valor_antigo=dados.get("valor_antigo"),
            valor_novo=dados.get("valor_novo"),
            context_path=dados.get("context_path"),
        )


class CmdAlterarCampoImagem(ComandoEditor):
    """Comando legado para alterar um campo de imagem no Protobuf e atualizar o buffer em memória RAM."""

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        caminho_antigo: str | None = None,
        bytes_antigo: bytes | None = None,
        caminho_novo: str | None = None,
        bytes_novo: bytes | None = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdAlterarCampoImagem"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdAlterarCampoImagem"
            )
            self._msg_cache = msg
        self.caminho_antigo: str | None = caminho_antigo
        self.bytes_antigo: bytes | None = bytes_antigo
        self.caminho_novo: str | None = caminho_novo
        self.bytes_novo: bytes | None = bytes_novo
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_novo and self.caminho_novo != self.caminho_antigo:
            self.model.remover_imagem_memoria(self.caminho_novo)
        if self.caminho_antigo and self.bytes_antigo:
            self.model.definir_imagem_memoria(self.caminho_antigo, self.bytes_antigo)

        self.model._set_primitivo(msg, self.campo_nome, self.caminho_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_antigo and self.caminho_antigo != self.caminho_novo:
            self.model.remover_imagem_memoria(self.caminho_antigo)
        if self.caminho_novo and self.bytes_novo:
            self.model.definir_imagem_memoria(self.caminho_novo, self.bytes_novo)

        self.model._set_primitivo(msg, self.campo_nome, self.caminho_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        bytes_antigo = self.bytes_antigo
        bytes_novo = self.bytes_novo
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado

            bytes_antigo = gerar_webp_anonimizado(self.bytes_antigo)
            bytes_novo = gerar_webp_anonimizado(self.bytes_novo)

        return {
            "classe": "CmdAlterarCampoImagem",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "caminho_antigo": self.caminho_antigo,
            "bytes_antigo": bytes_antigo,
            "caminho_novo": self.caminho_novo,
            "bytes_novo": bytes_novo,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarCampoImagem":
        return CmdAlterarCampoImagem(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            caminho_antigo=dados.get("caminho_antigo"),
            bytes_antigo=dados.get("bytes_antigo"),
            caminho_novo=dados.get("caminho_novo"),
            bytes_novo=dados.get("bytes_novo"),
            context_path=dados.get("context_path"),
        )


class CmdSubstituirImagemMemoria(ComandoEditor):
    """Comando legado para substituir os bytes de uma imagem existente em memória RAM."""

    ID_COMANDO = 1003

    def __init__(
        self,
        model: Any,
        caminho_relativo: str,
        bytes_antigo: bytes | None,
        bytes_novo: bytes,
        context_path: str | None = None,
        pode_mesclar: bool = False,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.caminho_relativo: str = caminho_relativo
        self.bytes_antigo: bytes | None = bytes_antigo
        self.bytes_novo: bytes = bytes_novo
        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdSubstituirImagemMemoria):
            return False
        if self.caminho_relativo == outro.caminho_relativo:
            self.bytes_novo = outro.bytes_novo
            if hasattr(outro, "context_path") and outro.context_path:
                self.context_path = outro.context_path
            self.model.definir_imagem_memoria(self.caminho_relativo, self.bytes_novo)
            return True
        return False

    def undo(self) -> None:
        if self.bytes_antigo is not None:
            self.model.definir_imagem_memoria(self.caminho_relativo, self.bytes_antigo)
        else:
            self.model.remover_imagem_memoria(self.caminho_relativo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model.definir_imagem_memoria(self.caminho_relativo, self.bytes_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        bytes_antigo = self.bytes_antigo
        bytes_novo = self.bytes_novo
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado

            bytes_antigo = gerar_webp_anonimizado(self.bytes_antigo)
            bytes_novo = gerar_webp_anonimizado(self.bytes_novo)

        return {
            "classe": "CmdSubstituirImagemMemoria",
            "caminho_relativo": self.caminho_relativo,
            "bytes_antigo": bytes_antigo,
            "bytes_novo": bytes_novo,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdSubstituirImagemMemoria":
        return CmdSubstituirImagemMemoria(
            model=model,
            caminho_relativo=dados["caminho_relativo"],
            bytes_antigo=dados.get("bytes_antigo"),
            bytes_novo=dados["bytes_novo"],
            context_path=dados.get("context_path"),
        )


class CmdInserirImagemMarkdown(ComandoEditor):
    """Comando legado para inserir uma tag de imagem no Markdown e gerenciar os bytes em memória RAM."""

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        texto_antigo: str | None = None,
        texto_novo: str = "",
        caminho_imagem: str | None = None,
        bytes_imagem: bytes | None = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdInserirImagemMarkdown"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdInserirImagemMarkdown"
            )
            self._msg_cache = msg
        self.texto_antigo: str | None = _copia_segura(texto_antigo)
        self.texto_novo: str = _copia_segura(texto_novo)
        self.caminho_imagem: str | None = caminho_imagem
        self.bytes_imagem: bytes | None = bytes_imagem
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_imagem and self.bytes_imagem:
            self.model.remover_imagem_memoria(self.caminho_imagem)
        self.model._set_primitivo(msg, self.campo_nome, self.texto_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_imagem and self.bytes_imagem:
            self.model.definir_imagem_memoria(self.caminho_imagem, self.bytes_imagem)
        self.model._set_primitivo(msg, self.campo_nome, self.texto_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        bytes_imagem = self.bytes_imagem
        if anonimizado and bytes_imagem:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado

            bytes_imagem = gerar_webp_anonimizado(self.bytes_imagem)

        return {
            "classe": "CmdInserirImagemMarkdown",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "texto_antigo": self.texto_antigo,
            "texto_novo": self.texto_novo,
            "caminho_imagem": self.caminho_imagem,
            "bytes_imagem": bytes_imagem,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdInserirImagemMarkdown":
        return CmdInserirImagemMarkdown(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            texto_antigo=dados.get("texto_antigo"),
            texto_novo=dados.get("texto_novo", ""),
            caminho_imagem=dados.get("caminho_imagem"),
            bytes_imagem=dados.get("bytes_imagem"),
            context_path=dados.get("context_path"),
        )


ComandoInserirImagemMarkdown = CmdInserirImagemMarkdown


class CmdInserirBotaoMarkdown(ComandoEditor):
    """
    Comando legado para inserir um botão/link no Markdown e opcionalmente gerenciar os bytes
    do documento anexo associado na memória RAM do CroquiModel.
    """

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        texto_antigo: str | None = None,
        texto_novo: str = "",
        caminho_anexo: str | None = None,
        bytes_anexo: bytes | None = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdInserirBotaoMarkdown"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdInserirBotaoMarkdown"
            )
            self._msg_cache = msg
        self.texto_antigo: str | None = _copia_segura(texto_antigo)
        self.texto_novo: str = _copia_segura(texto_novo)
        self.caminho_anexo: str | None = caminho_anexo
        self.bytes_anexo: bytes | None = bytes_anexo
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_anexo and self.bytes_anexo:
            if hasattr(self.model, "remover_anexo_memoria"):
                self.model.remover_anexo_memoria(self.caminho_anexo)
        self.model._set_primitivo(msg, self.campo_nome, self.texto_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_anexo and self.bytes_anexo:
            if hasattr(self.model, "definir_anexo_memoria"):
                self.model.definir_anexo_memoria(self.caminho_anexo, self.bytes_anexo)
        self.model._set_primitivo(msg, self.campo_nome, self.texto_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdInserirBotaoMarkdown",
            "caminho_msg": self.caminho_msg
            if self.caminho_msg is not None
            else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "texto_antigo": self.texto_antigo,
            "texto_novo": self.texto_novo,
            "caminho_anexo": self.caminho_anexo,
            "bytes_anexo": self.bytes_anexo,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdInserirBotaoMarkdown":
        return CmdInserirBotaoMarkdown(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            texto_antigo=dados.get("texto_antigo"),
            texto_novo=dados.get("texto_novo", ""),
            caminho_anexo=dados.get("caminho_anexo"),
            bytes_anexo=dados.get("bytes_anexo"),
            context_path=dados.get("context_path"),
        )


ComandoInserirBotaoMarkdown = CmdInserirBotaoMarkdown


class CmdAdicionarMapaArquivo(ComandoEditor):
    """
    Comando legado para adicionar um Mapa no Protobuf e registrar sua imagem no buffer em memória RAM (CroquiModel).
    """

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor: Any = None,
        caminho_absoluto: Path | str | None = None,
        img_bytes: bytes | None = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdAdicionarMapaArquivo"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg, self.campo_nome, nome_comando="CmdAdicionarMapaArquivo"
            )
            self._msg_cache = msg
        self.index: int = index
        self.valor: Any = _copia_segura(valor)
        self.caminho_absoluto: Path | str | None = caminho_absoluto
        caminho_rel = (
            str(valor.caminho_imagem_mapa)
            if hasattr(valor, "caminho_imagem_mapa")
            else str(caminho_absoluto)
        )
        self.caminho_relativo: str = caminho_rel
        self.img_bytes: bytes | None = img_bytes
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self._obter_msg()
        if msg is None:
            return
        self.model._remover_repeated(msg, self.campo_nome, self.index)
        if self.caminho_relativo:
            self.model.remover_imagem_memoria(self.caminho_relativo)

        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self._obter_msg()
        if msg is None:
            return
        if self.caminho_relativo and self.img_bytes:
            self.model.definir_imagem_memoria(self.caminho_relativo, self.img_bytes)
        self.model._adicionar_repeated(msg, self.campo_nome, self.index, self.valor)

        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        img_bytes = self.img_bytes
        caminho_abs_str = str(self.caminho_absoluto) if self.caminho_absoluto else ""
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado

            bytes_anonimizados = gerar_webp_anonimizado(self.img_bytes) if self.img_bytes else None
            img_bytes = bytes_anonimizados
            caminho_abs_str = "[ARQUIVO_MAPA_ANONIMIZADO]"

        return {
            "classe": "CmdAdicionarMapaArquivo",
            "caminho_msg": self.caminho_msg
            or resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self._obter_msg()),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor": _serializar_valor(self.valor, anonimizado=anonimizado),
            "caminho_absoluto": caminho_abs_str,
            "img_bytes": img_bytes,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: Any) -> "CmdAdicionarMapaArquivo":
        valor = _deserializar_valor(dados["valor"], model=model)
        caminho_abs = Path(dados["caminho_absoluto"]) if dados.get("caminho_absoluto") else None
        return CmdAdicionarMapaArquivo(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor=valor,
            caminho_absoluto=caminho_abs,
            img_bytes=dados.get("img_bytes"),
            context_path=dados.get("context_path"),
        )


class CmdRenomearEscalada(ComandoEditor):
    """
    Comando legado para renomeação de uma escalada e atualização de referências em mapas.
    """

    ID_COMANDO = 1008

    def __init__(
        self,
        model: Any,
        msg_escalada: Any = None,
        campo_nome: str = "nome",
        nome_antigo: str = "",
        nome_novo: str = "",
        referencias: list[Any] | None = None,
        context_path: str | None = None,
        pode_mesclar: bool = True,
        session_id: int | None = None,
        caminho_msg: str | None = None,
        caminhos_referencias: list[str] | None = None,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome

        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdRenomearEscalada"
            )
            if msg_escalada is not None:
                self._msg_cache = msg_escalada
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, msg_escalada, self.campo_nome, nome_comando="CmdRenomearEscalada"
            )
            self._msg_cache = msg_escalada

        self.nome_antigo: str = _copia_segura(nome_antigo) if nome_antigo is not None else ""
        self.nome_novo: str = _copia_segura(nome_novo) if nome_novo is not None else ""

        if caminhos_referencias is not None:
            self.caminhos_referencias: list[str] = list(caminhos_referencias)
            self._referencias_cache: list[Any] = list(referencias) if referencias else []
        else:
            self.caminhos_referencias = []
            self._referencias_cache = list(referencias) if referencias else []
            for ref in self._referencias_cache:
                caminho_ref = validar_pertence_ao_croqui(
                    self.model, ref, nome_comando="CmdRenomearEscalada"
                )
                self.caminhos_referencias.append(caminho_ref)

        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar
        self.session_id: int | None = session_id
        self.setText(f"Renomear escalada para {self.nome_novo}")

    @property
    def msg_escalada(self) -> Any:
        return self._obter_msg()

    @property
    def referencias(self) -> list[Any]:
        return self._obter_referencias()

    def _obter_referencias(self) -> list[Any]:
        if self._referencias_cache:
            return self._referencias_cache
        if not self.caminhos_referencias:
            return []
        from editor.commands.comandos_protobuf import navegar_para_alvo

        root = (
            self.model.obter_croqui_readonly()
            if hasattr(self.model, "obter_croqui_readonly")
            else getattr(self.model, "croqui", None)
        )
        resolvidos = []
        for cam in self.caminhos_referencias:
            ref = navegar_para_alvo(root, cam, getattr(self.model, "indice_uids", None))
            if ref is not None:
                resolvidos.append(ref)
        return resolvidos

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdRenomearEscalada):
            return False
        if self.session_id != getattr(outro, "session_id", None):
            return False
        if self.caminho_msg != outro.caminho_msg or self.campo_nome != outro.campo_nome:
            return False

        msg = self.msg_escalada
        if msg is None:
            return False

        self.nome_novo = outro.nome_novo
        self.setText(f"Renomear escalada para {self.nome_novo}")
        if hasattr(outro, "context_path") and outro.context_path:
            self.context_path = outro.context_path

        self.model._set_primitivo(msg, self.campo_nome, self.nome_novo)
        return True

    def undo(self) -> None:
        msg = self.msg_escalada
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.nome_antigo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg_escalada
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.nome_novo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdRenomearEscalada",
            "caminho_msg": self.caminho_msg,
            "campo_nome": self.campo_nome,
            "nome_antigo": self.nome_antigo,
            "nome_novo": self.nome_novo,
            "caminhos_referencias": self.caminhos_referencias,
            "context_path": self.context_path,
            "session_id": self.session_id,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdRenomearEscalada":
        return CmdRenomearEscalada(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            caminhos_referencias=dados.get("caminhos_referencias", []),
            campo_nome=dados.get("campo_nome", "nome"),
            nome_antigo=dados.get("nome_antigo", ""),
            nome_novo=dados.get("nome_novo", ""),
            context_path=dados.get("context_path"),
            session_id=dados.get("session_id"),
        )


COMANDOS_LEGADOS_MAP: dict[str, type[ComandoEditor]] = {
    "CmdAlterarPrimitivo": CmdAlterarPrimitivo,
    "CmdAlterarOneof": CmdAlterarOneof,
    "CmdAlterarRepeatedItem": CmdAlterarRepeatedItem,
    "CmdAlterarMultiplosRepeatedItems": CmdAlterarMultiplosRepeatedItems,
    "CmdMigrarSetor": CmdMigrarSetor,
    "CmdAlterarMetadadosCaminhoNovo": CmdAlterarMetadadosCaminhoNovo,
    "CmdAlterarCampoImagem": CmdAlterarCampoImagem,
    "CmdSubstituirImagemMemoria": CmdSubstituirImagemMemoria,
    "CmdInserirImagemMarkdown": CmdInserirImagemMarkdown,
    "CmdInserirBotaoMarkdown": CmdInserirBotaoMarkdown,
    "CmdAdicionarMapaArquivo": CmdAdicionarMapaArquivo,
    "CmdRenomearEscalada": CmdRenomearEscalada,
}
