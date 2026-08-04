import pytest
from pathlib import Path
import shutil
from unittest.mock import patch
from editor.core.storage import GerenciadorCaminhos
from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.core.croqui_format import ler_croqui, empacotar_croqui

@pytest.fixture
def storage_temp(tmp_path):
    storage = GerenciadorCaminhos()
    storage.obter_diretorio_base = lambda: tmp_path / "editor_aresta"
    storage.inicializar_diretorios()
    return storage

@pytest.fixture
def gerenciador(storage_temp):
    return GerenciadorCroquiExperimental(storage_temp)

def test_workflow_exportacao_importacao_ofuscada(gerenciador, storage_temp, tmp_path):
    # 1. CRIAR UM CROQUI EXPERIMENTAL
    id_origem = "br_mg_itambe"
    pico = "Pico do Itambé"
    with patch("editor.core.croqui_experimental.deploy"):
        caminho_origem = gerenciador.criar_novo_croqui(id_origem, pico, "MG", "Renato")
    
    # Adicionamos um arquivo extra para garantir que o ZIP pega tudo
    (caminho_origem / "database" / "info_extra.txt").write_text("segredo")
    
    # 2. EXPORTAR PARA .CROQUI
    caminho_exportado = tmp_path / "itambe.croqui"
    gerenciador.exportar_croqui(caminho_origem, caminho_exportado)
    
    assert caminho_exportado.exists()
    # Verifica ofuscação (não deve ser 'PK')
    assert caminho_exportado.read_bytes()[:2] != b"PK"
    
    # 3. IMPORTAR NOVAMENTE
    # Simulamos um novo ambiente (ou apenas uma nova importação)
    # O importar_croqui gera um novo timestamp e evita colisão
    with patch("editor.core.croqui_experimental.deploy"):
        caminho_importado = gerenciador.importar_croqui(caminho_exportado)
    
    # 4. VERIFICAR INTEGRIDADE
    assert caminho_importado.exists()
    assert caminho_importado != caminho_origem
    
    # O ID deve ser o mesmo (lido do croqui.yaml)
    assert id_origem in caminho_importado.name
    
    # Arquivos devem ser idênticos
    assert (caminho_importado / "database" / "info_extra.txt").read_text() == "segredo"
    assert (caminho_importado / "database" / "croqui.yaml").exists()
    assert (caminho_importado / "croqui_experimental.yaml").exists()
    
    # Deve ser um repositório git funcional
    assert (caminho_importado / ".git").is_dir()

def test_fallback_importacao_zip_comum(gerenciador, storage_temp, tmp_path):
    # 1. CRIAR UM ZIP COMUM (SEM OFUSCAÇÃO)
    pasta_fake = tmp_path / "fake_zip"
    pasta_fake.mkdir()
    db = pasta_fake / "database"
    db.mkdir()
    (db / "croqui.yaml").write_text("id: 'zip_comum'\nnome: 'Pico ZIP'")
    
    caminho_zip = tmp_path / "comum.zip"
    import zipfile
    with zipfile.ZipFile(caminho_zip, 'w') as z:
        z.write(db / "croqui.yaml", arcname="database/croqui.yaml")
        
    # 2. IMPORTAR
    # O gerenciador deve aceitar .zip e o ler_croqui deve detectar que já é um ZIP
    with patch("editor.core.croqui_experimental.deploy"):
        caminho_importado = gerenciador.importar_croqui(caminho_zip)
        
    # 3. VERIFICAR
    assert caminho_importado.exists()
    assert (caminho_importado / "database" / "croqui.yaml").exists()
    assert "zip_comum" in caminho_importado.name
