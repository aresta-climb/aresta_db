# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import yaml
from pathlib import Path
from unittest.mock import patch
import scripts.migrador as migrador
from scripts.helpers_migracao import configurar_croqui_teste

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
    with open(croqui_dir / "croqui.yaml", "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
# Copyright (C) 2026 ARESTA
#
# Este arquivo é livre; você pode redistribuí-lo e/ou modificá-lo
# sob os termos da Licença Pública Geral GNU.

import yaml
from pathlib import Path
from unittest.mock import patch
import scripts.migrador as migrador
from scripts.helpers_migracao import configurar_croqui_teste

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
    with open(croqui_dir / "croqui.yaml", "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
        
    assert dados.get("passo1") is True
    assert dados.get("passo2") is True
    assert dados.get("ultima_migracao") == 2


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
    assert "Uma descricao incrivelmente longa que passa de noventa caracteres em uma unica\\n" not in yaml_atualizado
    
    assert "ultima_migracao: 1" in yaml_atualizado
