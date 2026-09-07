# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtCore import QStandardPaths
from pathlib import Path
import os


def obter_diretorio_base_app() -> Path:
    """
    Retorna o caminho canônico do diretório de dados do aplicativo.
    - Windows: %APPDATA%/EditorAresta
    - Linux/Mac: ~/.local/share/EditorAresta (ou QStandardPaths)
    """
    appdata = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not appdata:
        appdata_env = os.environ.get("APPDATA")
        if appdata_env:
            return Path(appdata_env) / "EditorAresta"
        return Path.home() / ".local" / "share" / "EditorAresta"
    return Path(appdata)


class GerenciadorCaminhos:
    """
    Biblioteca para gerenciar caminhos de armazenamento local do Editor Aresta.
    """
    
    def __init__(self) -> None:
        self.nome_app: str = "editor_aresta"
        
    def obter_diretorio_base(self) -> Path:
        """
        Retorna o caminho base para os dados do aplicativo.
        """
        return obter_diretorio_base_app()

    def obter_caminho_recurso_interno(self, caminho_relativo: str) -> Path:
        """
        Retorna o caminho absoluto para um recurso interno empacotado (ex: imagens).
        Lida corretamente com o sys._MEIPASS quando compilado com PyInstaller
        e respeita sobreposições de canais ativos (ex: canal Beta).
        """
        from editor.core.configuracao_canal import obter_configuracao_canal
        config = obter_configuracao_canal()
        if config.eh_beta:
            nome_arquivo = Path(caminho_relativo).name
            caminho_canal = config.obter_caminho_recurso(nome_arquivo)
            if caminho_canal.exists():
                return caminho_canal

        import sys
        if hasattr(sys, '_MEIPASS'):
            base_path = Path(sys._MEIPASS)
        else:
            # Como storage.py está em editor/core, voltamos um nível para chegar em editor/
            base_path = Path(__file__).resolve().parent.parent
            
        return base_path / caminho_relativo

    def obter_caminho_base_repo(self) -> Path:
        """
        Retorna o caminho para o repositório aresta_db local.
        """
        return self.obter_diretorio_base() / "aresta_db"

    def obter_caminho_croquis_experimentais(self) -> Path:
        """
        Retorna o caminho para a pasta de croquis locais (experimentais).
        """
        return self.obter_diretorio_base() / "croquis"

    def obter_caminho_diarios_locais(self) -> Path:
        """
        Retorna o caminho para o diretório de diários locais (persistência temporária do modo repositório).
        """
        return self.obter_diretorio_base() / "diarios_locais"

    def obter_caminho_lixeira(self) -> Path:
        """
        Retorna o caminho para o diretório temporário interno da lixeira (.trash_interna).
        """
        return self.obter_diretorio_base() / ".trash_interna"

    def migrar_dados_legados_se_necessario(self) -> None:
        """
        Migra croquis e sessão da pasta legada 'Editor Aresta' para a pasta ativa
        (ex: 'Editor Aresta (Beta)') caso existam e ainda não estejam presentes.
        """
        base_atual = self.obter_diretorio_base()
        base_legada = base_atual.parent / "Editor Aresta"
        if base_legada.exists() and base_legada != base_atual:
            pasta_croquis_legados = base_legada / "croquis"
            pasta_croquis_atual = self.obter_caminho_croquis_experimentais()
            if pasta_croquis_legados.is_dir():
                import shutil
                for item in pasta_croquis_legados.iterdir():
                    destino = pasta_croquis_atual / item.name
                    if item.is_dir() and not destino.exists():
                        shutil.copytree(item, destino)

            sessao_legada = base_legada / ".sessao_auth.enc"
            sessao_atual = base_atual / ".sessao_auth.enc"
            if sessao_legada.is_file() and not sessao_atual.exists():
                import shutil
                shutil.copy2(sessao_legada, sessao_atual)

    def inicializar_diretorios(self) -> None:
        """
        Cria a estrutura de pastas necessária se não existir.
        """
        self.obter_diretorio_base().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_base_repo().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_croquis_experimentais().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_diarios_locais().mkdir(parents=True, exist_ok=True)
        self.obter_caminho_lixeira().mkdir(parents=True, exist_ok=True)
        self.migrar_dados_legados_se_necessario()


