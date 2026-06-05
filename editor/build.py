import PyInstaller.__main__
import os
import sys
import argparse
import pytest
from pathlib import Path

# Caminhos
DIRETORIO_EDITOR = Path(__file__).parent.resolve()
ARQUIVO_MAIN = DIRETORIO_EDITOR / "main.py"

def executar_build():
    """
    Executa o empacotamento do editor utilizando PyInstaller.
    Gera um executável standalone na pasta dist/.
    """
    if not ARQUIVO_MAIN.exists():
        raise FileNotFoundError(f"Arquivo principal não encontrado: {ARQUIVO_MAIN}")

    # Argumentos do PyInstaller
    argumentos = [
        str(ARQUIVO_MAIN),
        "--onefile",
        "--windowed",
        "--name", "ArestaEditor",
        "--clean",
        "--noconfirm",
        "--collect-all", "pygit2",
        "--collect-all", "keyring",
        "--collect-all", "qtawesome",
        "--distpath", str(DIRETORIO_EDITOR / "dist"),
        "--workpath", str(DIRETORIO_EDITOR / "build"),
        "--specpath", str(DIRETORIO_EDITOR),
    ]

    # Gera o ícone .ico dinamicamente para o executável
    try:
        try:
            from editor.views.estilo import Icones
        except ImportError:
            from views.estilo import Icones
            
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QBuffer
        from PIL import Image
        import io
        
        # O Qt exige uma instância de QApplication para operações de QIcon/QPixmap
        _app = QApplication.instance() or QApplication(sys.argv)
        
        caminho_icone = DIRETORIO_EDITOR / "logo.ico"
        
        # Gera múltiplas resoluções para um .ico profissional (Windows)
        tamanhos = [16, 32, 48, 64, 128, 256]
        imagens_pil = []
        for tam in tamanhos:
            pixmap = Icones.obter("logo", cor="#556b2f").pixmap(tam, tam)
            buffer = QBuffer()
            buffer.open(QBuffer.OpenModeFlag.ReadWrite)
            pixmap.save(buffer, "PNG")
            imagens_pil.append(Image.open(io.BytesIO(buffer.data().data())).copy())
            
        # Salva o arquivo .ico com todas as resoluções embutidas
        imagens_pil[-1].save(
            str(caminho_icone), 
            format='ICO', 
            sizes=[(img.width, img.height) for img in imagens_pil]
        )
        
        if caminho_icone.exists():
            argumentos.extend(["--icon", str(caminho_icone)])
            print(f"Ícone multi-resolução (16-256px) configurado: {caminho_icone}")
    except Exception as e:
        print(f"Aviso: Não foi possível gerar o arquivo .ico (usando padrão): {e}")

    print(f"Iniciando build do Editor Aresta a partir de {ARQUIVO_MAIN}...")
    PyInstaller.__main__.run(argumentos)
    print("Build concluído com sucesso!")

def executar_testes():
    """
    Executa todos os testes do editor utilizando pytest.
    """
    print(f"Executando testes em {DIRETORIO_EDITOR}...")
    # Executa o pytest no diretório do editor
    # O pytest automaticamente encontrará arquivos **/*_test.py
    resultado = pytest.main([str(DIRETORIO_EDITOR), "-v"])
    
    if resultado == 0:
        print("Todos os testes passaram!")
    else:
        print(f"Alguns testes falharam (código de saída: {resultado})")
    
    sys.exit(resultado)

def main(argv=None):
    parser = argparse.ArgumentParser(description="Script de build e testes do Aresta Editor")
    parser.add_argument(
        "modo", 
        choices=["test", "dist"], 
        help="Modo de operação: 'test' para rodar testes, 'dist' para compilar o executável"
    )
    
    args = parser.parse_args(argv)
    
    if args.modo == "test":
        executar_testes()
    elif args.modo == "dist":
        executar_build()

if __name__ == "__main__":
    main()
