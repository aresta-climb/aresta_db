from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit

class AtualizadorUI:
    """
    Controlador para salvar e restaurar o estado de foco e cursor dos inputs
    da interface de formulário de dados.
    """
    def __init__(self):
        self.campo_focado = None
        self.msg_id_focada = None
        self.posicao_cursor = None

    def salvar_estado_foco(self, formulario):
        """Salva qual widget de input estava com o foco atualmente no formulário."""
        widget_focado = QApplication.focusWidget()
        if not widget_focado:
            # Fallback para o foco local da janela do formulário (útil em testes headless)
            janela = formulario.window()
            if janela:
                widget_focado = janela.focusWidget()

        if widget_focado and formulario.isAncestorOf(widget_focado):
            self.campo_focado = widget_focado.property("protobuf_field")
            self.msg_id_focada = widget_focado.property("protobuf_msg_id")
            
            if isinstance(widget_focado, QLineEdit):
                self.posicao_cursor = widget_focado.cursorPosition()
            elif isinstance(widget_focado, QTextEdit):
                self.posicao_cursor = widget_focado.textCursor().position()
            else:
                self.posicao_cursor = None
        else:
            self.campo_focado = None
            self.msg_id_focada = None
            self.posicao_cursor = None

    def restaurar_estado_foco(self, formulario):
        """Procura o novo widget correspondente e restaura o foco e o cursor."""
        if not self.campo_focado or self.msg_id_focada is None:
            return

        # Encontra recursivamente todos os filhos do formulário
        for widget in formulario.findChildren(object):
            # Verifica se o widget possui as propriedades correspondentes
            field = widget.property("protobuf_field")
            msg_id = widget.property("protobuf_msg_id")
            
            if field == self.campo_focado and msg_id == self.msg_id_focada:
                # Restaura o foco
                widget.setFocus()
                
                # Restaura o cursor
                if self.posicao_cursor is not None:
                    if isinstance(widget, QLineEdit):
                        # Garante que o cursor não passe do limite do novo texto
                        widget.setCursorPosition(min(self.posicao_cursor, len(widget.text())))
                    elif isinstance(widget, QTextEdit):
                        cursor = widget.textCursor()
                        cursor.setPosition(min(self.posicao_cursor, len(widget.toPlainText())))
                        widget.setTextCursor(cursor)
                break
