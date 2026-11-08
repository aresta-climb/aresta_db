# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento e integração para o ponto de entrada CLI
`serving/resolver_feedback_ia.py`, exercitando compilação real de croqui e
repositório Git local real (`tmp_path`).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from serving.agente_feedback.cliente_gemini_feedback import (
    AlteracaoArquivoProposta,
    RespostaPropostaGemini,
)
from serving.agente_feedback.cliente_gemini_feedback_fake import ClienteGeminiFeedbackFake
from serving.agente_feedback.cliente_github_feedback import DadosIssueOuPr
from serving.agente_feedback.cliente_github_feedback_fake import ClienteGithubFeedbackFake
from serving.resolver_feedback_ia import (
    executar_cli,
    executar_commit_e_push_git,
    validar_pasta_croqui_local,
)


def _criar_croqui_compilavel(pasta_db: Path) -> Path:
    pasta_croqui = pasta_db / "br_mg_teste"
    (pasta_croqui / "imagens").mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (100, 100), color=(30, 50, 70))
    img.save(pasta_croqui / "imagens" / "capa.webp", format="WEBP")

    (pasta_croqui / "croqui.yaml").write_text(
        """# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: Ygo9aN5g9LtcLo
id: br_mg_teste
nome: Pico Teste
descricao: Descrição do pico
caminho_thumbnail: imagens/capa.webp
revisado_manualmente: true
status_desenho_extraivel: DESENHO_EXTRAIDO
picos:
- nome: Pico Teste
  setores_ou_grupos:
  - setor:
      caminho: setor_a.md
  localizacao:
    latitude: -197151110
    longitude: -467977210
  cidade: Araxá
  estado: MG
ultima_migracao: 5
publicar_croqui: true
""",
        encoding="utf-8",
    )
    (pasta_croqui / "setor_a.md").write_text(
        """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: dwuQyJozrODbgq
nome: Setor A
escaladas:
- uid: 0u3XfCe434ygyF
  via_esportiva:
    nome: Excalibur
    dificuldade: BR_7C
---

Texto do setor A.
""",
        encoding="utf-8",
    )
    return pasta_croqui


def test_valida_pasta_croqui_real_detectando_sucesso_e_erro_de_schema(
    tmp_path: Path,
) -> None:
    pasta_db = tmp_path / "database"
    pasta_croqui = _criar_croqui_compilavel(pasta_db)

    assert validar_pasta_croqui_local(pasta_croqui) == []

    # Introduz um enum de dificuldade inexistente no Protobuf para exercitar falha real de compilação
    texto_invalido = (
        (pasta_croqui / "setor_a.md")
        .read_text(encoding="utf-8")
        .replace("BR_7C", "GRAU_INEXISTENTE_99")
    )
    (pasta_croqui / "setor_a.md").write_text(texto_invalido, encoding="utf-8")

    erros = validar_pasta_croqui_local(pasta_croqui)
    assert len(erros) == 1
    assert "GRAU_INEXISTENTE_99" in erros[0] or "Falha" in erros[0]


def test_executa_commit_assinado_e_push_em_repositorio_git_local_real(
    tmp_path: Path,
) -> None:
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "--bare", str(remoto)], check=True)

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(remoto), str(clone)], check=True)
    subprocess.run(["git", "config", "user.name", "Aresta Bot"], cwd=clone, check=True)
    subprocess.run(["git", "config", "user.email", "bot@arestaclimb.com"], cwd=clone, check=True)

    arq = clone / "setor_a.md"
    arq.write_text("inicial", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=clone, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=clone, check=True)

    arq.write_text("atualizado", encoding="utf-8")
    executar_commit_e_push_git(
        branch_alvo="ai-fix/issue-99",
        mensagem_commit="fix: atualiza setor\n\nFixes #99",
        arquivos_modificados=[arq],
        diretorio_repo=clone,
    )

    log_remoto = subprocess.run(
        ["git", "log", "-1", "--format=%B", "refs/heads/ai-fix/issue-99"],
        cwd=remoto,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Fixes #99" in log_remoto
    assert "Signed-off-by:" in log_remoto


def test_executa_cli_ponta_a_ponta_com_sucesso(tmp_path: Path) -> None:
    pasta_db = tmp_path / "database"
    pasta_croqui = _criar_croqui_compilavel(pasta_db)
    novo_conteudo = (
        (pasta_croqui / "setor_a.md").read_text(encoding="utf-8").replace("BR_7C", "BR_7B")
    )

    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=7,
            titulo="[Croqui | br_mg_teste] Grau Excalibur",
            corpo="- **Pico / Croqui:** `br_mg_teste`\n- **Árvore de Navegação:** `Setor (Setor A)`\n## Descrição\nGrau é 7b",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    gemini_fake = ClienteGeminiFeedbackFake(
        respostas_proposta=[
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix(br_mg_teste): muda grau para 7b",
                resumo_mudanca="Grau atualizado para BR_7B.",
                motivo_nao_acionavel="",
                alteracoes=[AlteracaoArquivoProposta("setor_a.md", novo_conteudo)],
            )
        ]
    )

    codigo_saida = executar_cli(
        argv=[
            "--numero-alvo",
            "7",
            "--diretorio-database",
            str(pasta_db),
        ],
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, a: None,
    )

    assert codigo_saida == 0
    assert "Pull Request #100" in github_fake.comentarios_publicados[-1][1]
