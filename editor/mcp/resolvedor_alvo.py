# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any

from editor.commands.comandos_protobuf import (
    MensagemAlvoNaoEncontradaError,
    _ajustar_submensagem_variante_se_necessario,
    navegar_para_alvo,
    resolver_caminho_mensagem,
)
from editor.models.croqui_model import CroquiModel


def resolver_alvo_mcp(
    model: CroquiModel, alvo: str, campo_nome: str | None = None
) -> tuple[Any, str]:
    """
    Resolve um identificador de alvo MCP híbrido na árvore ativa do `CroquiModel`
    reutilizando a resolução em 3 níveis de `comandos_protobuf`:
    1. Raiz (`""`, `"root"`, `"node:root"` ou `uid` do `Croqui`).
    2. `UID` direto cadastrado na árvore / `IndiceUidsModel`.
    3. `<uid>.<subcaminho>` (ex: `"V1StGXR8.mapas.0"`).
    4. Caminho posicional desde a raiz (ex: `"picos.0"`).

    Retorna `(mensagem_proto, caminho_canonico)`.
    Lança `MensagemAlvoNaoEncontradaError` caso o alvo não exista.
    """
    raiz_proxy = model.obter_croqui_readonly()
    alvo_limpo = (alvo or "").strip()

    msg = navegar_para_alvo(raiz_proxy, alvo_limpo, model.indice_uids)
    if msg is None:
        raise MensagemAlvoNaoEncontradaError(
            f"Alvo '{alvo_limpo}' não encontrado na árvore ativa do croqui."
        )

    caminho = resolver_caminho_mensagem(raiz_proxy, msg)
    campo_base = (
        campo_nome.split(".", 1)[0]
        if campo_nome and "." in campo_nome and not campo_nome.startswith("ext_")
        else campo_nome
    )
    return _ajustar_submensagem_variante_se_necessario(msg, caminho, campo_base)
