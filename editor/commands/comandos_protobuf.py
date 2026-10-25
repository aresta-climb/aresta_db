# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import logging
from typing import Any

from google.protobuf.message import Message
from PySide6.QtGui import QUndoCommand

from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import _copia_segura

logger = logging.getLogger(__name__)


class MensagemAlvoNaoEncontradaError(LookupError):
    """Exceção levantada quando uma mensagem do Protobuf não pode ser encontrada ou resolvida na árvore ativa do croqui."""

    pass


def garantir_uids_em_mensagem(msg: Any) -> str:
    """
    Garante recursivamente que `msg` e todas as suas submensagens ativas possuam
    um `uid` NanoID (14 caracteres Base62) preenchido quando o seu `DESCRIPTOR`
    definir o campo `uid`.

    Preserva qualquer `uid` já preenchido, atua in-place sobre `msg` (desembrulhando
    `ReadOnlyProxy` se necessário) e evita ativar submensagens singulares vazias
    (`HasField` / variantes inativas de `oneof`), exceto `.conteudo` em `ArquivoSetor`
    e `ArquivoGrupo` quando `WhichOneof("arquivo") != "caminho"`.

    Retorna o `uid` principal de `msg` (ou o primeiro `uid` encontrado na sua
    subárvore ativa de `oneof`), ou `""` caso não haja `uid`.
    """
    from editor.models.readonly_proxy import ReadOnlyProxy

    if isinstance(msg, ReadOnlyProxy):
        msg = object.__getattribute__(msg, "_obj")

    if not hasattr(msg, "DESCRIPTOR"):
        return ""

    from scripts.gerenciar_uids_lib import gerar_uid

    uid_principal = ""
    desc = msg.DESCRIPTOR
    if "uid" in desc.fields_by_name:
        uid_atual = str(getattr(msg, "uid", "") or "").strip()
        if not uid_atual:
            uid_atual = gerar_uid()
            msg.uid = uid_atual
        uid_principal = uid_atual

    for field_desc in desc.fields:
        if getattr(field_desc, "type", None) != 11:
            continue

        eh_repeated = getattr(field_desc, "label", None) == 3 or getattr(
            field_desc, "is_repeated", False
        )
        if eh_repeated:
            for item in getattr(msg, field_desc.name):
                garantir_uids_em_mensagem(item)
        elif field_desc.containing_oneof is not None:
            nome_oneof = field_desc.containing_oneof.name
            ativo = msg.WhichOneof(nome_oneof)
            eh_conteudo_arquivo = (
                nome_oneof == "arquivo"
                and field_desc.name == "conteudo"
                and desc.name in ("ArquivoSetor", "ArquivoGrupo")
                and ativo != "caminho"
            )
            if ativo == field_desc.name or eh_conteudo_arquivo:
                uid_filho = garantir_uids_em_mensagem(getattr(msg, field_desc.name))
                if not uid_principal:
                    uid_principal = uid_filho
        elif msg.HasField(field_desc.name):
            garantir_uids_em_mensagem(getattr(msg, field_desc.name))

    return uid_principal



def _buscar_mensagem_por_uid(
    msg_atual: Any, uid_procurado: str, caminho_atual: str = ""
) -> tuple[Any, str] | None:
    """
    Varre a árvore Protobuf em busca da mensagem com `uid == uid_procurado`,
    retornando `(mensagem, caminho_canonico)` ou None.
    """
    if msg_atual is None:
        return None
    from editor.models.readonly_proxy import ReadOnlyProxy

    if isinstance(msg_atual, ReadOnlyProxy):
        msg_atual = object.__getattribute__(msg_atual, "_obj")

    if getattr(msg_atual, "uid", "") == uid_procurado:
        return msg_atual, caminho_atual

    if not hasattr(msg_atual, "DESCRIPTOR"):
        return None

    for descriptor in msg_atual.DESCRIPTOR.fields:
        if getattr(descriptor, "type", None) != 11:
            continue

        eh_repeated = getattr(descriptor, "label", None) == 3 or getattr(
            descriptor, "is_repeated", False
        )
        if eh_repeated:
            colecao = getattr(msg_atual, descriptor.name)
            for idx, item in enumerate(colecao):
                sub_caminho = (
                    f"{caminho_atual}.{descriptor.name}.{idx}"
                    if caminho_atual
                    else f"{descriptor.name}.{idx}"
                )
                achado = _buscar_mensagem_por_uid(item, uid_procurado, sub_caminho)
                if achado is not None:
                    return achado
        else:
            if descriptor.containing_oneof:
                ativo = msg_atual.WhichOneof(descriptor.containing_oneof.name)
                if ativo != descriptor.name:
                    continue
            elif not msg_atual.HasField(descriptor.name):
                continue

            sub_msg = getattr(msg_atual, descriptor.name)
            sub_caminho = (
                f"{caminho_atual}.{descriptor.name}" if caminho_atual else str(descriptor.name)
            )
            achado = _buscar_mensagem_por_uid(sub_msg, uid_procurado, sub_caminho)
            if achado is not None:
                return achado

    return None


def resolver_alvo_mensagem(
    root_msg: Any, target_msg: Any, indice_uids: Any = None
) -> str:
    """
    Resolve o identificador híbrido de alvo em 3 níveis a partir de root_msg até target_msg:
    1. UID direto (ex: 'esc_1234') se target_msg tiver UID.
    2. <uid_ancestral>.<subcaminho> (ex: 'setor_abc.imagens.0') se algum ancestral possuir UID.
    3. Fallback posicional desde a raiz (ex: 'picos.0.imagens.1') se nenhum ancestral possuir UID.
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

    def _resolver_rec(
        atual: Any, ancestral_uid: str | None, subcaminho: str, caminho_raiz: str
    ) -> str | None:
        uid_atual = getattr(atual, "uid", None)
        if uid_atual and isinstance(uid_atual, str) and uid_atual.strip():
            novo_ancestral_uid = uid_atual.strip()
            novo_subcaminho = ""
        else:
            novo_ancestral_uid = ancestral_uid
            novo_subcaminho = subcaminho

        if atual is target_msg:
            if novo_ancestral_uid:
                return (
                    f"{novo_ancestral_uid}.{novo_subcaminho}"
                    if novo_subcaminho
                    else novo_ancestral_uid
                )
            return caminho_raiz

        for descriptor in atual.DESCRIPTOR.fields:
            is_repeated = getattr(descriptor, "label", None) == 3 or getattr(
                descriptor, "is_repeated", False
            )
            if is_repeated:
                colecao = getattr(atual, descriptor.name)
                for idx, item in enumerate(colecao):
                    if isinstance(item, Message):
                        prox_sub = (
                            f"{novo_subcaminho}.{descriptor.name}.{idx}"
                            if novo_subcaminho
                            else f"{descriptor.name}.{idx}"
                        )
                        prox_raiz = (
                            f"{caminho_raiz}.{descriptor.name}.{idx}"
                            if caminho_raiz
                            else f"{descriptor.name}.{idx}"
                        )
                        resultado = _resolver_rec(
                            item, novo_ancestral_uid, prox_sub, prox_raiz
                        )
                        if resultado is not None:
                            return resultado
            else:
                is_message = getattr(descriptor, "type", None) == 11
                if is_message:
                    if descriptor.containing_oneof:
                        ativo = atual.WhichOneof(descriptor.containing_oneof.name)
                        if ativo is not None and ativo != descriptor.name:
                            continue
                    val = getattr(atual, descriptor.name)
                    if not atual.HasField(descriptor.name) and val is not target_msg:
                        continue
                    prox_sub = (
                        f"{novo_subcaminho}.{descriptor.name}"
                        if novo_subcaminho
                        else str(descriptor.name)
                    )
                    prox_raiz = (
                        f"{caminho_raiz}.{descriptor.name}"
                        if caminho_raiz
                        else str(descriptor.name)
                    )
                    resultado = _resolver_rec(
                        val, novo_ancestral_uid, prox_sub, prox_raiz
                    )
                    if resultado is not None:
                        return resultado
        return None

    res = _resolver_rec(root_msg, None, "", "")
    return res or ""


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
        is_repeated = getattr(descriptor, "label", None) == 3 or getattr(
            descriptor, "is_repeated", False
        )
        if is_repeated:
            val = getattr(root_msg, descriptor.name)
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
                    active = root_msg.WhichOneof(descriptor.containing_oneof.name)
                    if active is not None and active != descriptor.name:
                        continue
                elif not root_msg.HasField(descriptor.name):
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
            if not hasattr(atual, "__len__") or idx < 0 or idx >= len(atual):
                return None
            atual = atual[idx]
        else:
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
    return atual


def navegar_para_alvo(root_msg: Any, alvo: str, indice_uids: Any = None) -> Any:
    """
    Navega na árvore a partir de um alvo nos 3 níveis:
    1. UID direto: busca no IndiceUidsModel (O(1)) ou por busca de UID na árvore.
    2. <uid>.<subcaminho>: busca a âncora pelo UID e navega pelo subcaminho.
    3. Fallback posicional desde a raiz: navega a partir de root_msg.
    Retorna None de forma segura caso o alvo não exista, índice fora de limite ou variante oneof inativa.
    """
    if root_msg is None:
        return None
    from editor.models.readonly_proxy import ReadOnlyProxy

    if isinstance(root_msg, ReadOnlyProxy):
        root_msg = object.__getattribute__(root_msg, "_obj")
    if not alvo or alvo in ("root", "node:root"):
        return root_msg

    alvo_limpo = str(alvo).strip()
    partes = alvo_limpo.split(".", 1)
    prefixo = partes[0]
    subcaminho = partes[1] if len(partes) > 1 else ""

    ancora = None
    if indice_uids is not None and hasattr(indice_uids, "obter_objeto"):
        ancora = indice_uids.obter_objeto(prefixo)

    if ancora is None:
        achado = _buscar_mensagem_por_uid(root_msg, prefixo)
        if achado is not None:
            if not subcaminho:
                return achado[0]
            ancora = achado[0]

    if ancora is not None:
        if isinstance(ancora, ReadOnlyProxy):
            ancora = object.__getattribute__(ancora, "_obj")
        if not subcaminho:
            return ancora
        res = navegar_para_mensagem(ancora, subcaminho)
        if res is None and hasattr(ancora, "DESCRIPTOR") and "tipo" in ancora.DESCRIPTOR.oneofs_by_name:
            variante = ancora.WhichOneof("tipo")
            if variante:
                res = navegar_para_mensagem(getattr(ancora, variante), subcaminho)
        return res

    # Fallback posicional a partir da raiz (caminhos legados ou sem UID)
    return navegar_para_mensagem(root_msg, alvo_limpo)


def _ajustar_submensagem_variante_se_necessario(
    msg: Any, caminho: str, campo_nome: str | None
) -> tuple[Any, str]:
    """
    Se `msg` for uma Escalada ou Enfiada (possui `oneof tipo`) e `campo_nome`
    pertencer à variante ativa em vez do envelope externo, redireciona para a variante ativa.
    """
    if (
        campo_nome
        and hasattr(msg, "DESCRIPTOR")
        and campo_nome not in msg.DESCRIPTOR.fields_by_name
        and campo_nome not in msg.DESCRIPTOR.oneofs_by_name
        and "tipo" in msg.DESCRIPTOR.oneofs_by_name
    ):
        variante = msg.WhichOneof("tipo")
        if variante:
            sub_msg = getattr(msg, variante)
            if campo_nome in sub_msg.DESCRIPTOR.fields_by_name:
                if caminho.endswith(f".{variante}"):
                    novo_caminho = caminho
                else:
                    novo_caminho = f"{caminho}.{variante}" if caminho else str(variante)
                return sub_msg, novo_caminho
    return msg, caminho


def validar_pertence_ao_croqui(
    model: Any,
    msg: Any,
    campo_nome: str | None = None,
    nome_comando: str = "Comando",
    field_ext: Any = None,
) -> str:
    """
    Valida se a mensagem alvo fornecida (como Message ou str de endereçamento)
    pertence à árvore de dados ativa do croqui.
    Retorna o caminho/alvo canônico resolvido.
    """
    if model is None or msg is None:
        raise ValueError(f"Modelo ou mensagem inválida para o comando {nome_comando}.")

    from editor.models.readonly_proxy import ReadOnlyProxy

    root_raw = (
        model.obter_croqui_readonly()
        if hasattr(model, "obter_croqui_readonly")
        else getattr(model, "croqui", None)
    )
    if isinstance(root_raw, ReadOnlyProxy):
        root_raw = object.__getattribute__(root_raw, "_obj")

    indice_uids = getattr(model, "indice_uids", None) or (
        model.obter_indice_uids() if hasattr(model, "obter_indice_uids") else None
    )

    if isinstance(msg, str):
        alvo_str = msg.strip()
        if not alvo_str or alvo_str in ("root", "node:root"):
            caminho = ""
            msg_raw = root_raw
        else:
            msg_raw = navegar_para_alvo(root_raw, alvo_str, indice_uids)
            if msg_raw is None:
                raise ValueError(
                    f"Mensagem alvo '{alvo_str}' não encontrada na árvore ativa do croqui "
                    f"para o comando {nome_comando}."
                )
            caminho = alvo_str
    else:
        msg_raw = msg
        if isinstance(msg_raw, ReadOnlyProxy):
            msg_raw = object.__getattribute__(msg_raw, "_obj")

        if root_raw is not None and msg_raw is root_raw:
            caminho = ""
        elif root_raw is not None:
            caminho = resolver_alvo_mensagem(root_raw, msg_raw, indice_uids)
            if not caminho and (not hasattr(root_raw, "ListFields") or len(root_raw.ListFields()) > 0):
                raise ValueError(
                    f"Mensagem alvo órfã detectada para o comando {nome_comando}: "
                    f"a mensagem do tipo '{type(msg_raw).__name__}' não pertence à árvore ativa do croqui."
                )
        else:
            caminho = ""

    msg_raw, caminho = _ajustar_submensagem_variante_se_necessario(msg_raw, caminho, campo_nome)

    if campo_nome and msg_raw is not None and hasattr(msg_raw, "DESCRIPTOR"):
        if "." in campo_nome:
            parte_campo = campo_nome.split(".", 1)[0]
            if parte_campo not in msg_raw.DESCRIPTOR.fields_by_name:
                raise ValueError(
                    f"Campo '{campo_nome}' não existe na mensagem '{msg_raw.DESCRIPTOR.name}' "
                    f"para o comando {nome_comando}."
                )
        else:
            has_field = campo_nome in msg_raw.DESCRIPTOR.fields_by_name
            has_oneof = campo_nome in msg_raw.DESCRIPTOR.oneofs_by_name
            from aresta_api.proto.generated import croqui_pb2

            has_ext = (
                field_ext is not None
                or campo_nome.startswith("ext_")
                or hasattr(type(msg_raw), campo_nome)
                or hasattr(croqui_pb2, campo_nome)
            )
            if not (has_field or has_oneof or has_ext):
                raise ValueError(
                    f"Campo '{campo_nome}' não existe na mensagem '{msg_raw.DESCRIPTOR.name}' "
                    f"para o comando {nome_comando}."
                )

    return caminho


def _validar_campo_se_msg_existir(
    model: Any,
    caminho_msg: str | None,
    campo_nome: str | None,
    nome_comando: str = "Comando",
    field_ext: Any = None,
) -> None:
    """
    Valida a existência do campo no descriptor se a mensagem puder ser resolvida no modelo.
    Se a mensagem não existir no modelo (lazy resolution), não levanta erro prematuro.
    """
    if model is None or caminho_msg is None or not campo_nome:
        return
    root = (
        model.obter_croqui_readonly()
        if hasattr(model, "obter_croqui_readonly")
        else getattr(model, "croqui", None)
    )
    indice_uids = getattr(model, "indice_uids", None)
    msg_alvo = navegar_para_alvo(root, caminho_msg, indice_uids)
    if msg_alvo is not None and hasattr(msg_alvo, "DESCRIPTOR"):
        if "." in campo_nome:
            parte_campo = campo_nome.split(".", 1)[0]
            if parte_campo not in msg_alvo.DESCRIPTOR.fields_by_name:
                raise ValueError(
                    f"Campo '{campo_nome}' não existe na mensagem '{msg_alvo.DESCRIPTOR.name}' "
                    f"para o comando {nome_comando}."
                )
        else:
            has_field = campo_nome in msg_alvo.DESCRIPTOR.fields_by_name
            has_oneof = campo_nome in msg_alvo.DESCRIPTOR.oneofs_by_name
            from aresta_api.proto.generated import croqui_pb2

            has_ext = (
                field_ext is not None
                or campo_nome.startswith("ext_")
                or hasattr(type(msg_alvo), campo_nome)
                or hasattr(croqui_pb2, campo_nome)
            )
            if not (has_field or has_oneof or has_ext):
                raise ValueError(
                    f"Campo '{campo_nome}' não existe na mensagem '{msg_alvo.DESCRIPTOR.name}' "
                    f"para o comando {nome_comando}."
                )


def _serializar_valor(valor: Any, anonimizado: bool = False) -> Any:
    """Serializa tipos primitivos ou instâncias Protobuf Message para representação de dicionário."""
    if isinstance(valor, Message):
        return {"__tipo_protobuf__": type(valor).__name__, "__bytes__": valor.SerializeToString()}
    return valor


def _deserializar_valor(valor_serializado: Any, model: CroquiModel | None = None) -> Any:
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

    def __init__(self, parent: QUndoCommand | None = None) -> None:
        if parent is not None:
            super().__init__(parent)
        else:
            super().__init__()
        self._ignorar_primeiro_redo: bool = False
        self._caminho_msg: str | None = None
        self._msg_cache: Any = None

    @property
    def caminho_msg(self) -> str | None:
        return self._caminho_msg

    @caminho_msg.setter
    def caminho_msg(self, valor: str | None) -> None:
        self._caminho_msg = valor

    @property
    def alvo(self) -> str | None:
        """Alias para caminho_msg, compatível com a terminologia canônica de alvos."""
        return self._caminho_msg

    @alvo.setter
    def alvo(self, valor: str | None) -> None:
        self._caminho_msg = valor

    def _obter_msg(self, levantar_se_nao_encontrado: bool = False) -> Any:
        """
        Resolve a mensagem alvo atual na árvore do modelo a partir de caminho_msg.
        Se _msg_cache já estiver definido, retorna-o diretamente sem navegar novamente.
        Se caminho_msg não estiver definido, retorna _msg_cache.
        Se não for possível encontrar a mensagem alvo:
        - Levanta MensagemAlvoNaoEncontradaError se levantar_se_nao_encontrado for True.
        - Registra logger.error e retorna None se levantar_se_nao_encontrado for False.
        """
        if self._msg_cache is not None:
            return self._msg_cache

        model = getattr(self, "model", None)
        if model is None:
            return self._msg_cache

        if self._caminho_msg is None:
            return self._msg_cache

        root = (
            model.obter_croqui_readonly()
            if hasattr(model, "obter_croqui_readonly")
            else getattr(model, "croqui", None)
        )
        indice_uids = getattr(model, "indice_uids", None)
        alvo = navegar_para_alvo(root, self._caminho_msg, indice_uids)
        if alvo is None:
            if levantar_se_nao_encontrado:
                raise MensagemAlvoNaoEncontradaError(
                    f"Mensagem alvo não encontrada no caminho '{self._caminho_msg}' "
                    f"para o comando {type(self).__name__}."
                )
            logger.error(
                "Falha ao resolver mensagem alvo no caminho '%s' para o comando %s",
                self._caminho_msg,
                type(self).__name__,
            )
            return None

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

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        """Serializa o comando para dicionário. Subclasses devem sobrescrever."""
        raise NotImplementedError


_VALOR_OMITIDO = object()


def _eh_campo_repeated(field_desc: Any) -> bool:
    """Retorna True se o descritor de campo Protobuf representa uma coleção repeated."""
    return bool(
        getattr(field_desc, "label", None) == 3 or getattr(field_desc, "is_repeated", False)
    )


def _validar_tipo_valor_campo(field_desc: Any, valor: Any, nome_campo: str) -> None:
    """Valida se `valor` é compatível com o `FieldDescriptor` do Protobuf antes de empilhar no histórico."""
    if valor is None:
        return
    if getattr(field_desc, "message_type", None) is not None:
        valor_raw = getattr(valor, "_obj", valor)
        if (
            not isinstance(valor_raw, Message)
            or valor_raw.DESCRIPTOR.full_name != field_desc.message_type.full_name
        ):
            raise TypeError(
                f"Valor inválido para o campo '{nome_campo}': esperado mensagem "
                f"'{field_desc.message_type.name}', recebido '{type(valor).__name__}'."
            )
    elif getattr(field_desc, "enum_type", None) is not None:
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise TypeError(
                f"Valor inválido para o campo '{nome_campo}': esperado inteiro de enum "
                f"'{field_desc.enum_type.name}', recebido '{type(valor).__name__}'."
            )
        if valor not in field_desc.enum_type.values_by_number:
            opcoes = ", ".join(f"{v.name}={v.number}" for v in field_desc.enum_type.values)
            raise ValueError(
                f"Valor de enum inválido ({valor}) para '{nome_campo}' "
                f"({field_desc.enum_type.name}). Valores válidos: {opcoes}."
            )
    elif getattr(field_desc, "type", None) == 9:
        if not isinstance(valor, str):
            raise TypeError(
                f"Valor inválido para o campo '{nome_campo}': esperado string, "
                f"recebido '{type(valor).__name__}'."
            )
    elif getattr(field_desc, "type", None) == 8:
        if not isinstance(valor, bool):
            raise TypeError(
                f"Valor inválido para o campo '{nome_campo}': esperado booleano, "
                f"recebido '{type(valor).__name__}'."
            )
    else:
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise TypeError(
                f"Valor inválido para o campo '{nome_campo}': esperado inteiro, "
                f"recebido '{type(valor).__name__}'."
            )



class CmdAlterarCampo(ComandoEditor):
    """
    Comando unificado canônico para alterar qualquer campo singular no Protobuf via Model.

    Guiado por Introspecção do Protobuf DESCRIPTOR:
    - Campo escalar primitivo: usa model._set_primitivo
    - Item de lista repeated por índice ('campo.0'): usa model._alterar_repeated_item
    - Oneof ('tipo' ou variante direta): usa model._alterar_oneof
    - Submensagem singular (TYPE_MESSAGE): usa model._set_primitivo com CopyFrom ou ClearField
    - Extensão de Metadados: usa model._alterar_metadados_caminho_novo
    """

    ID_COMANDO = 1001

    def __init__(
        self,
        model: Any,
        alvo: Any = None,
        campo_nome: str = "",
        valor_novo: Any = None,
        valor_antigo: Any = _VALOR_OMITIDO,
        context_path: str | None = None,
        pode_mesclar: bool = False,
        session_id: int | str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
        field_ext: Any = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar or (session_id is not None)
        self.session_id: str | None = session_id

        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model,
                self.caminho_msg,
                self.campo_nome,
                "CmdAlterarCampo",
                field_ext=field_ext,
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model,
                alvo,
                self.campo_nome,
                nome_comando="CmdAlterarCampo",
                field_ext=field_ext,
            )
            if not isinstance(alvo, str):
                self._msg_cache = alvo

        # Inferência de modalidade e metadados via DESCRIPTOR
        msg_alvo = self._obter_msg()
        if msg_alvo is not None and hasattr(msg_alvo, "DESCRIPTOR"):
            msg_ajustada, novo_caminho = _ajustar_submensagem_variante_se_necessario(
                msg_alvo, self.caminho_msg or "", self.campo_nome
            )
            if novo_caminho != self.caminho_msg or msg_ajustada is not msg_alvo:
                self.caminho_msg = novo_caminho
                self._msg_cache = msg_ajustada
                msg_alvo = msg_ajustada
        self.modalidade: str = "primitivo"
        self._nome_campo_base: str = campo_nome
        self._indice_repeated: int = -1
        self._nome_oneof: str = ""
        self._var_antiga: str | None = None
        self._var_nova: str | None = None
        self._valor_variante_antiga: Any = None
        self._valor_variante_nova: Any = None
        self._field_ext: Any = None

        if "." in campo_nome and not campo_nome.startswith("ext_"):
            partes = campo_nome.split(".", 1)
            if not partes[1].isdigit():
                raise ValueError(
                    f"Índice inválido em '{campo_nome}': esperado '<campo>.<indice_inteiro>'."
                )
            self.modalidade = "repeated_item"
            self._nome_campo_base = partes[0]
            self._indice_repeated = int(partes[1])
            if msg_alvo is not None and hasattr(msg_alvo, "DESCRIPTOR"):
                field_desc = msg_alvo.DESCRIPTOR.fields_by_name.get(self._nome_campo_base)
                if field_desc is not None:
                    if not _eh_campo_repeated(field_desc):
                        raise ValueError(
                            f"O campo '{self._nome_campo_base}' em '{msg_alvo.DESCRIPTOR.name}' "
                            f"não é uma lista (repeated) e não aceita índice '{campo_nome}'."
                        )
                    _validar_tipo_valor_campo(field_desc, valor_novo, campo_nome)
                if valor_antigo is _VALOR_OMITIDO:
                    colecao = getattr(msg_alvo, self._nome_campo_base, [])
                    if 0 <= self._indice_repeated < len(colecao):
                        valor_antigo = colecao[self._indice_repeated]
                    else:
                        valor_antigo = None
        elif msg_alvo is not None and hasattr(msg_alvo, "DESCRIPTOR"):
            desc = msg_alvo.DESCRIPTOR
            if campo_nome in desc.oneofs_by_name:
                self.modalidade = "oneof"
                self._nome_oneof = campo_nome
                self._var_antiga = msg_alvo.WhichOneof(campo_nome)
                if self._var_antiga:
                    self._valor_variante_antiga = getattr(msg_alvo, self._var_antiga)
                if isinstance(valor_novo, tuple) and len(valor_novo) == 2:
                    self._var_nova, self._valor_variante_nova = valor_novo
                    if self._var_nova is not None:
                        field_var = desc.fields_by_name.get(self._var_nova)
                        if (
                            field_var is None
                            or getattr(field_var.containing_oneof, "name", None) != campo_nome
                        ):
                            raise ValueError(
                                f"A variante '{self._var_nova}' não pertence ao oneof "
                                f"'{campo_nome}' em '{desc.name}'."
                            )
                        _validar_tipo_valor_campo(
                            field_var, self._valor_variante_nova, self._var_nova
                        )
                elif valor_novo is None:
                    self._var_nova = None
                    self._valor_variante_nova = None
                else:
                    raise TypeError(
                        f"Valor inválido para o oneof '{campo_nome}': esperado tupla "
                        f"(nome_variante, mensagem) ou None, recebido '{type(valor_novo).__name__}'."
                    )
            elif campo_nome in desc.fields_by_name:
                field_desc = desc.fields_by_name[campo_nome]
                if _eh_campo_repeated(field_desc):
                    raise ValueError(
                        f"O campo '{campo_nome}' em '{desc.name}' é uma lista (repeated). "
                        f"Use '{campo_nome}.<indice>' para alterar um item específico ou "
                        f"CmdAdicionarRepeated / CmdRemoverRepeated para modificar a coleção."
                    )
                _validar_tipo_valor_campo(field_desc, valor_novo, campo_nome)
                if field_desc.containing_oneof:
                    self.modalidade = "oneof"
                    self._nome_oneof = field_desc.containing_oneof.name
                    self._var_antiga = msg_alvo.WhichOneof(self._nome_oneof)
                    if self._var_antiga:
                        self._valor_variante_antiga = getattr(msg_alvo, self._var_antiga)
                    if valor_novo is not None:
                        self._var_nova = campo_nome
                        self._valor_variante_nova = valor_novo
                    else:
                        self._var_nova = None
                        self._valor_variante_nova = None
                elif getattr(field_desc, "type", None) == 11:
                    self.modalidade = "submensagem"
                    if valor_antigo is _VALOR_OMITIDO:
                        if msg_alvo.HasField(campo_nome):
                            valor_antigo = getattr(msg_alvo, campo_nome)
                        else:
                            valor_antigo = None
                else:
                    self.modalidade = "primitivo"
                    if valor_antigo is _VALOR_OMITIDO:
                        valor_antigo = (
                            getattr(msg_alvo, campo_nome)
                            if msg_alvo.HasField(campo_nome)
                            else None
                        )
            elif field_ext is not None or campo_nome.startswith("ext_") or hasattr(type(getattr(msg_alvo, "_obj", msg_alvo)), campo_nome):
                from aresta_api.proto.generated import croqui_pb2

                self.modalidade = "extensao"
                raw_cls = type(getattr(msg_alvo, "_obj", msg_alvo))
                self._field_ext = field_ext or getattr(raw_cls, campo_nome, getattr(croqui_pb2, campo_nome, None))
                if valor_antigo is _VALOR_OMITIDO:
                    raw_msg = getattr(msg_alvo, "_obj", msg_alvo)
                    if self._field_ext is not None and raw_msg.HasExtension(self._field_ext):
                        ext = raw_msg.Extensions[self._field_ext]
                        valor_antigo = getattr(ext, "caminho_novo", "")
                    else:
                        valor_antigo = ""

        if valor_antigo is _VALOR_OMITIDO:
            valor_antigo = None

        garantir_uids_em_mensagem(valor_novo)
        garantir_uids_em_mensagem(self._valor_variante_nova)
        self._valor_variante_antiga = _copia_segura(self._valor_variante_antiga)
        self._valor_variante_nova = _copia_segura(self._valor_variante_nova)
        self.valor_antigo: Any = _copia_segura(valor_antigo)
        self.valor_novo: Any = _copia_segura(valor_novo)

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarCampo):
            return False
        if (
            self.caminho_msg == outro.caminho_msg
            and self.campo_nome == outro.campo_nome
            and self.session_id == outro.session_id
        ):
            msg = self.msg
            if msg is None:
                return False
            self.valor_novo = outro.valor_novo
            if hasattr(outro, "context_path") and outro.context_path:
                self.context_path = outro.context_path
            self._aplicar_mutacao(self.valor_novo, eh_redo=True)
            return True
        return False

    def _aplicar_mutacao(self, valor: Any, eh_redo: bool = True) -> None:
        msg = self.msg
        if msg is None:
            return

        if self.modalidade in ("primitivo", "submensagem"):
            self.model._set_primitivo(msg, self.campo_nome, valor)
        elif self.modalidade == "repeated_item":
            self.model._alterar_repeated_item(
                msg, self._nome_campo_base, self._indice_repeated, valor
            )
        elif self.modalidade == "oneof":
            if eh_redo:
                self.model._alterar_oneof(
                    msg,
                    self._nome_oneof,
                    self._var_antiga,
                    self._var_nova,
                    self._valor_variante_nova,
                )
            else:
                self.model._alterar_oneof(
                    msg,
                    self._nome_oneof,
                    self._var_nova,
                    self._var_antiga,
                    self._valor_variante_antiga,
                )
        elif self.modalidade == "extensao":
            if self._field_ext is not None:
                self.model._alterar_metadados_caminho_novo(msg, self._field_ext, valor)

        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def undo(self) -> None:
        self._aplicar_mutacao(self.valor_antigo, eh_redo=False)

    def executar_redo(self) -> None:
        self._aplicar_mutacao(self.valor_novo, eh_redo=True)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAlterarCampo",
            "caminho_msg": self.caminho_msg,
            "campo_nome": self.campo_nome,
            "valor_antigo": _serializar_valor(self.valor_antigo, anonimizado=anonimizado),
            "valor_novo": _serializar_valor(self.valor_novo, anonimizado=anonimizado),
            "context_path": self.context_path,
            "pode_mesclar": self.pode_mesclar,
            "session_id": self.session_id,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarCampo":
        valor_antigo = _deserializar_valor(dados.get("valor_antigo"), model=model)
        valor_novo = _deserializar_valor(dados.get("valor_novo"), model=model)
        return CmdAlterarCampo(
            model=model,
            caminho_msg=dados.get("caminho_msg") or dados.get("alvo") or "",
            campo_nome=dados.get("campo_nome", ""),
            valor_novo=valor_novo,
            valor_antigo=valor_antigo,
            context_path=dados.get("context_path"),
            pode_mesclar=dados.get("pode_mesclar", False),
            session_id=dados.get("session_id"),
        )


class CmdAlterarImagem(ComandoEditor):
    """
    Comando canônico para adicionar, substituir ou remover bytes de imagem (.webp) em memória RAM via CroquiModel.
    """

    ID_COMANDO = 1003

    def __init__(
        self,
        model: Any,
        nome_arquivo: str = "",
        bytes_novos: bytes | None = None,
        bytes_antigos: bytes | None = _VALOR_OMITIDO,  # type: ignore[assignment]
        context_path: str | None = None,
        pode_mesclar: bool = False,
        parent: QUndoCommand | None = None,
        caminho_relativo: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        arquivo_efetivo = nome_arquivo or caminho_relativo or ""
        self.nome_arquivo: str = str(arquivo_efetivo).replace("\\", "/")
        if bytes_antigos is _VALOR_OMITIDO:
            bytes_antigos = self.model.obter_bytes_imagem(self.nome_arquivo)
        self.bytes_antigos: bytes | None = bytes_antigos
        self.bytes_novos: bytes | None = bytes_novos
        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarImagem):
            return False
        if self.nome_arquivo == outro.nome_arquivo:
            self.bytes_novos = outro.bytes_novos
            if hasattr(outro, "context_path") and outro.context_path:
                self.context_path = outro.context_path
            self._aplicar(self.bytes_novos)
            return True
        return False

    def _aplicar(self, dados: bytes | None) -> None:
        if dados is not None:
            self.model.definir_imagem_memoria(self.nome_arquivo, dados)
        else:
            self.model.remover_imagem_memoria(self.nome_arquivo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def undo(self) -> None:
        self._aplicar(self.bytes_antigos)

    def executar_redo(self) -> None:
        self._aplicar(self.bytes_novos)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        bytes_ant = self.bytes_antigos
        bytes_nov = self.bytes_novos
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado

            if bytes_ant is not None:
                bytes_ant = gerar_webp_anonimizado(bytes_ant)
            if bytes_nov is not None:
                bytes_nov = gerar_webp_anonimizado(bytes_nov)

        return {
            "classe": "CmdAlterarImagem",
            "nome_arquivo": self.nome_arquivo,
            "bytes_antigos": bytes_ant,
            "bytes_novos": bytes_nov,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarImagem":
        return CmdAlterarImagem(
            model=model,
            nome_arquivo=dados["nome_arquivo"],
            bytes_novos=dados.get("bytes_novos"),
            bytes_antigos=dados.get("bytes_antigos"),
            context_path=dados.get("context_path"),
        )


class CmdAlterarAnexo(ComandoEditor):
    """
    Comando canônico para adicionar, substituir ou remover bytes de documentos anexos em memória RAM via CroquiModel.
    """

    ID_COMANDO = 1004

    def __init__(
        self,
        model: Any,
        nome_arquivo: str = "",
        bytes_novos: bytes | None = None,
        bytes_antigos: bytes | None = _VALOR_OMITIDO,  # type: ignore[assignment]
        context_path: str | None = None,
        pode_mesclar: bool = False,
        parent: QUndoCommand | None = None,
        caminho_relativo: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        arquivo_efetivo = nome_arquivo or caminho_relativo or ""
        self.nome_arquivo: str = str(arquivo_efetivo).replace("\\", "/")
        if bytes_antigos is _VALOR_OMITIDO:
            bytes_antigos = self.model.obter_bytes_anexo(self.nome_arquivo)
        self.bytes_antigos: bytes | None = bytes_antigos
        self.bytes_novos: bytes | None = bytes_novos
        self.context_path: str | None = context_path
        self.pode_mesclar: bool = pode_mesclar

    def id(self) -> int:
        return self.ID_COMANDO if self.pode_mesclar else -1

    def mergeWith(self, outro: QUndoCommand) -> bool:
        if not self.pode_mesclar or not getattr(outro, "pode_mesclar", False):
            return False
        if not isinstance(outro, CmdAlterarAnexo):
            return False
        if self.nome_arquivo == outro.nome_arquivo:
            self.bytes_novos = outro.bytes_novos
            if hasattr(outro, "context_path") and outro.context_path:
                self.context_path = outro.context_path
            self._aplicar(self.bytes_novos)
            return True
        return False

    def _aplicar(self, dados: bytes | None) -> None:
        if dados is not None:
            self.model.definir_anexo_memoria(self.nome_arquivo, dados)
        else:
            self.model.remover_anexo_memoria(self.nome_arquivo)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def undo(self) -> None:
        self._aplicar(self.bytes_antigos)

    def executar_redo(self) -> None:
        self._aplicar(self.bytes_novos)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAlterarAnexo",
            "nome_arquivo": self.nome_arquivo,
            "bytes_antigos": self.bytes_antigos,
            "bytes_novos": self.bytes_novos,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAlterarAnexo":
        return CmdAlterarAnexo(
            model=model,
            nome_arquivo=dados["nome_arquivo"],
            bytes_novos=dados.get("bytes_novos"),
            bytes_antigos=dados.get("bytes_antigos"),
            context_path=dados.get("context_path"),
        )


class CmdAdicionarRepeated(ComandoEditor):
    """Comando para adicionar um item em um campo repeated via Model."""

    def __init__(
        self,
        model: Any,
        alvo: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor: Any = None,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
        msg: Any = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        alvo_efetivo = alvo if alvo is not None else msg
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdAdicionarRepeated"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, alvo_efetivo, self.campo_nome, nome_comando="CmdAdicionarRepeated"
            )
            if not isinstance(alvo_efetivo, str):
                self._msg_cache = alvo_efetivo
        self.index: int = index
        garantir_uids_em_mensagem(valor)
        self.valor: Any = _copia_segura(valor)
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._remover_repeated(msg, self.campo_nome, self.index)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._adicionar_repeated(msg, self.campo_nome, self.index, self.valor)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdAdicionarRepeated",
            "caminho_msg": self.caminho_msg,
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor": _serializar_valor(self.valor, anonimizado=anonimizado),
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdAdicionarRepeated":
        valor = _deserializar_valor(dados["valor"], model=model)
        return CmdAdicionarRepeated(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor=valor,
            context_path=dados.get("context_path"),
        )


class CmdRemoverRepeated(ComandoEditor):
    """Comando para remover um item de um campo repeated via Model, limpando imagens em RAM se forem órfãs."""

    def __init__(
        self,
        model: Any,
        alvo: Any = None,
        campo_nome: str = "",
        index: int = 0,
        valor_removido: Any = None,
        context_path: str | None = None,
        imagens_removidas_ram: dict[str, bytes] | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
        msg: Any = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        alvo_efetivo = alvo if alvo is not None else msg
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdRemoverRepeated"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, alvo_efetivo, self.campo_nome, nome_comando="CmdRemoverRepeated"
            )
            if not isinstance(alvo_efetivo, str):
                self._msg_cache = alvo_efetivo
        self.index: int = index
        if valor_removido is None:
            msg_alvo = self._obter_msg()
            if msg_alvo is not None:
                container = getattr(msg_alvo, self.campo_nome, None)
                if container is not None and 0 <= index < len(container):
                    valor_removido = container[index]
        self.valor_removido: Any = _copia_segura(valor_removido)
        self.context_path: str | None = context_path

        if imagens_removidas_ram is not None:
            self.imagens_removidas_ram: dict[str, bytes] = dict(imagens_removidas_ram)
        else:
            self.imagens_removidas_ram = {}
            if hasattr(self.model, "obter_imagens_em_memoria") and hasattr(
                self.model, "obter_croqui_readonly"
            ):
                imagens_ram = self.model.obter_imagens_em_memoria()
                if imagens_ram:
                    from editor.core.imagens_croqui import obter_imagens_orfas_ao_remover

                    croqui_raiz = self.model.obter_croqui_readonly()
                    orfas = obter_imagens_orfas_ao_remover(
                        croqui_raiz, self.valor_removido, imagens_ram
                    )
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
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._remover_repeated(msg, self.campo_nome, self.index)
        for caminho in self.imagens_removidas_ram:
            self.model.remover_imagem_memoria(caminho)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        imagens_removidas_ram = self.imagens_removidas_ram
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado

            imagens_removidas_ram = {
                c: gerar_webp_anonimizado(b) for c, b in self.imagens_removidas_ram.items()
            }

        return {
            "classe": "CmdRemoverRepeated",
            "caminho_msg": self.caminho_msg,
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor_removido": _serializar_valor(self.valor_removido, anonimizado=anonimizado),
            "imagens_removidas_ram": imagens_removidas_ram,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdRemoverRepeated":
        valor_removido = _deserializar_valor(dados["valor_removido"], model=model)
        return CmdRemoverRepeated(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor_removido=valor_removido,
            context_path=dados.get("context_path"),
            imagens_removidas_ram=dados.get("imagens_removidas_ram"),
        )


class CmdMoverRepeated(ComandoEditor):
    """Comando para mover um item de uma coleção repeated para outra posição via Model."""

    def __init__(
        self,
        model: Any,
        alvo: Any = None,
        campo_nome: str = "",
        index_from: int = 0,
        index_to: int = 0,
        context_path: str | None = None,
        caminho_msg: str | None = None,
        parent: QUndoCommand | None = None,
        msg: Any = None,
    ) -> None:
        super().__init__(parent)
        self.model: Any = model
        self.campo_nome: str = campo_nome
        alvo_efetivo = alvo if alvo is not None else msg
        if caminho_msg is not None:
            self.caminho_msg = caminho_msg
            _validar_campo_se_msg_existir(
                self.model, self.caminho_msg, self.campo_nome, "CmdMoverRepeated"
            )
        else:
            self.caminho_msg = validar_pertence_ao_croqui(
                self.model, alvo_efetivo, self.campo_nome, nome_comando="CmdMoverRepeated"
            )
            if not isinstance(alvo_efetivo, str):
                self._msg_cache = alvo_efetivo
        self.index_from: int = index_from
        self.index_to: int = index_to
        self.context_path: str | None = context_path

    def undo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._mover_repeated(msg, self.campo_nome, self.index_to, self.index_from)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def executar_redo(self) -> None:
        msg = self.msg
        if msg is None:
            return
        self.model._mover_repeated(msg, self.campo_nome, self.index_from, self.index_to)
        if hasattr(self, "context_path") and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        return {
            "classe": "CmdMoverRepeated",
            "caminho_msg": self.caminho_msg,
            "campo_nome": self.campo_nome,
            "index_from": self.index_from,
            "index_to": self.index_to,
            "context_path": self.context_path,
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdMoverRepeated":
        return CmdMoverRepeated(
            model=model,
            caminho_msg=dados.get("caminho_msg", ""),
            campo_nome=dados["campo_nome"],
            index_from=dados["index_from"],
            index_to=dados["index_to"],
            context_path=dados.get("context_path"),
        )


class CmdMacro(ComandoEditor):
    """
    Comando composto que agrupa uma sequência ordenada de comandos derivados de ComandoEditor.
    Garante execução atômica de Redo e Undo, serialização completa para o GerenciadorDiario
    e propagação de armar_carregamento_silencioso para todos os subcomandos.
    """

    def __init__(
        self,
        comandos: list[ComandoEditor] | None = None,
        texto: str = "Macro",
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(parent)
        self.comandos: list[ComandoEditor] = list(comandos) if comandos else []
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

    def serializar(self, anonimizado: bool = False) -> dict[str, Any]:
        """Serializa o macro e recursivamente todos os seus subcomandos."""
        return {
            "classe": "CmdMacro",
            "texto": self.text(),
            "comandos": [cmd.serializar(anonimizado=anonimizado) for cmd in self.comandos],
        }

    @staticmethod
    def deserializar(dados: dict[str, Any], model: CroquiModel) -> "CmdMacro":
        """Reconstrói o macro e todos os seus subcomandos via deserializar_comando."""
        comandos_reconstruidos = [deserializar_comando(c, model) for c in dados.get("comandos", [])]
        return CmdMacro(comandos=comandos_reconstruidos, texto=dados.get("texto", "Macro"))


def deserializar_comando(dados: dict[str, Any], model: CroquiModel) -> ComandoEditor:
    """Factory global para deserializar qualquer ComandoEditor a partir de seu dicionário serializado."""
    classe_nome = dados.get("classe")
    mapa_canonicos: dict[str, type[ComandoEditor]] = {
        "CmdAlterarCampo": CmdAlterarCampo,
        "CmdAlterarImagem": CmdAlterarImagem,
        "CmdAlterarAnexo": CmdAlterarAnexo,
        "CmdAdicionarRepeated": CmdAdicionarRepeated,
        "CmdRemoverRepeated": CmdRemoverRepeated,
        "CmdMoverRepeated": CmdMoverRepeated,
        "CmdMacro": CmdMacro,
    }

    if classe_nome in mapa_canonicos:
        return mapa_canonicos[classe_nome].deserializar(dados, model)  # type: ignore[no-any-return]

    from editor.commands.comandos_legados import COMANDOS_LEGADOS_MAP

    if classe_nome in COMANDOS_LEGADOS_MAP:
        return COMANDOS_LEGADOS_MAP[classe_nome].deserializar(dados, model)  # type: ignore[no-any-return]

    raise ValueError(f"Classe de comando desconhecida para deserialização: {classe_nome}")
