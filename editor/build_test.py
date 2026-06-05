import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from editor.build import executar_build, DIRETORIO_EDITOR

def test_executar_build_configura_icone_corretamente():
    """
    Valida se o script de build gera o ícone e passa a flag --icon para o PyInstaller.
    """
    # Mock do PyInstaller para evitar a compilação real (que é lenta)
    with patch("PyInstaller.__main__.run") as mock_run:
        # Mock do QPixmap.save e PIL.Image.open para não precisar de ambiente gráfico completo nem arquivos reais
        with patch("PyQt6.QtGui.QPixmap.save", return_value=True) as mock_save:
            with patch("PIL.Image.open") as mock_image_open:
                # Mock da existência do arquivo main.py e logo.ico
                with patch("pathlib.Path.exists", return_value=True):
                    # Mock de Image.open retornar um objeto com atributos width/height
                    mock_img = MagicMock()
                    mock_img.width = 16
                    mock_img.height = 16
                    mock_image_open.return_value = mock_img
                    
                    executar_build()
                
                # 1. Verifica se tentou salvar os frames PNG no buffer (6 resoluções)
                assert mock_save.call_count == 6
                
                # 2. Verifica se o PyInstaller foi chamado com a flag --icon
                argumentos_passados = mock_run.call_args[0][0]
                assert "--icon" in argumentos_passados
                
                # 3. Verifica se o caminho do ícone está correto nos argumentos
                caminho_esperado = str(DIRETORIO_EDITOR / "logo.ico")
                idx = argumentos_passados.index("--icon")
                assert argumentos_passados[idx + 1] == caminho_esperado
                
                # 4. Verifica se o nome do executável está correto
                assert "ArestaEditor" in argumentos_passados

def test_executar_build_falha_se_main_nao_existe():
    """Valida se o build interrompe se o main.py sumir."""
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            executar_build()
