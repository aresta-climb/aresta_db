# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any

from editor.commands.comandos_protobuf import (
    MensagemAlvoNaoEncontradaError,
    navegar_para_mensagem,
)
from editor.models.croqui_model import CroquiModel


def _buscar_mensagem_por_uid(
    msg_atual: Any, uid_procurado: str, caminho_atual: str = ""
) -> tuple[Any, str] | None:
    """
    Varre a árvore Protobuf em busca da mensagem com `uid == uid_procurado`
    sem instanciar sub-mensagens opcionais vazias, retornando `(mensagem, caminho_canonico)`.
    """
    if getattr(msg_atual, "uid", "") == uid_procurado:
        return msg_atual, caminho_atual

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
                novo_caminho = f"{caminho}.{variante}" if caminho else str(variante)
                return sub_msg, novo_caminho
    return msg, caminho


def resolver_alvo_mcp(
    model: CroquiModel, alvo: str, campo_nome: str | None = None
) -> tuple[Any, str]:
    """
    Resolve um identificador de alvo MCP híbrido na árvore ativa do `CroquiModel`:
    1. Raiz (`""`, `"root"`, `"node:root"` ou `uid` do `Croqui`).
    2. `UID` direto de 14 caracteres (ou qualquer `uid` cadastrado na árvore).
    3. `<uid>.<subcaminho>` (ex: `"V1StGXR8_Z5jdH.mapas.0"`).
    4. Caminho posicional desde a raiz (ex: `"picos.0"`).

    Retorna `(mensagem_proxy_ou_proto, caminho_canonico)`.
    Lança `MensagemAlvoNaoEncontradaError` caso o alvo não exista.
    """
    raiz_proxy = model.obter_croqui_readonly()
    alvo_limpo = (alvo or "").strip()

    if not alvo_limpo or alvo_limpo in ("root", "node:root"):
        return _ajustar_submensagem_variante_se_necessario(raiz_proxy, "", campo_nome)

    # 1. Tentativa por UID exato na árvore
    if "." not in alvo_limpo:
        achado_uid = _buscar_mensagem_por_uid(raiz_proxy, alvo_limpo)
        if achado_uid is not None:
            msg_uid, cam_uid = achado_uid
            return _ajustar_submensagem_variante_se_necessario(msg_uid, cam_uid, campo_nome)

    # 2. Tentativa híbrida <uid>.<subcaminho>
    if "." in alvo_limpo:
        prefixo_uid, subcaminho = alvo_limpo.split(".", 1)
        achado_base = _buscar_mensagem_por_uid(raiz_proxy, prefixo_uid)
        if achado_base is not None:
            msg_base, cam_base = achado_base
            cam_completo = f"{cam_base}.{subcaminho}" if cam_base else subcaminho
            msg_sub = navegar_para_mensagem(raiz_proxy, cam_completo)
            if (
                msg_sub is None
                and hasattr(msg_base, "DESCRIPTOR")
                and "tipo" in msg_base.DESCRIPTOR.oneofs_by_name
            ):
                variante = msg_base.WhichOneof("tipo")
                if variante:
                    cam_completo = (
                        f"{cam_base}.{variante}.{subcaminho}"
                        if cam_base
                        else f"{variante}.{subcaminho}"
                    )
                    msg_sub = navegar_para_mensagem(raiz_proxy, cam_completo)
            if msg_sub is None:
                raise MensagemAlvoNaoEncontradaError(
                    f"Alvo '{alvo_limpo}' não encontrado na árvore ativa do croqui."
                )
            return _ajustar_submensagem_variante_se_necessario(msg_sub, cam_completo, campo_nome)

    # 3. Tentativa por caminho posicional desde a raiz
    msg_posicional = navegar_para_mensagem(raiz_proxy, alvo_limpo)
    if msg_posicional is not None:
        return _ajustar_submensagem_variante_se_necessario(msg_posicional, alvo_limpo, campo_nome)

    raise MensagemAlvoNaoEncontradaError(
        f"Alvo '{alvo_limpo}' não encontrado na árvore ativa do croqui."
    )
