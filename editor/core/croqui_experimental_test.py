# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os

import pygit2
import pytest

from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.core.serializacao_util import carregar_yaml
from editor.core.storage import GerenciadorCaminhos


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

    # QUANDO criar o croqui experimental
    caminho_croqui = gerenciador.criar_novo_croqui(id_croqui, pico, estado, nome_usuario)

    # ENTÃO a pasta raiz deve existir dentro de croquis_experimentais
    assert caminho_croqui.parent == storage_temp.obter_caminho_croquis_experimentais()
    assert len(caminho_croqui.name) == 8

    # E deve conter as subpastas database e compilado
    assert (caminho_croqui / "database").is_dir()
    assert (caminho_croqui / "compilado").is_dir()

    # E o database/croqui.yaml deve estar preenchido corretamente
    croqui_yaml = caminho_croqui / "database" / "croqui.yaml"
    assert croqui_yaml.is_file()
    dados = carregar_yaml(croqui_yaml.read_text(encoding="utf-8"))
    assert dados["id"] == id_croqui
    assert dados["nome"] == pico
    assert dados["picos"][0]["nome"] == pico
    assert dados["picos"][0]["estado"] == estado

    # E não deve criar repositório git local redundante na pasta do croqui experimental
    assert not (caminho_croqui / ".git").exists()

    # E os arquivos YAML devem estar com quebras de linha estritamente em LF (\n)
    assert b"\r\n" not in croqui_yaml.read_bytes()
    assert b"\r\n" not in (caminho_croqui / "croqui_experimental.yaml").read_bytes()


def test_abrir_croqui(gerenciador, storage_temp):
    caminho_croqui = gerenciador._criar_estrutura_croqui("br_es_abrir", "A")
    gerenciador.abrir_croqui(caminho_croqui, "B")

    yaml_path = caminho_croqui / "croqui_experimental.yaml"
    dados = carregar_yaml(yaml_path.read_text(encoding="utf-8"))
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
    """Verifica se a compilação gera os arquivos corretamente sem criar repositório git local."""
    # DADO um croqui com arquivos válidos
    caminho_croqui = gerenciador._criar_estrutura_croqui("br_mg_compilar", "User")
    (caminho_croqui / "database" / "croqui.yaml").write_text(
        "id: br_mg_compilar\nnome: Teste\nultima_migracao: 5\npicos:\n  - nome: Teste\n    estado: MG\n",
        encoding="utf-8",
    )

    # QUANDO compilar
    gerenciador.compilar_croqui(caminho_croqui)

    # ENTÃO o binário compilado e o arquivo de debug YAML devem existir (sem compilado.md legado)
    assert (caminho_croqui / "compilado" / "compilado.binarypb").is_file()
    assert (caminho_croqui / "compilado" / "compilado.yaml").is_file()
    assert not (caminho_croqui / "compilado" / "compilado.md").exists()
    assert not (caminho_croqui / ".git").exists()


def test_compilar_croqui_compacta_saida_diretamente_em_compilado(gerenciador, storage_temp):
    """Garante que compilar_croqui move os arquivos compilados para a raiz de compilado/ sem subpasta redundante."""
    from PIL import Image

    caminho_croqui = gerenciador._criar_estrutura_croqui("br_mg_compacto", "User")
    pasta_db = caminho_croqui / "database"
    (pasta_db / "imagens").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), color="blue").save(pasta_db / "imagens" / "foto.webp", "WEBP")
    (pasta_db / "croqui.yaml").write_text(
        "id: br_mg_compacto\nnome: Compacto\nultima_migracao: 5\n"
        "caminho_thumbnail: imagens/foto.webp\n"
        "picos:\n  - nome: Compacto\n    estado: MG\n",
        encoding="utf-8",
    )

    gerenciador.compilar_croqui(caminho_croqui)

    compilado_dir = caminho_croqui / "compilado"
    assert (compilado_dir / "compilado.binarypb").is_file()
    assert (compilado_dir / "compilado.yaml").is_file()
    foto_compilada = compilado_dir / "imagens" / "foto.webp"
    assert foto_compilada.is_file()
    assert not (compilado_dir / "br_mg_compacto").exists()

    # Substitui conteúdo mantendo mesmo tamanho e mtime_ns da origem para provar que a
    # recompilação incremental aciona o fast-path de stat() sem recopiar a imagem do zero
    st_src = (pasta_db / "imagens" / "foto.webp").stat()
    conteudo_sentinela = b"X" * st_src.st_size
    foto_compilada.write_bytes(conteudo_sentinela)
    os.utime(foto_compilada, ns=(st_src.st_mtime_ns, st_src.st_mtime_ns))

    gerenciador.compilar_croqui(caminho_croqui)

    assert (compilado_dir / "compilado.binarypb").is_file()
    assert (compilado_dir / "compilado.yaml").is_file()
    assert foto_compilada.is_file()
    assert foto_compilada.read_bytes() == conteudo_sentinela
    assert not (compilado_dir / "br_mg_compacto").exists()


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
    (caminho_oficial / "croqui.yaml").write_text(
        "id: br_mg_itambe\nnome: Pico do Itambé\nultima_migracao: 5\n"
        "picos:\n  - nome: Pico do Itambé\n    estado: MG\n",
        encoding="utf-8",
    )
    setor_dir = caminho_oficial / "setor_a"
    setor_dir.mkdir()
    (setor_dir / "setor.yaml").write_text("nome: Setor A", encoding="utf-8")

    # QUANDO criar o experimental a partir desse oficial
    caminho_exp = gerenciador.criar_croqui_a_partir_de_oficial(
        id_oficial, "Renato", "Cópia oficial"
    )

    # ENTÃO os arquivos devem ter sido copiados para a pasta database e compilados
    assert (caminho_exp / "database" / "croqui.yaml").is_file()
    assert (caminho_exp / "database" / "setor_a" / "setor.yaml").is_file()
    assert (caminho_exp / "compilado" / "compilado.binarypb").is_file()

    # E os metadados experimentais devem estar corretos
    yaml_meta = caminho_exp / "croqui_experimental.yaml"
    dados_meta = carregar_yaml(yaml_meta.read_text(encoding="utf-8"))
    assert "Renato" in dados_meta["autores"]
    assert dados_meta["resumo_edicao"] == "Cópia oficial"

    # E não deve criar repositório git local redundante na pasta do croqui experimental
    assert not (caminho_exp / ".git").exists()


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


def test_id_original_salvo_ao_criar_e_importar(gerenciador, storage_temp):
    """Verifica se o id_original é salvo no yaml ao criar novo ou importar de oficial."""
    # Teste 1: Criar novo
    id_novo = "br_sp_novo_teste"
    caminho_novo = gerenciador.criar_novo_croqui(id_novo, "Pico Novo", "SP", "User")

    yaml_novo = caminho_novo / "croqui_experimental.yaml"
    dados_novo = carregar_yaml(yaml_novo.read_text(encoding="utf-8"))
    assert dados_novo.get("id_original") == id_novo

    # Teste 2: Criar a partir de oficial
    id_oficial = "br_sp_oficial_teste"
    caminho_repo = storage_temp.obter_caminho_base_repo()
    caminho_oficial = caminho_repo / "database" / id_oficial
    caminho_oficial.mkdir(parents=True)
    (caminho_oficial / "croqui.yaml").write_text(
        f"id: {id_oficial}\nnome: Pico Oficial\nultima_migracao: 5\n"
        "picos:\n  - nome: Pico Oficial\n    estado: SP\n",
        encoding="utf-8",
    )

    caminho_exp = gerenciador.criar_croqui_a_partir_de_oficial(id_oficial, "User")

    yaml_exp = caminho_exp / "croqui_experimental.yaml"
    dados_exp = carregar_yaml(yaml_exp.read_text(encoding="utf-8"))
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
    assert pasta_antiga.exists()  # Não muda o nome fisicamente
    assert nova_pasta == pasta_antiga
    assert (nova_pasta / "teste.txt").read_text() == "ok"


def test_renomear_pasta_croqui_sem_timestamp_prefixo(gerenciador, storage_temp):
    """Verifica comportamento se a pasta não tiver prefixo numérico claro."""
    caminho_exp = storage_temp.obter_caminho_croquis_experimentais()
    pasta_antiga = caminho_exp / "apenas_texto"
    pasta_antiga.mkdir()

    nova_pasta = gerenciador.renomear_pasta_croqui(pasta_antiga, "novo_nome")

    assert pasta_antiga.exists()
    assert nova_pasta == pasta_antiga


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
    assert nova_pasta == pasta_antiga

    # O diretório 'br_mg_id_velho' NÃO deve existir mais dentro de 'compilado' do novo path
    compilado_velho = nova_pasta / "compilado" / old_id
    assert not compilado_velho.exists()


def test_criar_croqui_a_partir_de_oficial_com_commit_base_sha(gerenciador, storage_temp):
    """Verifica se o commit_base_sha é gravado nos metadados ao criar a partir de oficial."""
    caminho_repo = storage_temp.obter_caminho_base_repo()
    caminho_repo.mkdir(parents=True, exist_ok=True)
    repo = pygit2.init_repository(str(caminho_repo), False)

    # Cria pasta e arquivo de croqui oficial simulado
    id_oficial = "br_mg_oficial"
    pasta_oficial = caminho_repo / "database" / id_oficial
    pasta_oficial.mkdir(parents=True)
    (pasta_oficial / "croqui.yaml").write_text(
        "id: br_mg_oficial\nnome: Oficial\nultima_migracao: 5\n"
        "picos:\n  - nome: Oficial\n    estado: MG\n",
        encoding="utf-8",
    )

    # Cria um commit no repositório base
    repo.index.add_all(["database"])
    repo.index.write()
    tree = repo.index.write_tree()
    autor = pygit2.Signature("Teste", "teste@aresta.local")
    commit_oid = repo.create_commit("HEAD", autor, autor, "Commit base de teste", tree, [])
    commit_sha = str(commit_oid)

    caminho_exp = gerenciador.criar_croqui_a_partir_de_oficial(id_oficial, "Renato", "Edicao teste")

    yaml_path = caminho_exp / "croqui_experimental.yaml"
    dados = carregar_yaml(yaml_path.read_text(encoding="utf-8"))

    assert dados.get("commit_base_sha") == commit_sha


def test_criar_novo_croqui_grava_ultima_migracao_versao_maxima(gerenciador, storage_temp):
    """Verifica se o novo croqui criado grava a versão máxima de migração no croqui.yaml."""
    from scripts.migrador import obter_ultima_versao_migracao

    versao_esperada = obter_ultima_versao_migracao()
    assert versao_esperada >= 5

    caminho_exp = gerenciador.criar_novo_croqui("br_mg_migracao", "Pico Migrado", "MG", "Usuario")

    croqui_yaml = caminho_exp / "database" / "croqui.yaml"
    dados = carregar_yaml(croqui_yaml.read_text(encoding="utf-8"))

    assert dados.get("ultima_migracao") == versao_esperada


def test_compilar_croqui_remove_pasta_git_legada_se_existir(gerenciador, storage_temp):
    """Garante que compilar_croqui limpa eventual pasta .git legada existente no croqui experimental."""
    import stat

    caminho_exp = gerenciador._criar_estrutura_croqui("br_mg_legado_git", "Usuario")
    (caminho_exp / "database" / "croqui.yaml").write_text(
        "id: br_mg_legado_git\nnome: Legado Git\nultima_migracao: 5\n"
        "picos:\n  - nome: Legado Git\n    estado: MG\n",
        encoding="utf-8",
    )
    pasta_git_legada = caminho_exp / ".git" / "objects"
    pasta_git_legada.mkdir(parents=True)
    obj_readonly = pasta_git_legada / "pack_legado"
    obj_readonly.write_text("objeto git legado", encoding="utf-8")
    os.chmod(obj_readonly, os.stat(obj_readonly).st_mode & ~stat.S_IWRITE)

    gerenciador.compilar_croqui(caminho_exp)

    assert not (caminho_exp / ".git").exists()
    assert (caminho_exp / "compilado" / "compilado.binarypb").is_file()


def test_casos_borda_log_dialog_abrir_sem_yaml_e_compilar_sem_git(gerenciador, storage_temp):
    logs: list[str] = []

    class DialogoLogSimples:
        def adicionar_log(self, msg: str) -> None:
            logs.append(msg)

    # Garante que caminho_repo existente mas sem repositório git válido não quebra _obter_commit_base_sha
    caminho_repo = storage_temp.obter_caminho_base_repo()
    caminho_repo.mkdir(parents=True, exist_ok=True)

    caminho_exp = gerenciador.criar_novo_croqui(
        "br_mg_log", "Pico Log", "MG", "Usuario", log_dialog=DialogoLogSimples()
    )
    assert any("Inicializando compilação" in m for m in logs)
    assert not (caminho_exp / ".git").exists()

    # abrir_croqui em pasta sem croqui_experimental.yaml não falha
    pasta_vazia = storage_temp.obter_caminho_croquis_experimentais() / "sem_meta"
    pasta_vazia.mkdir(parents=True)
    gerenciador.abrir_croqui(pasta_vazia, "Usuario")

    # compilar_croqui em pasta arbitrária sem .git compila sem criar .git
    pasta_sem_git = storage_temp.obter_caminho_croquis_experimentais() / "sem_git"
    (pasta_sem_git / "database").mkdir(parents=True)
    (pasta_sem_git / "database" / "croqui.yaml").write_text(
        "id: br_mg_sem_git\nnome: Sem Git\nultima_migracao: 5\n"
        "picos:\n  - nome: Sem Git\n    estado: MG\n",
        encoding="utf-8",
    )
    gerenciador.compilar_croqui(pasta_sem_git)
    assert not (pasta_sem_git / ".git").exists()
    assert (pasta_sem_git / "compilado" / "compilado.binarypb").is_file()
