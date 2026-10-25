# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.core.historico import GerenciadorHistorico
from editor.mcp.despachante import DespachanteQt
from editor.mcp.ferramentas_ciclo_vida import registrar_ferramentas_ciclo_vida
from editor.mcp.servidor import ServidorMCP
from editor.models.croqui_model import CroquiModel


class _WorkspaceFake:
    """Fake determinístico de Workspace para testes comportamentais sem I/O externo."""

    def __init__(self, pasta_raiz: Path) -> None:
        self.caminho_raiz = pasta_raiz
        self.compilacoes = 0

    def obter_caminho_database(self) -> Path:
        caminho = self.caminho_raiz / "database"
        caminho.mkdir(parents=True, exist_ok=True)
        return caminho

    def processar_renomeacao_e_compilacao(self, novo_id: str, id_atual: str, _storage: object):
        self.compilacoes += 1
        return self.caminho_raiz, ["Aviso: teste de compilação"], False


def _chamar(servidor: ServidorMCP, nome: str, argumentos: dict) -> dict:
    resp = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": nome, "arguments": argumentos},
        }
    )
    assert resp is not None
    res = resp["result"]
    if res.get("isError"):
        raise RuntimeError(res["content"][0]["text"])
    return res["structuredContent"]


def test_ciclo_vida_desfazer_refazer_status_foco_e_salvar_compilar(qapp, tmp_path: Path):
    """Valida aresta_status_workspace, aresta_desfazer, aresta_refazer, aresta_focar_elemento, aresta_salvar e aresta_compilar."""
    croqui = croqui_pb2.Croqui(uid="uid_croqui_cv1", id="cipo_teste", nome="Serra do Cipó")
    pico = croqui.picos.add(nome="Pico 1")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    setor.uid = "uid_setor_cv01"
    setor.nome = "Setor Central"

    model = CroquiModel(croqui)
    historico = GerenciadorHistorico()
    controller = CroquiController(model, historico)
    workspace = _WorkspaceFake(tmp_path)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)

    uris_focadas: list[str] = []
    model.foco_requisitado.connect(uris_focadas.append)
    focos_custom: list[tuple[str, str]] = []

    registrar_ferramentas_ciclo_vida(
        servidor=servidor,
        model=model,
        undo_stack=historico,
        workspace=workspace,
        callback_foco=lambda cam, pag: focos_custom.append((cam, pag)),
    )

    # 1. Status inicial limpo
    status_ini = _chamar(servidor, "aresta_status_workspace", {})
    assert status_ini["id_croqui"] == "cipo_teste"
    assert status_ini["modificado"] is False
    assert status_ini["total_comandos"] == 0

    # 2. Mutação via controller -> histórico sujo -> desfazer e refazer via MCP
    raiz = model.obter_croqui_readonly()
    controller.alterar_primitivo(raiz, "nome", "Serra do Cipó", "Cipó Editado")
    status_mod = _chamar(servidor, "aresta_status_workspace", {})
    assert status_mod["modificado"] is True
    assert status_mod["pode_desfazer"] is True

    res_undo = _chamar(servidor, "aresta_desfazer", {})
    assert res_undo["indice_historico"] == 0
    assert raiz.nome == "Serra do Cipó"

    res_redo = _chamar(servidor, "aresta_refazer", {})
    assert res_redo["indice_historico"] == 1
    assert raiz.nome == "Cipó Editado"

    # 3. Focar elemento por UID e na raiz
    res_foco = _chamar(
        servidor,
        "aresta_focar_elemento",
        {"alvo": "uid_setor_cv01", "pagina": "dados"},
    )
    assert res_foco["caminho"] == "picos.0.setores_ou_grupos.0.setor.conteudo"
    assert res_foco["uri"] == "page:dados/picos.0.setores_ou_grupos.0.setor.conteudo"
    assert uris_focadas[-1] == "page:dados/picos.0.setores_ou_grupos.0.setor.conteudo"
    assert focos_custom[-1] == (
        "picos.0.setores_ou_grupos.0.setor.conteudo",
        "dados",
    )

    res_foco_raiz = _chamar(
        servidor,
        "aresta_focar_elemento",
        {"alvo": "", "pagina": "mapas"},
    )
    assert res_foco_raiz["uri"] == "page:mapas"

    # 4. Salvar e compilar no workspace
    res_salvar = _chamar(servidor, "aresta_salvar", {})
    assert res_salvar["status"] == "ok"
    assert workspace.compilacoes == 1
    assert (workspace.obter_caminho_database() / "croqui.yaml").is_file()

    res_compilar = _chamar(servidor, "aresta_compilar", {})
    assert res_compilar["status"] == "ok"
    assert "Aviso: teste de compilação" in res_compilar["mensagens"]
    assert workspace.compilacoes == 2


def test_ciclo_vida_com_qundostack_puro_e_sem_workspace(qapp, tmp_path: Path):
    """Valida operação com QUndoStack direto e erro amigável ao salvar sem workspace configurado."""
    croqui = croqui_pb2.Croqui(uid="uid_croqui_cv2", nome="Teste")
    model = CroquiModel(croqui)
    pilha = QUndoStack()
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)

    registrar_ferramentas_ciclo_vida(
        servidor=servidor,
        model=model,
        undo_stack=pilha,
        workspace=None,
    )

    _chamar(servidor, "aresta_desfazer", {})
    _chamar(servidor, "aresta_refazer", {})

    resp_sem_ws = servidor.processar_mensagem_jsonrpc(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "aresta_salvar", "arguments": {}},
        }
    )
    assert resp_sem_ws is not None
    assert resp_sem_ws["result"]["isError"] is True
