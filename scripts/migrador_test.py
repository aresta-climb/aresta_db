# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import py_compile
import sys
import textwrap
from pathlib import Path

import pytest

import scripts.migrador as migrador
from editor.core.serializacao_util import carregar_yaml
from scripts.helpers_migracao import configurar_croqui_teste
from scripts.markdown_frontmatter_lib import parse_md_com_frontmatter


def test_obter_ultima_versao_migracao_vazia(tmp_path: Path) -> None:
    """Testa obter_ultima_versao_migracao quando não há migrações na pasta."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    versao = migrador.obter_ultima_versao_migracao(diretorio_migracoes=migracoes_dir)
    assert versao == 0


def test_obter_ultima_versao_migracao_com_arquivos(tmp_path: Path) -> None:
    """Testa obter_ultima_versao_migracao com várias migrações presentes."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    (migracoes_dir / "0001_migracao.py").write_text("def migrar(c): pass", encoding="utf-8")
    (migracoes_dir / "0002_outra.py").write_text("def migrar(c): pass", encoding="utf-8")
    (migracoes_dir / "0002_test.py").write_text("def test(): pass", encoding="utf-8")
    (migracoes_dir / "invalid_name.py").write_text("def migrar(c): pass", encoding="utf-8")

    versao = migrador.obter_ultima_versao_migracao(diretorio_migracoes=migracoes_dir)
    assert versao == 2


def test_aplicar_migracoes_sucesso(tmp_path: Path) -> None:
    """Testa a execução sequencial de migrações em um croqui."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    migracao_1 = textwrap.dedent("""
        from editor.core.serializacao_util import carregar_yaml, serializar_yaml
        def migrar(caminho_croqui):
            caminho_yaml = caminho_croqui / "croqui.yaml"
            dados = carregar_yaml(caminho_yaml.read_text(encoding="utf-8"))
            dados["passo1"] = True
            caminho_yaml.write_text(serializar_yaml(dados), encoding="utf-8")
    """).strip()

    migracao_2 = textwrap.dedent("""
        from editor.core.serializacao_util import carregar_yaml, serializar_yaml
        def migrar(caminho_croqui):
            caminho_yaml = caminho_croqui / "croqui.yaml"
            dados = carregar_yaml(caminho_yaml.read_text(encoding="utf-8"))
            dados["passo2"] = True
            caminho_yaml.write_text(serializar_yaml(dados), encoding="utf-8")
    """).strip()

    (migracoes_dir / "0001_p1.py").write_text(migracao_1, encoding="utf-8")
    (migracoes_dir / "0002_p2.py").write_text(migracao_2, encoding="utf-8")

    yaml_croqui = """
    id: croqui_teste
    nome: Teste Migrador
    ultima_migracao: 0
    """
    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content=yaml_croqui)

    migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir)

    dados = carregar_yaml((croqui_dir / "croqui.yaml").read_text(encoding="utf-8"))
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

    monkeypatch.setitem(sys.modules, "scripts.finalizar_mapas", None)

    migrador.aplicar_migracoes(croqui_dir)

    dados = carregar_yaml((croqui_dir / "croqui.yaml").read_text(encoding="utf-8"))
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

    migracao_legada = textwrap.dedent("""
        from scripts.finalizar_mapas import parse_md_com_frontmatter, salvar_md_com_frontmatter

        def migrar(caminho_croqui):
            arquivo_md = caminho_croqui / "info.md"
            fm, corpo = parse_md_com_frontmatter(arquivo_md)
            fm = fm or {}
            fm["migrado_com_sucesso"] = True
            salvar_md_com_frontmatter(arquivo_md, fm, corpo)
    """).strip()

    (migracoes_dir / "0001_legada.py").write_text(migracao_legada, encoding="utf-8")

    yaml_croqui = """
    id: croqui_legado
    nome: Croqui Legado
    ultima_migracao: 0
    """
    arquivos = {"info.md": "---\nversao: 1\n---\nCorpo original"}
    croqui_dir = configurar_croqui_teste(
        tmp_path / "croqui_legado", yaml_content=yaml_croqui, arquivos=arquivos
    )

    monkeypatch.delitem(sys.modules, "scripts.finalizar_mapas", raising=False)

    migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir)

    fm_atualizado, corpo_atualizado = parse_md_com_frontmatter(croqui_dir / "info.md")
    assert fm_atualizado is not None
    assert fm_atualizado.get("migrado_com_sucesso") is True
    assert corpo_atualizado == "Corpo original"


def test_aplicar_migracoes_formata_yaml_com_cabecalho_spdx_e_bloco_literal(
    tmp_path: Path,
) -> None:
    """
    Testa se o migrador atualiza ultima_migracao com cabeçalho SPDX e formatação limpa.
    """
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    migracao_1 = "def migrar(caminho_croqui):\n    pass\n"
    (migracoes_dir / "0001_p1.py").write_text(migracao_1, encoding="utf-8")

    yaml_croqui = textwrap.dedent("""
    id: croqui_teste
    nome: Croqui Teste
    descricao: |
      Uma descricao incrivelmente longa que passa de noventa caracteres em uma unica linha de forma direta e sem piedade.
    ultima_migracao: 0
    """).lstrip()

    croqui_dir = configurar_croqui_teste(tmp_path / "croqui_fmt", yaml_croqui)
    yaml_path = croqui_dir / "croqui.yaml"

    migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir)

    yaml_atualizado = yaml_path.read_text(encoding="utf-8")
    assert yaml_atualizado.startswith("# SPDX-License-Identifier: ODbL-1.0\n")
    assert "descricao: |" in yaml_atualizado
    assert "ultima_migracao: 1" in yaml_atualizado


def test_obter_caminho_migracoes_padrao() -> None:
    """Testa que obter_caminho_migracoes retorna a pasta migracoes existente no repo."""
    caminho = migrador.obter_caminho_migracoes()
    assert caminho.name == "migracoes"
    assert caminho.is_dir()


def test_obter_caminho_migracoes_sys_frozen_meipass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Testa que quando executando congelado com PyInstaller, busca em sys._MEIPASS."""
    meipass_migracoes = tmp_path / "meipass" / "migracoes"
    meipass_migracoes.mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "meipass"), raising=False)

    caminho = migrador.obter_caminho_migracoes()
    assert caminho == meipass_migracoes


def test_obter_caminho_migracoes_sys_frozen_macos_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_obter_caminho_migracoes_sys_frozen_macos_trata_excecao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Testa tratamento de exceção ao acessar caminho no macOS quando congelado."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", None)

    caminho = migrador.obter_caminho_migracoes()
    assert caminho.name == "migracoes"


def test_obter_caminho_migracoes_fallback_repo_base(tmp_path: Path) -> None:
    """Testa fallback para provedor_repo_base quando o caminho padrão não existe."""
    repo_migracoes = tmp_path / "repo_base" / "migracoes"
    repo_migracoes.mkdir(parents=True)

    caminho = migrador.obter_caminho_migracoes(
        caminho_padrao=tmp_path / "inexistente" / "migracoes",
        provedor_repo_base=lambda: tmp_path / "repo_base",
    )
    assert caminho == repo_migracoes


def test_obter_caminho_migracoes_fallback_padrao_quando_nada_existe(tmp_path: Path) -> None:
    """Testa que retorna o caminho padrão quando nenhuma alternativa existe."""
    caminho_padrao = tmp_path / "inexistente" / "migracoes"

    caminho = migrador.obter_caminho_migracoes(
        caminho_padrao=caminho_padrao,
        provedor_repo_base=lambda: tmp_path / "repo_inexistente",
    )
    assert caminho == caminho_padrao

    # E também exercita o provedor padrão (GerenciadorCaminhos)
    caminho_default_provider = migrador.obter_caminho_migracoes(caminho_padrao=caminho_padrao)
    assert isinstance(caminho_default_provider, Path)


def test_obter_caminho_migracoes_fallback_ignora_excecao(tmp_path: Path) -> None:
    """Testa que exceções no provedor de fallback são tratadas retornando o caminho padrão."""
    caminho_padrao = tmp_path / "inexistente" / "migracoes"

    def provedor_com_falha() -> Path | None:
        raise RuntimeError("falha simulada")

    caminho = migrador.obter_caminho_migracoes(
        caminho_padrao=caminho_padrao,
        provedor_repo_base=provedor_com_falha,
    )
    assert caminho == caminho_padrao


def test_obter_ultima_versao_migracao_com_arquivos_pyc(tmp_path: Path) -> None:
    """Valida identificação da versão máxima de migração com arquivos de bytecode .pyc."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.pyc").write_bytes(b"pyc")
    (migracoes_dir / "0003_p3.pyc").write_bytes(b"pyc")
    (migracoes_dir / "0003_test.pyc").write_bytes(b"pyc")

    versao = migrador.obter_ultima_versao_migracao(diretorio_migracoes=migracoes_dir)
    assert versao == 3


def test_aplicar_migracoes_com_arquivos_pyc_compilados(tmp_path: Path) -> None:
    """Valida execução de migrações quando apenas arquivos .pyc compilados existem."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    codigo_migracao = textwrap.dedent("""
        from editor.core.serializacao_util import carregar_yaml, serializar_yaml
        def migrar(caminho_croqui):
            caminho_yaml = caminho_croqui / "croqui.yaml"
            dados = carregar_yaml(caminho_yaml.read_text(encoding="utf-8"))
            dados["executou_pyc"] = True
            caminho_yaml.write_text(serializar_yaml(dados), encoding="utf-8")
    """).strip()

    arq_py = migracoes_dir / "0001_teste.py"
    arq_py.write_text(codigo_migracao, encoding="utf-8")
    arq_pyc = migracoes_dir / "0001_teste.pyc"
    py_compile.compile(str(arq_py), cfile=str(arq_pyc), doraise=True)
    arq_py.unlink()

    yaml_croqui = "id: croqui_teste\nultima_migracao: 0\n"
    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content=yaml_croqui)

    migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir)

    dados = carregar_yaml((croqui_dir / "croqui.yaml").read_text(encoding="utf-8"))
    assert dados.get("executou_pyc") is True
    assert dados.get("ultima_migracao") == 1


def test_aplicar_migracoes_prioriza_py_quando_ambos_existem(tmp_path: Path) -> None:
    """Valida que quando existem .py e .pyc para a mesma migração, .py é preferido."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()

    codigo_py = textwrap.dedent("""
        from editor.core.serializacao_util import carregar_yaml, serializar_yaml
        def migrar(caminho_croqui):
            caminho_yaml = caminho_croqui / "croqui.yaml"
            dados = carregar_yaml(caminho_yaml.read_text(encoding="utf-8"))
            dados["origem"] = "fonte_py"
            caminho_yaml.write_text(serializar_yaml(dados), encoding="utf-8")
    """).strip()

    arq_py = migracoes_dir / "0001_teste.py"
    arq_py.write_text(codigo_py, encoding="utf-8")
    arq_pyc = migracoes_dir / "0001_teste.pyc"
    py_compile.compile(str(arq_py), cfile=str(arq_pyc), doraise=True)

    yaml_croqui = "id: croqui_teste\nultima_migracao: 0\n"
    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content=yaml_croqui)

    migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir)

    dados = carregar_yaml((croqui_dir / "croqui.yaml").read_text(encoding="utf-8"))
    assert dados.get("origem") == "fonte_py"
    assert dados.get("ultima_migracao") == 1


def test_aplicar_migracoes_quando_yaml_nao_existe(tmp_path: Path) -> None:
    """Valida retorno imediato (False) quando o arquivo croqui.yaml não existe no diretório."""
    croqui_vazio = tmp_path / "croqui_vazio"
    croqui_vazio.mkdir()
    assert migrador.aplicar_migracoes(croqui_vazio) is False


def test_aplicar_migracoes_ultima_migracao_formato_string_e_invalido(tmp_path: Path) -> None:
    """Valida conversão resiliente de ultima_migracao quando presente como string numérica ou inválida."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.py").write_text("def migrar(c): pass", encoding="utf-8")

    # Caso 1: string numérica ("1") -> não deve rodar migração 1
    croqui_dir1 = configurar_croqui_teste(
        tmp_path / "croqui1", yaml_content="ultima_migracao: '1'\n"
    )
    assert migrador.aplicar_migracoes(croqui_dir1, diretorio_migracoes=migracoes_dir) is False

    # Caso 2: string não convertível ("invalido") -> fallback para 0 e executa migração 1
    croqui_dir2 = configurar_croqui_teste(
        tmp_path / "croqui2", yaml_content="ultima_migracao: 'invalido'\n"
    )
    assert migrador.aplicar_migracoes(croqui_dir2, diretorio_migracoes=migracoes_dir) is True
    dados = carregar_yaml((croqui_dir2 / "croqui.yaml").read_text(encoding="utf-8"))
    assert dados.get("ultima_migracao") == 1


def test_aplicar_migracoes_sem_migracoes_pendentes(tmp_path: Path) -> None:
    """Valida retorno antecipado (False) quando a versão do croqui já é superior ou igual às migrações existentes."""
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_p1.py").write_text("def migrar(c): pass", encoding="utf-8")

    croqui_dir = configurar_croqui_teste(tmp_path / "croqui", yaml_content="ultima_migracao: 5\n")
    assert migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir) is False


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

    with pytest.raises(ValueError, match="Erro fatal"):
        migrador.aplicar_migracoes(croqui_dir, diretorio_migracoes=migracoes_dir)
