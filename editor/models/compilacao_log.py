# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

class CompilacaoLog:
    """Modelo simples para armazenar o estado das saídas de compilação."""
    
    def __init__(self) -> None:
        self._logs: list[str] = []
        self._tem_avisos_ou_erros: bool = False

    def atualizar(self, mensagens: list[str]) -> None:
        """Atualiza o estado dos logs e recalcula se existem erros ou avisos."""
        self._logs = mensagens
        self._tem_avisos_ou_erros = self._verificar_erros_ou_avisos(mensagens)


    def obter_logs(self) -> list[str]:
        """Retorna a lista de mensagens armazenadas."""
        return self._logs

    def tem_avisos_ou_erros(self) -> bool:
        """Retorna True se alguma mensagem na lista for categorizada como aviso ou erro."""
        return self._tem_avisos_ou_erros

    def _verificar_erros_ou_avisos(self, mensagens: list[str]) -> bool:
        """Verifica se as palavras-chave estão presentes em alguma das linhas."""
        palavras_chave = ["aviso", "erro", "error", "falhou", "failed"]
        for mensagem in mensagens:
            msg_low = mensagem.lower()
            if any(p in msg_low for p in palavras_chave):
                return True
        return False
