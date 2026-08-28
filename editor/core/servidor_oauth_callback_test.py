# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import requests
import threading
import time

from editor.core.servidor_oauth_callback import ServidorCallbackOAuth


class TesteServidorCallbackOAuth:
    """Testes unitários para o servidor efêmero de captura de callback OAuth."""

    def teste_alocacao_dinamica_de_porta_e_url_redirecionamento(self):
        servidor = ServidorCallbackOAuth()
        porta = servidor.iniciar_escuta()
        try:
            assert porta > 0
            url_redirecionamento = servidor.obter_url_redirecionamento()
            assert url_redirecionamento == f"http://localhost:{porta}/callback"
        finally:
            servidor.encerrar()

    def teste_recebimento_tokens_via_post(self):
        servidor = ServidorCallbackOAuth()
        porta = servidor.iniciar_escuta()

        try:
            payload = {
                "access_token": "jwt-supabase-teste",
                "refresh_token": "refresh-teste",
                "provider_token": "token-github-teste",
            }

            url_tokens = f"http://127.0.0.1:{porta}/tokens"
            resposta = requests.post(url_tokens, json=payload, timeout=5)
            assert resposta.status_code == 200
            assert "sucesso" in resposta.text.lower()

            resultado = servidor.aguardar_tokens(tempo_limite=2)
            assert resultado is not None
            assert resultado["access_token"] == "jwt-supabase-teste"
            assert resultado["refresh_token"] == "refresh-teste"
            assert resultado["provider_token"] == "token-github-teste"
        finally:
            servidor.encerrar()

    def teste_recebimento_tokens_via_query_params(self):
        servidor = ServidorCallbackOAuth()
        porta = servidor.iniciar_escuta()

        try:
            url_callback = (
                f"http://127.0.0.1:{porta}/callback?"
                f"access_token=jwt-query&refresh_token=refresh-query&provider_token=git-query"
            )
            resposta = requests.get(url_callback, timeout=5)
            assert resposta.status_code == 200
            assert "Autenticação concluída" in resposta.text

            resultado = servidor.aguardar_tokens(tempo_limite=2)
            assert resultado is not None
            assert resultado["access_token"] == "jwt-query"
            assert resultado["refresh_token"] == "refresh-query"
            assert resultado["provider_token"] == "git-query"
        finally:
            servidor.encerrar()

    def teste_servir_pagina_html_de_captura_hash(self):
        servidor = ServidorCallbackOAuth()
        porta = servidor.iniciar_escuta()

        try:
            url_callback = f"http://127.0.0.1:{porta}/callback"
            resposta = requests.get(url_callback, timeout=5)
            assert resposta.status_code == 200
            assert "text/html" in resposta.headers["Content-Type"]
            assert "window.location.hash" in resposta.text
        finally:
            servidor.encerrar()

    def teste_recebimento_erro_via_query_params(self):
        servidor = ServidorCallbackOAuth()
        porta = servidor.iniciar_escuta()

        try:
            url_callback = (
                f"http://127.0.0.1:{porta}/callback?"
                f"error=access_denied&error_description=The+user+has+denied+your+application"
            )
            resposta = requests.get(url_callback, timeout=5)
            assert resposta.status_code == 200

            resultado = servidor.aguardar_tokens(tempo_limite=2)
            assert resultado is not None
            assert "erro" in resultado
            assert "The user has denied your application" in resultado["erro"]
        finally:
            servidor.encerrar()
