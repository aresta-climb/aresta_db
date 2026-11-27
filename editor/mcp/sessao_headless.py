# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Sessão oficial Headless do Editor Aresta (3ª porta de entrada), permitindo carregar
um croqui de `database/<id>` e operar todo o catálogo MCP em memória ou via `stdio`
sobre `QGuiApplication` (`QT_QPA_PLATFORM=offscreen`), sem instanciar janelas.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

from google.protobuf.json_format import ParseDict
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.controllers.mapas_controller import MapasController
from editor.core.historico import GerenciadorHistorico
from editor.core.serializacao_util import carregar_yaml
from editor.core.storage import GerenciadorCaminhos
from editor.core.workspace import HeadlessWorkspace
from editor.mcp.despachante import DespachanteQt
from editor.mcp.registro_ferramentas import registrar_catalogo_ferramentas_croqui
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel
from scripts.deploy_generated import registrar_snapshot_disco_arquivo
from scripts.migrador import aplicar_migracoes

_APP_QT_HEADLESS: QCoreApplication | None = None


def garantir_aplicacao_qt_headless() -> QCoreApplication:
    """
    Garante uma instância ativa de `QApplication` em modo `QT_QPA_PLATFORM=offscreen`
    (necessária para `QUndoStack` e `QGraphicsScene` de `aresta_renderizar_mapa`),
    mantendo referência global viva e sem instanciar nenhuma janela ou `QWidget`.
    """
    global _APP_QT_HEADLESS
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    inst = QApplication.instance()
    if inst is not None:
        _APP_QT_HEADLESS = inst
        return inst
    _APP_QT_HEADLESS = QApplication([])  # pragma: no cover
    return _APP_QT_HEADLESS  # pragma: no cover


class SessaoEditorHeadless:
    """Encapsula o ciclo de vida completo de um croqui aberto no Editor Aresta em modo Headless."""

    def __init__(
        self,
        *,
        croqui_model: CroquiModel,
        historico: GerenciadorHistorico,
        croqui_controller: CroquiController,
        mapas_controller: MapasController,
        workspace: HeadlessWorkspace,
        servidor_mcp: ServidorMCP,
    ) -> None:
        self.croqui_model = croqui_model
        self.historico = historico
        self.croqui_controller = croqui_controller
        self.mapas_controller = mapas_controller
        self.workspace = workspace
        self.servidor_mcp = servidor_mcp
        self._proximo_id_req = 1

    def __enter__(self) -> SessaoEditorHeadless:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.fechar()

    @property
    def id_croqui(self) -> str:
        """Retorna o identificador atual do croqui carregado."""
        raiz = self.croqui_model.obter_croqui_readonly()
        return str(getattr(raiz, "id", "") or self.workspace.obter_id_croqui_atual())

    @property
    def caminho_database(self) -> Path:
        """Retorna o diretório `database/<id>` ativo da sessão."""
        return self.workspace.obter_caminho_database()

    def obter_caminho_compilado(self) -> Path:
        """Retorna o diretório temporário onde `compilado.binarypb` desta sessão é gerado."""
        return self.workspace.obter_caminho_compilado()

    def fechar(self) -> None:
        """Libera recursos temporários associados ao `HeadlessWorkspace`."""
        self.workspace.fechar()

    def processar_jsonrpc(self, mensagem: dict[str, Any]) -> dict[str, Any] | None:
        """Processa uma mensagem JSON-RPC 2.0 diretamente em memória no `ServidorMCP`."""
        return self.servidor_mcp.processar_mensagem_jsonrpc(mensagem)

    def listar_ferramentas(self) -> list[dict[str, Any]]:
        """Retorna a lista de definições `tools/list` registradas no `ServidorMCP`."""
        resposta = self.processar_jsonrpc(
            {"jsonrpc": "2.0", "id": self._proximo_id_req, "method": "tools/list", "params": {}}
        )
        self._proximo_id_req += 1
        assert resposta is not None
        ferramentas: list[dict[str, Any]] = list(resposta["result"]["tools"])
        return ferramentas

    def chamar_ferramenta(
        self, nome: str, argumentos: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Invoca uma ferramenta MCP em processo (`in-process`) e retorna o dicionário de resultado
        padronizado (`content`, `structuredContent` opcional e `isError`).
        """
        resposta = self.processar_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": self._proximo_id_req,
                "method": "tools/call",
                "params": {"name": nome, "arguments": argumentos or {}},
            }
        )
        self._proximo_id_req += 1
        assert resposta is not None
        if "error" in resposta:
            mensagem_erro = str(resposta["error"].get("message", "Erro MCP desconhecido."))
            return {
                "content": [{"type": "text", "text": mensagem_erro}],
                "isError": True,
            }
        resultado: dict[str, Any] = dict(resposta["result"])
        return resultado


def abrir_editor_headless(
    caminho_croqui: Path | str,
    *,
    diretorio_compilado: Path | None = None,
    diretorio_sessao_mcp: Path | None = None,
    storage: GerenciadorCaminhos | None = None,
    cliente_overpass: Any = None,
) -> SessaoEditorHeadless:
    """
    Abre `database/<id_croqui>` (ou diretamente seu `croqui.yaml`) em uma `SessaoEditorHeadless`
    oficial do Editor Aresta, aplicando migrações e registrando o catálogo completo de ferramentas MCP.
    """
    caminho_resolvido = Path(caminho_croqui).resolve()
    if caminho_resolvido.is_file() and caminho_resolvido.name == "croqui.yaml":
        caminho_db = caminho_resolvido.parent
    else:
        caminho_db = caminho_resolvido

    caminho_yaml = caminho_db / "croqui.yaml"
    if not caminho_yaml.is_file():
        raise FileNotFoundError(
            f"Arquivo croqui.yaml não encontrado para inicialização headless em '{caminho_croqui}'."
        )

    garantir_aplicacao_qt_headless()
    aplicar_migracoes(caminho_db)

    dados_yaml = carregar_yaml(caminho_yaml.read_text(encoding="utf-8"))
    dados_croqui: dict[str, Any] = dados_yaml if isinstance(dados_yaml, dict) else {}
    croqui_msg = ParseDict(dados_croqui, croqui_pb2.Croqui(), ignore_unknown_fields=True)
    croqui_msg.Extensions[
        croqui_pb2.Croqui.ext_metadados_arquivo
    ].dados_json_originais = json.dumps(dados_croqui, ensure_ascii=False)
    registrar_snapshot_disco_arquivo(caminho_yaml, dados_croqui, None)

    croqui_model = CroquiModel(croqui_msg)
    croqui_model.definir_caminho_db(caminho_db)
    croqui_model.carregar_arquivos_externos(caminho_db)

    historico = GerenciadorHistorico()
    croqui_controller = CroquiController(croqui_model, historico)
    workspace = HeadlessWorkspace(caminho_db, diretorio_compilado=diretorio_compilado)
    dir_sessao = diretorio_sessao_mcp or workspace.obter_pasta_servidor_celular()
    servidor_mcp = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=dir_sessao)

    mapas_controller = registrar_catalogo_ferramentas_croqui(
        servidor=servidor_mcp,
        croqui_model=croqui_model,
        croqui_controller=croqui_controller,
        historico=historico,
        workspace=workspace,
        storage=storage,
        cliente_overpass=cliente_overpass,
    )

    id_ativo = str(getattr(croqui_model.obter_croqui_readonly(), "id", "") or caminho_db.name)
    servidor_mcp.definir_croqui_ativo(id_ativo, str(caminho_db), croqui_aberto=True)

    return SessaoEditorHeadless(
        croqui_model=croqui_model,
        historico=historico,
        croqui_controller=croqui_controller,
        mapas_controller=mapas_controller,
        workspace=workspace,
        servidor_mcp=servidor_mcp,
    )


def executar_servidor_stdio_headless(
    sessao: SessaoEditorHeadless,
    entrada: TextIO | None = None,
    saida: TextIO | None = None,
) -> int:
    """
    Executa o loop JSON-RPC 2.0 sobre `stdio` diretamente contra `sessao` em memória,
    sem necessidade de porta TCP ou servidor HTTP.
    """
    fluxo_in = entrada if entrada is not None else sys.stdin
    fluxo_out = saida if saida is not None else sys.stdout

    for linha_bruta in fluxo_in:
        linha = linha_bruta.strip()
        if not linha:
            continue
        try:
            mensagem = json.loads(linha)
        except ValueError:
            fluxo_out.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Erro de sintaxe JSON na entrada stdio.",
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            fluxo_out.flush()
            continue

        resposta = sessao.processar_jsonrpc(mensagem)
        if resposta is not None:
            fluxo_out.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            fluxo_out.flush()

    return 0
