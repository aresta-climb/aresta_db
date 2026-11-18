# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Orquestrador de Smoke Test Pós-Build Offline para os binários distribuídos do Editor Aresta
(Windows PyInstaller/MSIX, macOS .app ARM64 e Intel sob Rosetta 2, e Linux Flatpak).

Executa o pacote empacotado real sem qualquer acesso à internet externa:
1. Sobe um servidor HTTP local (127.0.0.1) emulando as rotas REST de OTP do Supabase Auth;
2. Inicializa um repositório Git upstream real em disco (pygit2) com um croqui oficial e um PDF de teste;
3. Opcionalmente valida a arquitetura binária Mach-O (arm64 vs x86_64) no macOS;
4. Conduz login OTP na TelaDeAbertura -> clone Git -> ServidorMCP HTTP na TelaDeCarregamento ->
   importação de croqui na JanelaPrincipal -> particionamento de PDF (pymupdf + WebP) ->
   salvamento/compilação Protobuf -> validação de ddgs/lxml e encerramento limpo com código 0.
"""

import argparse
import base64
import json
import os
import platform
import struct
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pygit2
import pymupdf as _pymupdf
from PIL import Image

from editor.mcp.sessao import listar_sessoes_mcp
from scripts.gerenciar_uids_lib import gerar_uid
from scripts.migrador import obter_ultima_versao_migracao

pymupdf: Any = _pymupdf

EMAIL_SMOKE = "smoke@arestaclimb.com"
CODIGO_OTP_SMOKE = "123456"
ID_CROQUI_SMOKE_PADRAO = "br_mg_smoke_oficial"

_CPU_TYPE_X86_64 = 0x01000007
_CPU_TYPE_ARM64 = 0x0100000C
_MAPA_CPU_MACHO: dict[int, str] = {
    _CPU_TYPE_X86_64: "x86_64",
    _CPU_TYPE_ARM64: "arm64",
}


class ErroSmokeTestPacote(RuntimeError):
    """Exceção lançada quando qualquer etapa da verificação pós-build do pacote falha."""


def _gerar_jwt_smoke(email: str) -> str:
    cabecalho = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    exp = int(time.time()) + 7200
    corpo = (
        base64.urlsafe_b64encode(
            json.dumps({"sub": "usr-smoke-001", "email": email, "exp": exp}).encode("utf-8")
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{cabecalho}.{corpo}.assinatura_smoke_local"


class ServidorAuthSupabaseLocal:
    """Servidor HTTP efêmero em loopback (127.0.0.1) implementando as rotas OTP do Supabase Auth."""

    def __init__(self) -> None:
        self.contagem_otp: int = 0
        self.contagem_verify: int = 0
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._criar_handler())
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def _criar_handler(self) -> type[BaseHTTPRequestHandler]:
        servidor_pai = self

        class _HandlerAuth(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def _responder_json(self, status: int, corpo: dict[str, Any]) -> None:
                dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def _ler_json(self) -> dict[str, Any]:
                tam = int(self.headers.get("Content-Length", "0") or "0")
                bruto = self.rfile.read(tam) if tam > 0 else b"{}"
                try:
                    lido = json.loads(bruto.decode("utf-8"))
                    return lido if isinstance(lido, dict) else {}
                except Exception:
                    return {}

            def do_POST(self) -> None:
                caminho = self.path.split("?", 1)[0]
                corpo = self._ler_json()
                if caminho == "/auth/v1/otp":
                    servidor_pai.contagem_otp += 1
                    self._responder_json(200, {"ok": True})
                    return

                if caminho == "/auth/v1/verify":
                    token = str(corpo.get("token") or "").strip()
                    email = str(corpo.get("email") or EMAIL_SMOKE).strip()
                    if token != CODIGO_OTP_SMOKE:
                        self._responder_json(400, {"msg": "Token has expired or is invalid"})
                        return
                    servidor_pai.contagem_verify += 1
                    self._responder_json(
                        200,
                        {
                            "access_token": _gerar_jwt_smoke(email),
                            "refresh_token": "refresh_smoke_local",
                            "user": {
                                "id": "usr-smoke-001",
                                "email": email,
                                "user_metadata": {"nome_completo": "Escalador Smoke Test"},
                            },
                        },
                    )
                    return

                self._responder_json(404, {"msg": "Rota não encontrada"})

            def do_GET(self) -> None:
                caminho = self.path.split("?", 1)[0]
                if caminho == "/auth/v1/user":
                    self._responder_json(
                        200,
                        {
                            "id": "usr-smoke-001",
                            "email": EMAIL_SMOKE,
                            "user_metadata": {"nome_completo": "Escalador Smoke Test"},
                        },
                    )
                    return
                self._responder_json(404, {"msg": "Rota não encontrada"})

        return _HandlerAuth

    @property
    def porta(self) -> int:
        return int(self._httpd.server_address[1])

    @property
    def url_base(self) -> str:
        return f"http://127.0.0.1:{self.porta}"

    def __enter__(self) -> "ServidorAuthSupabaseLocal":
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=3.0)


def ler_arquiteturas_macho(caminho_binario: Path) -> set[str]:
    """Lê os cabeçalhos binários Mach-O (64-bit ou Universal Fat) e retorna as arquiteturas presentes."""
    if not caminho_binario.is_file():
        raise ErroSmokeTestPacote(
            f"Binário não encontrado para verificação Mach-O: {caminho_binario}"
        )

    dados = caminho_binario.read_bytes()
    if len(dados) < 8:
        raise ErroSmokeTestPacote(f"Arquivo '{caminho_binario}' não é um binário Mach-O válido.")

    magica = dados[:4]
    if magica == b"\xcf\xfa\xed\xfe":
        (cputype,) = struct.unpack("<I", dados[4:8])
        arq = _MAPA_CPU_MACHO.get(cputype)
        return {arq} if arq else set()

    if magica == b"\xca\xfe\xba\xbe":
        (nfat_arch,) = struct.unpack(">I", dados[4:8])
        arquiteturas: set[str] = set()
        offset = 8
        for _ in range(nfat_arch):
            if offset + 20 <= len(dados):
                (cputype,) = struct.unpack(">I", dados[offset : offset + 4])
                arq = _MAPA_CPU_MACHO.get(cputype)
                if arq:
                    arquiteturas.add(arq)
            offset += 20
        return arquiteturas

    raise ErroSmokeTestPacote(f"Arquivo '{caminho_binario}' não é um binário Mach-O válido.")


def verificar_arquitetura_macho(caminho_binario: Path, arquitetura_esperada: str) -> None:
    """Garante que o binário Mach-O contém a arquitetura alvo ('arm64' ou 'x86_64')."""
    encontradas = ler_arquiteturas_macho(caminho_binario)
    esperada_norm = arquitetura_esperada.strip().lower()
    if esperada_norm not in encontradas:
        raise ErroSmokeTestPacote(
            f"Arquitetura Mach-O divergente em '{caminho_binario}': "
            f"esperada '{esperada_norm}', encontradas {sorted(encontradas)}."
        )


def montar_comando_execucao_smoke(
    comando_base: list[str],
    *,
    arquitetura_esperada: str | None = None,
    plataforma_host: str | None = None,
    maquina_host: str | None = None,
    variaveis_sandbox: dict[str, str] | None = None,
) -> list[str]:
    """
    Monta a linha de comando final com '--smoke-test', prefixando 'arch -x86_64'
    automaticamente ao executar um binário Intel x86_64 sob Rosetta 2 em host Apple Silicon
    e injetando '--env=CHAVE=VALOR' quando o comando alvo for 'flatpak run'.
    """
    plat = plataforma_host or sys.platform
    maq = (maquina_host or platform.machine()).lower()
    prefixo: list[str] = []
    if (
        plat == "darwin"
        and arquitetura_esperada == "x86_64"
        and maq == "arm64"
        and comando_base[:2] != ["arch", "-x86_64"]
    ):
        prefixo = ["arch", "-x86_64"]

    cmd_ajustado = list(comando_base)
    if variaveis_sandbox and len(cmd_ajustado) >= 3 and cmd_ajustado[:2] == ["flatpak", "run"]:
        flags_env = [f"--env={k}={v}" for k, v in variaveis_sandbox.items()]
        cmd_ajustado = ["flatpak", "run", *flags_env, *cmd_ajustado[2:]]

    sufixo = [] if "--smoke-test" in cmd_ajustado else ["--smoke-test"]
    return [*prefixo, *cmd_ajustado, *sufixo]


@dataclass(frozen=True)
class AmbienteSmokeTest:
    """Caminhos temporários isolados preparados para uma execução de smoke test."""

    diretorio_raiz: Path
    diretorio_dados: Path
    caminho_repo_upstream: Path
    caminho_pdf_teste: Path
    id_croqui_oficial: str


def preparar_ambiente_smoke_test(diretorio_base: Path) -> AmbienteSmokeTest:
    """
    Inicializa um diretório de dados vazio, um repositório Git upstream real na branch 'main'
    com um croqui oficial válido e um arquivo PDF de 1 página contendo imagem e texto vetorial.
    """
    diretorio_base.mkdir(parents=True, exist_ok=True)
    diretorio_dados = diretorio_base / "dados_app"
    diretorio_dados.mkdir(parents=True, exist_ok=True)

    caminho_repo_upstream = diretorio_base / "upstream_repo"
    repo = pygit2.init_repository(str(caminho_repo_upstream), initial_head="main")
    pasta_croqui = caminho_repo_upstream / "database" / ID_CROQUI_SMOKE_PADRAO
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    (pasta_croqui / "croqui.yaml").write_text(
        f"id: {ID_CROQUI_SMOKE_PADRAO}\n"
        f"uid: {gerar_uid()}\n"
        f"nome: Serra do Smoke Test\n"
        f"ultima_migracao: {obter_ultima_versao_migracao()}\n"
        f"picos:\n"
        f"  - nome: Pico Smoke\n"
        f"    estado: MG\n",
        encoding="utf-8",
    )

    indice = repo.index
    indice.add_all()
    indice.write()
    arvore_oid = indice.write_tree()
    autor = pygit2.Signature("Aresta Smoke", EMAIL_SMOKE)
    repo.create_commit(
        "refs/heads/main", autor, autor, "chore: croqui inicial smoke test", arvore_oid, []
    )

    # Gera PDF real de 1 página com imagem RGB embutida e texto para exercitar pymupdf + Pillow WebP
    caminho_img_tmp = diretorio_base / "amostra_parede.png"
    Image.new("RGB", (320, 220), (48, 110, 72)).save(str(caminho_img_tmp), format="PNG")
    caminho_pdf_teste = diretorio_base / "croqui_smoke.pdf"
    doc = pymupdf.open()
    pagina = doc.new_page(width=595, height=842)
    pagina.insert_text((50, 40), "Setor Smoke Principal")
    pagina.insert_image(pymupdf.Rect(50, 60, 370, 280), filename=str(caminho_img_tmp))
    doc.save(str(caminho_pdf_teste))
    doc.close()

    return AmbienteSmokeTest(
        diretorio_raiz=diretorio_base,
        diretorio_dados=diretorio_dados,
        caminho_repo_upstream=caminho_repo_upstream,
        caminho_pdf_teste=caminho_pdf_teste,
        id_croqui_oficial=ID_CROQUI_SMOKE_PADRAO,
    )


def _chamar_ferramenta_mcp_http(
    client: httpx.Client,
    url_mcp: str,
    req_id: int,
    nome_ferramenta: str,
    argumentos: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post(
        url_mcp,
        json={
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": nome_ferramenta, "arguments": argumentos},
        },
    )
    resp.raise_for_status()
    corpo = resp.json()
    if "error" in corpo:
        raise ErroSmokeTestPacote(f"Erro na ferramenta MCP '{nome_ferramenta}': {corpo['error']}")
    resultado = corpo.get("result", {})
    texto = resultado.get("content", [{}])[0].get("text", "{}")
    dados: dict[str, Any] = json.loads(texto)
    if resultado.get("isError"):
        raise ErroSmokeTestPacote(f"Erro na ferramenta MCP '{nome_ferramenta}': {dados}")
    return dados


def executar_smoke_test_pacote(
    comando_base: list[str],
    *,
    diretorio_trabalho: Path | None = None,
    arquitetura_esperada: str | None = None,
    caminho_binario_macho: Path | None = None,
    timeout_segundos: float = 60.0,
) -> dict[str, Any]:
    """
    Executa o smoke test ponta a ponta offline contra o comando/binário informado.
    Lança ErroSmokeTestPacote caso qualquer etapa falhe ou o processo retorne código != 0.
    """
    if arquitetura_esperada and caminho_binario_macho is not None:
        verificar_arquitetura_macho(caminho_binario_macho, arquitetura_esperada)

    ctx_temp = (
        tempfile.TemporaryDirectory(prefix="aresta_smoke_") if diretorio_trabalho is None else None
    )
    try:
        pasta_raiz = (
            Path(ctx_temp.name).resolve() if ctx_temp is not None else diretorio_trabalho.resolve()  # type: ignore[union-attr]
        )
        amb = preparar_ambiente_smoke_test(pasta_raiz)

        with ServidorAuthSupabaseLocal() as srv_auth:
            vars_smoke = {
                "QT_QPA_PLATFORM": "offscreen",
                "ARESTA_DESATIVAR_TELEMETRIA": "1",
                "ARESTA_DIRETORIO_DADOS": str(amb.diretorio_dados),
                "ARESTA_SUPABASE_URL": srv_auth.url_base,
                "ARESTA_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_smoke_local",
                "ARESTA_GIT_UPSTREAM_URL": amb.caminho_repo_upstream.as_uri(),
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            cmd_final = montar_comando_execucao_smoke(
                comando_base,
                arquitetura_esperada=arquitetura_esperada,
                variaveis_sandbox=vars_smoke,
            )
            env = dict(os.environ)
            env.update(vars_smoke)

            proc = subprocess.Popen(
                cmd_final,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            prazo = time.monotonic() + timeout_segundos
            arq_sessao_mcp = amb.diretorio_dados / "mcp_sessao.json"

            try:
                while not arq_sessao_mcp.is_file():
                    if proc.poll() is not None or time.monotonic() > prazo:
                        if proc.poll() is None:
                            proc.kill()
                        out, err = proc.communicate(timeout=5.0)
                        raise ErroSmokeTestPacote(
                            f"Falha aguardando ServidorMCP (código={proc.returncode}).\nSTDOUT:\n{out}\nSTDERR:\n{err}"
                        )
                    time.sleep(0.05)

                sessao_mcp = json.loads(arq_sessao_mcp.read_text(encoding="utf-8"))
                url_mcp = f"http://127.0.0.1:{sessao_mcp['porta']}/mcp"

                with httpx.Client(timeout=20.0) as client:
                    # 1. Confirma que o clone Git trouxe o croqui oficial na TelaDeCarregamento
                    listagem = _chamar_ferramenta_mcp_http(
                        client, url_mcp, 1, "aresta_listar_croquis", {}
                    )
                    ids_oficiais = [
                        (c.get("id_croqui") or c.get("id")) if isinstance(c, dict) else str(c)
                        for c in listagem.get("oficiais", [])
                    ]
                    assert amb.id_croqui_oficial in ids_oficiais, (
                        f"Croqui oficial '{amb.id_croqui_oficial}' ausente após sync Git: {listagem}"
                    )

                    # 2. Importa o croqui oficial e transiciona para a JanelaPrincipal
                    _chamar_ferramenta_mcp_http(
                        client,
                        url_mcp,
                        2,
                        "aresta_importar_croqui_oficial",
                        {"id_oficial": amb.id_croqui_oficial},
                    )

                    # 3. Aguarda a JanelaPrincipal ativar o croqui nas sessões MCP
                    croqui_pronto = False
                    while not croqui_pronto and time.monotonic() <= prazo:
                        croqui_pronto = any(
                            s.id_croqui == amb.id_croqui_oficial
                            for s in listar_sessoes_mcp(amb.diretorio_dados)
                        )
                        if not croqui_pronto:
                            time.sleep(0.05)

                    # 4. Particiona o PDF real exercitando pymupdf + conversão WebP
                    res_pdf = _chamar_ferramenta_mcp_http(
                        client,
                        url_mcp,
                        4,
                        "aresta_particionar_pdf_croqui",
                        {
                            "caminho_pdf": str(amb.caminho_pdf_teste),
                            "partes": {"01_setor_smoke": [0]},
                            "incluir_paginas": True,
                        },
                    )
                    imagens = (
                        res_pdf.get("partes_processadas", {})
                        .get("01_setor_smoke", {})
                        .get("imagens_extraidas", [])
                    )
                    assert len(imagens) > 0, (
                        f"Nenhuma imagem WebP extraída pelo pymupdf no smoke test: {res_pdf}"
                    )

                    # 5. Salva e compila o croqui exercitando Protobuf, LibYAML, zstd e brotli
                    res_salvar = _chamar_ferramenta_mcp_http(
                        client, url_mcp, 5, "aresta_salvar", {}
                    )
                    assert res_salvar.get("status") == "ok", (
                        f"Falha ao salvar/compilar croqui: {res_salvar}"
                    )

                # 6. Sinaliza encerramento para validar ddgs/lxml internos e fechar limpo
                (amb.diretorio_dados / ".encerrar_smoke_test").write_text("ok", encoding="utf-8")
                restante = max(2.0, prazo - time.monotonic())
                out_final, err_final = proc.communicate(timeout=restante)
                assert proc.returncode == 0, (
                    f"Processo encerrou com código {proc.returncode}.\nSTDOUT:\n{out_final}\nSTDERR:\n{err_final}"
                )

                arq_concluido = amb.diretorio_dados / ".smoke_test_concluido.json"
                assert arq_concluido.is_file() and srv_auth.contagem_verify >= 1

                relatorio_interno: dict[str, Any] = json.loads(
                    arq_concluido.read_text(encoding="utf-8")
                )
                return {
                    "status": "ok",
                    "otp_verificados": srv_auth.contagem_verify,
                    "imagens_extraidas": imagens,
                    "relatorio_interno": relatorio_interno,
                }
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3.0)
    finally:
        if ctx_temp is not None:
            ctx_temp.cleanup()


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada CLI para execução nos workflows de CI/CD de Windows, macOS e Linux."""
    lista_args = list(sys.argv[1:] if argv is None else argv)
    extras: list[str] = []
    if "--" in lista_args:
        idx_sep = lista_args.index("--")
        extras = lista_args[idx_sep + 1 :]
        lista_args = lista_args[:idx_sep]

    parser = argparse.ArgumentParser(
        description="Executa smoke test pós-build offline contra o pacote compilado do Editor Aresta."
    )
    parser.add_argument(
        "--executavel",
        type=Path,
        default=None,
        help="Caminho direto para o binário empacotado (ex: EditorAresta.exe ou EditorAresta.app/Contents/MacOS/EditorAresta).",
    )
    parser.add_argument(
        "--diretorio-trabalho",
        type=Path,
        default=None,
        help="Diretório temporário explícito (necessário no Flatpak para compartilhamento via --filesystem).",
    )
    parser.add_argument(
        "--arquitetura-esperada",
        choices=["arm64", "x86_64"],
        default=None,
        help="Valida cabeçalho Mach-O no macOS e aciona Rosetta 2 automaticamente quando necessário.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Tempo máximo em segundos para conclusão do smoke test.",
    )
    args = parser.parse_args(lista_args)

    comando_base: list[str] = []
    if args.executavel is not None:
        comando_base.append(str(args.executavel.resolve()))
    comando_base.extend(extras)

    if not comando_base:
        parser.error("Informe --executavel <caminho> ou argumentos após '--'.")

    try:
        resultado = executar_smoke_test_pacote(
            comando_base,
            diretorio_trabalho=args.diretorio_trabalho,
            arquitetura_esperada=args.arquitetura_esperada,
            caminho_binario_macho=args.executavel if args.arquitetura_esperada else None,
            timeout_segundos=args.timeout,
        )
        print(
            f"✅ Smoke test pós-build concluído com sucesso: {json.dumps(resultado, ensure_ascii=False)}"
        )
        return 0
    except Exception as erro:
        print(f"❌ Falha no smoke test pós-build: {erro}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
