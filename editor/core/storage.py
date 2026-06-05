from PyQt6.QtCore import QStandardPaths
from pathlib import Path
import os

class GerenciadorCaminhos:
    """
    Biblioteca para gerenciar caminhos de armazenamento local do Editor Aresta.
    """
    
    def __init__(self):
        self.nome_app = "aresta_editor"
        
    def obter_diretorio_base(self) -> Path:
        """
        Retorna o caminho base para os dados do aplicativo.
        """
        appdata = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not appdata:
            # Fallback caso writableLocation falhe
            appdata = os.path.expanduser("~/.local/share")
            
        return Path(appdata) / self.nome_app

    def obter_caminho_base_repo(self) -> Path:
        """
        Retorna o caminho para o repositório aresta_db local.
        """
        return self.obter_diretorio_base() / "aresta_db"

    def obter_caminho_croquis_experimentais(self) -> Path:
        """
        Retorna o caminho para a pasta de croquis experimentais.
        """
        return self.obter_diretorio_base() / "croquis_experimentais"

    def obter_caminho_lixeira(self) -> Path:
        """
        Retorna o caminho para o diretório temporário interno da lixeira (.trash_interna).
        """
        return self.obter_diretorio_base() / ".trash_interna"

    def inicializar_diretorios(self):
        """
        Cria a estrutura de pastas necessária se não existir.
        """
        self.obter_diretorio_base().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_base_repo().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_croquis_experimentais().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_lixeira().mkdir(parents=True, exist_ok=True)
