# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any


from editor.core.classificador_mensagens import eh_linha_de_erro, eh_linha_de_aviso


class CompilacaoController:
    """Controlador que faz a mediação entre a saída da compilação, o modelo de log e a view."""
    
    def __init__(self, model: Any, view: Any) -> None:
        self.model: Any = model
        self.view: Any = view

    def processar_resultado(self, mensagens: list[str]) -> None:
        """Recebe as mensagens, atualiza o modelo e decide se mostra ou oculta o painel."""
        self.model.atualizar(mensagens)
        
        if self.model.tem_avisos_ou_erros():
            html_formatado = self._formatar_para_html(mensagens)
            self.view.atualizar_texto(html_formatado)
            self.view.exibir_painel()
        else:
            self.view.ocultar_painel()


    def _formatar_para_html(self, mensagens: list[str]) -> str:
        """Formata as strings em HTML aplicando cores de acordo com erros e avisos."""
        linhas_html = []
        
        for msg in mensagens:
            cor = "#333333"  # Padrão
            
            if eh_linha_de_erro(msg):
                cor = "#D32F2F"  # Vermelho forte (Material)
            elif eh_linha_de_aviso(msg):
                cor = "#F57C00"  # Laranja forte (Material)
                
            # O escape básico de HTML seria ideal, mas para não abstrair demais, mantemos simples.
            msg_escapada = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Usando &nbsp; para espaços consecutivos para garantir a preservação estrita da indentação no QTextEdit
            msg_com_espacos = msg_escapada.replace("  ", "&nbsp;&nbsp;")
            linhas_html.append(f'<span style="color: {cor};">{msg_com_espacos}</span>')
            
        conteudo = "<br>".join(linhas_html)
        return f'<div style="white-space: pre-wrap;">{conteudo}</div>'
