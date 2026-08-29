# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Any, Dict, List, Tuple
from PySide6.QtGui import QUndoCommand
from google.protobuf.message import Message
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import _copia_segura


def resolver_caminho_mensagem(root_msg: Any, target_msg: Any) -> str:
    """
    Retorna a string de caminho (ex: 'setores.0.vias.1') a partir de root_msg até target_msg.
    Retorna '' se target_msg for a própria root_msg.
    """
    if root_msg is None or target_msg is None:
        return ""
    from editor.models.readonly_proxy import ReadOnlyProxy
    if isinstance(root_msg, ReadOnlyProxy):
        root_msg = object.__getattribute__(root_msg, "_obj")
    if isinstance(target_msg, ReadOnlyProxy):
        target_msg = object.__getattribute__(target_msg, "_obj")
    if root_msg is target_msg:
        return ""

    if not hasattr(root_msg, "DESCRIPTOR"):
        return ""

    for descriptor in root_msg.DESCRIPTOR.fields:
        # Se for campo repeated (label == 3 ou is_repeated)
        is_repeated = getattr(descriptor, "label", None) == 3 or getattr(descriptor, "is_repeated", False)
        if is_repeated:
            try:
                val = getattr(root_msg, descriptor.name)
            except Exception:
                continue
            for idx, item in enumerate(val):
                if isinstance(item, Message):
                    if item is target_msg:
                        return f"{descriptor.name}.{idx}"
                    sub_caminho = resolver_caminho_mensagem(item, target_msg)
                    if sub_caminho:
                        return f"{descriptor.name}.{idx}.{sub_caminho}"
        else:
            # Para campo singular de mensagem (type == 11)
            is_message = getattr(descriptor, "type", None) == 11
            if is_message:
                try:
                    if not root_msg.HasField(descriptor.name):
                        continue
                except ValueError:
                    continue
                val = getattr(root_msg, descriptor.name)
                if val is target_msg:
                    return str(descriptor.name)
                sub_caminho = resolver_caminho_mensagem(val, target_msg)
                if sub_caminho:
                    return f"{descriptor.name}.{sub_caminho}"
    return ""



def navegar_para_mensagem(root_msg: Any, caminho: str) -> Any:
    """
    Navega a partir de root_msg seguindo o caminho (ex: 'setores.0.vias.1') e retorna a Message correspondente.
    """
    from editor.models.readonly_proxy import ReadOnlyProxy
    if isinstance(root_msg, ReadOnlyProxy):
        root_msg = object.__getattribute__(root_msg, "_obj")
    if not caminho or caminho in ("root", "node:root"):
        return root_msg

    partes = caminho.split(".")
    atual = root_msg
    for parte in partes:
        if parte.isdigit():
            atual = atual[int(parte)]
        else:
            atual = getattr(atual, parte)
        if isinstance(atual, ReadOnlyProxy):
            atual = object.__getattribute__(atual, "_obj")
    return atual


def _serializar_valor(valor: Any, anonimizado: bool = False) -> Any:
    """Serializa tipos primitivos ou instâncias Protobuf Message para representação de dicionário."""
    if isinstance(valor, Message):
        return {
            "__tipo_protobuf__": type(valor).__name__,
            "__bytes__": valor.SerializeToString()
        }
    return valor


def _deserializar_valor(valor_serializado: Any, model: Optional[CroquiModel] = None) -> Any:
    """Reconstrói tipo primitivo ou Protobuf Message a partir de representação serializada."""
    if isinstance(valor_serializado, dict) and "__tipo_protobuf__" in valor_serializado:
        tipo_nome = valor_serializado["__tipo_protobuf__"]
        import aresta_api.proto.generated.croqui_pb2 as croqui_pb2
        import aresta_api.proto.generated.indice_pb2 as indice_pb2
        cls = getattr(croqui_pb2, tipo_nome, None) or getattr(indice_pb2, tipo_nome, None)
        if cls:
            msg = cls()
            msg.ParseFromString(valor_serializado["__bytes__"])
            return msg
    return valor_serializado


class ComandoEditor(QUndoCommand):
    """
    Classe base para todos os comandos de Undo/Redo do Editor Aresta.
    
    Suporta carregamento silencioso na inicialização da aplicação:
    Quando o editor abre um croqui já salvo no disco (croqui.yaml), o modelo já contém
    o estado final consolidado. Para popular a QUndoStack sem reexecutar mutações desnecessárias
    em memória, a flag `_ignorar_primeiro_redo` pode ser ativada antes do push.
    Ao ser empurrado na pilha, o Qt chama `redo()`, que consome a flag silenciosamente sem alterar o modelo.
    Chamadas subsequentes de Redo (Ctrl+Y) pelo usuário executam a mutação normalmente.
    """
    def __init__(self, parent: Optional[QUndoCommand] = None) -> None:
        super().__init__(parent)
        self._ignorar_primeiro_redo: bool = False

    def armar_carregamento_silencioso(self) -> None:
        """Ativa a flag para que a próxima invocação de redo() (ao ser adicionado na QUndoStack) não aplique mutações."""
        self._ignorar_primeiro_redo = True

    def redo(self) -> None:
        """Executa a mutação de Redo, ignorando a primeira chamada se o comando foi armado para carga silenciosa."""
        if getattr(self, "_ignorar_primeiro_redo", False):
            self._ignorar_primeiro_redo = False
            return
        self.executar_redo()

    def executar_redo(self) -> None:
        """Aplica a mutação de avanço (Redo) no modelo."""
        raise NotImplementedError


class CmdAlterarPrimitivo(ComandoEditor):
    """Comando para alterar um campo primitivo de uma mensagem Protobuf via Model."""
    ID_COMANDO = 1001

    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        valor_antigo: Any,
        valor_novo: Any,
        context_path: Optional[str] = None,
        pode_mesclar: bool = False,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: Optional[str] = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarPrimitivo):
            return False
        id_self = self.msg.obter_id_nativo() if hasattr(self.msg, 'obter_id_nativo') else id(self.msg)
        id_outro = outro.msg.obter_id_nativo() if hasattr(outro.msg, 'obter_id_nativo') else id(outro.msg)
        if id_self == id_outro and self.campo_nome == outro.campo_nome:
            self.valor_novo = outro.valor_novo
            if hasattr(outro, 'context_path') and outro.context_path:
                self.context_path = outro.context_path
            self.model._set_primitivo(self.msg, self.campo_nome, self.valor_novo)
            return True
        return False

    def undo(self) -> None:
        self.model._set_primitivo(self.msg, self.campo_nome, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._set_primitivo(self.msg, self.campo_nome, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarPrimitivo",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarPrimitivo":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        return CmdAlterarPrimitivo(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            valor_antigo=dados.get("valor_antigo"),
            valor_novo=dados.get("valor_novo"),
            context_path=dados.get("context_path")
        )



class CmdAdicionarRepeated(ComandoEditor):
    """Comando para adicionar um item em um campo repeated via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        index: int,
        valor: Any,
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.index: int = index
        self.valor: Any = _copia_segura(valor)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        self.model._remover_repeated(self.msg, self.campo_nome, self.index)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAdicionarRepeated",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor": _serializar_valor(self.valor, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAdicionarRepeated":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        valor = _deserializar_valor(dados["valor"], model=model)
        return CmdAdicionarRepeated(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor=valor,
            context_path=dados.get("context_path")
        )


class CmdRemoverRepeated(ComandoEditor):
    """Comando para remover um item de um campo repeated via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        index: int,
        valor_removido: Any,
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.index: int = index
        self.valor_removido: Any = _copia_segura(valor_removido)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor_removido)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._remover_repeated(self.msg, self.campo_nome, self.index)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdRemoverRepeated",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor_removido": _serializar_valor(self.valor_removido, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdRemoverRepeated":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        valor_removido = _deserializar_valor(dados["valor_removido"], model=model)
        return CmdRemoverRepeated(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor_removido=valor_removido,
            context_path=dados.get("context_path")
        )


class CmdAlterarOneof(ComandoEditor):
    """Comando para alterar a escolha ativa de um campo oneof via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any,
        oneof_nome: str,
        nome_antigo: Optional[str],
        valor_antigo: Any,
        nome_novo: Optional[str],
        valor_novo: Any,
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.oneof_nome: str = oneof_nome
        self.nome_antigo: Optional[str] = nome_antigo
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.nome_novo: Optional[str] = nome_novo
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        self.model._alterar_oneof(self.msg, self.oneof_nome, self.nome_novo, self.nome_antigo, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._alterar_oneof(self.msg, self.oneof_nome, self.nome_antigo, self.nome_novo, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarOneof",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "oneof_nome": self.oneof_nome,
            "nome_antigo": self.nome_antigo,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "nome_novo": self.nome_novo,
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarOneof":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        valor_antigo = _deserializar_valor(dados["valor_antigo"], model=model)
        valor_novo = _deserializar_valor(dados["valor_novo"], model=model)
        return CmdAlterarOneof(
            model=model,
            msg=msg,
            oneof_nome=dados["oneof_nome"],
            nome_antigo=dados["nome_antigo"],
            valor_antigo=valor_antigo,
            nome_novo=dados["nome_novo"],
            valor_novo=valor_novo,
            context_path=dados.get("context_path")
        )


class CmdAlterarRepeatedItem(ComandoEditor):
    """Comando para alterar um item específico em uma coleção repeated via Model."""
    ID_COMANDO = 1002

    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        index: int,
        valor_antigo: Any,
        valor_novo: Any,
        context_path: Optional[str] = None,
        pode_mesclar: bool = False,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.index: int = index
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: Optional[str] = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarRepeatedItem):
            return False
        id_self = self.msg.obter_id_nativo() if hasattr(self.msg, 'obter_id_nativo') else id(self.msg)
        id_outro = outro.msg.obter_id_nativo() if hasattr(outro.msg, 'obter_id_nativo') else id(outro.msg)
        if id_self == id_outro and self.campo_nome == outro.campo_nome and self.index == outro.index:
            self.valor_novo = outro.valor_novo
            if hasattr(outro, 'context_path') and outro.context_path:
                self.context_path = outro.context_path
            self.model._alterar_repeated_item(self.msg, self.campo_nome, self.index, self.valor_novo)
            return True
        return False

    def undo(self) -> None:
        self.model._alterar_repeated_item(self.msg, self.campo_nome, self.index, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._alterar_repeated_item(self.msg, self.campo_nome, self.index, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarRepeatedItem",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarRepeatedItem":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        valor_antigo = _deserializar_valor(dados["valor_antigo"], model=model)
        valor_novo = _deserializar_valor(dados["valor_novo"], model=model)
        return CmdAlterarRepeatedItem(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor_antigo=valor_antigo,
            valor_novo=valor_novo,
            context_path=dados.get("context_path")
        )


class CmdAlterarMultiplosRepeatedItems(ComandoEditor):
    """Comando para alterar múltiplos itens em uma coleção repeated simultaneamente via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        alteracoes: List[Tuple[int, Any, Any]],
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.alteracoes: List[Tuple[int, Any, Any]] = []
        for index, valor_antigo, valor_novo in alteracoes:
            self.alteracoes.append((index, _copia_segura(valor_antigo), _copia_segura(valor_novo)))
        self.context_path: Optional[str] = context_path
        self.setText(f"Alterados {len(self.alteracoes)} itens em {self.campo_nome}")

    def undo(self) -> None:
        for index, valor_antigo, _ in self.alteracoes:
            self.model._alterar_repeated_item(self.msg, self.campo_nome, index, valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        for index, _, valor_novo in self.alteracoes:
            self.model._alterar_repeated_item(self.msg, self.campo_nome, index, valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        alt_serializadas = [
            (idx, _serializar_valor(v_ant, anonimizado=anonimizado), _serializar_valor(v_nov, anonimizado=anonimizado))
            for idx, v_ant, v_nov in self.alteracoes
        ]
        return {
            "classe": "CmdAlterarMultiplosRepeatedItems",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "alteracoes": alt_serializadas,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarMultiplosRepeatedItems":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        alt_deserializadas = [
            (idx, _deserializar_valor(v_ant, model=model), _deserializar_valor(v_nov, model=model))
            for idx, v_ant, v_nov in dados["alteracoes"]
        ]
        return CmdAlterarMultiplosRepeatedItems(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            alteracoes=alt_deserializadas,
            context_path=dados.get("context_path")
        )


class CmdMoverRepeated(ComandoEditor):
    """Comando para mover um item de uma coleção repeated para outra posição via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        index_from: int,
        index_to: int,
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.index_from: int = index_from
        self.index_to: int = index_to
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        self.model._mover_repeated(self.msg, self.campo_nome, self.index_to, self.index_from)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._mover_repeated(self.msg, self.campo_nome, self.index_from, self.index_to)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdMoverRepeated",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index_from": self.index_from,
            "index_to": self.index_to,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdMoverRepeated":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        return CmdMoverRepeated(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            index_from=dados["index_from"],
            index_to=dados["index_to"],
            context_path=dados.get("context_path")
        )



class CmdAlterarMetadadosCaminhoNovo(ComandoEditor):
    """Comando para alterar o sub-campo caminho_novo de uma extensão MetadadosArquivoNoEditor via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any,
        field_ext: Any,
        valor_antigo: Any,
        valor_novo: Any,
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.field_ext: Any = field_ext
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        self.model._alterar_metadados_caminho_novo(self.msg, self.field_ext, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model._alterar_metadados_caminho_novo(self.msg, self.field_ext, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarMetadadosCaminhoNovo",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "containing_type": self.field_ext.containing_type.name if self.field_ext.containing_type else None,
            "field_ext_nome": self.field_ext.name,
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarMetadadosCaminhoNovo":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
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
            msg=msg,
            field_ext=field_ext,
            valor_antigo=dados.get("valor_antigo"),
            valor_novo=dados.get("valor_novo"),
            context_path=dados.get("context_path")
        )


class CmdAlterarCampoImagem(ComandoEditor):
    """
    Comando para alterar um campo de imagem no Protobuf e atualizar o buffer em memória RAM.
    """
    def __init__(
        self,
        model: Any,
        msg: Any,
        campo_nome: str,
        caminho_antigo: Optional[str],
        bytes_antigo: Optional[bytes],
        caminho_novo: Optional[str],
        bytes_novo: Optional[bytes],
        context_path: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.msg: Any = msg
        self.campo_nome: str = campo_nome
        self.caminho_antigo: Optional[str] = caminho_antigo
        self.bytes_antigo: Optional[bytes] = bytes_antigo
        self.caminho_novo: Optional[str] = caminho_novo
        self.bytes_novo: Optional[bytes] = bytes_novo
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        if self.caminho_novo and self.caminho_novo != self.caminho_antigo:
            self.model.remover_imagem_memoria(self.caminho_novo)
        if self.caminho_antigo and self.bytes_antigo:
            self.model.definir_imagem_memoria(self.caminho_antigo, self.bytes_antigo)
            
        self.model._set_primitivo(self.msg, self.campo_nome, self.caminho_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        if self.caminho_antigo and self.caminho_antigo != self.caminho_novo:
            self.model.remover_imagem_memoria(self.caminho_antigo)
        if self.caminho_novo and self.bytes_novo:
            self.model.definir_imagem_memoria(self.caminho_novo, self.bytes_novo)
            
        self.model._set_primitivo(self.msg, self.campo_nome, self.caminho_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        bytes_antigo = self.bytes_antigo
        bytes_novo = self.bytes_novo
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado
            bytes_antigo = gerar_webp_anonimizado(self.bytes_antigo)
            bytes_novo = gerar_webp_anonimizado(self.bytes_novo)
            
        return {
            "classe": "CmdAlterarCampoImagem",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "caminho_antigo": self.caminho_antigo,
            "bytes_antigo": bytes_antigo,
            "caminho_novo": self.caminho_novo,
            "bytes_novo": bytes_novo,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarCampoImagem":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        return CmdAlterarCampoImagem(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            caminho_antigo=dados.get("caminho_antigo"),
            bytes_antigo=dados.get("bytes_antigo"),
            caminho_novo=dados.get("caminho_novo"),
            bytes_novo=dados.get("bytes_novo"),
            context_path=dados.get("context_path")
        )


class CmdSubstituirImagemMemoria(ComandoEditor):
    """
    Comando para substituir os bytes de uma imagem existente em memória RAM.
    """
    ID_COMANDO = 1003

    def __init__(
        self,
        model: Any,
        caminho_relativo: str,
        bytes_antigo: Optional[bytes],
        bytes_novo: bytes,
        context_path: Optional[str] = None,
        pode_mesclar: bool = False,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.caminho_relativo: str = caminho_relativo
        self.bytes_antigo: Optional[bytes] = bytes_antigo
        self.bytes_novo: bytes = bytes_novo
        self.context_path: Optional[str] = context_path
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
            if hasattr(outro, 'context_path') and outro.context_path:
                self.context_path = outro.context_path
            self.model.definir_imagem_memoria(self.caminho_relativo, self.bytes_novo)
            return True
        return False

    def undo(self) -> None:
        if self.bytes_antigo is not None:
            self.model.definir_imagem_memoria(self.caminho_relativo, self.bytes_antigo)
        else:
            self.model.remover_imagem_memoria(self.caminho_relativo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        self.model.definir_imagem_memoria(self.caminho_relativo, self.bytes_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
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
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdSubstituirImagemMemoria":
        return CmdSubstituirImagemMemoria(
            model=model,
            caminho_relativo=dados["caminho_relativo"],
            bytes_antigo=dados.get("bytes_antigo"),
            bytes_novo=dados["bytes_novo"],
            context_path=dados.get("context_path")
        )


def deserializar_comando(dados: Dict[str, Any], model: CroquiModel) -> QUndoCommand:
    """Factory global para deserializar qualquer QUndoCommand a partir de seu dicionário serializado."""
    classe_nome = dados.get("classe")
    mapa_classes: Dict[str, Any] = {
        "CmdAlterarPrimitivo": CmdAlterarPrimitivo,
        "CmdAdicionarRepeated": CmdAdicionarRepeated,
        "CmdRemoverRepeated": CmdRemoverRepeated,
        "CmdAlterarOneof": CmdAlterarOneof,
        "CmdAlterarRepeatedItem": CmdAlterarRepeatedItem,
        "CmdAlterarMultiplosRepeatedItems": CmdAlterarMultiplosRepeatedItems,
        "CmdMoverRepeated": CmdMoverRepeated,
        "CmdAlterarMetadadosCaminhoNovo": CmdAlterarMetadadosCaminhoNovo,
        "CmdAlterarCampoImagem": CmdAlterarCampoImagem,
        "CmdSubstituirImagemMemoria": CmdSubstituirImagemMemoria,
    }
    
    if classe_nome in mapa_classes:
        return mapa_classes[classe_nome].deserializar(dados, model)  # type: ignore[no-any-return]
    
    # Import dinâmico para comandos de mapas
    if classe_nome == "CmdAdicionarMapaArquivo":
        from editor.commands.comandos_mapas import CmdAdicionarMapaArquivo
        return CmdAdicionarMapaArquivo.deserializar(dados, model)
        
    raise ValueError(f"Classe de comando desconhecida para deserialização: {classe_nome}")

