# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from pathlib import Path
import os
import shutil
import zipfile
import pygit2
import yaml
from editor.core.croqui_format import ler_croqui, empacotar_croqui

from unittest.mock import patch
from editor.core.storage import GerenciadorCaminhos
from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from aresta_api.proto.generated.croqui_experimental_pb2 import CroquiExperimental


@pytest.fixture
def storage_temp(tmp_path):
    storage = GerenciadorCaminhos()
    storage.obter_diretorio_base = lambda: tmp_path / "editor_aresta"
    storage.inicializar_diretorios()
    return storage

@pytest.fixture
def gerenciador(storage_temp):
    return GerenciadorCroquiExperimental(storage_temp)

def test_criar_novo_croqui_experimental(gerenciador, storage_temp):
    # DADO os metadados de um croqui
    id_croqui = "br_mg_teste"
    pico = "Pedra do Teste"
    estado = "MG"
    nome_usuario = "Renato"
    
    # QUANDO criar o croqui experimental (mockando deploy para ser rápido)
    with patch("editor.core.croqui_experimental.deploy"):
        caminho_croqui = gerenciador.criar_novo_croqui(id_croqui, pico, estado, nome_usuario)
    
    # ENTÃO a pasta raiz deve existir dentro de croquis_experimentais
    assert caminho_croqui.parent == storage_temp.obter_caminho_croquis_experimentais()
    assert "br_mg_teste" in caminho_croqui.name
    
    # E deve conter as subpastas database e compilado
    assert (caminho_croqui / "database").is_dir()
    assert (caminho_croqui / "compilado").is_dir()
    
    # E o database/croqui.yaml deve estar preenchido corretamente
    croqui_yaml = caminho_croqui / "database" / "croqui.yaml"
    assert croqui_yaml.is_file()
    with open(croqui_yaml, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    assert dados["id"] == id_croqui
    assert dados["nome"] == pico
    assert dados["picos"][0]["nome"] == pico
    assert dados["picos"][0]["estado"] == estado
    
    # E deve ser um repositório git local válido
    assert (caminho_croqui / ".git").is_dir()
    repo = pygit2.Repository(str(caminho_croqui))
    assert not repo.is_bare

def test_exportar_croqui(gerenciador, storage_temp, tmp_path):
    # DADO um croqui experimental existente
    caminho_croqui = gerenciador._criar_estrutura_croqui("br_sp_export", "A")
    
    # Criamos um arquivo simulado dentro do database para garantir que é exportado
    (caminho_croqui / "database" / "croqui.yaml").write_text("teste")
    
    caminho_destino = tmp_path / "exportado.croqui"
    
    # QUANDO exportar
    gerenciador.exportar_croqui(caminho_croqui, caminho_destino)
    
    # ENTÃO o arquivo .croqui deve ser gerado
    assert caminho_destino.is_file()
    
    # E o primeiro byte deve estar ofuscado
    assert caminho_destino.read_bytes()[:1] != b"P"
    
    # E deve ser possível extrair o conteúdo (desofuscando)
    pasta_verificacao = tmp_path / "verificacao"
    ler_croqui(caminho_destino, pasta_verificacao)
    
    assert (pasta_verificacao / "database" / "croqui.yaml").is_file()
    assert (pasta_verificacao / "croqui_experimental.yaml").is_file()

def test_abrir_croqui(gerenciador, storage_temp):
    caminho_croqui = gerenciador._criar_estrutura_croqui("br_es_abrir", "A")
    gerenciador.abrir_croqui(caminho_croqui, "B")
    
    yaml_path = caminho_croqui / "croqui_experimental.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    assert "A" in dados["autores"]
    assert "B" in dados["autores"]

def test_excluir_croqui_com_arquivos_somente_leitura(gerenciador, tmp_path):
    """
    Verifica se a exclusão lida corretamente com arquivos somente-leitura 
    (cenário comum em pastas .git no Windows).
    """
    import stat
    
    # Criar uma pasta de teste
    pasta_teste = tmp_path / "croqui_com_readonly"
    pasta_teste.mkdir()
    
    # Criar um arquivo e marcá-lo como somente-leitura
    arquivo_readonly = pasta_teste / "somente_leitura.txt"
    arquivo_readonly.write_text("não pode me apagar")
    
    # Remover permissão de escrita (read-only)
    mode = os.stat(arquivo_readonly).st_mode
    os.chmod(arquivo_readonly, mode & ~stat.S_IWRITE)

    # QUANDO excluir
    gerenciador.excluir_croqui(pasta_teste)
    
    # ENTÃO a pasta deve ter sido removida com sucesso
    assert not pasta_teste.exists()

def test_compilar_croqui_sucesso(gerenciador, storage_temp):
    """Verifica se a compilação gera os arquivos corretamente e cria um commit."""
    # DADO um croqui com arquivos válidos
    caminho_croqui = gerenciador._criar_estrutura_croqui("br_mg_compilar", "User")
    (caminho_croqui / "database" / "croqui.yaml").write_text("id: br_mg_compilar\nnome: Teste")
    
    # QUANDO compilar (mockando o deploy para determinismo)
    with patch("editor.core.croqui_experimental.deploy") as mock_deploy:
        gerenciador.compilar_croqui(caminho_croqui)
        
        # Verifica se o deploy foi chamado com as flags corretas
        mock_deploy.assert_called_once()
        kwargs = mock_deploy.call_args.kwargs
        assert kwargs["force_thumbnails"] is True
        assert kwargs["gerar_arquivos_de_debug"] is True
    
    # E deve haver um commit de compilação
    repo = pygit2.Repository(str(caminho_raiz := caminho_croqui))
    last_commit = repo.revparse_single("HEAD")
    assert "Compila" in last_commit.message

def test_compilar_croqui_falha_sem_yaml(gerenciador, storage_temp):
    """Verifica se falha ao compilar um croqui sem croqui.yaml."""
    # DADO um croqui sem croqui.yaml na database
    caminho_croqui = gerenciador._criar_estrutura_croqui("br_mg_erro", "User")
    
    # QUANDO tentar compilar, deve levantar RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        gerenciador.compilar_croqui(caminho_croqui)
    
    assert "Erro durante a compilação" in str(excinfo.value)

def test_criar_croqui_a_partir_de_oficial_sucesso(gerenciador, storage_temp):
    """Verifica se cria corretamente um experimental a partir de um oficial."""
    # DADO um croqui oficial simulado no repositório base
    id_oficial = "br_mg_itambe"
    caminho_repo = storage_temp.obter_caminho_base_repo()
    caminho_oficial = caminho_repo / "database" / id_oficial
    caminho_oficial.mkdir(parents=True)
    
    # Criar alguns arquivos oficiais
    (caminho_oficial / "croqui.yaml").write_text("id: br_mg_itambe\nnome: Pico do Itambé")
    setor_dir = caminho_oficial / "setor_a"
    setor_dir.mkdir()
    (setor_dir / "setor.yaml").write_text("nome: Setor A")
    
    # QUANDO criar o experimental a partir desse oficial
    with patch("editor.core.croqui_experimental.deploy") as mock_deploy:
        caminho_exp = gerenciador.criar_croqui_a_partir_de_oficial(id_oficial, "Renato", "Cópia oficial")
        
        # ENTÃO a compilação deve ter sido chamada
        mock_deploy.assert_called_once()
        
    # E os arquivos devem ter sido copiados para a pasta database
    assert (caminho_exp / "database" / "croqui.yaml").is_file()
    assert (caminho_exp / "database" / "setor_a" / "setor.yaml").is_file()
    
    # E os metadados experimentais devem estar corretos
    yaml_meta = caminho_exp / "croqui_experimental.yaml"
    with open(yaml_meta, "r", encoding="utf-8") as f:
        dados_meta = yaml.safe_load(f)
    assert "Renato" in dados_meta["autores"]
    assert dados_meta["resumo_edicao"] == "Cópia oficial"
    
    # E deve haver um histórico git com três commits (inicial + compilação + importação)
    repo = pygit2.Repository(str(caminho_exp))
    commits = list(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL))
    assert len(commits) == 3
    assert "Importação" in commits[0].message
    assert "Compilação" in commits[1].message
    assert "Commit inicial" in commits[2].message




def test_criar_croqui_a_partir_de_oficial_cleanup_em_falha(gerenciador, storage_temp):

    """Verifica se remove a pasta se falhar ao criar a partir de oficial."""
    # DADO um oficial que não existe (vai falhar)
    id_oficial = "oficial_fantasma"
    
    # QUANDO tentar criar
    with pytest.raises(FileNotFoundError):
        gerenciador.criar_croqui_a_partir_de_oficial(id_oficial, "User")
        
    # ENTÃO nenhuma pasta nova deve restar no storage (exceto a pasta base vazia)
    diretorio_exp = storage_temp.obter_caminho_croquis_experimentais()
    pastas = list(diretorio_exp.iterdir())
    assert len(pastas) == 0

def test_importar_croqui_cleanup_em_falha(gerenciador, tmp_path):
    """Verifica se remove a pasta se falhar ao importar zip corrompido."""
    # DADO um arquivo zip inválido
    zip_ruim = tmp_path / "corrompido.croqui"
    zip_ruim.write_text("não sou um zip")
    
    # QUANDO tentar importar
    with pytest.raises(Exception): # zipfile.BadZipFile
        gerenciador.importar_croqui(zip_ruim)
        
    # ENTÃO a pasta temporária de extração deve ter sido removida
    diretorio_exp = gerenciador.caminhos.obter_caminho_croquis_experimentais()
    pastas = list(diretorio_exp.iterdir())
    assert len(pastas) == 0

def test_importar_croqui_com_pasta_raiz_aninhada(gerenciador, tmp_path):
    """Verifica se normaliza a estrutura se o ZIP tiver uma pasta raiz aninhada."""
    # DADO um ZIP com estrutura: raiz/database/croqui.yaml
    caminho_zip = tmp_path / "aninhado.croqui"
    temp_dir = tmp_path / "preparar_zip"
    pasta_raiz = temp_dir / "minha_pasta_extra"
    db_dir = pasta_raiz / "database"
    db_dir.mkdir(parents=True)
    (db_dir / "croqui.yaml").write_text("id: 'pico_aninhado'\nnome: 'Pico Aninhado'")
    
    # Empacotamos como .croqui ofuscado
    empacotar_croqui(temp_dir, caminho_zip)
        
    # QUANDO importar
    with patch("editor.core.croqui_experimental.deploy"): # Mock deploy para não precisar de tudo
        caminho_final = gerenciador.importar_croqui(caminho_zip)
        
    # ENTÃO a estrutura deve ter sido achatada (database deve estar na raiz do destino)
    assert (caminho_final / "database" / "croqui.yaml").exists()
    assert not (caminho_final / "minha_pasta_extra").exists()
    assert "pico_aninhado" in caminho_final.name

def test_id_original_salvo_ao_criar_e_importar(gerenciador, storage_temp):
    """Verifica se o id_original é salvo no yaml ao criar novo ou importar de oficial."""
    # Teste 1: Criar novo
    id_novo = "br_sp_novo_teste"
    with patch("editor.core.croqui_experimental.deploy"):
        caminho_novo = gerenciador.criar_novo_croqui(id_novo, "Pico Novo", "SP", "User")
        
    yaml_novo = caminho_novo / "croqui_experimental.yaml"
    with open(yaml_novo, "r", encoding="utf-8") as f:
        dados_novo = yaml.safe_load(f)
    assert dados_novo.get("id_original") == id_novo

    # Teste 2: Criar a partir de oficial
    id_oficial = "br_sp_oficial_teste"
    caminho_repo = storage_temp.obter_caminho_base_repo()
    caminho_oficial = caminho_repo / "database" / id_oficial
    caminho_oficial.mkdir(parents=True)
    (caminho_oficial / "croqui.yaml").write_text(f"id: {id_oficial}\nnome: Pico Oficial")
    
    with patch("editor.core.croqui_experimental.deploy"):
        caminho_exp = gerenciador.criar_croqui_a_partir_de_oficial(id_oficial, "User")
        
    yaml_exp = caminho_exp / "croqui_experimental.yaml"
    with open(yaml_exp, "r", encoding="utf-8") as f:
        dados_exp = yaml.safe_load(f)
    assert dados_exp.get("id_original") == id_oficial

def test_renomear_pasta_croqui_sucesso(gerenciador, storage_temp):
    """Verifica se renomeia mantendo o timestamp e retorna o novo caminho."""
    # Cria uma pasta mock com nome formatado (timestamp_id)
    caminho_exp = storage_temp.obter_caminho_croquis_experimentais()
    timestamp = "20260606120000"
    old_id = "br_mg_antigo"
    pasta_antiga = caminho_exp / f"{timestamp}_{old_id}"
    pasta_antiga.mkdir()
    (pasta_antiga / "teste.txt").write_text("ok")
    
    # Chama o método que deve renomear
    novo_id = "br_mg_novo"
    nova_pasta = gerenciador.renomear_pasta_croqui(pasta_antiga, novo_id)
    
    # Validações
    assert not pasta_antiga.exists()
    assert nova_pasta.exists()
    assert nova_pasta.name == f"{timestamp}_{novo_id}"
    assert (nova_pasta / "teste.txt").read_text() == "ok"
    
def test_renomear_pasta_croqui_sem_timestamp_prefixo(gerenciador, storage_temp):
    """Verifica comportamento se a pasta não tiver prefixo numérico claro."""
    caminho_exp = storage_temp.obter_caminho_croquis_experimentais()
    pasta_antiga = caminho_exp / "apenas_texto"
    pasta_antiga.mkdir()
    
    nova_pasta = gerenciador.renomear_pasta_croqui(pasta_antiga, "novo_nome")
    
    assert not pasta_antiga.exists()
    assert nova_pasta.exists()
    # Se não tinha timestamp, pode prefixar com a hora atual ou usar apenas o id,
    # assumiremos que o novo método gere um prefixo novo para manter padrão
    assert nova_pasta.name.endswith("_novo_nome")
    assert nova_pasta.name.split("_")[0].isdigit()

def test_renomear_pasta_croqui_limpa_compilado_antigo(gerenciador, storage_temp):
    """Verifica se o conteúdo compilado com o ID antigo é apagado ao renomear o croqui."""
    caminho_exp = storage_temp.obter_caminho_croquis_experimentais()
    timestamp = "20260606120000"
    old_id = "br_mg_id_velho"
    novo_id = "br_mg_id_novo"
    
    pasta_antiga = caminho_exp / f"{timestamp}_{old_id}"
    pasta_antiga.mkdir(parents=True)
    
    # Simula a estrutura do compilado antigo
    pasta_compilado_antigo = pasta_antiga / "compilado" / old_id
    pasta_compilado_antigo.mkdir(parents=True)
    (pasta_compilado_antigo / "index.html").write_text("ok")
    
    # Chama o método
    nova_pasta = gerenciador.renomear_pasta_croqui(pasta_antiga, novo_id)
    
    # Verifica
    assert nova_pasta.exists()
    assert not pasta_antiga.exists()
    
    # O diretório 'br_mg_id_velho' NÃO deve existir mais dentro de 'compilado' do novo path
    compilado_velho = nova_pasta / "compilado" / old_id
    assert not compilado_velho.exists()

