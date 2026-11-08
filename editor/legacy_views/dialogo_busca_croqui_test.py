# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from editor.core.serializacao_util import serializar_yaml
from editor.core.storage import GerenciadorCaminhos
from editor.legacy_views.dialogo_busca_croqui import DialogoBuscaCroqui


@pytest.fixture
def storage_real(tmp_path: Path) -> GerenciadorCaminhos:
    storage = GerenciadorCaminhos()
    storage.obter_diretorio_base = lambda: tmp_path / "editor_aresta"
    storage.inicializar_diretorios()
    return storage


def test_deve_listar_croquis_e_pre_selecionar_primeiro_item_ao_abrir(
    qtbot, storage_real: GerenciadorCaminhos
):
    database_dir = storage_real.obter_caminho_base_repo() / "database"
    database_dir.mkdir(parents=True, exist_ok=True)

    croqui1_dir = database_dir / "br_mg_araxa_bocaina"
    croqui1_dir.mkdir()
    with open(croqui1_dir / "croqui.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"nome": "Serra da Bocaina"}, f)

    croqui2_dir = database_dir / "br_mg_arcos_corumba"
    croqui2_dir.mkdir()
    with open(croqui2_dir / "croqui.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"nome": "Corumbá"}, f)

    # Pasta sem croqui.yaml e pasta com croqui.yaml corrompido (devem fazer fallback para o id)
    (database_dir / "br_mg_sem_yaml").mkdir()
    croqui_invalido = database_dir / "br_mg_yaml_invalido"
    croqui_invalido.mkdir()
    (croqui_invalido / "croqui.yaml").write_text("::: yaml_invalido: [", encoding="utf-8")

    dialogo = DialogoBuscaCroqui(storage_real)
    qtbot.addWidget(dialogo)

    assert dialogo.lista_croquis.count() == 4
    items = [dialogo.lista_croquis.item(i).text() for i in range(dialogo.lista_croquis.count())]
    assert "Serra da Bocaina (br_mg_araxa_bocaina)" in items
    assert "Corumbá (br_mg_arcos_corumba)" in items
    assert "br_mg_sem_yaml (br_mg_sem_yaml)" in items
    assert "br_mg_yaml_invalido (br_mg_yaml_invalido)" in items

    # Deve já pré-selecionar o primeiro item e habilitar o botão Confirmar
    assert dialogo.lista_croquis.currentRow() == 0
    assert dialogo.btn_confirmar.isEnabled() is True
    assert dialogo.obter_id_selecionado() == "br_mg_araxa_bocaina"


def test_deve_selecionar_primeiro_item_visivel_ao_filtrar_e_confirmar_com_enter(
    qtbot, storage_real: GerenciadorCaminhos
):
    database_dir = storage_real.obter_caminho_base_repo() / "database"
    database_dir.mkdir(parents=True, exist_ok=True)

    croqui1 = database_dir / "br_mg_bocaina"
    croqui1.mkdir()
    with open(croqui1 / "croqui.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"nome": "Bocaina"}, f)

    croqui2 = database_dir / "br_mg_corumba"
    croqui2.mkdir()
    with open(croqui2 / "croqui.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"nome": "Corumbá"}, f)

    dialogo = DialogoBuscaCroqui(storage_real)
    qtbot.addWidget(dialogo)
    dialogo.show()

    # Inicialmente seleciona o item 0 (Bocaina)
    assert dialogo.lista_croquis.currentRow() == 0
    assert dialogo.obter_id_selecionado() == "br_mg_bocaina"

    # Filtrar por "corumba" oculta o item 0 e deve selecionar automaticamente o item 1 (Corumbá)
    qtbot.keyClicks(dialogo.campo_busca, "corumba")

    assert dialogo.lista_croquis.isRowHidden(0) is True
    assert dialogo.lista_croquis.isRowHidden(1) is False
    assert dialogo.lista_croquis.currentRow() == 1
    assert dialogo.btn_confirmar.isEnabled() is True
    assert dialogo.obter_id_selecionado() == "br_mg_corumba"

    # Pressionar Enter direto no campo de busca confirma imediatamente o item visível pré-selecionado
    with qtbot.waitSignal(dialogo.accepted, timeout=1000):
        qtbot.keyClick(dialogo.campo_busca, Qt.Key.Key_Return)

    assert dialogo.id_selecionado == "br_mg_corumba"


def test_deve_limpar_selecao_e_desabilitar_confirmacao_quando_filtro_nao_encontra_itens(
    qtbot, storage_real: GerenciadorCaminhos
):
    database_dir = storage_real.obter_caminho_base_repo() / "database"
    database_dir.mkdir(parents=True, exist_ok=True)

    croqui1 = database_dir / "br_mg_bocaina"
    croqui1.mkdir()
    with open(croqui1 / "croqui.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"nome": "Bocaina"}, f)

    dialogo = DialogoBuscaCroqui(storage_real)
    qtbot.addWidget(dialogo)
    dialogo.show()

    qtbot.keyClicks(dialogo.campo_busca, "inexistente_xyz")

    assert dialogo.lista_croquis.currentRow() == -1
    assert dialogo.btn_confirmar.isEnabled() is False
    assert dialogo.obter_id_selecionado() is None

    # Chamar accept() sem seleção válida não aceita o diálogo
    dialogo.accept()
    assert dialogo.id_selecionado is None


def test_dialogo_busca_croqui_sem_storage_ou_sem_pasta_database(qtbot, tmp_path: Path):
    dialogo_sem_storage = DialogoBuscaCroqui(None)
    qtbot.addWidget(dialogo_sem_storage)
    assert dialogo_sem_storage.lista_croquis.count() == 0
    assert dialogo_sem_storage.btn_confirmar.isEnabled() is False
    assert dialogo_sem_storage.obter_id_selecionado() is None

    storage_vazio = GerenciadorCaminhos()
    storage_vazio.obter_diretorio_base = lambda: tmp_path / "vazio"
    dialogo_sem_db = DialogoBuscaCroqui(storage_vazio)
    qtbot.addWidget(dialogo_sem_db)
    assert dialogo_sem_db.lista_croquis.count() == 0
    assert dialogo_sem_db.btn_confirmar.isEnabled() is False
