# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import yaml
from PyQt6.QtCore import Qt
from editor.legacy_views.dialogo_busca_croqui import DialogoBuscaCroqui

@pytest.fixture
def mock_storage(tmp_path):
    from unittest.mock import MagicMock
    mock = MagicMock()
    # O diretório base onde database/ estará
    mock.obter_caminho_base_repo.return_value = tmp_path
    return mock

def test_deve_listar_croquis_do_database(qtbot, mock_storage, tmp_path):
    # Setup: Criar pastas e croqui.yaml falsos na database
    database_dir = tmp_path / "database"
    database_dir.mkdir()
    
    croqui1_dir = database_dir / "br_mg_araxa_bocaina"
    croqui1_dir.mkdir()
    with open(croqui1_dir / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"nome": "Serra da Bocaina"}, f)
        
    croqui2_dir = database_dir / "br_mg_arcos_corumba"
    croqui2_dir.mkdir()
    with open(croqui2_dir / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"nome": "Corumbá"}, f)
        
    # Pasta sem croqui.yaml (deve usar o id)
    croqui3_dir = database_dir / "br_mg_sem_yaml"
    croqui3_dir.mkdir()
        
    dialogo = DialogoBuscaCroqui(mock_storage)
    qtbot.addWidget(dialogo)
    
    assert dialogo.lista_croquis.count() == 3
    items = [dialogo.lista_croquis.item(i).text() for i in range(dialogo.lista_croquis.count())]
    assert "Serra da Bocaina (br_mg_araxa_bocaina)" in items
    assert "Corumbá (br_mg_arcos_corumba)" in items
    assert "br_mg_sem_yaml (br_mg_sem_yaml)" in items

def test_deve_filtrar_croquis_por_texto(qtbot, mock_storage, tmp_path):
    database_dir = tmp_path / "database"
    database_dir.mkdir(exist_ok=True)
    
    croqui1 = database_dir / "bocaina"
    croqui1.mkdir()
    with open(croqui1 / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"nome": "Bocaina"}, f)
        
    croqui2 = database_dir / "corumba"
    croqui2.mkdir()
    with open(croqui2 / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"nome": "Corumba"}, f)
        
    dialogo = DialogoBuscaCroqui(mock_storage)
    qtbot.addWidget(dialogo)
    
    # Filtrar por "boc"
    qtbot.keyClicks(dialogo.campo_busca, "boc")
    
    # Verifica que apenas 1 item está visível
    visiveis = 0
    for i in range(dialogo.lista_croquis.count()):
        if not dialogo.lista_croquis.isRowHidden(i):
            visiveis += 1
            
    assert visiveis == 1
    # Pega o item visível
    for i in range(dialogo.lista_croquis.count()):
        if not dialogo.lista_croquis.isRowHidden(i):
            assert "Bocaina" in dialogo.lista_croquis.item(i).text()

def test_deve_selecionar_croqui_e_retornar_id(qtbot, mock_storage, tmp_path):
    database_dir = tmp_path / "database"
    database_dir.mkdir(exist_ok=True)
    
    croqui1 = database_dir / "teste_id"
    croqui1.mkdir()
    with open(croqui1 / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"nome": "Nome de Teste"}, f)
        
    dialogo = DialogoBuscaCroqui(mock_storage)
    qtbot.addWidget(dialogo)
    
    # Selecionar item
    dialogo.lista_croquis.setCurrentRow(0)
    
    # Confirmar
    with qtbot.waitSignal(dialogo.accepted):
        qtbot.mouseClick(dialogo.btn_confirmar, Qt.MouseButton.LeftButton)
        
    assert dialogo.obter_id_selecionado() == "teste_id"

