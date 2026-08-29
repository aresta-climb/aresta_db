# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any


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
        palavras_erro = ["erro", "error", "falhou", "failed"]
        
        for msg in mensagens:
            msg_low = msg.lower()
            cor = "#333333"  # Padrão
            
            if any(p in msg_low for p in palavras_erro):
                cor = "#D32F2F"  # Vermelho forte (Material)
            elif "aviso" in msg_low:
                cor = "#F57C00"  # Laranja forte (Material)
                
            # O escape básico de HTML seria ideal, mas para não abstrair demais, mantemos simples.
            msg_escapada = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Usando &nbsp; para espaços consecutivos para garantir a preservação estrita da indentação no QTextEdit
            msg_com_espacos = msg_escapada.replace("  ", "&nbsp;&nbsp;")
            linhas_html.append(f'<span style="color: {cor};">{msg_com_espacos}</span>')
            
        conteudo = "<br>".join(linhas_html)
        return f'<div style="white-space: pre-wrap;">{conteudo}</div>'
