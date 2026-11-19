# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import struct
import sys
from pathlib import Path

import httpx
import pygit2
import pytest

from editor.release_tools.smoke_test_pacote import (
    CODIGO_OTP_SMOKE,
    EMAIL_SMOKE,
    ErroSmokeTestPacote,
    ServidorAuthSupabaseLocal,
    executar_smoke_test_pacote,
    ler_arquiteturas_macho,
    main,
    montar_comando_execucao_smoke,
    preparar_ambiente_smoke_test,
    verificar_arquitetura_macho,
)


def test_servidor_auth_supabase_local_fluxo_otp_e_erros() -> None:
    """Valida rotas HTTP /auth/v1/otp, /auth/v1/verify, /auth/v1/user e códigos de erro."""
    with ServidorAuthSupabaseLocal() as srv:
        assert srv.url_base.startswith("http://127.0.0.1:")
        with httpx.Client(timeout=5.0) as client:
            r_otp = client.post(f"{srv.url_base}/auth/v1/otp", json={"email": EMAIL_SMOKE})
            assert r_otp.status_code == 200

            r_invalido = client.post(
                f"{srv.url_base}/auth/v1/verify",
                json={"email": EMAIL_SMOKE, "token": "000000"},
            )
            assert r_invalido.status_code == 400

            r_verify = client.post(
                f"{srv.url_base}/auth/v1/verify",
                json={"email": EMAIL_SMOKE, "token": CODIGO_OTP_SMOKE},
            )
            assert r_verify.status_code == 200
            dados = r_verify.json()
            assert dados["access_token"]
            assert dados["user"]["user_metadata"]["nome_completo"] == "Escalador Smoke Test"

            r_user = client.get(
                f"{srv.url_base}/auth/v1/user",
                headers={"Authorization": f"Bearer {dados['access_token']}"},
            )
            assert r_user.status_code == 200
            assert r_user.json()["email"] == EMAIL_SMOKE

            r_404_get = client.get(f"{srv.url_base}/rota/inexistente")
            assert r_404_get.status_code == 404
            r_404_post = client.post(f"{srv.url_base}/rota/inexistente", content=b"nao-json")
            assert r_404_post.status_code == 404

        assert srv.contagem_otp >= 1
        assert srv.contagem_verify >= 1


def test_verificacao_arquitetura_macho_thin_fat_e_erros(tmp_path: Path) -> None:
    """Valida leitura binária de cabeçalhos Mach-O (arm64, x86_64, universal2 e inválidos)."""
    bin_arm64 = tmp_path / "bin_arm64"
    bin_arm64.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x0100000C) + b"\x00" * 24)
    assert ler_arquiteturas_macho(bin_arm64) == {"arm64"}
    verificar_arquitetura_macho(bin_arm64, "arm64")

    bin_x86 = tmp_path / "bin_x86_64"
    bin_x86.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x01000007) + b"\x00" * 24)
    assert ler_arquiteturas_macho(bin_x86) == {"x86_64"}
    verificar_arquitetura_macho(bin_x86, "x86_64")

    with pytest.raises(ErroSmokeTestPacote, match="Arquitetura Mach-O divergente"):
        verificar_arquitetura_macho(bin_x86, "arm64")

    # Universal binary (fat big-endian header com 2 arquiteturas)
    cabecalho_fat = (
        b"\xca\xfe\xba\xbe"
        + struct.pack(">I", 2)
        + struct.pack(">IIIII", 0x01000007, 3, 4096, 1024, 12)
        + struct.pack(">IIIII", 0x0100000C, 0, 8192, 1024, 12)
    )
    bin_fat = tmp_path / "bin_universal"
    bin_fat.write_bytes(cabecalho_fat)
    assert ler_arquiteturas_macho(bin_fat) == {"x86_64", "arm64"}
    verificar_arquitetura_macho(bin_fat, "x86_64")

    # CPU desconhecida em Mach-O válido é ignorada sem quebrar
    bin_outro = tmp_path / "bin_outro"
    bin_outro.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x00000012) + b"\x00" * 24)
    assert ler_arquiteturas_macho(bin_outro) == set()

    # Erros para arquivo ausente, truncado (< 8 bytes) ou não-Mach-O
    with pytest.raises(ErroSmokeTestPacote, match="Binário não encontrado"):
        ler_arquiteturas_macho(tmp_path / "inexistente")

    curto = tmp_path / "curto.bin"
    curto.write_bytes(b"123")
    with pytest.raises(ErroSmokeTestPacote, match="não é um binário Mach-O válido"):
        ler_arquiteturas_macho(curto)

    nao_macho = tmp_path / "texto.txt"
    nao_macho.write_bytes(b"MZ_windows_pe_header")
    with pytest.raises(ErroSmokeTestPacote, match="não é um binário Mach-O válido"):
        ler_arquiteturas_macho(nao_macho)


def test_montar_comando_execucao_smoke_rosetta_e_nativo() -> None:
    """Valida prefixo arch -x86_64 apenas quando rodando x86_64 em host darwin arm64."""
    cmd_rosetta = montar_comando_execucao_smoke(
        ["/app/EditorAresta"],
        arquitetura_esperada="x86_64",
        plataforma_host="darwin",
        maquina_host="arm64",
    )
    assert cmd_rosetta == ["arch", "-x86_64", "/app/EditorAresta", "--smoke-test"]

    cmd_nativo = montar_comando_execucao_smoke(
        ["/app/EditorAresta"],
        arquitetura_esperada="arm64",
        plataforma_host="darwin",
        maquina_host="arm64",
    )
    assert cmd_nativo == ["/app/EditorAresta", "--smoke-test"]

    cmd_ja_tem_flag = montar_comando_execucao_smoke(["EditorAresta.exe", "--smoke-test"])
    assert cmd_ja_tem_flag == ["EditorAresta.exe", "--smoke-test"]

    cmd_flatpak = montar_comando_execucao_smoke(
        ["flatpak", "run", "--filesystem=/tmp/s", "com.arestaclimb.Editor"],
        variaveis_sandbox={"QT_QPA_PLATFORM": "offscreen"},
    )
    assert "--env=QT_QPA_PLATFORM=offscreen" in cmd_flatpak
    assert cmd_flatpak[-1] == "--smoke-test"


def test_preparar_ambiente_smoke_test_cria_repo_git_e_pdf_real(tmp_path: Path) -> None:
    """Valida criação de repositório Git upstream na branch main com croqui.yaml e PDF real."""
    amb = preparar_ambiente_smoke_test(tmp_path / "amb")
    assert amb.caminho_pdf_teste.is_file()
    assert amb.caminho_pdf_teste.stat().st_size > 100
    repo = pygit2.Repository(str(amb.caminho_repo_upstream))
    assert repo.head.shorthand == "main"
    assert (
        amb.caminho_repo_upstream / "database" / amb.id_croqui_oficial / "croqui.yaml"
    ).is_file()


def test_executar_smoke_test_pacote_ponta_a_ponta_real_e_cli(tmp_path: Path) -> None:
    """
    Executa o fluxo completo ponta a ponta em subprocesso real contra editor/main.py:
    Login OTP -> Clone pygit2 -> TelaDeCarregamento (ServidorMCP HTTP) -> Importar croqui ->
    JanelaPrincipal -> aresta_particionar_pdf_croqui (pymupdf + WebP) -> aresta_salvar ->
    validação de ddgs/lxml -> encerramento limpo com código 0 via CLI main().
    """
    raiz_repo = Path(__file__).resolve().parent.parent.parent
    script_main = raiz_repo / "editor" / "main.py"

    codigo = main(
        [
            "--diretorio-trabalho",
            str(tmp_path / "exec_real"),
            "--timeout",
            "45",
            "--",
            sys.executable,
            str(script_main),
        ]
    )
    assert codigo == 0


def test_executar_smoke_test_pacote_falha_rapida_quando_binario_quebra(tmp_path: Path) -> None:
    """Garante erro detalhado imediato quando o processo alvo falha, excede tempo, erra MCP ou falta comando."""
    from editor.release_tools.smoke_test_pacote import _chamar_ferramenta_mcp_http

    # 1. Sem comando_base na CLI -> SystemExit(2) do argparse
    with pytest.raises(SystemExit) as exc_vazio:
        main([])
    assert exc_vazio.value.code == 2

    # 2. Timeout matando processo travado e usando TemporaryDirectory implícito (diretorio_trabalho=None)
    script_lento = tmp_path / "lento.py"
    script_lento.write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
    with pytest.raises(ErroSmokeTestPacote, match="Falha aguardando ServidorMCP"):
        executar_smoke_test_pacote(
            [sys.executable, str(script_lento)],
            diretorio_trabalho=None,
            timeout_segundos=0.15,
        )

    # 2b. Exceção após mcp_sessao.json existir mata processo vivo no bloco finally
    script_sessao_morta = tmp_path / "sessao_morta.py"
    script_sessao_morta.write_text(
        "import os, pathlib, time\n"
        "d = pathlib.Path(os.environ['ARESTA_DIRETORIO_DADOS'])\n"
        "(d / 'mcp_sessao.json').write_text('{\"porta\": 1}', encoding='utf-8')\n"
        "time.sleep(10)\n",
        encoding="utf-8",
    )
    with pytest.raises(httpx.HTTPError):
        executar_smoke_test_pacote(
            [sys.executable, str(script_sessao_morta)],
            diretorio_trabalho=tmp_path / "run_sessao_morta",
            timeout_segundos=5.0,
        )

    # 3. Verificação de arquitetura Mach-O acionada diretamente via executar_smoke_test_pacote
    bin_falso_arm = tmp_path / "falso_arm"
    bin_falso_arm.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x0100000C) + b"\x00" * 24)
    with pytest.raises(ErroSmokeTestPacote, match="Arquitetura Mach-O divergente"):
        executar_smoke_test_pacote(
            [str(bin_falso_arm)],
            arquitetura_esperada="x86_64",
            caminho_binario_macho=bin_falso_arm,
        )

    # 4. Resposta error e isError de ferramenta MCP HTTP lançam ErroSmokeTestPacote
    from editor.mcp.ferramentas_conhecimento import registrar_ferramentas_conhecimento
    from editor.mcp.servidor import ServidorMCP

    srv_mcp = ServidorMCP(diretorio_sessao=tmp_path / "mcp_err")
    srv_mcp.definir_croqui_ativo("", croqui_aberto=False)
    registrar_ferramentas_conhecimento(srv_mcp)
    srv_mcp.registrar_ferramenta(
        nome="ferramenta_requer_croqui",
        descricao="Teste",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=lambda _a: {"ok": True},
        requer_croqui=True,
    )
    srv_mcp.iniciar()
    try:
        url_teste = f"http://127.0.0.1:{srv_mcp.porta}/mcp"
        with httpx.Client(timeout=5.0) as client:
            with pytest.raises(ErroSmokeTestPacote, match="Erro na ferramenta MCP"):
                _chamar_ferramenta_mcp_http(client, url_teste, 98, "ferramenta_inexistente", {})
            with pytest.raises(ErroSmokeTestPacote, match="Erro na ferramenta MCP"):
                _chamar_ferramenta_mcp_http(client, url_teste, 99, "ferramenta_requer_croqui", {})
    finally:
        srv_mcp.parar()

    # 5. Binário encerrando com erro via CLI --executavel
    script_falha = tmp_path / "falha.py"
    script_falha.write_text(
        "import sys\nsys.stderr.write('ModuleNotFoundError simulado\\n')\nsys.exit(3)\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc_cli:
        main(
            [
                "--executavel",
                sys.executable,
                "--diretorio-trabalho",
                str(tmp_path / "run_cli_erro"),
                "--timeout",
                "5",
                "--",
                str(script_falha),
            ]
        )
    assert exc_cli.value.code == 1


def test_smoke_test_pacote_isola_pyside6_no_host_e_reconfigura_utf8_cli(tmp_path: Path) -> None:
    """
    Garante que importar smoke_test_pacote não carrega PySide6 (permitindo hosts Linux sem libEGL),
    que _croqui_ativo_nas_sessoes_mcp tolera arquivo ausente ou JSON parcial e que stdout cp1252 aceita emojis.
    """
    import io
    import subprocess

    from editor.release_tools.smoke_test_pacote import (
        _croqui_ativo_nas_sessoes_mcp,
        configurar_streams_utf8_cli,
    )

    buf = io.BytesIO()
    stream_cp1252 = io.TextIOWrapper(buf, encoding="cp1252", errors="strict")
    configurar_streams_utf8_cli((stream_cp1252, object()))
    stream_cp1252.write("✅ Smoke test pós-build concluído ❌\n")
    stream_cp1252.flush()
    assert "✅ Smoke test pós-build concluído ❌" in buf.getvalue().decode("utf-8")

    pasta = tmp_path / "sessoes"
    pasta.mkdir(parents=True)
    assert _croqui_ativo_nas_sessoes_mcp(pasta, "br_mg_smoke") is False
    (pasta / "mcp_sessoes.json").write_text("{json_parcial", encoding="utf-8")
    assert _croqui_ativo_nas_sessoes_mcp(pasta, "br_mg_smoke") is False
    (pasta / "mcp_sessoes.json").write_text(
        '{"sessoes": [{"porta": 27378, "id_croqui": "br_mg_smoke"}]}',
        encoding="utf-8",
    )
    assert _croqui_ativo_nas_sessoes_mcp(pasta, "br_mg_smoke") is True

    res = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, editor.release_tools.smoke_test_pacote; "
            "assert not any(m.startswith('PySide6') for m in sys.modules), list(sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stderr

    from editor.release_tools.smoke_test_pacote import (
        executar_smoke_test_pacote,
        montar_kwargs_popen_smoke,
    )

    kw_win = montar_kwargs_popen_smoke(["C:\\dist\\EditorAresta.exe", "--smoke-test"], "win32")
    assert "creationflags" in kw_win and "stdout" not in kw_win
    kw_linux = montar_kwargs_popen_smoke(["/app/bin/EditorAresta", "--smoke-test"], "linux")
    assert kw_linux["stdout"] == subprocess.PIPE

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if sys.platform.startswith("win") and pythonw.is_file():
        relatorio_gui = executar_smoke_test_pacote(
            [str(pythonw), "-m", "editor.main"],
            diretorio_trabalho=tmp_path / "smoke_pythonw_detached",
            timeout_segundos=45.0,
        )
        assert relatorio_gui["status"] == "ok"
