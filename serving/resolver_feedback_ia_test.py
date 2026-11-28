# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais e de integração para `serving/resolver_feedback_ia.py`,
validando `git add -A` restrito à pasta do croqui (edição, adição e deleção de `.md`)
e execução ponta a ponta via CLI com `SessaoEditorHeadless`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from serving.agente_feedback.cliente_gemini_feedback import (
    NOME_FERRAMENTA_FINALIZAR,
    ChamadaFerramentaAgente,
)
from serving.agente_feedback.cliente_gemini_feedback_fake import ClienteGeminiFeedbackFake
from serving.agente_feedback.cliente_github_feedback import DadosIssueOuPr
from serving.agente_feedback.cliente_github_feedback_fake import ClienteGithubFeedbackFake
from serving.resolver_feedback_ia import executar_cli, executar_commit_e_push_git


def _criar_croqui_compilavel(pasta_db: Path) -> Path:
    pasta_croqui = pasta_db / "br_mg_teste"
    (pasta_croqui / "imagens").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (100, 100), color=(30, 50, 70)).save(
        pasta_croqui / "imagens" / "capa.webp", format="WEBP"
    )
    (pasta_croqui / "croqui.yaml").write_text(
        """# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: Ygo9aN5g9LtcLo
id: br_mg_teste
nome: Pico Teste
descricao: Descrição do pico
caminho_thumbnail: imagens/capa.webp
ultima_migracao: 5
publicar_croqui: true
picos:
- nome: Pico Teste
  cidade: Araxá
  estado: MG
  setores_ou_grupos:
  - setor:
      caminho: setor_a.md
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


def test_executa_commit_assinado_e_push_capturando_novos_e_removidos_sem_tocar_fora(
    tmp_path: Path,
) -> None:
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "--bare", str(remoto)], check=True)

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(remoto), str(clone)], check=True)
    subprocess.run(["git", "config", "user.name", "Aresta Bot"], cwd=clone, check=True)
    subprocess.run(["git", "config", "user.email", "bot@arestaclimb.com"], cwd=clone, check=True)

    pasta_croqui = clone / "database" / "br_mg_teste"
    pasta_croqui.mkdir(parents=True)
    arq_antigo = pasta_croqui / "antigo.md"
    arq_antigo.write_text("antigo", encoding="utf-8")
    arq_fora = clone / "README.md"
    arq_fora.write_text("original", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=clone, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=clone, check=True)

    # Deleta antigo.md, cria setor_novo.md e suja README.md fora de database/br_mg_teste
    arq_antigo.unlink()
    (pasta_croqui / "setor_novo.md").write_text("novo setor", encoding="utf-8")
    arq_fora.write_text("sujo fora do escopo", encoding="utf-8")

    executar_commit_e_push_git(
        branch_alvo="ai-fix/issue-108",
        mensagem_commit="fix: migra setor\n\nFixes #108",
        pasta_croqui=pasta_croqui,
        diretorio_repo=clone,
    )

    arquivos_commit = subprocess.run(
        ["git", "show", "--name-status", "--format=", "refs/heads/ai-fix/issue-108"],
        cwd=remoto,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "D\tdatabase/br_mg_teste/antigo.md" in arquivos_commit
    assert "A\tdatabase/br_mg_teste/setor_novo.md" in arquivos_commit
    assert "README.md" not in arquivos_commit


def test_executa_cli_ponta_a_ponta_com_sessao_headless_link_action_e_codigo_saida_falha(
    tmp_path: Path,
) -> None:
    pasta_db = tmp_path / "database"
    pasta_croqui = _criar_croqui_compilavel(pasta_db)

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
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=8,
            titulo="Sem croqui válido",
            corpo="Relato sem croqui_id",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    gemini_fake = ClienteGeminiFeedbackFake(
        turnos_programados=[
            [
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {"alvo": "0u3XfCe434ygyF", "campo": "dificuldade", "valor": "BR_7B"},
                ),
                ChamadaFerramentaAgente(
                    NOME_FERRAMENTA_FINALIZAR,
                    {
                        "acao": "abrir_pr",
                        "titulo_pr": "fix(br_mg_teste): muda grau para 7b",
                        "resumo_mudanca": "Grau atualizado para BR_7B.",
                    },
                ),
            ]
        ]
    )

    ambiente_actions = {
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "aresta-climb/aresta_db",
        "GITHUB_RUN_ID": "46084467316",
    }
    codigo_saida = executar_cli(
        argv=[
            "--numero-alvo",
            "7",
            "--diretorio-database",
            str(pasta_db),
        ],
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
        ambiente=ambiente_actions,
    )

    assert codigo_saida == 0
    comentario_sucesso = github_fake.comentarios_publicados[-1][1]
    assert "Pull Request #100" in comentario_sucesso
    assert (
        "https://github.com/aresta-climb/aresta_db/actions/runs/46084467316" in comentario_sucesso
    )
    assert "BR_7B" in (pasta_croqui / "setor_a.md").read_text(encoding="utf-8")

    # Quando falha (croqui_nao_identificado ou falha_validacao), retorna código de saída 1 e inclui link da Action!
    codigo_falha = executar_cli(
        argv=[
            "--numero-alvo",
            "8",
            "--diretorio-database",
            str(pasta_db),
        ],
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
        ambiente={},
    )
    assert codigo_falha == 1
