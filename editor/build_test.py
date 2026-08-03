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
        with patch("PIL.Image.open") as mock_image_open:
            # Mock da existência do arquivo main.py, logo_app.png e logo.ico
            with patch("pathlib.Path.exists", return_value=True):
                mock_img = MagicMock()
                mock_img.mode = 'RGBA'
                mock_img.width = 16
                mock_img.height = 16
                mock_img.resize.return_value = mock_img
                mock_image_open.return_value = mock_img
                executar_build(force_icon_generation=True)
            
            # 1. Verifica se tentou redimensionar a imagem para as 6 resoluções
            assert mock_img.resize.call_count == 6
            assert mock_img.save.call_count == 1
            
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

def test_executar_build_pula_geracao_se_icone_existe():
    """Valida se pula a geração de imagem se o logo.ico já existir."""
    with patch("PyInstaller.__main__.run"):
        with patch("PIL.Image.open") as mock_image_open:
            # path.exists retorna True para main.py e para logo.ico
            with patch("pathlib.Path.exists", return_value=True):
                executar_build(force_icon_generation=False)
                
            mock_image_open.assert_not_called()

def test_executar_build_forca_geracao_se_flag_passada():
    """Valida se força a geração de imagem mesmo se o logo.ico existir se flag for verdadeira."""
    with patch("PyInstaller.__main__.run"):
        with patch("PIL.Image.open") as mock_image_open:
            with patch("pathlib.Path.exists", return_value=True):
                mock_img = MagicMock()
                mock_img.mode = 'RGBA'
                mock_img.width = 16
                mock_img.height = 16
                mock_img.resize.return_value = mock_img
                mock_image_open.return_value = mock_img
                
                executar_build(force_icon_generation=True)
                
            # open deve ter sido chamado, forçando a geração do ícone
            assert mock_image_open.call_count == 1
