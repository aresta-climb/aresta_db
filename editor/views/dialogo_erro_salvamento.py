# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Union
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from editor.core.telemetria import sanitizar_texto_caminhos


def copiar_para_area_transferencia(texto: str) -> None:
    """Copia o texto fornecido para a área de transferência do sistema."""
    app = QApplication.instance()
    if app:
        clipboard = QApplication.clipboard()
        clipboard.setText(texto)


def criar_dialogo_erro_salvamento(
    pai: Optional[QWidget],
    erro: Union[str, Exception],
    traceback_detalhado: str = ""
) -> QMessageBox:
    """
    Constrói uma caixa de diálogo informativa e acolhedora orientando o usuário
    sobre falhas durante o salvamento ou compilação do croqui, mantendo os
    detalhes técnicos acessíveis em uma seção expansível.
    """
    dialogo = QMessageBox(pai)
    dialogo.setIcon(QMessageBox.Icon.Critical)
    dialogo.setWindowTitle("Não foi possível salvar o croqui")
    dialogo.setText("Não foi possível salvar o croqui.")

    mensagem_informativa = (
        "Ocorreu um erro durante o processo de compilação ou persistência.\n\n"
        "Seus dados em tela permanecem seguros e não foram perdidos. "
        "Você pode tentar salvar novamente ou copiar os detalhes técnicos "
        "para relatar o problema aos desenvolvedores."
    )
    dialogo.setInformativeText(mensagem_informativa)

    texto_erro = str(erro)
    detalhes = f"Erro: {texto_erro}"
    if traceback_detalhado:
        detalhes = f"{detalhes}\n\nDetalhes técnicos e rastreamento:\n{traceback_detalhado}"

    detalhes_sanitizados = sanitizar_texto_caminhos(detalhes)
    dialogo.setDetailedText(detalhes_sanitizados)

    botao_fechar = dialogo.addButton("Fechar", QMessageBox.ButtonRole.RejectRole)
    botao_copiar = dialogo.addButton("Copiar Detalhes", QMessageBox.ButtonRole.ActionRole)
    botao_copiar.clicked.connect(lambda: copiar_para_area_transferencia(detalhes_sanitizados))

    dialogo.setDefaultButton(botao_fechar)
    return dialogo


def exibir_dialogo_erro_salvamento(
    pai: Optional[QWidget],
    erro: Union[str, Exception],
    traceback_detalhado: str = ""
) -> int:
    """
    Constrói e exibe modalmente o diálogo de erro de salvamento amigável.
    """
    dialogo = criar_dialogo_erro_salvamento(pai, erro, traceback_detalhado)
    return dialogo.exec()
