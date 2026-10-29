# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import os
import secrets
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from editor.core.instancia_unica import trava_arquivo_operacao
from editor.core.storage import obter_diretorio_base_app

PORTA_MCP_PADRAO = 27378
NOME_ARQUIVO_SESSAO_MCP = "mcp_sessao.json"
NOME_ARQUIVO_SESSOES_MCP = "mcp_sessoes.json"
VARIAVEL_AMBIENTE_PORTA_MCP = "ARESTA_MCP_PORTA"


@dataclass(frozen=True)
class DadosSessaoMcp:
    """Metadados da sessão ativa do servidor MCP local do Editor Aresta."""

    porta: int
    pid: int
    token: str
    id_croqui: str = ""
    caminho_database: str = ""

    @property
    def url_http(self) -> str:
        """Retorna o endpoint HTTP JSON-RPC direto."""
        return f"http://127.0.0.1:{self.porta}/mcp"

    @property
    def url_sse(self) -> str:
        """Retorna o endpoint SSE para clientes MCP baseados em eventos."""
        return f"http://127.0.0.1:{self.porta}/mcp/sse"

    def para_dict(self) -> dict[str, object]:
        """Serializa os metadados da sessão para dicionário compatível com JSON."""
        return {
            "porta": self.porta,
            "pid": self.pid,
            "token": self.token,
            "id_croqui": self.id_croqui,
            "caminho_database": self.caminho_database,
            "url_http": self.url_http,
            "url_sse": self.url_sse,
        }


def obter_caminho_sessao_mcp(diretorio_base: Path | None = None) -> Path:
    """Retorna o caminho absoluto do arquivo `mcp_sessao.json`."""
    base = Path(diretorio_base) if diretorio_base is not None else obter_diretorio_base_app()
    return base / NOME_ARQUIVO_SESSAO_MCP


def obter_caminho_sessoes_mcp(diretorio_base: Path | None = None) -> Path:
    """Retorna o caminho absoluto do arquivo `mcp_sessoes.json` (registro multi-janela)."""
    base = Path(diretorio_base) if diretorio_base is not None else obter_diretorio_base_app()
    return base / NOME_ARQUIVO_SESSOES_MCP


def _tentar_vincular_porta(porta: int) -> socket.socket | None:
    """Tenta vincular e retornar um socket TCP em `127.0.0.1:porta`, ou `None` se ocupada."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind(("127.0.0.1", porta))
        return sock
    except OSError:
        sock.close()
        return None


def porta_disponivel_local(porta: int) -> bool:
    """Verifica se a porta TCP informada está livre para vinculação em `127.0.0.1`."""
    sock = _tentar_vincular_porta(porta)
    if sock is not None:
        sock.close()
        return True
    return False


def _extrair_porta_ambiente(env: Mapping[str, str] | None = None) -> int | None:
    ambiente = env if env is not None else os.environ
    valor = ambiente.get(VARIAVEL_AMBIENTE_PORTA_MCP, "").strip()
    if valor.isdigit():
        porta = int(valor)
        if 1 <= porta <= 65535:
            return porta
    return None


def vincular_socket_mcp(
    porta_preferencial: int | None = None,
    max_tentativas_sequenciais: int = 15,
    env: Mapping[str, str] | None = None,
) -> tuple[socket.socket, int]:
    """
    Vincula e retorna um socket TCP em `127.0.0.1` na `porta_preferencial`
    (ou `ARESTA_MCP_PORTA` / `27378`) com fallback sequencial ou porta efêmera do SO.
    """
    porta_inicial = (
        porta_preferencial
        if porta_preferencial is not None
        else (_extrair_porta_ambiente(env) or PORTA_MCP_PADRAO)
    )
    for deslocamento in range(max_tentativas_sequenciais):
        candidata = porta_inicial + deslocamento
        if 1 <= candidata <= 65535:
            sock = _tentar_vincular_porta(candidata)
            if sock is not None:
                return sock, candidata

    sock_efemero = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_efemero.bind(("127.0.0.1", 0))
    return sock_efemero, int(sock_efemero.getsockname()[1])


def alocar_porta_mcp(
    porta_preferencial: int | None = None,
    max_tentativas_sequenciais: int = 15,
    env: Mapping[str, str] | None = None,
) -> int:
    """
    Aloca uma porta local livre em `127.0.0.1`, iniciando pela `porta_preferencial`
    (ou `ARESTA_MCP_PORTA` / `27378`) e fazendo fallback sequencial ou para porta efêmera do SO.
    """
    sock, porta = vincular_socket_mcp(
        porta_preferencial=porta_preferencial,
        max_tentativas_sequenciais=max_tentativas_sequenciais,
        env=env,
    )
    sock.close()
    return porta


def _deserializar_sessao(dados: dict[str, object]) -> DadosSessaoMcp | None:
    porta = dados.get("porta")
    if not isinstance(porta, int) or isinstance(porta, bool):
        return None
    return DadosSessaoMcp(
        porta=porta,
        pid=int(str(dados.get("pid", 0))),
        token=str(dados.get("token", "")),
        id_croqui=str(dados.get("id_croqui", "")),
        caminho_database=str(dados.get("caminho_database", "")),
    )


def listar_sessoes_mcp(diretorio_base: Path | None = None) -> list[DadosSessaoMcp]:
    """Lê a lista de sessões ativas do arquivo `mcp_sessoes.json`."""
    caminho = obter_caminho_sessoes_mcp(diretorio_base)
    if not caminho.is_file():
        return []
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    itens = bruto.get("sessoes", []) if isinstance(bruto, dict) else []
    resultado: list[DadosSessaoMcp] = []
    for item in itens:
        sessao = _deserializar_sessao(item)
        if sessao is not None:
            resultado.append(sessao)
    return resultado


def registrar_sessao_multi_mcp(
    sessao: DadosSessaoMcp,
    diretorio_base: Path | None = None,
) -> None:
    """Registra ou atualiza (por porta) os metadados da sessão em `mcp_sessoes.json`."""
    caminho = obter_caminho_sessoes_mcp(diretorio_base)
    with trava_arquivo_operacao(caminho.with_suffix(".lock"), timeout_s=2.0):
        atuais = listar_sessoes_mcp(diretorio_base)
        atualizadas: list[DadosSessaoMcp] = []
        substituida = False
        for existente in atuais:
            if existente.porta == sessao.porta:
                atualizadas.append(sessao)
                substituida = True
            else:
                atualizadas.append(existente)
        if not substituida:
            atualizadas.append(sessao)
        conteudo = {"sessoes": [s.para_dict() for s in atualizadas]}
        caminho.write_text(json.dumps(conteudo, indent=2, ensure_ascii=False), encoding="utf-8")


def desregistrar_sessao_multi_mcp(
    porta: int,
    diretorio_base: Path | None = None,
) -> list[DadosSessaoMcp]:
    """Remove a sessão da `porta` informada de `mcp_sessoes.json` e retorna as restantes."""
    caminho = obter_caminho_sessoes_mcp(diretorio_base)
    with trava_arquivo_operacao(caminho.with_suffix(".lock"), timeout_s=2.0):
        restantes = [s for s in listar_sessoes_mcp(diretorio_base) if s.porta != int(porta)]
        if restantes:
            conteudo = {"sessoes": [s.para_dict() for s in restantes]}
            caminho.write_text(json.dumps(conteudo, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            caminho.unlink(missing_ok=True)
            obter_caminho_sessao_mcp(diretorio_base).unlink(missing_ok=True)
        return restantes


def gravar_sessao_mcp(
    porta: int,
    token: str | None = None,
    diretorio_base: Path | None = None,
    id_croqui: str = "",
    caminho_database: str = "",
) -> DadosSessaoMcp:
    """Persiste os dados da sessão ativa do servidor MCP em `mcp_sessao.json` e `mcp_sessoes.json`."""
    token_final = token if token is not None else secrets.token_urlsafe(24)
    sessao = DadosSessaoMcp(
        porta=int(porta),
        pid=os.getpid(),
        token=token_final,
        id_croqui=str(id_croqui),
        caminho_database=str(caminho_database),
    )
    caminho = obter_caminho_sessao_mcp(diretorio_base)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(sessao.para_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    registrar_sessao_multi_mcp(sessao, diretorio_base=diretorio_base)
    return sessao


def ler_sessao_mcp(diretorio_base: Path | None = None) -> DadosSessaoMcp | None:
    """Lê os dados da sessão ativa do arquivo `mcp_sessao.json`, ou retorna `None` se indisponível."""
    caminho = obter_caminho_sessao_mcp(diretorio_base)
    if not caminho.is_file():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return _deserializar_sessao(dados)
    except (OSError, ValueError, TypeError):
        return None


def remover_sessao_mcp(diretorio_base: Path | None = None, porta: int | None = None) -> None:
    """Remove a sessão do servidor MCP e promove outra sessão ativa caso existam múltiplas janelas."""
    if porta is not None:
        restantes = desregistrar_sessao_multi_mcp(porta, diretorio_base)
        if restantes:
            caminho_principal = obter_caminho_sessao_mcp(diretorio_base)
            caminho_principal.write_text(
                json.dumps(restantes[0].para_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        return

    obter_caminho_sessao_mcp(diretorio_base).unlink(missing_ok=True)
    obter_caminho_sessoes_mcp(diretorio_base).unlink(missing_ok=True)


def descobrir_url_mcp_ativa(
    diretorio_base: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """
    Descobre a URL HTTP JSON-RPC (`http://127.0.0.1:<porta>/mcp`) e o token de sessão
    priorizando `ARESTA_MCP_PORTA`, depois `mcp_sessao.json` e por fim a porta padrão `27378`.
    """
    sessao = ler_sessao_mcp(diretorio_base)
    porta_env = _extrair_porta_ambiente(env)
    if porta_env is not None:
        return f"http://127.0.0.1:{porta_env}/mcp", (sessao.token if sessao else "")
    if sessao is not None:
        return sessao.url_http, sessao.token
    return f"http://127.0.0.1:{PORTA_MCP_PADRAO}/mcp", ""
