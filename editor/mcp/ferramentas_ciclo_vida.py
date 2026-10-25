# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Callable
from typing import Any

from editor.core.storage import GerenciadorCaminhos
from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel
from scripts.deploy_generated import (
    persistir_contexto_memoria_no_disco,
    usar_contexto_memoria_deploy,
)


def _obter_pilha_qt(undo_stack: Any) -> Any:
    if hasattr(undo_stack, "obter_pilha"):
        return undo_stack.obter_pilha()
    return undo_stack


def _executar_salvamento_e_compilacao(
    model: CroquiModel,
    undo_stack: Any,
    workspace: Any,
    storage: GerenciadorCaminhos | None = None,
) -> dict[str, Any]:
    """
    Executa a extração e serialização do CroquiModel em memória RAM, compila via
    workspace e persiste os arquivos finais no disco.
    """
    if workspace is None:
        raise ValueError("Nenhum workspace configurado para salvar ou compilar o croqui.")

    caminho_db = workspace.obter_caminho_database()
    cache_md: dict[str, tuple[dict[str, Any] | None, str]] = {}
    corpos_brutos_md: dict[str, str] = {}

    croqui_data = model.extrair_arquivos_e_serializar(
        caminho_db,
        cache_md_out=cache_md,
        corpos_brutos_md_out=corpos_brutos_md,
        persistir_no_disco=False,
    )

    novo_id = str(croqui_data.get("id", ""))
    nome_raiz = workspace.caminho_raiz.name
    partes = nome_raiz.split("_", 1)
    id_atual = partes[1] if len(partes) > 1 and partes[0].isdigit() else nome_raiz

    with usar_contexto_memoria_deploy(
        [caminho_db],
        croqui_data,
        cache_md=cache_md,
        corpos_brutos_md=corpos_brutos_md,
    ) as ctx_deploy:
        caminho_retornado, mensagens, database_modificado = (
            workspace.processar_renomeacao_e_compilacao(novo_id, id_atual, storage)
        )
        if not ctx_deploy.persistido_no_disco:
            persistir_contexto_memoria_no_disco(caminho_db, ctx_deploy)

    pilha = _obter_pilha_qt(undo_stack)
    pilha.setClean()

    return {
        "status": "ok",
        "caminho": str(caminho_retornado),
        "mensagens": list(mensagens),
        "database_modificado": bool(database_modificado),
    }


def registrar_ferramentas_ciclo_vida(
    servidor: ServidorMCP,
    model: CroquiModel,
    undo_stack: Any,
    workspace: Any | None = None,
    storage: GerenciadorCaminhos | None = None,
    callback_foco: Callable[[str, str], None] | None = None,
) -> None:
    """
    Registra no `ServidorMCP` as ferramentas de ciclo de vida e workspace:
    `aresta_compilar`, `aresta_salvar`, `aresta_desfazer`, `aresta_refazer`,
    `aresta_focar_elemento` e `aresta_status_workspace`.
    """

    def _status_historico() -> dict[str, Any]:
        pilha = _obter_pilha_qt(undo_stack)
        return {
            "status": "ok",
            "indice_historico": int(pilha.index()),
            "total_comandos": int(pilha.count()),
            "pode_desfazer": bool(pilha.canUndo()),
            "pode_refazer": bool(pilha.canRedo()),
        }

    def _desfazer(_args: dict[str, Any]) -> dict[str, Any]:
        if hasattr(undo_stack, "desfazer"):
            undo_stack.desfazer()
        else:
            undo_stack.undo()
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return _status_historico()

    def _refazer(_args: dict[str, Any]) -> dict[str, Any]:
        if hasattr(undo_stack, "refazer"):
            undo_stack.refazer()
        else:
            undo_stack.redo()
        model.indice_uids.carregar_do_croqui(model.obter_croqui_readonly())
        return _status_historico()

    def _focar_elemento(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo") or "")
        pagina = str(args.get("pagina") or "dados")
        _, caminho = resolver_alvo_mcp(model, alvo) if alvo else (None, "")
        uri = f"page:{pagina}/{caminho}" if caminho else f"page:{pagina}"
        model.notificar_foco_requisitado(uri)
        if callback_foco is not None:
            callback_foco(caminho, pagina)
        return {
            "status": "ok",
            "caminho": caminho,
            "pagina": pagina,
            "uri": uri,
        }

    def _status_workspace(_args: dict[str, Any]) -> dict[str, Any]:
        raiz = model.obter_croqui_readonly()
        pilha = _obter_pilha_qt(undo_stack)
        caminho_db = str(workspace.obter_caminho_database()) if workspace is not None else ""
        return {
            "id_croqui": str(getattr(raiz, "id", "")),
            "nome_croqui": str(getattr(raiz, "nome", "")),
            "uid_croqui": str(getattr(raiz, "uid", "")),
            "caminho_database": caminho_db,
            "modificado": not bool(pilha.isClean()),
            "indice_historico": int(pilha.index()),
            "total_comandos": int(pilha.count()),
            "pode_desfazer": bool(pilha.canUndo()),
            "pode_refazer": bool(pilha.canRedo()),
        }

    def _salvar_ou_compilar(_args: dict[str, Any]) -> dict[str, Any]:
        return _executar_salvamento_e_compilacao(model, undo_stack, workspace, storage)

    servidor.registrar_ferramenta(
        nome="aresta_salvar",
        descricao="Salva as alterações em memória para o disco e compila o croqui no workspace ativo.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_salvar_ou_compilar,
    )
    servidor.registrar_ferramenta(
        nome="aresta_compilar",
        descricao="Executa o pipeline de validação e compilação do croqui e retorna a lista de erros ou avisos.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_salvar_ou_compilar,
    )
    servidor.registrar_ferramenta(
        nome="aresta_desfazer",
        descricao="Desfaz (Undo) o último comando ou macro na pilha de histórico do editor.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_desfazer,
    )
    servidor.registrar_ferramenta(
        nome="aresta_refazer",
        descricao="Refaz (Redo) o último comando ou macro desfeito na pilha de histórico do editor.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_refazer,
    )
    servidor.registrar_ferramenta(
        nome="aresta_focar_elemento",
        descricao="Foca e seleciona visualmente um elemento na interface gráfica por UID ou caminho.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string", "description": "UID ou caminho do elemento."},
                "pagina": {
                    "type": "string",
                    "description": "Página da interface: 'dados', 'imagens', 'mapas' ou 'historico'.",
                },
            },
        },
        manipulador=_focar_elemento,
    )
    servidor.registrar_ferramenta(
        nome="aresta_status_workspace",
        descricao="Retorna metadados do workspace ativo, estado de modificação e contadores da pilha de histórico.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_status_workspace,
    )
