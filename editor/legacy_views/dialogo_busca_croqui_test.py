import pytest
from PyQt6.QtCore import Qt
from editor.legacy_views.dialogo_busca_croqui import DialogoBuscaCroqui
from aresta_api.proto.generated.indice_pb2 import Indice

@pytest.fixture
def mock_storage(tmp_path):
    from unittest.mock import MagicMock
    mock = MagicMock()
    # O diretório base onde generated/indice.binarypb estará
    mock.obter_caminho_base_repo.return_value = tmp_path
    return mock

def test_deve_listar_croquis_do_indice(qtbot, mock_storage, tmp_path):
    # Setup: Criar indice.binarypb falso
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir()
    indice_file = generated_dir / "indice.binarypb"
    
    indice = Indice()
    c1 = indice.croquis.add()
    c1.id = "br_mg_araxa_bocaina"
    c1.nome = "Serra da Bocaina"
    
    c2 = indice.croquis.add()
    c2.id = "br_mg_arcos_corumba"
    c2.nome = "Corumbá"
    
    with open(indice_file, "wb") as f:
        f.write(indice.SerializeToString())
        
    dialogo = DialogoBuscaCroqui(mock_storage)
    qtbot.addWidget(dialogo)
    
    assert dialogo.lista_croquis.count() == 2
    items = [dialogo.lista_croquis.item(i).text() for i in range(dialogo.lista_croquis.count())]
    assert "Serra da Bocaina (br_mg_araxa_bocaina)" in items
    assert "Corumbá (br_mg_arcos_corumba)" in items

def test_deve_filtrar_croquis_por_texto(qtbot, mock_storage, tmp_path):
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir(exist_ok=True)
    indice_file = generated_dir / "indice.binarypb"
    
    indice = Indice()
    indice.croquis.add(id="bocaina", nome="Bocaina")
    indice.croquis.add(id="corumba", nome="Corumba")
    
    with open(indice_file, "wb") as f:
        f.write(indice.SerializeToString())
        
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
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir(exist_ok=True)
    indice_file = generated_dir / "indice.binarypb"
    indice = Indice()
    indice.croquis.add(id="teste_id", nome="Nome de Teste")
    with open(indice_file, "wb") as f:
        f.write(indice.SerializeToString())
        
    dialogo = DialogoBuscaCroqui(mock_storage)
    qtbot.addWidget(dialogo)
    
    # Selecionar item
    dialogo.lista_croquis.setCurrentRow(0)
    
    # Confirmar
    with qtbot.waitSignal(dialogo.accepted):
        qtbot.mouseClick(dialogo.btn_confirmar, Qt.MouseButton.LeftButton)
        
    assert dialogo.obter_id_selecionado() == "teste_id"
