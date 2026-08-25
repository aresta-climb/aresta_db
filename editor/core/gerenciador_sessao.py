# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import os
import base64
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from editor.core.storage import GerenciadorCaminhos


@dataclass
class SessaoUsuario:
    """
    Representa a sessão unificada do usuário autenticado no Aresta Editor.
    """

    email: str
    nome_completo: str
    jwt_supabase: str
    token_atualizacao: str
    token_github: Optional[str] = None

    @property
    def eh_mantenedor(self) -> bool:
        """Retorna True se o usuário possui credencial de mantenedor do GitHub."""
        return bool(self.token_github)

    def para_dicionario(self) -> Dict[str, Any]:
        """Serializa os dados da sessão em um dicionário."""
        return asdict(self)

    @classmethod
    def de_dicionario(cls, dados: Dict[str, Any]) -> "SessaoUsuario":
        """Reconstrói uma instância de SessaoUsuario a partir de um dicionário."""
        return cls(
            email=dados.get("email", ""),
            nome_completo=dados.get("nome_completo", ""),
            jwt_supabase=dados.get("jwt_supabase", ""),
            token_atualizacao=dados.get("token_atualizacao", ""),
            token_github=dados.get("token_github"),
        )


class GerenciadorSessao:
    """
    Gerencia o armazenamento persistente da sessão usando Envelope Encryption:
    - Chave mestra de 256 bits gerada aleatoriamente e armazenada no Keyring do SO.
    - Payload da sessão criptografado com AES-256-GCM (AEAD) gravado no AppData.
    """

    IDENTIFICADOR_CHAVE_CRIPTOGRAFIA = "chave_criptografia_sessao"

    def __init__(
        self,
        usar_memoria: bool = False,
        nome_servico: str = "editor_aresta",
        identificador_usuario: str = "sessao_atual",
        caminho_arquivo_sessao: Optional[Path] = None,
    ):
        self.usar_memoria = usar_memoria
        self.nome_servico = nome_servico
        self.identificador_usuario = identificador_usuario
        self._sessao_memoria: Optional[str] = None
        if caminho_arquivo_sessao:
            self._caminho_arquivo = caminho_arquivo_sessao
        else:
            self._caminho_arquivo = (
                GerenciadorCaminhos().obter_diretorio_base() / ".sessao_auth.enc"
            )

    def _obter_ou_criar_chave_criptografia(self) -> bytes:
        """Obtém a chave AES de 256 bits do Keyring ou gera uma nova de forma segura."""
        chave_b64 = keyring.get_password(
            self.nome_servico, self.IDENTIFICADOR_CHAVE_CRIPTOGRAFIA
        )
        if chave_b64:
            try:
                chave = base64.b64decode(chave_b64.encode("ascii"))
                if len(chave) == 32:
                    return chave
            except Exception:
                pass

        # Gera nova chave AES-256 (32 bytes)
        chave = AESGCM.generate_key(bit_length=256)
        chave_b64 = base64.b64encode(chave).decode("ascii")
        keyring.set_password(
            self.nome_servico, self.IDENTIFICADOR_CHAVE_CRIPTOGRAFIA, chave_b64
        )
        return chave

    def salvar_sessao(self, sessao: SessaoUsuario) -> None:
        """Salva a sessão do usuário criptografada com AES-256-GCM."""
        payload = json.dumps(sessao.para_dicionario())
        if self.usar_memoria:
            self._sessao_memoria = payload
            return

        chave = self._obter_ou_criar_chave_criptografia()
        aesgcm = AESGCM(chave)
        nonce = os.urandom(12)  # 96 bits nonce padrão para AES-GCM
        ciphertext_com_tag = aesgcm.encrypt(
            nonce, payload.encode("utf-8"), associated_data=None
        )

        self._caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
        self._caminho_arquivo.write_bytes(nonce + ciphertext_com_tag)

    def obter_sessao(self) -> Optional[SessaoUsuario]:
        """Recupera e decifra a sessão do usuário com validação de integridade."""
        if self.usar_memoria:
            payload = self._sessao_memoria
            if not payload:
                return None
            try:
                return SessaoUsuario.de_dicionario(json.loads(payload))
            except Exception:
                return None

        if not self._caminho_arquivo.exists():
            return None

        chave_b64 = keyring.get_password(
            self.nome_servico, self.IDENTIFICADOR_CHAVE_CRIPTOGRAFIA
        )
        if not chave_b64:
            self.limpar_sessao()
            return None

        try:
            chave = base64.b64decode(chave_b64.encode("ascii"))
            dados = self._caminho_arquivo.read_bytes()
            if len(dados) < 28:  # 12 bytes nonce + 16 bytes auth tag mínima
                self.limpar_sessao()
                return None

            nonce = dados[:12]
            ciphertext_com_tag = dados[12:]

            aesgcm = AESGCM(chave)
            plaintext = aesgcm.decrypt(
                nonce, ciphertext_com_tag, associated_data=None
            )
            dados_sessao = json.loads(plaintext.decode("utf-8"))
            return SessaoUsuario.de_dicionario(dados_sessao)
        except Exception:
            # Qualquer falha de integridade, chave inválida ou arquivo corrompido limpa a sessão
            self.limpar_sessao()
            return None

    def recuperar_token(self) -> Optional[str]:
        """Recupera o token JWT do Supabase da sessão ativa para compatibilidade."""
        sessao = self.obter_sessao()
        return sessao.jwt_supabase if sessao else None

    def limpar_sessao(self) -> None:
        """Remove a chave mestra do Keyring e o arquivo criptografado do disco."""
        if self.usar_memoria:
            self._sessao_memoria = None
        else:
            try:
                keyring.delete_password(
                    self.nome_servico, self.IDENTIFICADOR_CHAVE_CRIPTOGRAFIA
                )
            except Exception:
                pass

            # Limpeza preventiva de chaves e identificadores legados
            for chave_legada in (
                "chave_mestra_criptografia_sessao",
                "sessao_atual",
                "github_token",
            ):
                try:
                    keyring.delete_password(self.nome_servico, chave_legada)
                except Exception:
                    pass

            if self._caminho_arquivo.exists():
                try:
                    self._caminho_arquivo.unlink()
                except Exception:
                    pass
