# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Any
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication

def obter_pacote_atual():
    """
    Tenta obter o objeto Package.current via WinRT no Windows.
    Retorna o pacote ou levanta OSError/ImportError em ambiente não-Windows ou sem identidade de pacote.
    """
    if sys.platform != "win32":
        raise OSError(15700, "Ambiente não-Windows: identidade de pacote MSIX não suportada.")
    try:
        from winrt.windows.applicationmodel import Package
        return Package.current
    except Exception as e:
        raise OSError(15700, f"Processo sem identidade de pacote: {e}")

def obter_contexto_loja():
    """
    Obtém a instância padrão de StoreContext via WinRT no Windows.
    """
    if sys.platform != "win32":
        raise OSError(15700, "Ambiente não-Windows: StoreContext não suportado.")
    try:
        from winrt.windows.services.store import StoreContext
        return StoreContext.get_default()
    except Exception as e:
        raise OSError(15700, f"Falha ao obter StoreContext: {e}")

class StatusAtualizacao(Enum):
    NAO_APLICAVEL = "nao_aplicavel"
    SEM_ATUALIZACAO = "sem_atualizacao"
    ATUALIZACAO_DISPONIVEL = "atualizacao_disponivel"
    ATUALIZACAO_OBRIGATORIA = "atualizacao_obrigatoria"
    ERRO_CHECAGEM = "erro_checagem"

@dataclass
class ResultadoAtualizacao:
    status: StatusAtualizacao
    versao_disponivel: Optional[str] = None
    mensagem: Optional[str] = None
    pacotes_atualizacao: List[Any] = field(default_factory=list)

    @property
    def tem_atualizacao(self) -> bool:
        return self.status in (StatusAtualizacao.ATUALIZACAO_DISPONIVEL, StatusAtualizacao.ATUALIZACAO_OBRIGATORIA)

    @property
    def obrigatoria(self) -> bool:
        return self.status == StatusAtualizacao.ATUALIZACAO_OBRIGATORIA

class ServicoLoja:
    """
    Serviço autônomo (Library-First) para gerenciamento de atualizações via Microsoft Store.
    Fornece verificação assíncrona, estratégia híbrida de instalação e bypass em dev.
    """
    ID_PRODUTO_PADRAO = "9NBLGGH4NNS1" # ID do produto na Microsoft Store

    def __init__(self, id_produto: Optional[str] = None):
        self.id_produto = id_produto or self.ID_PRODUTO_PADRAO

    def possui_identidade_pacote(self) -> bool:
        """
        Verifica se o processo atual está executando dentro de um pacote MSIX com identidade.
        """
        try:
            pacote = obter_pacote_atual()
            return pacote is not None and hasattr(pacote, "id") and bool(pacote.id.name)
        except Exception:
            return False

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """
        Consulta a Microsoft Store por atualizações disponíveis.
        Se executado fora da Store (ex: ambiente dev), retorna status NAO_APLICAVEL.
        """
        if not self.possui_identidade_pacote():
            return ResultadoAtualizacao(
                status=StatusAtualizacao.NAO_APLICAVEL,
                mensagem="Executando fora do ambiente Microsoft Store (bypass ativo)."
            )

        try:
            contexto = obter_contexto_loja()
            # No WinRT Python, métodos síncronos/assíncronos podem ser chamados diretamente ou via async
            if hasattr(contexto, "get_app_and_optional_store_package_updates"):
                updates = contexto.get_app_and_optional_store_package_updates()
            elif hasattr(contexto, "get_app_and_optional_store_package_updates_async"):
                updates = contexto.get_app_and_optional_store_package_updates_async()
            else:
                updates = []

            if not updates:
                return ResultadoAtualizacao(
                    status=StatusAtualizacao.SEM_ATUALIZACAO,
                    mensagem="O aplicativo está na versão mais recente."
                )

            eh_obrigatoria = any(getattr(u, "is_mandatory", False) for u in updates)
            primeiro_update = updates[0]
            
            versao_str = None
            try:
                pkg_version = primeiro_update.package.id.version
                versao_str = f"{pkg_version.major}.{pkg_version.minor}.{pkg_version.build}.{pkg_version.revision}"
            except Exception:
                pass

            status = StatusAtualizacao.ATUALIZACAO_OBRIGATORIA if eh_obrigatoria else StatusAtualizacao.ATUALIZACAO_DISPONIVEL

            return ResultadoAtualizacao(
                status=status,
                versao_disponivel=versao_str,
                mensagem="Nova versão disponível na Microsoft Store.",
                pacotes_atualizacao=list(updates)
            )

        except Exception as e:
            return ResultadoAtualizacao(
                status=StatusAtualizacao.ERRO_CHECAGEM,
                mensagem=f"Erro ao consultar a Microsoft Store: {str(e)}"
            )

    def solicitar_instalacao_atualizacao(self, resultado: Optional[ResultadoAtualizacao] = None, parent_hwnd: Any = None) -> bool:
        """
        Executa a instalação da atualização adotando a estratégia híbrida:
        1. Tenta acionar a UI in-app nativa via WinRT (RequestDownloadAndInstallStorePackageUpdatesAsync).
        2. Se falhar ou não estiver disponível, faz o fallback abrindo o protocolo ms-windows-store://.
        """
        try:
            pacotes = resultado.pacotes_atualizacao if resultado else []
            if not pacotes:
                # Se não foram fornecidos pacotes, busca novamente
                res = self.verificar_atualizacoes_disponiveis()
                pacotes = res.pacotes_atualizacao

            if pacotes:
                contexto = obter_contexto_loja()
                if hasattr(contexto, "request_download_and_install_store_package_updates"):
                    operacao = contexto.request_download_and_install_store_package_updates(pacotes)
                    return True
                elif hasattr(contexto, "request_download_and_install_store_package_updates_async"):
                    operacao = contexto.request_download_and_install_store_package_updates_async(pacotes)
                    return True

            # Se não conseguiu pelo WinRT, recorre ao fallback
            return self.abrir_pagina_na_loja()
        except Exception:
            return self.abrir_pagina_na_loja()

    def abrir_pagina_na_loja(self, id_produto: Optional[str] = None) -> bool:
        """
        Abre a página do produto diretamente na Microsoft Store via protocolo URI e comanda o encerramento do app.
        """
        pid = id_produto or self.id_produto
        url_loja = f"ms-windows-store://pdp/?ProductId={pid}"
        aberto = QDesktopServices.openUrl(QUrl(url_loja))
        QApplication.quit()
        return aberto
