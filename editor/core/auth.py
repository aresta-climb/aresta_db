# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import requests
import time
from typing import Optional, Dict

class GerenciadorAutenticacao:
    """
    Gerencia o fluxo de autenticação com o GitHub via Device Flow.
    """
    
    def __init__(self, id_cliente: str):
        self.id_cliente = id_cliente
        self.codigo_dispositivo: Optional[str] = None
        self.usuario_logado: Optional[str] = None
        self.url_base = "https://github.com/login"

    def validar_token(self, token: str) -> bool:
        """
        Valida o token chamando a API do GitHub.
        Armazena o login do usuário se válido.
        """
        import github
        try:
            g = github.Github(auth=github.Auth.Token(token))
            usuario = g.get_user()
            self.usuario_logado = usuario.login
            return True
        except Exception:
            return False

    def solicitar_codigo_dispositivo(self) -> Dict:
        """
        Inicia o handshake do Device Flow.
        Retorna o dicionário com user_code e verification_uri.
        """
        url = f"{self.url_base}/device/code"
        payload = {
            "client_id": self.id_cliente,
            "scope": "repo workflow"
        }
        headers = {"Accept": "application/json"}
        
        response = requests.post(url, data=payload, headers=headers)
        
        if response.status_code == 404:
            raise Exception(
                "GitHub retornou 404 para o endpoint de Device Flow. "
                "Isso geralmente significa que o 'Client ID' é inválido ou que o 'Device Flow' "
                "não foi habilitado nas configurações do seu GitHub App / OAuth App."
            )
            
        response.raise_for_status()
        dados = response.json()
        self.codigo_dispositivo = dados.get("device_code")
        return dados

    def aguardar_token(self, tempo_limite: float = 300, intervalo_poll: float = 5) -> Optional[str]:
        """
        Realiza o polling para verificar se o usuário autorizou o acesso.
        Retorna o access_token se autorizado, ou None se expirar/cancelar.
        """
        if not self.codigo_dispositivo:
            raise ValueError("Código de dispositivo não solicitado.")
            
        url = f"{self.url_base}/oauth/access_token"
        payload = {
            "client_id": self.id_cliente,
            "device_code": self.codigo_dispositivo,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }
        headers = {"Accept": "application/json"}
        
        inicio = time.time()
        while time.time() - inicio < tempo_limite:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()
            
            dados = response.json()
            if "access_token" in dados:
                return dados["access_token"]
            
            erro = dados.get("error")
            if erro == "authorization_pending":
                time.sleep(intervalo_poll)
            elif erro == "slow_down":
                intervalo_poll += 5
                time.sleep(intervalo_poll)
            else:
                # Erros como "expired_token" ou "access_denied"
                break
                
        return None

    def salvar_token(self, token: str):
        """
        Salva o token de acesso no keyring do sistema operacional.
        """
        import keyring
        keyring.set_password("editor_aresta", "github_token", token)

    def recuperar_token(self) -> Optional[str]:
        """
        Recupera o token de acesso do keyring.
        """
        import keyring
        return keyring.get_password("editor_aresta", "github_token")
