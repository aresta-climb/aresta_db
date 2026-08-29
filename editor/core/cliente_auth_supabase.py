# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
from typing import Optional, Dict, Any
import requests

_URL_SUPABASE_PADRAO = os.getenv(
    "ARESTA_SUPABASE_URL", "https://yzkhiaoqtxvvcyyuwmqg.supabase.co"
)
_CHAVE_PUBLICA_PADRAO = os.getenv(
    "ARESTA_SUPABASE_PUBLISHABLE_KEY",
    "sb_publishable_ZOrO8ix2EsWlSHEWrZr42A_JycWrAV3",
)


import re


def traduzir_mensagem_erro_supabase(mensagem: str) -> str:
    """Traduz mensagens técnicas comuns retornadas pelo Supabase Auth para português."""
    if not mensagem:
        return mensagem

    # For security purposes, you can only request this after X seconds.
    match_after = re.search(
        r"For security purposes, you can only request this after (\d+) seconds?",
        mensagem,
        re.IGNORECASE,
    )
    if match_after:
        segundos = int(match_after.group(1))
        unidade = "segundo" if segundos == 1 else "segundos"
        return f"Por motivos de segurança, você só pode solicitar um novo código após {segundos} {unidade}."

    # For security purposes, you can only request this once every X seconds.
    match_every = re.search(
        r"For security purposes, you can only request this once every (\d+) seconds?",
        mensagem,
        re.IGNORECASE,
    )
    if match_every:
        segundos = int(match_every.group(1))
        unidade = "segundo" if segundos == 1 else "segundos"
        return f"Por motivos de segurança, você só pode solicitar um novo código a cada {segundos} {unidade}."

    traducoes_exatas = {
        "token has expired or is invalid": "O código de acesso expirou ou é inválido.",
        "invalid login credentials": "Credenciais de login inválidas.",
        "email rate limit exceeded": "Limite de envio de e-mails atingido. Tente novamente mais tarde.",
        "user already registered": "Usuário já cadastrado.",
        "unsupported provider: provider is not enabled": "Provedor de autenticação não está habilitado no servidor.",
        "error getting user profile from external provider": "Não foi possível obter o perfil e e-mail da sua conta externa (GitHub).",
    }

    msg_lower = mensagem.strip().lower()
    for chave, traducao in traducoes_exatas.items():
        if chave in msg_lower:
            return traducao

    return mensagem


class ErroAutenticacaoSupabase(Exception):
    """Exceção lançada quando ocorre um erro na autenticação com o Supabase."""

    def __init__(self, mensagem: str, codigo_status: Optional[int] = None) -> None:
        super().__init__(traduzir_mensagem_erro_supabase(mensagem))
        self.codigo_status = codigo_status


class ClienteAuthSupabase:
    """
    Biblioteca cliente REST para autenticação via Supabase Auth (OTP, Verify, User, Token).
    """

    def __init__(
        self,
        url_supabase: Optional[str] = None,
        chave_publica: Optional[str] = None,
        tempo_limite: int = 15,
    ) -> None:
        self.url_supabase: str = (url_supabase or _URL_SUPABASE_PADRAO).rstrip("/")
        self.chave_publica: str = chave_publica or _CHAVE_PUBLICA_PADRAO
        self.tempo_limite: int = tempo_limite


    def _obter_cabecalhos(self, jwt: Optional[str] = None) -> Dict[str, str]:
        token_auth = jwt or self.chave_publica
        cabecalhos = {
            "apikey": self.chave_publica,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_auth}",
        }
        return cabecalhos

    def _tratar_resposta(self, resposta: requests.Response) -> Dict[str, Any]:
        dados: dict[str, Any]
        try:
            res_json = resposta.json()
            dados = res_json if isinstance(res_json, dict) else {"resultado": res_json}
        except Exception:
            dados = {"msg": resposta.text}

        if not resposta.ok:
            mensagem_erro = (
                dados.get("msg")
                or dados.get("message")
                or dados.get("error_description")
                or dados.get("error")
                or f"Erro HTTP {resposta.status_code}"
            )
            raise ErroAutenticacaoSupabase(
                mensagem_erro, codigo_status=resposta.status_code
            )

        return dados

    def solicitar_codigo_otp(self, email: str) -> bool:
        """
        Envia uma solicitação de código OTP de 6 dígitos para o e-mail informado.
        """
        url = f"{self.url_supabase}/auth/v1/otp"
        payload = {"email": email.strip(), "create_user": True}

        resposta = requests.post(
            url,
            json=payload,
            headers=self._obter_cabecalhos(),
            timeout=self.tempo_limite,
        )
        self._tratar_resposta(resposta)
        return True

    def verificar_codigo_otp(self, email: str, token: str) -> Dict[str, Any]:
        """
        Valida o código OTP de 6 dígitos e retorna os dados de sessão (access_token, user, etc.).
        """
        url = f"{self.url_supabase}/auth/v1/verify"
        payload = {
            "type": "email",
            "email": email.strip(),
            "token": token.strip(),
        }

        resposta = requests.post(
            url,
            json=payload,
            headers=self._obter_cabecalhos(),
            timeout=self.tempo_limite,
        )
        return self._tratar_resposta(resposta)

    def atualizar_nome_autor(self, jwt: str, nome_completo: str) -> bool:
        """
        Atualiza o nome completo do autor nos metadados da conta do Supabase Auth.
        """
        url = f"{self.url_supabase}/auth/v1/user"
        payload = {"data": {"nome_completo": nome_completo.strip()}}

        resposta = requests.put(
            url,
            json=payload,
            headers=self._obter_cabecalhos(jwt=jwt),
            timeout=self.tempo_limite,
        )
        self._tratar_resposta(resposta)
        return True

    def renovar_sessao(self, token_atualizacao: str) -> Dict[str, Any]:
        """
        Renova a sessão expirada do usuário utilizando o refresh_token.
        """
        url = f"{self.url_supabase}/auth/v1/token?grant_type=refresh_token"
        payload = {"refresh_token": token_atualizacao.strip()}

        resposta = requests.post(
            url,
            json=payload,
            headers=self._obter_cabecalhos(),
            timeout=self.tempo_limite,
        )
        return self._tratar_resposta(resposta)

    def obter_usuario_atual(self, jwt: str) -> Dict[str, Any]:
        """
        Obtém os dados do usuário autenticado a partir do token JWT.
        """
        url = f"{self.url_supabase}/auth/v1/user"
        resposta = requests.get(
            url, headers=self._obter_cabecalhos(jwt=jwt), timeout=self.tempo_limite
        )
        return self._tratar_resposta(resposta)
