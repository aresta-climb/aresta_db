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


def test_ciclo_vida_status_foco_salvar_compilar_sem_expor_undo_redo(qapp, tmp_path: Path):
    """Valida aresta_status_workspace, aresta_focar_elemento, aresta_salvar, aresta_compilar e ausência de undo/redo."""
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

    # Garante que aresta_desfazer e aresta_refazer NÃO são expostas no catálogo MCP
    resp_list = servidor.processar_mensagem_jsonrpc(
        {"jsonrpc": "2.0", "id": 99, "method": "tools/list", "params": {}}
    )
    nomes_tools = {t["name"] for t in resp_list["result"]["tools"]}
    assert "aresta_desfazer" not in nomes_tools
    assert "aresta_refazer" not in nomes_tools

    # 1. Status inicial limpo
    status_ini = _chamar(servidor, "aresta_status_workspace", {})
    assert status_ini["id_croqui"] == "cipo_teste"
    assert status_ini["modificado"] is False
    assert status_ini["total_comandos"] == 0

    # 2. Mutação via controller -> histórico sujo refletido no status_workspace
    raiz = model.obter_croqui_readonly()
    controller.alterar_primitivo(raiz, "nome", "Serra do Cipó", "Cipó Editado")
    status_mod = _chamar(servidor, "aresta_status_workspace", {})
    assert status_mod["modificado"] is True
    assert status_mod["pode_desfazer"] is True

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

    status_pilha = _chamar(servidor, "aresta_status_workspace", {})
    assert status_pilha["total_comandos"] == 0

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


class _StorageFake:
    """Fake determinístico de GerenciadorCaminhos apontando para diretórios temporários reais."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.exp_dir = base / "croquis_experimentais"
        self.repo_dir = base / "repo_oficial"
        self.exp_dir.mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "database").mkdir(parents=True, exist_ok=True)

    def obter_caminho_croquis_experimentais(self) -> Path:
        return self.exp_dir

    def obter_caminho_base_repo(self) -> Path:
        return self.repo_dir


def test_gestao_croquis_listar_criar_importar_e_abrir(qapp, tmp_path: Path):
    """
    Valida aresta_listar_croquis, aresta_criar_novo_croqui, aresta_importar_croqui_oficial
    e aresta_abrir_croqui_existente funcionando inclusive sem croqui aberto (TelaDeCarregamento).
    """
    import pymupdf

    from editor.mcp.ferramentas_ciclo_vida import registrar_ferramentas_gestao_croquis
    from editor.mcp.sessao import gravar_sessao_mcp
    from scripts.gerenciar_uids_lib import gerar_uid
    from scripts.migrador import obter_ultima_versao_migracao

    storage = _StorageFake(tmp_path)

    # Prepara um croqui oficial mínimo no repositório fake para importação
    pasta_oficial = storage.obter_caminho_base_repo() / "database" / "br_mg_cipo_setor_sol"
    pasta_oficial.mkdir(parents=True, exist_ok=True)
    (pasta_oficial / "croqui.yaml").write_text(
        f"id: br_mg_cipo_setor_sol\nuid: {gerar_uid()}\nnome: Setor do Sol\nultima_migracao: {obter_ultima_versao_migracao()}\npicos:\n  - nome: Serra do Cipó\n    estado: MG\n",
        encoding="utf-8",
    )

    # Cria um PDF temporário para testar cópia automática no criar_novo_croqui
    pdf_origem = tmp_path / "meu_guia.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(pdf_origem))
    doc.close()

    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    servidor.definir_croqui_ativo("", croqui_aberto=False)

    abertos_via_callback: list[Path] = []
    registrar_ferramentas_gestao_croquis(
        servidor=servidor,
        storage=storage,
        usuario="Agente Teste",
        callback_abrir_croqui=lambda p: (
            abertos_via_callback.append(p) or {"janela_aberta": True}
        ),
    )

    # 1. Cria novo croqui com cópia de PDF original (mesmo com croqui_aberto=False)
    res_criado = _chamar(
        servidor,
        "aresta_criar_novo_croqui",
        {
            "nome_pico": "Pedra do Baú",
            "cidade": "São Bento",
            "estado": "SP",
            "pais": "BR",
            "caminho_pdf_original": str(pdf_origem),
        },
    )
    assert res_criado["status"] == "criado"
    assert res_criado["id_croqui"] == "br_sp_sao_bento_pedra_do_bau"
    assert res_criado["janela_aberta"] is True
    caminho_exp_criado = Path(res_criado["caminho"])
    assert (caminho_exp_criado / "database" / "raw_original_pdf" / "croqui_original.pdf").is_file()
    assert len(abertos_via_callback) == 1

    # 2. Importa croqui oficial
    res_imp = _chamar(
        servidor,
        "aresta_importar_croqui_oficial",
        {"id_oficial": "br_mg_cipo_setor_sol", "resumo_edicao": "Atualizar vias via MCP"},
    )
    assert res_imp["status"] == "importado"
    assert res_imp["id_croqui"] == "br_mg_cipo_setor_sol"

    # 3. Lista croquis com e sem filtro
    gravar_sessao_mcp(
        porta=27378,
        diretorio_base=tmp_path,
        id_croqui="br_sp_sao_bento_pedra_do_bau",
        caminho_database=str(caminho_exp_criado / "database"),
    )
    res_lista = _chamar(servidor, "aresta_listar_croquis", {})
    assert len(res_lista["abertos"]) == 1
    assert len(res_lista["experimentais"]) == 2
    assert len(res_lista["oficiais"]) == 1

    res_filtrado = _chamar(servidor, "aresta_listar_croquis", {"filtro": "baú"})
    assert len(res_filtrado["experimentais"]) == 1
    assert res_filtrado["oficiais"] == []

    # 4. Abrir croqui já aberto retorna status 'ja_aberto'
    res_ja_aberto = _chamar(
        servidor,
        "aresta_abrir_croqui_existente",
        {"identificador": "br_sp_sao_bento_pedra_do_bau"},
    )
    assert res_ja_aberto["status"] == "ja_aberto"

    res_imp_ja_aberto = _chamar(
        servidor,
        "aresta_importar_croqui_oficial",
        {"id_oficial": "br_sp_sao_bento_pedra_do_bau"},
    )
    assert res_imp_ja_aberto["status"] == "ja_aberto"

    # 5. Abrir croqui experimental existente por id_croqui lógico
    res_abrir = _chamar(
        servidor,
        "aresta_abrir_croqui_existente",
        {"identificador": "br_mg_cipo_setor_sol"},
    )
    assert res_abrir["status"] == "aberto"
    assert res_abrir["id_croqui"] == "br_mg_cipo_setor_sol"


def test_particionar_pdf_croqui_aloca_e_preserva_uids(qapp, tmp_path: Path):
    """
    Valida aresta_particionar_pdf_croqui extraindo sub-PDFs e imagens WebP via repartir_pdf,
    pré-alocando Botao, Setor, Grupo e ColecaoDeMapas com UIDs NanoID e preservando-os ao reexecutar.
    """
    import pymupdf
    from PIL import Image

    # Cria um PDF real de 4 páginas com imagem embutida na página 1
    pdf_origem = tmp_path / "origem.pdf"
    img_temp = tmp_path / "foto_parede.png"
    Image.new("RGB", (200, 120), color=(40, 100, 180)).save(img_temp)

    doc = pymupdf.open()
    for i in range(4):
        pag = doc.new_page(width=400, height=400)
        pag.insert_text((40, 50), f"Pagina {i}")
        if i == 1:
            pag.insert_image(pymupdf.Rect(50, 80, 250, 200), filename=str(img_temp))
    doc.save(str(pdf_origem))
    doc.close()

    croqui = croqui_pb2.Croqui(uid="uid_croqui_pdf", id="croqui_pdf", nome="Croqui PDF")
    model = CroquiModel(croqui)
    historico = GerenciadorHistorico()
    workspace = _WorkspaceFake(tmp_path)
    servidor = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)

    registrar_ferramentas_ciclo_vida(
        servidor=servidor,
        model=model,
        undo_stack=historico,
        workspace=workspace,
    )

    partes_arg = {
        "00_introducao": [0],
        "01_setor_principal": [1],
        "02_grupo_leste": [2],
        "03_mapas_gerais": [3],
    }
    tipos_arg = {
        "02_grupo_leste": "grupo",
    }

    res1 = _chamar(
        servidor,
        "aresta_particionar_pdf_croqui",
        {
            "partes": partes_arg,
            "tipos_partes": tipos_arg,
            "caminho_pdf": str(pdf_origem),
        },
    )
    assert res1["status"] == "ok"
    proc1 = res1["partes_processadas"]
    assert proc1["00_introducao"]["tipo"] == "botao"
    assert proc1["01_setor_principal"]["tipo"] == "setor"
    assert proc1["02_grupo_leste"]["tipo"] == "grupo"
    assert proc1["03_mapas_gerais"]["tipo"] == "mapas_gerais"
    assert len(proc1["01_setor_principal"]["imagens_extraidas"]) == 1

    uid_botao_1 = proc1["00_introducao"]["uid"]
    uid_setor_1 = proc1["01_setor_principal"]["uid"]
    uid_grupo_1 = proc1["02_grupo_leste"]["uid"]
    uid_mapas_1 = proc1["03_mapas_gerais"]["uid"]
    assert all([uid_botao_1, uid_setor_1, uid_grupo_1, uid_mapas_1])

    # Reexecutar aresta_particionar_pdf_croqui (fluxo de atualização) deve preservar os mesmos UIDs!
    res2 = _chamar(
        servidor,
        "aresta_particionar_pdf_croqui",
        {
            "partes": partes_arg,
            "tipos_partes": tipos_arg,
        },
    )
    proc2 = res2["partes_processadas"]
    assert proc2["00_introducao"]["uid"] == uid_botao_1
    assert proc2["01_setor_principal"]["uid"] == uid_setor_1
    assert proc2["02_grupo_leste"]["uid"] == uid_grupo_1
    assert proc2["03_mapas_gerais"]["uid"] == uid_mapas_1
    assert len(model.obter_croqui_readonly().botoes) == 1
    assert len(model.obter_croqui_readonly().picos[0].setores_ou_grupos) == 2

