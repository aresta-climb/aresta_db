# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais e de integração para `serving/integrador_pr_lib.py`,
utilizando repositórios Git reais em `tmp_path` e `ClienteGhIntegradorFake`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from serving.cliente_gh_integrador_fake import ClienteGhIntegradorFake
from serving.integrador_pr_lib import (
    CheckPullRequest,
    ClienteGhIntegrador,
    ErroClienteGhIntegrador,
    EstadoMergePullRequest,
    InfoPullRequest,
    aguardar_check_dco,
    aguardar_e_validar_checks_pr,
    commitar_e_enviar_alteracoes,
    configurar_identidade_git_bot,
    executar_cli,
    obter_informacoes_pr,
    realizar_merge_com_ressincronizacao,
    sincronizar_branch_com_base,
)


def _criar_par_repositorios_git(tmp_path: Path) -> tuple[Path, Path]:
    """Cria um repositório bare (`origin`) e um clone de trabalho com branch `main` inicializada."""
    dir_origin = tmp_path / "origin.git"
    dir_clone = tmp_path / "trabalho"
    subprocess.run(["git", "init", "--bare", str(dir_origin)], check=True, capture_output=True)
    subprocess.run(
        ["git", "clone", str(dir_origin), str(dir_clone)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Teste Inicial"],
        cwd=dir_clone,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "teste@aresta.climb"],
        cwd=dir_clone,
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "main"], cwd=dir_clone, check=True, capture_output=True
    )
    (dir_clone / "database" / "croqui_a").mkdir(parents=True)
    (dir_clone / "generated").mkdir(parents=True)
    (dir_clone / "generated" / "indice.yaml").write_text("versao: 1\n", encoding="utf-8")
    # Arquivo sem quebra de linha final no ancestral para exercitar merge de EOF
    (dir_clone / "database" / "croqui_a" / "setor.md").write_bytes(
        b"| - | Virose operaria | VIIIa |\n| - | Covidinho | VIIb |\n| - | Covide hepatica | VIIa (4+2) |"
    )
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "chore: estado inicial"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    return dir_origin, dir_clone


def test_cliente_gh_integrador_real_interpreta_respostas_e_trata_falhas() -> None:
    """Garante que `ClienteGhIntegrador` traduz saídas do `gh` CLI e trata códigos de erro."""
    comandos_recebidos: list[list[str]] = []

    def executor_sucesso(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        comandos_recebidos.append(cmd)
        if cmd[:3] == ["gh", "pr", "view"] and "headRefName,baseRefName" in cmd:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=json.dumps({"headRefName": "ai-fix/issue-76", "baseRefName": "main"}),
                stderr="",
            )
        if cmd[:3] == ["gh", "pr", "checks"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=json.dumps([{"name": "validate", "bucket": "pass", "state": "SUCCESS"}]),
                stderr="",
            )
        if cmd[:2] == ["gh", "api"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="123456\n", stderr="")
        if cmd[:3] == ["gh", "pr", "view"] and "mergeable,mergeStateStatus" in cmd:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=json.dumps({"mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}),
                stderr="",
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="Merged", stderr="")

    cliente = ClienteGhIntegrador(
        repositorio="aresta-climb/aresta_db",
        executor_comando=executor_sucesso,
    )
    info = cliente.obter_info_pr(78)
    assert info == InfoPullRequest(numero=78, branch_head="ai-fix/issue-76", branch_base="main")

    checks = cliente.listar_checks_pr(78)
    assert checks == [CheckPullRequest(nome="validate", bucket="pass", state="SUCCESS")]
    assert cliente.obter_id_usuario_bot("aresta-bot[bot]") == "123456"
    assert cliente.obter_estado_merge_pr(78) == EstadoMergePullRequest(
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
    )
    assert cliente.realizar_merge_pr(78) is True

    def executor_falha(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="erro gh")

    cliente_falho = ClienteGhIntegrador(
        repositorio="aresta-climb/aresta_db",
        executor_comando=executor_falha,
    )
    with pytest.raises(ErroClienteGhIntegrador, match="erro gh"):
        cliente_falho.obter_info_pr(78)
    assert cliente_falho.listar_checks_pr(78) == []
    assert cliente_falho.obter_id_usuario_bot("aresta-bot[bot]") == ""
    assert cliente_falho.obter_estado_merge_pr(78) == EstadoMergePullRequest(
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
    )
    assert cliente_falho.realizar_merge_pr(78) is False


def test_obter_informacoes_pr_grava_github_output(tmp_path: Path) -> None:
    """Garante que `obter_informacoes_pr` exporta branch, base_branch e pr_number no GITHUB_OUTPUT."""
    fake = ClienteGhIntegradorFake()
    fake.registrar_info_pr(
        InfoPullRequest(numero=78, branch_head="ai-fix/issue-76", branch_base="main")
    )
    arq_output = tmp_path / "github_output.txt"

    info = obter_informacoes_pr(78, fake, caminho_github_output=arq_output)
    assert info.branch_head == "ai-fix/issue-76"
    assert obter_informacoes_pr(78, fake) == info
    conteudo = arq_output.read_text(encoding="utf-8")
    assert "branch=ai-fix/issue-76\n" in conteudo
    assert "base_branch=main\n" in conteudo
    assert "pr_number=78\n" in conteudo


def test_aguardar_e_validar_checks_pr_ignora_proprio_integrate_e_aprova_apos_pending(
    tmp_path: Path,
) -> None:
    """Garante que o check 'integrate' é ignorado e o polling aguarda outros checks pendentes."""
    fake = ClienteGhIntegradorFake()
    fake.registrar_sequencia_checks(
        78,
        [
            # Tentativa 1: apenas o próprio 'integrate' está presente -> total filtrado = 0
            [CheckPullRequest(nome="integrate", bucket="pending", state="IN_PROGRESS")],
            # Tentativa 2: 'validate' pendente e 'integrate' falho de execução anterior
            [
                CheckPullRequest(nome="integrate", bucket="fail", state="FAILURE"),
                CheckPullRequest(nome="validate", bucket="pending", state="IN_PROGRESS"),
            ],
            # Tentativa 3: 'validate' e 'DCO' aprovados, 'integrate' pendente
            [
                CheckPullRequest(nome="integrate", bucket="pending", state="IN_PROGRESS"),
                CheckPullRequest(nome="validate", bucket="pass", state="SUCCESS"),
                CheckPullRequest(nome="DCO", bucket="pass", state="SUCCESS"),
            ],
        ],
    )
    esperas: list[float] = []
    arq_output = tmp_path / "output.txt"

    codigo = aguardar_e_validar_checks_pr(
        78,
        fake,
        max_tentativas=5,
        intervalo_segundos=10.0,
        funcao_espera=esperas.append,
        caminho_github_output=arq_output,
    )
    assert codigo == 0
    assert esperas == [10.0, 10.0]
    assert "codigo_saida=0\n" in arq_output.read_text(encoding="utf-8")


def test_aguardar_e_validar_checks_pr_fail_fast_timeout_e_pr_invalido(tmp_path: Path) -> None:
    """Garante retorno 2 para PR inválido e retorno 1 para falha de check ou timeout."""
    fake = ClienteGhIntegradorFake()
    arq_invalido = tmp_path / "out_invalido.txt"
    assert (
        aguardar_e_validar_checks_pr(
            0,
            fake,
            funcao_espera=lambda _: None,
            caminho_github_output=arq_invalido,
        )
        == 2
    )
    assert "codigo_saida=2\n" in arq_invalido.read_text(encoding="utf-8")

    # Fail-fast quando 'validate' falha
    fake.registrar_sequencia_checks(
        79,
        [[CheckPullRequest(nome="validate", bucket="fail", state="FAILURE")]],
    )
    arq_falha = tmp_path / "out_falha.txt"
    assert (
        aguardar_e_validar_checks_pr(
            79,
            fake,
            funcao_espera=lambda _: None,
            caminho_github_output=arq_falha,
        )
        == 1
    )
    assert "codigo_saida=1\n" in arq_falha.read_text(encoding="utf-8")

    # Timeout quando continua pending até esgotar max_tentativas
    fake.registrar_sequencia_checks(
        80,
        [[CheckPullRequest(nome="validate", bucket="pending", state="IN_PROGRESS")]],
    )
    arq_timeout = tmp_path / "out_timeout.txt"
    assert (
        aguardar_e_validar_checks_pr(
            80,
            fake,
            max_tentativas=2,
            funcao_espera=lambda _: None,
            caminho_github_output=arq_timeout,
        )
        == 1
    )
    assert "codigo_saida=1\n" in arq_timeout.read_text(encoding="utf-8")


def test_configurar_identidade_git_bot_com_e_sem_id(tmp_path: Path) -> None:
    """Garante configuração de user.name e user.email no Git com e sem ID numérico do bot."""
    _, dir_clone = _criar_par_repositorios_git(tmp_path)
    fake = ClienteGhIntegradorFake()
    fake.registrar_id_bot("aresta-bot[bot]", "554433")

    nome, email = configurar_identidade_git_bot("aresta-bot", fake, dir_clone)
    assert nome == "aresta-bot[bot]"
    assert email == "554433+aresta-bot[bot]@users.noreply.github.com"

    email_git = subprocess.check_output(
        ["git", "config", "user.email"], cwd=dir_clone, text=True
    ).strip()
    assert email_git == "554433+aresta-bot[bot]@users.noreply.github.com"

    fake_sem_id = ClienteGhIntegradorFake()
    _, email_sem_id = configurar_identidade_git_bot("outro-bot", fake_sem_id, dir_clone)
    assert email_sem_id == "outro-bot[bot]@users.noreply.github.com"


def test_sincronizar_branch_com_base_resolve_generated_e_eof_newline(tmp_path: Path) -> None:
    """Garante que o merge prévio resolve conflitos em `generated/` e conflitos de EOF newline em `database/`."""
    dir_origin, dir_clone = _criar_par_repositorios_git(tmp_path)

    # Cria branch do PR #80 a partir do commit inicial da main
    subprocess.run(
        ["git", "checkout", "-b", "ai-fix/issue-75"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    (dir_clone / "generated" / "indice.yaml").write_text("versao: pr80\n", encoding="utf-8")
    (dir_clone / "database" / "croqui_a" / "setor.md").write_text(
        "| - | Virose operaria | VIIIa |\n| - | Covidinho | VIIb |\n| - | Covide hepatica | VIIa (7+2) |\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "feat: atualiza Covide hepatica para 7+2"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )

    # Enquanto isso, a main avança com as mudanças do PR #78 (alterando Virose operaria + EOF newline + generated/)
    subprocess.run(["git", "checkout", "main"], cwd=dir_clone, check=True, capture_output=True)
    (dir_clone / "generated" / "indice.yaml").write_text("versao: main_pr78\n", encoding="utf-8")
    (dir_clone / "database" / "croqui_a" / "setor.md").write_text(
        "| - | Virose operaria | VIIIc |\n| - | Covidinho | VIIb |\n| - | Covide hepatica | VIIa (4+2) |\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "feat: atualiza Virose operaria para 8c"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "main"], cwd=dir_clone, check=True, capture_output=True
    )

    # Volta para a branch do PR #80 e sincroniza com origin/main
    subprocess.run(
        ["git", "checkout", "ai-fix/issue-75"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    codigo = sincronizar_branch_com_base("main", dir_clone)
    assert codigo == 0

    # Verifica que generated/indice.yaml assumiu a base (main_pr78) e setor.md combinou ambas as edições!
    assert (dir_clone / "generated" / "indice.yaml").read_text(
        encoding="utf-8"
    ) == "versao: main_pr78\n"
    conteudo_md = (dir_clone / "database" / "croqui_a" / "setor.md").read_text(encoding="utf-8")
    assert "| - | Virose operaria | VIIIc |" in conteudo_md
    assert "| - | Covide hepatica | VIIa (7+2) |" in conteudo_md


def test_sincronizar_branch_com_base_retorna_erro_em_conflito_real(tmp_path: Path) -> None:
    """Garante retorno 1 quando há conflito real na mesma linha de um arquivo em `database/`."""
    _, dir_clone = _criar_par_repositorios_git(tmp_path)

    subprocess.run(
        ["git", "checkout", "-b", "branch-conflito"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    (dir_clone / "database" / "croqui_a" / "setor.md").write_text(
        "linha 1: edicao da branch\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "feat: edicao branch"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )

    subprocess.run(["git", "checkout", "main"], cwd=dir_clone, check=True, capture_output=True)
    (dir_clone / "database" / "croqui_a" / "setor.md").write_text(
        "linha 1: edicao conflitante na main\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "feat: edicao main"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "main"], cwd=dir_clone, check=True, capture_output=True
    )

    subprocess.run(
        ["git", "checkout", "branch-conflito"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    assert sincronizar_branch_com_base("main", dir_clone) == 1


def test_commitar_e_enviar_alteracoes_com_e_sem_mudancas(tmp_path: Path) -> None:
    """Garante que `commitar_e_enviar_alteracoes` faz commit assinado e push apenas quando há diffs."""
    _, dir_clone = _criar_par_repositorios_git(tmp_path)

    # Sem alterações -> retorna False
    assert commitar_e_enviar_alteracoes(dir_clone) is False

    # Com alterações em generated/ -> faz commit -s e push para origin
    (dir_clone / "generated" / "indice.yaml").write_text("versao: 2\n", encoding="utf-8")
    assert commitar_e_enviar_alteracoes(dir_clone) is True

    mensagem_ultimo_commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%B"], cwd=dir_clone, text=True
    )
    assert "Signed-off-by:" in mensagem_ultimo_commit


def test_aguardar_check_dco_sucesso_falha_e_timeout() -> None:
    """Garante que `aguardar_check_dco` valida aprovação, falha explícita e esgotamento de tempo."""
    fake = ClienteGhIntegradorFake()
    fake.registrar_sequencia_checks(
        78,
        [
            [CheckPullRequest(nome="validate", bucket="pass", state="SUCCESS")],
            [CheckPullRequest(nome="DCO", bucket="pending", state="PENDING")],
            [CheckPullRequest(nome="DCO", bucket="pass", state="SUCCESS")],
        ],
    )
    assert aguardar_check_dco(78, fake, max_tentativas=4, funcao_espera=lambda _: None) == 0

    # Falha explícita do DCO
    fake.registrar_sequencia_checks(
        79,
        [[CheckPullRequest(nome="DCO", bucket="fail", state="ACTION_REQUIRED")]],
    )
    assert aguardar_check_dco(79, fake, max_tentativas=3, funcao_espera=lambda _: None) == 1

    # Timeout aguardando DCO
    fake.registrar_sequencia_checks(
        80,
        [[CheckPullRequest(nome="DCO", bucket="pending", state="PENDING")]],
    )
    assert aguardar_check_dco(80, fake, max_tentativas=2, funcao_espera=lambda _: None) == 1


def test_realizar_merge_com_ressincronizacao_quando_base_avanca(tmp_path: Path) -> None:
    """Garante que `realizar_merge_com_ressincronizacao` recompila e envia quando detecta CONFLICTING."""
    _, dir_clone = _criar_par_repositorios_git(tmp_path)
    fake = ClienteGhIntegradorFake()
    fake.registrar_sequencia_estados_merge(
        78,
        [
            EstadoMergePullRequest(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            EstadoMergePullRequest(mergeable="MERGEABLE", merge_state_status="CLEAN"),
        ],
    )
    fake.registrar_sequencia_resultados_merge(78, [True])

    compilacoes: list[list[str]] = []

    def compilador_falso(pastas: list[str], repo: Path) -> None:
        compilacoes.append(pastas)
        (repo / "generated" / "indice.yaml").write_text("versao: recompilado\n", encoding="utf-8")

    codigo = realizar_merge_com_ressincronizacao(
        78,
        "main",
        fake,
        dir_clone,
        pastas_alteradas=["database/croqui_a"],
        compilador_deploy=compilador_falso,
        max_tentativas=3,
        funcao_espera=lambda _: None,
    )
    assert codigo == 0
    assert compilacoes == [["database/croqui_a"]]
    assert fake.merges_solicitados == [78]

    # Ressincronização sem pastas_alteradas em database/
    fake.registrar_sequencia_estados_merge(
        78,
        [
            EstadoMergePullRequest(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            EstadoMergePullRequest(mergeable="MERGEABLE", merge_state_status="CLEAN"),
        ],
    )
    assert (
        realizar_merge_com_ressincronizacao(
            78,
            "main",
            fake,
            dir_clone,
            pastas_alteradas=None,
            max_tentativas=2,
            funcao_espera=lambda _: None,
        )
        == 0
    )


def test_realizar_merge_com_ressincronizacao_falha_em_conflito_real_ou_esgotamento(
    tmp_path: Path,
) -> None:
    """Garante retorno 1 se o merge falhar em todas as tentativas ou encontrar conflito real."""
    _, dir_clone = _criar_par_repositorios_git(tmp_path)
    fake = ClienteGhIntegradorFake()
    fake.registrar_sequencia_estados_merge(
        78,
        [EstadoMergePullRequest(mergeable="MERGEABLE", merge_state_status="BLOCKED")],
    )
    fake.registrar_sequencia_resultados_merge(78, [False])

    assert (
        realizar_merge_com_ressincronizacao(
            78,
            "main",
            fake,
            dir_clone,
            max_tentativas=2,
            funcao_espera=lambda _: None,
        )
        == 1
    )

    # Cria conflito real entre branch atual e origin/main e simula estado CONFLICTING
    subprocess.run(
        ["git", "checkout", "-b", "branch-conflito-merge"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    (dir_clone / "database" / "croqui_a" / "setor.md").write_text("conflito A\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "feat: A"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "checkout", "main"], cwd=dir_clone, check=True, capture_output=True)
    (dir_clone / "database" / "croqui_a" / "setor.md").write_text("conflito B\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=dir_clone, check=True)
    subprocess.run(
        ["git", "commit", "-s", "-m", "feat: B"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "main"], cwd=dir_clone, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "checkout", "branch-conflito-merge"],
        cwd=dir_clone,
        check=True,
        capture_output=True,
    )

    fake.registrar_sequencia_estados_merge(
        79,
        [EstadoMergePullRequest(mergeable="CONFLICTING", merge_state_status="DIRTY")],
    )
    assert (
        realizar_merge_com_ressincronizacao(
            79,
            "main",
            fake,
            dir_clone,
            max_tentativas=2,
            funcao_espera=lambda _: None,
        )
        == 1
    )


def test_executar_cli_todos_subcomandos(tmp_path: Path) -> None:
    """Exercita todos os subcomandos públicos de `executar_cli` de ponta a ponta."""
    _, dir_clone = _criar_par_repositorios_git(tmp_path)
    fake = ClienteGhIntegradorFake()
    fake.registrar_info_pr(
        InfoPullRequest(numero=78, branch_head="ai-fix/issue-76", branch_base="main")
    )
    fake.registrar_sequencia_checks(
        78,
        [
            [
                CheckPullRequest(nome="validate", bucket="pass", state="SUCCESS"),
                CheckPullRequest(nome="DCO", bucket="pass", state="SUCCESS"),
            ]
        ],
    )
    fake.registrar_id_bot("aresta-bot[bot]", "112233")

    arq_out = tmp_path / "gh_out.txt"
    assert (
        executar_cli(
            [
                "obter-info",
                "--pr",
                "78",
                "--repo",
                "aresta-climb/aresta_db",
                "--github-output",
                str(arq_out),
            ],
            cliente_gh=fake,
            diretorio_repo=dir_clone,
            funcao_espera=lambda _: None,
        )
        == 0
    )

    assert (
        executar_cli(
            [
                "validar-checks",
                "--pr",
                "78",
                "--repo",
                "aresta-climb/aresta_db",
                "--github-output",
                str(arq_out),
            ],
            cliente_gh=fake,
            diretorio_repo=dir_clone,
            funcao_espera=lambda _: None,
        )
        == 0
    )

    assert (
        executar_cli(
            [
                "sincronizar-base",
                "--base-branch",
                "main",
                "--app-slug",
                "aresta-bot",
                "--repo",
                "aresta-climb/aresta_db",
            ],
            cliente_gh=fake,
            diretorio_repo=dir_clone,
            funcao_espera=lambda _: None,
        )
        == 0
    )

    (dir_clone / "generated" / "indice.yaml").write_text("versao: 3\n", encoding="utf-8")
    assert (
        executar_cli(
            [
                "commitar-e-enviar",
                "--app-slug",
                "aresta-bot",
                "--repo",
                "aresta-climb/aresta_db",
            ],
            cliente_gh=fake,
            diretorio_repo=dir_clone,
            funcao_espera=lambda _: None,
        )
        == 0
    )

    assert (
        executar_cli(
            [
                "verificar-dco",
                "--pr",
                "78",
                "--repo",
                "aresta-climb/aresta_db",
            ],
            cliente_gh=fake,
            diretorio_repo=dir_clone,
            funcao_espera=lambda _: None,
        )
        == 0
    )

    assert (
        executar_cli(
            [
                "realizar-merge",
                "--pr",
                "78",
                "--repo",
                "aresta-climb/aresta_db",
                "--base-branch",
                "main",
                "--pastas",
                "database/croqui_a",
            ],
            cliente_gh=fake,
            diretorio_repo=dir_clone,
            funcao_espera=lambda _: None,
            compilador_deploy=lambda _p, _r: None,
        )
        == 0
    )
