# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

import scripts.migrador as migrador
from scripts.helpers_migracao import configurar_croqui_teste
from scripts.markdown_frontmatter_lib import parse_md_com_frontmatter


class MockedPath:
    def __init__(self, target_dir: Path):
        self.target_dir = target_dir

    def resolve(self):
        return self

    @property
    def parent(self):
        return self

    def __truediv__(self, other):
        if other == "migracoes":
            return self.target_dir
        return Path(other)


def test_obter_ultima_versao_migracao_vazia(tmp_path):
    """
    Testa obter_ultima_versao_migracao quando não há migrações na pasta.
    """
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    mock_path = MockedPath(migracoes_dir)
    with patch("scripts.migrador.Path", return_value=mock_path):
        versao = migrador.obter_ultima_versao_migracao()
        assert versao == 0


def test_obter_ultima_versao_migracao_com_arquivos(tmp_path):
    """
    Testa obter_ultima_versao_migracao com várias migrações presentes.
    """
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    # Cria arquivos de migração simulados
    (migracoes_dir / "0001_migracao.py").write_text("def migrar(c): pass")
    (migracoes_dir / "0002_outra.py").write_text("def migrar(c): pass")
    (migracoes_dir / "0002_test.py").write_text("def test(): pass")  # Deve ser ignorado
    (migracoes_dir / "invalid_name.py").write_text("def migrar(c): pass")  # Deve ser ignorado

    mock_path = MockedPath(migracoes_dir)
    with patch("scripts.migrador.Path", return_value=mock_path):
        versao = migrador.obter_ultima_versao_migracao()
        assert versao == 2


def test_aplicar_migracoes_sucesso(tmp_path):
    """
    Testa a execução sequencial de migrações em um croqui.
    """
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    # Escreve migrações fictícias que alteram um campo no yaml do croqui
    migracao_1 = """
    import yaml
    def migrar(caminho_croqui):
        caminho_yaml = caminho_croqui / "croqui.yaml"
        with open(caminho_yaml, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        dados["passo1"] = True
        with open(caminho_yaml, "w", encoding="utf-8") as f:
            yaml.dump(dados, f)
    """

    migracao_2 = """
    import yaml
    def migrar(caminho_croqui):
        caminho_yaml = caminho_croqui / "croqui.yaml"
        with open(caminho_yaml, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        dados["passo2"] = True
        with open(caminho_yaml, "w", encoding="utf-8") as f:
            yaml.dump(dados, f)
    """

    import textwrap

    migracao_1 = textwrap.dedent(migracao_1).strip()
    migracao_2 = textwrap.dedent(migracao_2).strip()

    (migracoes_dir / "0001_p1.py").write_text(migracao_1, encoding="utf-8")
    (migracoes_dir / "0002_p2.py").write_text(migracao_2, encoding="utf-8")

    # Configura croqui de teste com ultima_migracao = 0
    yaml_croqui = """
    id: croqui_teste
    nome: Teste Migrador
    ultima_migracao: 0
    """
    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content=yaml_croqui)

    mock_path = MockedPath(migracoes_dir)
    with patch("scripts.migrador.Path", return_value=mock_path):
        migrador.aplicar_migracoes(croqui_dir)

    # Verifica se ambas as migrações foram aplicadas e o ID final atualizado
    with open(croqui_dir / "croqui.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    assert dados.get("passo1") is True
    assert dados.get("passo2") is True
    assert dados.get("ultima_migracao") == 2


def test_aplicar_migracoes_reais_com_migracao_0003_sem_scripts_finalizar_mapas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Testa que a aplicação das migrações reais do repositório (em especial a 0003)
    funciona mesmo em ambientes empacotados onde scripts.finalizar_mapas não existe.
    """
    yaml_croqui = """
    id: croqui_migracao_0003
    nome: Pico com Mapas Gerais
    ultima_migracao: 2
    botoes:
      - texto: Mapas Gerais
        destino:
          secao_textual:
            caminho: mapas_gerais.md
    picos:
      - nome: Pico Principal
    """
    arquivos = {
        "mapas_gerais.md": """---
titulo: Mapas
---
![Acesso](imagens/mapas_gerais/p0.webp)
"""
    }
    croqui_dir = configurar_croqui_teste(
        tmp_path / "croqui_real", yaml_content=yaml_croqui, arquivos=arquivos
    )

    # Simula ambiente onde scripts.finalizar_mapas não está acessível como módulo
    monkeypatch.setitem(sys.modules, "scripts.finalizar_mapas", None)

    # Executa as migrações reais do repositório
    migrador.aplicar_migracoes(croqui_dir)

    with open(croqui_dir / "croqui.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    assert dados.get("ultima_migracao") >= 3
    assert (croqui_dir / "mapas_gerais.md").exists()


def test_aplicar_migracoes_compatibilidade_legada_scripts_finalizar_mapas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Testa que scripts de migração antigos contendo 'from scripts.finalizar_mapas import ...'
    continuam sendo executados com sucesso graças ao fallback de compatibilidade do migrador.
    """
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    migracao_legada = """
from scripts.finalizar_mapas import parse_md_com_frontmatter, salvar_md_com_frontmatter

def migrar(caminho_croqui):
    arquivo_md = caminho_croqui / "info.md"
    fm, corpo = parse_md_com_frontmatter(arquivo_md)
    fm = fm or {}
    fm["migrado_com_sucesso"] = True
    salvar_md_com_frontmatter(arquivo_md, fm, corpo)
"""
    import textwrap

    (migracoes_dir / "0001_legada.py").write_text(
        textwrap.dedent(migracao_legada).strip(), encoding="utf-8"
    )

    yaml_croqui = """
    id: croqui_legado
    nome: Croqui Legado
    ultima_migracao: 0
    """
    arquivos = {"info.md": "---\nversao: 1\n---\nCorpo original"}
    croqui_dir = configurar_croqui_teste(
        tmp_path / "croqui_legado", yaml_content=yaml_croqui, arquivos=arquivos
    )

    # Força sys.modules a não ter scripts.finalizar_mapas previamente
    monkeypatch.delitem(sys.modules, "scripts.finalizar_mapas", raising=False)

    mock_path = MockedPath(migracoes_dir)
    with patch("scripts.migrador.Path", return_value=mock_path):
        migrador.aplicar_migracoes(croqui_dir)

    fm_atualizado, corpo_atualizado = parse_md_com_frontmatter(croqui_dir / "info.md")
    assert fm_atualizado is not None
    assert fm_atualizado.get("migrado_com_sucesso") is True
    assert corpo_atualizado == "Corpo original"


def test_aplicar_migracoes_preserva_formatacao_width_90(tmp_path):
    """
    Testa se o migrador atualiza ultima_migracao mantendo a formatação com
    width=90 e sem gerar caracteres de escape/contrabarra para continuar linhas.
    """
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    # Escreve uma migração vazia
    migracao_1 = "def migrar(caminho_croqui):\n    pass\n"
    (migracoes_dir / "0001_p1.py").write_text(migracao_1, encoding="utf-8")

    # Configura croqui de teste com ultima_migracao = 0 e descricao longa (que passa de 90 chars na mesma linha)
    import textwrap

    yaml_croqui = textwrap.dedent("""
    id: croqui_teste
    nome: Croqui Teste
    descricao: >
      Uma descricao incrivelmente longa que passa de noventa caracteres em uma unica linha de forma direta e sem piedade.
    ultima_migracao: 0
    """).lstrip()

    croqui_dir = configurar_croqui_teste(tmp_path, yaml_croqui)
    yaml_path = croqui_dir / "croqui.yaml"

    mock_path = MockedPath(migracoes_dir)
    with patch("scripts.migrador.Path", return_value=mock_path):
        migrador.aplicar_migracoes(croqui_dir)

    # Lê o arquivo atualizado como texto puro
    yaml_atualizado = yaml_path.read_text(encoding="utf-8")

    # Verifica se a descricao NÃO possui backslashes (\) gerados pelo PyYAML no final da linha
    assert "\\\n" not in yaml_atualizado

    # Verifica se o texto sofreu quebra por ter mais que 90 chars mas de forma yaml safe usando bloco
    assert (
        "Uma descricao incrivelmente longa que passa de noventa caracteres em uma unica\\n"
        not in yaml_atualizado
    )

    assert "ultima_migracao: 1" in yaml_atualizado


def test_obter_caminho_migracoes_padrao():
    """Testa que obter_caminho_migracoes retorna a pasta migracoes existente no repo."""
    caminho = migrador.obter_caminho_migracoes()
    assert caminho.name == "migracoes"
    assert caminho.is_dir()


def test_obter_caminho_migracoes_sys_frozen_meipass(tmp_path, monkeypatch):
    """Testa que quando executando congelado com PyInstaller, busca em sys._MEIPASS."""
    meipass_migracoes = tmp_path / "meipass" / "migracoes"
    meipass_migracoes.mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)

    caminho = migrador.obter_caminho_migracoes()
    assert caminho == meipass_migracoes


def test_obter_caminho_migracoes_sys_frozen_macos_resources(tmp_path, monkeypatch):
    """Testa que quando congelado no macOS, busca prioritariamente em Contents/Resources/migracoes."""
    app_contents = tmp_path / "EditorAresta.app" / "Contents"
    macos_dir = app_contents / "MacOS"
    resources_dir = app_contents / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)
    resources_migracoes = resources_dir / "migracoes"
    resources_migracoes.mkdir()

    falso_executavel = macos_dir / "EditorAresta"
    falso_executavel.write_bytes(b"bin")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", str(falso_executavel))

    caminho = migrador.obter_caminho_migracoes()
    assert caminho == resources_migracoes


def test_obter_caminho_migracoes_sys_frozen_macos_trata_excecao(monkeypatch):
    """Testa tratamento de exceção ao acessar caminho no macOS quando congelado."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", None)

    caminho = migrador.obter_caminho_migracoes()
    assert caminho.name == "migracoes"


def test_obter_caminho_migracoes_fallback_repo_base(tmp_path, monkeypatch):
    """Testa fallback para GerenciadorCaminhos().obter_caminho_base_repo() quando padrao nao existe."""
    repo_migracoes = tmp_path / "repo_base" / "migracoes"
    repo_migracoes.mkdir(parents=True)

    class FakeGerenciadorCaminhos:
        def obter_caminho_base_repo(self):
            return tmp_path / "repo_base"

    monkeypatch.setattr(
        migrador,
        "_obter_caminho_padrao_migracoes",
        lambda: tmp_path / "inexistente" / "migracoes",
    )

    with patch("editor.core.storage.GerenciadorCaminhos", FakeGerenciadorCaminhos):
        caminho = migrador.obter_caminho_migracoes()
        assert caminho == repo_migracoes


def test_obter_caminho_migracoes_fallback_padrao_quando_nada_existe(tmp_path, monkeypatch):
    """Testa que retorna o caminho padrao quando nenhuma alternativa existe."""
    caminho_padrao = tmp_path / "inexistente" / "migracoes"
    monkeypatch.setattr(migrador, "_obter_caminho_padrao_migracoes", lambda: caminho_padrao)

    class FakeGerenciadorCaminhosSemRepo:
        def obter_caminho_base_repo(self):
            return tmp_path / "repo_inexistente"

    with patch("editor.core.storage.GerenciadorCaminhos", FakeGerenciadorCaminhosSemRepo):
        caminho = migrador.obter_caminho_migracoes()
        assert caminho == caminho_padrao


def test_obter_caminho_migracoes_fallback_ignora_excecao(tmp_path, monkeypatch):
    """Testa que excecoes no fallback sao tratadas retornando o caminho padrao."""
    caminho_padrao = tmp_path / "inexistente" / "migracoes"
    monkeypatch.setattr(migrador, "_obter_caminho_padrao_migracoes", lambda: caminho_padrao)

    with patch(
        "scripts.migrador._obter_caminho_repo_base_fallback",
        side_effect=Exception("falha simulada"),
    ):
        caminho = migrador.obter_caminho_migracoes()
        assert caminho == caminho_padrao


def test_obter_caminho_repo_base_fallback_excecao(monkeypatch):
    """Testa que excecoes dentro de _obter_caminho_repo_base_fallback retornam None."""
    from editor.core import storage

    def falha():
        raise RuntimeError("falha storage")

    monkeypatch.setattr(storage, "GerenciadorCaminhos", falha)
    assert migrador._obter_caminho_repo_base_fallback() is None


def test_obter_ultima_versao_migracao_com_arquivos_pyc(tmp_path: Path) -> None:
    """Valida identificação da versão máxima de migração com arquivos de bytecode .pyc."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.pyc").write_bytes(b"pyc")
    (migracoes_dir / "0003_p3.pyc").write_bytes(b"pyc")
    (migracoes_dir / "0003_test.pyc").write_bytes(b"pyc")  # Deve ser ignorado

    mock_path = MockedPath(migracoes_dir)
    with patch("scripts.migrador.Path", return_value=mock_path):
        versao = migrador.obter_ultima_versao_migracao()
        assert versao == 3


def test_aplicar_migracoes_com_arquivos_pyc_compilados(tmp_path: Path) -> None:
    """Valida execução de migrações quando apenas arquivos .pyc compilados existem (cenário de produção)."""
    import py_compile
    import textwrap

    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    codigo_migracao = textwrap.dedent("""
    import yaml
    def migrar(caminho_croqui):
        caminho_yaml = caminho_croqui / "croqui.yaml"
        with open(caminho_yaml, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        dados["executou_pyc"] = True
        with open(caminho_yaml, "w", encoding="utf-8") as f:
            yaml.dump(dados, f)
    """).strip()

    arq_py = migracoes_dir / "0001_teste.py"
    arq_py.write_text(codigo_migracao, encoding="utf-8")
    arq_pyc = migracoes_dir / "0001_teste.pyc"
    py_compile.compile(str(arq_py), cfile=str(arq_pyc), doraise=True)
    arq_py.unlink()  # Exclui o arquivo fonte .py

    yaml_croqui = "id: croqui_teste\nultima_migracao: 0\n"
    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content=yaml_croqui)

    with patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir):
        migrador.aplicar_migracoes(croqui_dir)

    with open(croqui_dir / "croqui.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    assert dados.get("executou_pyc") is True
    assert dados.get("ultima_migracao") == 1


def test_aplicar_migracoes_prioriza_py_quando_ambos_existem(tmp_path: Path) -> None:
    """Valida que quando existem .py e .pyc para a mesma migração, não há duplicação e .py é preferido."""
    import py_compile
    import textwrap

    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    codigo_py = textwrap.dedent("""
    import yaml
    def migrar(caminho_croqui):
        caminho_yaml = caminho_croqui / "croqui.yaml"
        with open(caminho_yaml, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        dados["origem"] = "fonte_py"
        with open(caminho_yaml, "w", encoding="utf-8") as f:
            yaml.dump(dados, f)
    """).strip()

    arq_py = migracoes_dir / "0001_teste.py"
    arq_py.write_text(codigo_py, encoding="utf-8")
    arq_pyc = migracoes_dir / "0001_teste.pyc"
    py_compile.compile(str(arq_py), cfile=str(arq_pyc), doraise=True)

    yaml_croqui = "id: croqui_teste\nultima_migracao: 0\n"
    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content=yaml_croqui)

    with patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir):
        migrador.aplicar_migracoes(croqui_dir)

    with open(croqui_dir / "croqui.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    assert dados.get("origem") == "fonte_py"
    assert dados.get("ultima_migracao") == 1


def test_aplicar_migracoes_quando_yaml_nao_existe(tmp_path: Path) -> None:
    """Valida retorno imediato quando o arquivo croqui.yaml não existe no diretório."""
    croqui_vazio = tmp_path / "croqui_vazio"
    croqui_vazio.mkdir()
    migrador.aplicar_migracoes(croqui_vazio)


def test_aplicar_migracoes_ultima_migracao_formato_string_e_invalido(tmp_path: Path) -> None:
    """Valida conversão resiliente de ultima_migracao quando presente como string numérica ou inválida."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.py").write_text("def migrar(c): pass", encoding="utf-8")

    # Caso 1: string numérica ("1") -> não deve rodar migração 1
    croqui_dir1 = configurar_croqui_teste(
        tmp_path / "croqui1", yaml_content="ultima_migracao: '1'\n"
    )
    with patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir):
        migrador.aplicar_migracoes(croqui_dir1)

    # Caso 2: string não convertível ("invalido") -> fallback para 0 e executa migração 1
    croqui_dir2 = configurar_croqui_teste(
        tmp_path / "croqui2", yaml_content="ultima_migracao: 'invalido'\n"
    )
    with patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir):
        migrador.aplicar_migracoes(croqui_dir2)
    with open(croqui_dir2 / "croqui.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    assert dados.get("ultima_migracao") == 1


def test_aplicar_migracoes_sem_migracoes_pendentes(tmp_path: Path) -> None:
    """Valida retorno antecipado quando a versão do croqui já é superior ou igual às migrações existentes."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.py").write_text("def migrar(c): pass", encoding="utf-8")

    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content="ultima_migracao: 5\n")
    with patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir):
        migrador.aplicar_migracoes(croqui_dir)


def test_aplicar_migracoes_modulo_sem_loader(tmp_path: Path) -> None:
    """Valida tratamento seguro quando importlib retorna spec sem loader."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.py").write_text("def migrar(c): pass", encoding="utf-8")

    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content="ultima_migracao: 0\n")

    with (
        patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir),
        patch("importlib.util.spec_from_file_location", return_value=None),
    ):
        migrador.aplicar_migracoes(croqui_dir)


def test_aplicar_migracoes_falha_na_execucao_relanca_excecao(tmp_path: Path) -> None:
    """Valida que exceções levantadas na função migrar() são registradas e relançadas."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_falha.py").write_text(
        "def migrar(c): raise ValueError('Erro fatal')", encoding="utf-8"
    )

    croqui_dir = configurar_croqui_teste(
        tmp_path / "croqui_falha", yaml_content="ultima_migracao: 0\n"
    )

    with patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir):
        with pytest.raises(ValueError, match="Erro fatal"):
            migrador.aplicar_migracoes(croqui_dir)


def test_obter_e_aplicar_migracoes_ignora_excecao_conversao_inteiro(tmp_path: Path) -> None:
    """Valida tratamento defensivo caso a conversão para inteiro falhe em nomes compatíveis com a regex."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_teste.py").write_text("def migrar(c): pass", encoding="utf-8")

    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content="ultima_migracao: 0\n")

    mock_match = MagicMock()
    mock_match.group.return_value = "invalido"
    mock_regex = MagicMock()
    mock_regex.match.return_value = mock_match

    with (
        patch("scripts.migrador.obter_caminho_migracoes", return_value=migracoes_dir),
        patch.object(migrador, "EXPRESSAO_MIGRACAO", mock_regex),
    ):
        migrador.aplicar_migracoes(croqui_dir)
        assert migrador.obter_ultima_versao_migracao() == 0
