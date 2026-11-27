# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Registro canônico unificado do catálogo completo de ferramentas MCP do Editor Aresta,
compartilhado entre a interface gráfica (Modos Padrão e Local) e o Modo Headless.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QWidget

from editor.controllers.croqui_controller import CroquiController
from editor.controllers.mapas_controller import MapasController
from editor.mcp.ferramentas_betas import registrar_ferramentas_betas
from editor.mcp.ferramentas_ciclo_vida import registrar_ferramentas_ciclo_vida
from editor.mcp.ferramentas_comandos import registrar_ferramentas_comandos
from editor.mcp.ferramentas_conhecimento import registrar_ferramentas_conhecimento
from editor.mcp.ferramentas_visao import registrar_ferramentas_visao
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


def registrar_catalogo_ferramentas_croqui(
    servidor: ServidorMCP,
    croqui_model: CroquiModel,
    croqui_controller: CroquiController,
    historico: Any,
    workspace: Any | None = None,
    storage: Any | None = None,
    provedor_widget_alvo: Callable[[str], QWidget | None] | None = None,
    provedor_selecao_atual: Callable[[], dict[str, Any]] | None = None,
    callback_foco: Callable[[str, str], None] | None = None,
    callback_abrir_croqui: Callable[[Path], dict[str, Any] | None] | None = None,
    cliente_overpass: Any = None,
) -> MapasController:
    """
    Registra em `servidor` todas as ferramentas MCP de comandos, visão/mapas,
    ciclo de vida, conhecimento e curadoria de betas para um croqui carregado.
    """
    mapas_controller = MapasController(croqui_model, historico)
    if workspace is not None and hasattr(workspace, "obter_caminho_database"):
        caminho_db = workspace.obter_caminho_database()
        if caminho_db:
            mapas_controller.set_caminho_db(Path(caminho_db))

    registrar_ferramentas_comandos(
        servidor,
        croqui_controller,
        mapas_controller,
        cliente_overpass=cliente_overpass,
    )
    registrar_ferramentas_visao(
        servidor,
        croqui_model,
        provedor_widget_alvo=provedor_widget_alvo,
        provedor_selecao_atual=provedor_selecao_atual,
    )
    registrar_ferramentas_ciclo_vida(
        servidor,
        croqui_model,
        historico,
        workspace=workspace,
        storage=storage,
        callback_foco=callback_foco,
        callback_abrir_croqui=callback_abrir_croqui,
    )
    registrar_ferramentas_conhecimento(servidor, model=croqui_model)
    registrar_ferramentas_betas(
        servidor,
        croqui_model,
        croqui_controller,
    )
    return mapas_controller
