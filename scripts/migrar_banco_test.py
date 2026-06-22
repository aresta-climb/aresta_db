import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from scripts.migrar_banco import migrar_todos_os_croquis, obter_lista_migracoes

def test_obter_lista_migracoes(tmp_path):
    # DADO uma pasta migracoes com arquivos válidos e inválidos
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    
    (migracoes_dir / "0001_initial.py").write_text("MIGRATION_ID = 1\n", encoding="utf-8")
    (migracoes_dir / "0002_centralizar.py").write_text("MIGRATION_ID = 2\n", encoding="utf-8")
    (migracoes_dir / "invalid.py").write_text("", encoding="utf-8")
    (migracoes_dir / "0003_algo.txt").write_text("", encoding="utf-8")
    
    # QUANDO pedimos a lista de migrações
    migracoes = obter_lista_migracoes(migracoes_dir)
    
    # ENTÃO deve retornar apenas os válidos, parseados e ordenados
    assert len(migracoes) == 2
    assert migracoes[0][0] == 1
    assert "0001_initial.py" in str(migracoes[0][1])
    assert migracoes[1][0] == 2
    assert "0002_centralizar.py" in str(migracoes[1][1])

def test_migrar_todos_os_croquis(tmp_path, capsys):
    # DADO um banco de dados com croquis e scripts de migração
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    
    # Croqui 1: ultima_migracao = 1
    croqui1_dir = db_dir / "croqui1"
    croqui1_dir.mkdir()
    (croqui1_dir / "croqui.yaml").write_text("id: croqui1\nultima_migracao: 1\n", encoding="utf-8")
    
    # Croqui 2: ultima_migracao = 2
    croqui2_dir = db_dir / "croqui2"
    croqui2_dir.mkdir()
    (croqui2_dir / "croqui.yaml").write_text("id: croqui2\nultima_migracao: 2\n", encoding="utf-8")
    
    # Croqui 3: sem ultima_migracao (deve ser 0)
    croqui3_dir = db_dir / "croqui3"
    croqui3_dir.mkdir()
    (croqui3_dir / "croqui.yaml").write_text("id: croqui3\n", encoding="utf-8")
    
    # Pasta inválida sem croqui.yaml
    invalid_dir = db_dir / "invalid"
    invalid_dir.mkdir()
    
    # DADO scripts de migracao 0001 e 0002
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    
    mig_0001 = migracoes_dir / "0001_initial.py"
    mig_0001.write_text("""
MIGRATION_ID = 1
def migrar(croqui_dir):
    with open(croqui_dir / 'croqui.yaml', 'r', encoding='utf-8') as f:
        data = f.read()
    if 'migracao_1_aplicada' not in data:
        with open(croqui_dir / 'croqui.yaml', 'a', encoding='utf-8') as f:
            f.write('\\nmigracao_1_aplicada: true\\nultima_migracao: 1\\n')
""", encoding="utf-8")

    mig_0002 = migracoes_dir / "0002_centralizar.py"
    mig_0002.write_text("""
MIGRATION_ID = 2
def migrar(croqui_dir):
    with open(croqui_dir / 'croqui.yaml', 'r', encoding='utf-8') as f:
        data = f.read()
    if 'migracao_2_aplicada' not in data:
        with open(croqui_dir / 'croqui.yaml', 'a', encoding='utf-8') as f:
            f.write('\\nmigracao_2_aplicada: true\\nultima_migracao: 2\\n')
""", encoding="utf-8")

    # QUANDO executamos a migração global
    migrar_todos_os_croquis(db_dir, migracoes_dir)
    
    # ENTÃO:
    # Croqui 1 (tinha 1): deve aplicar apenas a 2
    c1 = (croqui1_dir / "croqui.yaml").read_text(encoding="utf-8")
    assert "migracao_1_aplicada" not in c1
    assert "migracao_2_aplicada" in c1
    
    # Croqui 2 (tinha 2): não deve aplicar nenhuma
    c2 = (croqui2_dir / "croqui.yaml").read_text(encoding="utf-8")
    assert "migracao_1_aplicada" not in c2
    assert "migracao_2_aplicada" not in c2
    
    # Croqui 3 (tinha 0): deve aplicar a 1 e depois a 2
    c3 = (croqui3_dir / "croqui.yaml").read_text(encoding="utf-8")
    assert "migracao_1_aplicada" in c3
    assert "migracao_2_aplicada" in c3

def test_migracao_sem_funcao_migrar_ou_id(tmp_path, capsys):
    # DADO um banco de dados
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    croqui1_dir = db_dir / "croqui1"
    croqui1_dir.mkdir()
    (croqui1_dir / "croqui.yaml").write_text("id: croqui1\nultima_migracao: 0\n", encoding="utf-8")
    
    # E um script de migração inválido (faltando função)
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_invalid.py").write_text("MIGRATION_ID = 1\n", encoding="utf-8")
    
    # QUANDO executamos
    with pytest.raises(SystemExit):
        migrar_todos_os_croquis(db_dir, migracoes_dir)
        
    captured = capsys.readouterr()
    assert "não possui uma função 'migrar(croqui_dir)' ou 'MIGRATION_ID'" in captured.out

def test_obter_lista_migracoes_excecao(tmp_path):
    # DADO um script de migração que dá erro no import
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_invalid.py").write_text("import modulo_que_nao_existe\nMIGRATION_ID = 1\n", encoding="utf-8")
    
    # QUANDO pedimos a lista
    migracoes = obter_lista_migracoes(migracoes_dir)
    
    # ENTÃO deve ignorar o erro e retornar vazio
    assert len(migracoes) == 0

def test_migrar_todos_os_croquis_nenhuma_migracao(tmp_path, capsys):
    # DADO nenhuma migração
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    
    # QUANDO executamos
    migrar_todos_os_croquis(db_dir, migracoes_dir)
    
    # ENTÃO deve avisar
    captured = capsys.readouterr()
    assert "Nenhuma migração encontrada." in captured.out

def test_migrar_todos_os_croquis_yaml_invalido(tmp_path):
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    croqui1_dir = db_dir / "croqui1"
    croqui1_dir.mkdir()
    # YAML vazio
    (croqui1_dir / "croqui.yaml").write_text("", encoding="utf-8")
    
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_mig.py").write_text("MIGRATION_ID = 1\ndef migrar(c): pass", encoding="utf-8")
    
    # Executa silenciosamente sem erro e ignora o yaml vazio
    migrar_todos_os_croquis(db_dir, migracoes_dir)

def test_migrar_todos_os_croquis_erro_na_migracao(tmp_path, capsys):
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    croqui1_dir = db_dir / "croqui1"
    croqui1_dir.mkdir()
    (croqui1_dir / "croqui.yaml").write_text("id: t\n", encoding="utf-8")
    
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    (migracoes_dir / "0001_mig.py").write_text("MIGRATION_ID = 1\ndef migrar(c): raise Exception('Erro falho')", encoding="utf-8")
    
    with pytest.raises(SystemExit):
        migrar_todos_os_croquis(db_dir, migracoes_dir)
        
    captured = capsys.readouterr()
    assert "Erro falho" in captured.out

def test_migrar_banco_main(tmp_path, capsys):
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    migracoes_dir = tmp_path / "migracoes"
    migracoes_dir.mkdir()
    
    # Testar __main__ execution path com mock sys.argv
    from scripts import migrar_banco
    
    # Argv curto
    with patch("sys.argv", ["migrar_banco.py"]):
        with pytest.raises(SystemExit):
            migrar_banco.main()
            
    # Diretorio DB invalido
    with patch("sys.argv", ["migrar_banco.py", str(db_dir / "nonexistent"), str(migracoes_dir)]):
        with pytest.raises(SystemExit):
            migrar_banco.main()
            
    # Diretorio Mig invalido
    with patch("sys.argv", ["migrar_banco.py", str(db_dir), str(migracoes_dir / "nonexistent")]):
        with pytest.raises(SystemExit):
            migrar_banco.main()
            
    # Sucesso
    with patch("sys.argv", ["migrar_banco.py", str(db_dir), str(migracoes_dir)]):
        migrar_banco.main()
