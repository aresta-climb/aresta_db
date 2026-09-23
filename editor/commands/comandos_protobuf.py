# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import logging
from typing import Optional, Any, Dict, List, Tuple
from PySide6.QtGui import QUndoCommand
from google.protobuf.message import Message
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import _copia_segura

logger = logging.getLogger(__name__)


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
                if descriptor.containing_oneof:
                    try:
                        active = root_msg.WhichOneof(descriptor.containing_oneof.name)
                        if active is not None and active != descriptor.name:
                            continue
                    except Exception:
                        pass
                try:
                    val = getattr(root_msg, descriptor.name)
                except Exception:
                    continue
                if val is target_msg:
                    return str(descriptor.name)
                sub_caminho = resolver_caminho_mensagem(val, target_msg)
                if sub_caminho:
                    return f"{descriptor.name}.{sub_caminho}"
    return ""



def navegar_para_mensagem(root_msg: Any, caminho: str) -> Any:
    """
    Navega a partir de root_msg seguindo o caminho (ex: 'setores.0.vias.1') e retorna a Message correspondente.
    Retorna None de forma segura se o caminho for inválido, índice fora de limite ou variante oneof inativa.
    """
    if root_msg is None:
        return None
    from editor.models.readonly_proxy import ReadOnlyProxy
    if isinstance(root_msg, ReadOnlyProxy):
        root_msg = object.__getattribute__(root_msg, "_obj")
    if not caminho or caminho in ("root", "node:root"):
        return root_msg

    partes = caminho.split(".")
    atual = root_msg
    for parte in partes:
        if parte.isdigit():
            idx = int(parte)
            try:
                if not hasattr(atual, "__len__") or idx < 0 or idx >= len(atual):
                    return None
                atual = atual[idx]
            except Exception:
                return None
        else:
            try:
                if hasattr(atual, "DESCRIPTOR"):
                    campo_desc = atual.DESCRIPTOR.fields_by_name.get(parte)
                    if campo_desc is None:
                        return None
                    if campo_desc.containing_oneof:
                        ativo = atual.WhichOneof(campo_desc.containing_oneof.name)
                        if ativo != parte:
                            return None
                if not hasattr(atual, parte):
                    return None
                atual = getattr(atual, parte)
            except Exception:
                return None
        if isinstance(atual, ReadOnlyProxy):
            atual = object.__getattribute__(atual, "_obj")
        if atual is None:
            return None
    return atual


def validar_pertence_ao_croqui(
    model: Any,
    msg: Any,
    campo_nome: Optional[str] = None,
    nome_comando: str = "Comando"
) -> str:
    """
    Valida se a mensagem alvo fornecida pertence à árvore de dados ativa do croqui.
    Se msg for o nó raiz (ou proxy do nó raiz), o caminho é considerado "".
    Se msg for outro nó, resolver_caminho_mensagem(root, msg) deve retornar um caminho não vazio.
    Se a mensagem for órfã ou o campo_nome não existir no DESCRIPTOR da mensagem, lança ValueError.
    Retorna o caminho resolvido.
    """
    if model is None or msg is None:
        raise ValueError(f"Modelo ou mensagem inválida para o comando {nome_comando}.")

    from editor.models.readonly_proxy import ReadOnlyProxy

    root_raw = model.obter_croqui_readonly() if hasattr(model, "obter_croqui_readonly") else getattr(model, "croqui", None)
    if isinstance(root_raw, ReadOnlyProxy):
        root_raw = object.__getattribute__(root_raw, "_obj")

    msg_raw = msg
    if isinstance(msg_raw, ReadOnlyProxy):
        msg_raw = object.__getattribute__(msg_raw, "_obj")

    if root_raw is not None and msg_raw is root_raw:
        caminho = ""
    elif root_raw is not None:
        caminho = resolver_caminho_mensagem(root_raw, msg_raw)
        if not caminho and (not hasattr(root_raw, "ListFields") or len(root_raw.ListFields()) > 0):
            raise ValueError(
                f"Mensagem alvo órfã detectada para o comando {nome_comando}: "
                f"a mensagem do tipo '{type(msg_raw).__name__}' não pertence à árvore ativa do croqui."
            )
    else:
        caminho = ""

    if campo_nome and hasattr(msg_raw, "DESCRIPTOR"):
        if campo_nome not in msg_raw.DESCRIPTOR.fields_by_name:
            raise ValueError(
                f"Campo '{campo_nome}' não existe na mensagem '{msg_raw.DESCRIPTOR.name}' "
                f"para o comando {nome_comando}."
            )

    return caminho


def _validar_campo_se_msg_existir(
    model: Any,
    caminho_msg: Optional[str],
    campo_nome: Optional[str],
    nome_comando: str = "Comando"
) -> None:
    """
    Valida a existência do campo no descriptor se a mensagem puder ser resolvida no modelo.
    Se a mensagem não existir no modelo (lazy resolution), não levanta erro prematuro.
    """
    if model is None or caminho_msg is None or not campo_nome:
        return
    root = model.obter_croqui_readonly() if hasattr(model, "obter_croqui_readonly") else getattr(model, "croqui", None)
    msg_alvo = navegar_para_mensagem(root, caminho_msg)
    if msg_alvo is not None and hasattr(msg_alvo, "DESCRIPTOR"):
        if campo_nome not in msg_alvo.DESCRIPTOR.fields_by_name:
            raise ValueError(
                f"Campo '{campo_nome}' não existe na mensagem '{msg_alvo.DESCRIPTOR.name}' "
                f"para o comando {nome_comando}."
            )



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

    Suporta resolução tardia (Lazy Resolution) da mensagem alvo:
    Armazena o caminho `caminho_msg` e resolve a referência da mensagem no modelo
    sob demanda através do método `_obter_msg()` e da propriedade `msg`.
    """
    def __init__(self, parent: Optional[QUndoCommand] = None) -> None:
        super().__init__(parent)
        self._ignorar_primeiro_redo: bool = False
        self._caminho_msg: Optional[str] = None
        self._msg_cache: Any = None

    @property
    def caminho_msg(self) -> Optional[str]:
        return self._caminho_msg

    @caminho_msg.setter
    def caminho_msg(self, valor: Optional[str]) -> None:
        self._caminho_msg = valor

    def _obter_msg(self) -> Any:
        """
        Resolve a mensagem alvo atual na árvore do modelo a partir de caminho_msg.
        Se caminho_msg não estiver definido, retorna _msg_cache.
        Se não for possível encontrar a mensagem alvo, registra logger.error e retorna None.
        """
        model = getattr(self, "model", None)
        if model is None:
            return self._msg_cache

        if self._caminho_msg is None:
            return self._msg_cache

        root = model.obter_croqui_readonly() if hasattr(model, "obter_croqui_readonly") else getattr(model, "croqui", None)
        alvo = navegar_para_mensagem(root, self._caminho_msg)
        if alvo is None:
            logger.error(
                "Falha ao resolver mensagem alvo no caminho '%s' para o comando %s",
                self._caminho_msg,
                type(self).__name__
            )
            return None

        if self._msg_cache is not None:
            return self._msg_cache

        return alvo

    @property
    def msg(self) -> Any:
        return self._obter_msg()

    @msg.setter
    def msg(self, valor: Any) -> None:
        self._msg_cache = valor

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

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        """Serializa o comando para dicionário. Subclasses devem sobrescrever."""
        raise NotImplementedError


class CmdAlterarPrimitivo(ComandoEditor):
    """Comando para alterar um campo primitivo de uma mensagem Protobuf via Model."""
    ID_COMANDO = 1001

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        valor_antigo: Any = None,
        valor_novo: Any = None,
        context_path: Optional[str] = None,
        pode_mesclar: bool = False,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdAlterarPrimitivo")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdAlterarPrimitivo")
            self._msg_cache = msg
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
        if self.caminho_msg == outro.caminho_msg and self.campo_nome == outro.campo_nome:
            msg = self.msg
            if msg is None:
                return False
            self.valor_novo = outro.valor_novo
            if hasattr(outro, 'context_path') and outro.context_path:
                self.context_path = outro.context_path
            self.model._set_primitivo(msg, self.campo_nome, self.valor_novo)
            return True
        return False

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarPrimitivo",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarPrimitivo":
        return CmdAlterarPrimitivo(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
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
        msg: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor: Any = None,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdAdicionarRepeated")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdAdicionarRepeated")
            self._msg_cache = msg
        self.index: int = index
        self.valor: Any = _copia_segura(valor)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._remover_repeated(msg, self.campo_nome, self.index)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._adicionar_repeated(msg, self.campo_nome, self.index, self.valor)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAdicionarRepeated",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor": _serializar_valor(self.valor, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAdicionarRepeated":
        valor = _deserializar_valor(dados["valor"], model=model)
        return CmdAdicionarRepeated(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor=valor,
            context_path=dados.get("context_path")
        )


class CmdRemoverRepeated(ComandoEditor):
    """Comando para remover um item de um campo repeated via Model, limpando imagens em RAM se forem órfãs."""
    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor_removido: Any = None,
        context_path: Optional[str] = None,
        imagens_removidas_ram: Optional[Dict[str, bytes]] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdRemoverRepeated")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdRemoverRepeated")
            self._msg_cache = msg
        self.index: int = index
        self.valor_removido: Any = _copia_segura(valor_removido)
        self.context_path: Optional[str] = context_path

        if imagens_removidas_ram is not None:
            self.imagens_removidas_ram: Dict[str, bytes] = dict(imagens_removidas_ram)
        else:
            self.imagens_removidas_ram = {}
            if hasattr(self.model, "obter_imagens_em_memoria") and hasattr(self.model, "obter_croqui_readonly"):
                imagens_ram = self.model.obter_imagens_em_memoria()
                if imagens_ram:
                    from editor.core.imagens_croqui import obter_imagens_orfas_ao_remover
                    croqui_raiz = self.model.obter_croqui_readonly()
                    orfas = obter_imagens_orfas_ao_remover(croqui_raiz, self.valor_removido, imagens_ram)
                    for caminho in orfas:
                        if caminho in imagens_ram:
                            self.imagens_removidas_ram[caminho] = imagens_ram[caminho]

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._adicionar_repeated(msg, self.campo_nome, self.index, self.valor_removido)
        for caminho, conteudo in self.imagens_removidas_ram.items():
            self.model.definir_imagem_memoria(caminho, conteudo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._remover_repeated(msg, self.campo_nome, self.index)
        for caminho in self.imagens_removidas_ram:
            self.model.remover_imagem_memoria(caminho)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        imagens_removidas_ram = self.imagens_removidas_ram
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado
            imagens_removidas_ram = {
                c: gerar_webp_anonimizado(b) for c, b in self.imagens_removidas_ram.items()
            }

        return {
            "classe": "CmdRemoverRepeated",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor_removido": _serializar_valor(self.valor_removido, anonimizado=anonimizado),
            "imagens_removidas_ram": imagens_removidas_ram,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdRemoverRepeated":
        valor_removido = _deserializar_valor(dados["valor_removido"], model=model)
        return CmdRemoverRepeated(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor_removido=valor_removido,
            context_path=dados.get("context_path"),
            imagens_removidas_ram=dados.get("imagens_removidas_ram")
        )


class CmdAlterarOneof(ComandoEditor):
    """Comando para alterar a escolha ativa de um campo oneof via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any = None,
        oneof_nome: str = "",
        nome_antigo: Optional[str] = None,
        valor_antigo: Any = None,
        nome_novo: Optional[str] = None,
        valor_novo: Any = None,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.oneof_nome: str = oneof_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, nome_comando="CmdAlterarOneof")
            self._msg_cache = msg
        self.nome_antigo: Optional[str] = nome_antigo
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.nome_novo: Optional[str] = nome_novo
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_oneof(msg, self.oneof_nome, self.nome_novo, self.nome_antigo, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_oneof(msg, self.oneof_nome, self.nome_antigo, self.nome_novo, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarOneof",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "oneof_nome": self.oneof_nome,
            "nome_antigo": self.nome_antigo,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "nome_novo": self.nome_novo,
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarOneof":
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
            context_path=dados.get("context_path")
        )


class CmdAlterarRepeatedItem(ComandoEditor):
    """Comando para alterar um item específico em uma coleção repeated via Model."""
    ID_COMANDO = 1002

    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor_antigo: Any = None,
        valor_novo: Any = None,
        context_path: Optional[str] = None,
        pode_mesclar: bool = False,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdAlterarRepeatedItem")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdAlterarRepeatedItem")
            self._msg_cache = msg
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
        if self.caminho_msg == outro.caminho_msg and self.campo_nome == outro.campo_nome and self.index == outro.index:
            msg = self.msg
            if msg is None:
                return False
            self.valor_novo = outro.valor_novo
            if hasattr(outro, 'context_path') and outro.context_path:
                self.context_path = outro.context_path
            self.model._alterar_repeated_item(msg, self.campo_nome, self.index, self.valor_novo)
            return True
        return False

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_repeated_item(msg, self.campo_nome, self.index, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_repeated_item(msg, self.campo_nome, self.index, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarRepeatedItem",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarRepeatedItem":
        valor_antigo = _deserializar_valor(dados["valor_antigo"], model=model)
        valor_novo = _deserializar_valor(dados["valor_novo"], model=model)
        return CmdAlterarRepeatedItem(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
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
        msg: Any = None,
        campo_nome: str = "",
        alteracoes: Optional[List[Tuple[int, Any, Any]]] = None,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdAlterarMultiplosRepeatedItems")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdAlterarMultiplosRepeatedItems")
            self._msg_cache = msg
        self.alteracoes: List[Tuple[int, Any, Any]] = []
        if alteracoes:
            for index, valor_antigo, valor_novo in alteracoes:
                self.alteracoes.append((index, _copia_segura(valor_antigo), _copia_segura(valor_novo)))
        self.context_path: Optional[str] = context_path
        self.setText(f"Alterados {len(self.alteracoes)} itens em {self.campo_nome}")

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        for index, valor_antigo, _ in self.alteracoes:
            self.model._alterar_repeated_item(msg, self.campo_nome, index, valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        for index, _, valor_novo in self.alteracoes:
            self.model._alterar_repeated_item(msg, self.campo_nome, index, valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        alt_serializadas = [
            (idx, _serializar_valor(v_ant, anonimizado=anonimizado), _serializar_valor(v_nov, anonimizado=anonimizado))
            for idx, v_ant, v_nov in self.alteracoes
        ]
        return {
            "classe": "CmdAlterarMultiplosRepeatedItems",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "alteracoes": alt_serializadas,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarMultiplosRepeatedItems":
        alt_deserializadas = [
            (idx, _deserializar_valor(v_ant, model=model), _deserializar_valor(v_nov, model=model))
            for idx, v_ant, v_nov in dados["alteracoes"]
        ]
        return CmdAlterarMultiplosRepeatedItems(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            alteracoes=alt_deserializadas,
            context_path=dados.get("context_path")
        )


class CmdMoverRepeated(ComandoEditor):
    """Comando para mover um item de uma coleção repeated para outra posição via Model."""
    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        index_from: int = 0,
        index_to: int = 0,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdMoverRepeated")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdMoverRepeated")
            self._msg_cache = msg
        self.index_from: int = index_from
        self.index_to: int = index_to
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._mover_repeated(msg, self.campo_nome, self.index_to, self.index_from)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._mover_repeated(msg, self.campo_nome, self.index_from, self.index_to)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdMoverRepeated",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index_from": self.index_from,
            "index_to": self.index_to,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdMoverRepeated":
        return CmdMoverRepeated(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
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
        msg: Any = None,
        field_ext: Any = None,
        valor_antigo: Any = None,
        valor_novo: Any = None,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.field_ext: Any = field_ext
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, nome_comando="CmdAlterarMetadadosCaminhoNovo")
            self._msg_cache = msg
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_metadados_caminho_novo(msg, self.field_ext, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._alterar_metadados_caminho_novo(msg, self.field_ext, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        return {
            "classe": "CmdAlterarMetadadosCaminhoNovo",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "containing_type": self.field_ext.containing_type.name if self.field_ext and self.field_ext.containing_type else None,
            "field_ext_nome": self.field_ext.name if self.field_ext else "",
            "valor_antigo": self.valor_antigo,
            "valor_novo": self.valor_novo,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarMetadadosCaminhoNovo":
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
            context_path=dados.get("context_path")
        )


class CmdAlterarCampoImagem(ComandoEditor):
    """
    Comando para alterar um campo de imagem no Protobuf e atualizar o buffer em memória RAM.
    """
    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        caminho_antigo: Optional[str] = None,
        bytes_antigo: Optional[bytes] = None,
        caminho_novo: Optional[str] = None,
        bytes_novo: Optional[bytes] = None,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdAlterarCampoImagem")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdAlterarCampoImagem")
            self._msg_cache = msg
        self.caminho_antigo: Optional[str] = caminho_antigo
        self.bytes_antigo: Optional[bytes] = bytes_antigo
        self.caminho_novo: Optional[str] = caminho_novo
        self.bytes_novo: Optional[bytes] = bytes_novo
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_novo and self.caminho_novo != self.caminho_antigo:
            self.model.remover_imagem_memoria(self.caminho_novo)
        if self.caminho_antigo and self.bytes_antigo:
            self.model.definir_imagem_memoria(self.caminho_antigo, self.bytes_antigo)
            
        self.model._set_primitivo(msg, self.campo_nome, self.caminho_antigo)
        if hasattr(self, 'context_path') and self.context_path:
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
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "caminho_antigo": self.caminho_antigo,
            "bytes_antigo": bytes_antigo,
            "caminho_novo": self.caminho_novo,
            "bytes_novo": bytes_novo,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdAlterarCampoImagem":
        return CmdAlterarCampoImagem(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
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


class CmdInserirImagemMarkdown(ComandoEditor):
    """
    Comando para inserir uma tag de imagem no Markdown e gerenciar os bytes em memória RAM.
    """
    def __init__(
        self,
        model: Any,
        msg: Any = None,
        campo_nome: str = "",
        texto_antigo: Optional[str] = None,
        texto_novo: str = "",
        caminho_imagem: Optional[str] = None,
        bytes_imagem: Optional[bytes] = None,
        context_path: Optional[str] = None,
        caminho_msg: Optional[str] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdInserirImagemMarkdown")
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg, self.campo_nome, nome_comando="CmdInserirImagemMarkdown")
            self._msg_cache = msg
        self.texto_antigo: Optional[str] = _copia_segura(texto_antigo)
        self.texto_novo: str = _copia_segura(texto_novo)
        self.caminho_imagem: Optional[str] = caminho_imagem
        self.bytes_imagem: Optional[bytes] = bytes_imagem
        self.context_path: Optional[str] = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_imagem and self.bytes_imagem:
            self.model.remover_imagem_memoria(self.caminho_imagem)
        self.model._set_primitivo(msg, self.campo_nome, self.texto_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        if self.caminho_imagem and self.bytes_imagem:
            self.model.definir_imagem_memoria(self.caminho_imagem, self.bytes_imagem)
        self.model._set_primitivo(msg, self.campo_nome, self.texto_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        bytes_imagem = self.bytes_imagem
        if anonimizado and bytes_imagem:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado
            bytes_imagem = gerar_webp_anonimizado(self.bytes_imagem)

        return {
            "classe": "CmdInserirImagemMarkdown",
            "caminho_msg": self.caminho_msg if self.caminho_msg is not None else resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "texto_antigo": self.texto_antigo,
            "texto_novo": self.texto_novo,
            "caminho_imagem": self.caminho_imagem,
            "bytes_imagem": bytes_imagem,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdInserirImagemMarkdown":
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


class CmdMacro(ComandoEditor):
    """
    Comando composto que agrupa uma sequência ordenada de comandos derivados de ComandoEditor.
    Garante execução atômica de Redo e Undo, serialização completa para o GerenciadorDiario
    e propagação de armar_carregamento_silencioso para todos os subcomandos.
    """
    def __init__(
        self,
        comandos: Optional[List[ComandoEditor]] = None,
        texto: str = "Macro",
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.comandos: List[ComandoEditor] = list(comandos) if comandos else []
        self.setText(texto)

    def adicionar_comando(self, comando: ComandoEditor) -> None:
        """Adiciona um subcomando à sequência do macro."""
        self.comandos.append(comando)

    def armar_carregamento_silencioso(self) -> None:
        """Ativa a flag para que a próxima invocação de redo() do macro não aplique mutações."""
        super().armar_carregamento_silencioso()

    def undo(self) -> None:
        """Desfaz todos os subcomandos em ordem reversa."""
        for cmd in reversed(self.comandos):
            cmd.undo()

    def executar_redo(self) -> None:
        """Executa todos os subcomandos em ordem cronológica de avanço."""
        for cmd in self.comandos:
            cmd.redo()

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
        """Serializa o macro e recursivamente todos os seus subcomandos."""
        return {
            "classe": "CmdMacro",
            "texto": self.text(),
            "comandos": [cmd.serializar(anonimizado=anonimizado) for cmd in self.comandos]
        }

    @staticmethod
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdMacro":
        """Reconstrói o macro e todos os seus subcomandos via deserializar_comando."""
        comandos_reconstruidos = [
            deserializar_comando(c, model) for c in dados.get("comandos", [])
        ]
        return CmdMacro(
            comandos=comandos_reconstruidos,
            texto=dados.get("texto", "Macro")
        )


class CmdRenomearEscalada(ComandoEditor):
    """
    Comando atômico para renomeação de uma escalada e atualização síncrona
    de todas as referências em mapas que apontam para ela no pico.
    Suporta mesclagem contínua via mergeWith delimitada por session_id.
    """
    ID_COMANDO = 1008

    def __init__(
        self,
        model: Any,
        msg_escalada: Any = None,
        campo_nome: str = "nome",
        nome_antigo: str = "",
        nome_novo: str = "",
        referencias: Optional[List[Any]] = None,
        context_path: Optional[str] = None,
        pode_mesclar: bool = True,
        session_id: Optional[int] = None,
        caminho_msg: Optional[str] = None,
        caminhos_referencias: Optional[List[str]] = None,
        parent: Optional[QUndoCommand] = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome

        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(self.model, self.caminho_msg, self.campo_nome, "CmdRenomearEscalada")
            if msg_escalada is not None:
                self._msg_cache = msg_escalada
        else:
            self.caminho_msg = validar_pertence_ao_croqui(self.model, msg_escalada, self.campo_nome, nome_comando="CmdRenomearEscalada")
            self._msg_cache = msg_escalada

        self.nome_antigo: str = _copia_segura(nome_antigo) if nome_antigo is not None else ""
        self.nome_novo: str = _copia_segura(nome_novo) if nome_novo is not None else ""

        if caminhos_referencias is not None:
            self.caminhos_referencias: List[str] = list(caminhos_referencias)
            self._referencias_cache: List[Any] = list(referencias) if referencias else []
        else:
            self.caminhos_referencias = []
            self._referencias_cache = list(referencias) if referencias else []
            for ref in self._referencias_cache:
                caminho_ref = validar_pertence_ao_croqui(self.model, ref, "escalada", nome_comando="CmdRenomearEscalada")
                self.caminhos_referencias.append(caminho_ref)

        self.context_path: Optional[str] = context_path
        self.pode_mesclar: bool = pode_mesclar
        self.session_id: Optional[int] = session_id
        self.setText(f"Renomear escalada para {self.nome_novo}")

    @property
    def msg_escalada(self) -> Any:
        return self._obter_msg()

    @property
    def referencias(self) -> List[Any]:
        return self._obter_referencias()

    def _obter_referencias(self) -> List[Any]:
        if self._referencias_cache:
            return self._referencias_cache
        if not self.caminhos_referencias:
            return []
        root = self.model.obter_croqui_readonly() if hasattr(self.model, "obter_croqui_readonly") else getattr(self.model, "croqui", None)
        resolvidos = []
        for cam in self.caminhos_referencias:
            ref = navegar_para_mensagem(root, cam)
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
        if hasattr(outro, 'context_path') and outro.context_path:
            self.context_path = outro.context_path

        self.model._set_primitivo(msg, self.campo_nome, self.nome_novo)
        for ref in self.referencias:
            self.model._set_primitivo(ref, "escalada", self.nome_novo)
        return True

    def undo(self) -> None:
        msg = self.msg_escalada
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.nome_antigo)
        for ref in self.referencias:
            self.model._set_primitivo(ref, "escalada", self.nome_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg_escalada
        if msg is None:
            return
        self.model._set_primitivo(msg, self.campo_nome, self.nome_novo)
        for ref in self.referencias:
            self.model._set_primitivo(ref, "escalada", self.nome_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> Dict[str, Any]:
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
    def deserializar(dados: Dict[str, Any], model: CroquiModel) -> "CmdRenomearEscalada":
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


def deserializar_comando(dados: Dict[str, Any], model: CroquiModel) -> ComandoEditor:
    """Factory global para deserializar qualquer ComandoEditor a partir de seu dicionário serializado."""
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
        "CmdInserirImagemMarkdown": CmdInserirImagemMarkdown,
        "CmdMacro": CmdMacro,
        "CmdRenomearEscalada": CmdRenomearEscalada,
    }
    
    if classe_nome in mapa_classes:
        return mapa_classes[classe_nome].deserializar(dados, model)  # type: ignore[no-any-return]
    
    # Import dinâmico para comandos de mapas
    if classe_nome == "CmdAdicionarMapaArquivo":
        from editor.commands.comandos_mapas import CmdAdicionarMapaArquivo
        return CmdAdicionarMapaArquivo.deserializar(dados, model)
        
    raise ValueError(f"Classe de comando desconhecida para deserialização: {classe_nome}")


