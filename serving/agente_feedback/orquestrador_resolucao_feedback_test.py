# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento e integração para `OrquestradorResolucaoFeedback`,
exercitando o fluxo completo de Issues `feedback:croqui`, comando `/ai-fix` em Issues
e PRs, Hard Jail de escopo em `database/<croqui_id>/`, preservação SPDX e autoretry.
"""

from __future__ import annotations

from pathlib import Path

from serving.agente_feedback.cliente_gemini_feedback import (
    AlteracaoArquivoProposta,
    RespostaPropostaGemini,
)
from serving.agente_feedback.cliente_gemini_feedback_fake import ClienteGeminiFeedbackFake
from serving.agente_feedback.cliente_github_feedback import DadosIssueOuPr
from serving.agente_feedback.cliente_github_feedback_fake import ClienteGithubFeedbackFake
from serving.agente_feedback.orquestrador_resolucao_feedback import (
    OrquestradorResolucaoFeedback,
    validar_escopo_e_cabecalho_alteracao,
)

CONTEUDO_SETOR_VALIDO_7C = """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: dwuQyJozrODbgq
nome: Setor Bem-vindo
escaladas:
- uid: 0u3XfCe434ygyF
  via_esportiva:
    nome: Excalibur
    dificuldade: BR_7C
---

Descrição do setor.
"""

CONTEUDO_SETOR_VALIDO_7B = """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: dwuQyJozrODbgq
nome: Setor Bem-vindo
escaladas:
- uid: 0u3XfCe434ygyF
  via_esportiva:
    nome: Excalibur
    dificuldade: BR_7B
---

Descrição do setor.
"""


def _preparar_croqui_no_disco(tmp_path: Path) -> Path:
    pasta_db = tmp_path / "database"
    pasta_croqui = pasta_db / "br_mg_araxa"
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    (pasta_croqui / "croqui.yaml").write_text(
        """# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: Ygo9aN5g9LtcLo
id: br_mg_araxa
nome: Bocaina
picos:
- nome: Bocaina
  setores_ou_grupos:
  - setor:
      caminho: setor_bem_vindo.md
ultima_migracao: 5
""",
        encoding="utf-8",
    )
    (pasta_croqui / "setor_bem_vindo.md").write_text(CONTEUDO_SETOR_VALIDO_7C, encoding="utf-8")
    return pasta_db


def test_resolve_issue_automaticamente_criando_branch_commit_e_pull_request(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_no_disco(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=15,
            titulo="[Croqui | br_mg_araxa] Grau errado",
            corpo=(
                "## Descrição\nO grau da Excalibur é 7b\n\n"
                "### Captura de Tela\n"
                '<a href="https://feedback.arestaclimb.com/anexos/15/screenshot.webp">img</a>\n\n'
                "## Informações Gerais\n"
                "- **Pico / Croqui:** `br_mg_araxa`\n"
                "- **Árvore de Navegação:** `Início -> Pico (br_mg_araxa) -> Setor (Setor Bem-vindo) -> Via (Excalibur)`\n"
            ),
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    github_fake.registrar_anexo(
        "https://feedback.arestaclimb.com/anexos/15/screenshot.webp",
        b"webp_bytes",
        "image/webp",
    )

    gemini_fake = ClienteGeminiFeedbackFake(
        respostas_proposta=[
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix(br_mg_araxa): altera grau da via Excalibur para 7b",
                resumo_mudanca="Atualizado campo dificuldade de BR_7C para BR_7B.",
                motivo_nao_acionavel="",
                alteracoes=[
                    AlteracaoArquivoProposta(
                        arquivo_relativo="setor_bem_vindo.md",
                        conteudo_novo=CONTEUDO_SETOR_VALIDO_7B,
                    )
                ],
            )
        ]
    )

    commits_realizados: list[tuple[str, str, list[str]]] = []

    def executor_git_memoria(branch: str, mensagem: str, arquivos: list[Path]) -> None:
        commits_realizados.append((branch, mensagem, [a.name for a in arquivos]))

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=executor_git_memoria,
        validador_croqui=lambda _: [],
    )

    resultado = orquestrador.processar_evento(numero_issue_ou_pr=15)

    assert resultado.status == "pr_criada"
    assert resultado.numero_pr == 100
    assert (pasta_db / "br_mg_araxa" / "setor_bem_vindo.md").read_text(
        encoding="utf-8"
    ) == CONTEUDO_SETOR_VALIDO_7B
    assert len(commits_realizados) == 1
    assert commits_realizados[0][0] == "ai-fix/issue-15"
    assert "Fixes #15" in commits_realizados[0][1]
    assert "Pull Request #100" in github_fake.comentarios_publicados[-1][1]


def test_realiza_autoretry_quando_primeira_tentativa_falha_no_validador(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_no_disco(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=16,
            titulo="[Croqui | br_mg_araxa] Grau Excalibur",
            corpo="- **Pico / Croqui:** `br_mg_araxa`\n- **Árvore de Navegação:** `Início -> Pico (br_mg_araxa)`",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )

    conteudo_invalido = CONTEUDO_SETOR_VALIDO_7C.replace("BR_7C", "SETE_B_INVALIDO")
    gemini_fake = ClienteGeminiFeedbackFake(
        arquivos_desambiguados=["setor_bem_vindo.md"],
        respostas_proposta=[
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix: tentativa 1",
                resumo_mudanca="Tentativa 1",
                motivo_nao_acionavel="",
                alteracoes=[AlteracaoArquivoProposta("setor_bem_vindo.md", conteudo_invalido)],
            ),
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix: tentativa 2 valida",
                resumo_mudanca="Tentativa 2",
                motivo_nao_acionavel="",
                alteracoes=[
                    AlteracaoArquivoProposta("setor_bem_vindo.md", CONTEUDO_SETOR_VALIDO_7B)
                ],
            ),
        ],
    )

    def validador_simulado(pasta_croqui: Path) -> list[str]:
        texto = (pasta_croqui / "setor_bem_vindo.md").read_text(encoding="utf-8")
        if "SETE_B_INVALIDO" in texto:
            return ["Enum de dificuldade inválido: SETE_B_INVALIDO"]
        return []

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, a: None,
        validador_croqui=validador_simulado,
    )

    resultado = orquestrador.processar_evento(numero_issue_ou_pr=16)

    assert resultado.status == "pr_criada"
    assert len(gemini_fake.chamadas_desambiguacao) == 1
    assert len(gemini_fake.chamadas_proposta) == 2
    assert "SETE_B_INVALIDO" in gemini_fake.chamadas_proposta[1]["erro_validacao_anterior"]


def test_aborta_e_restaura_disco_quando_autoretry_tambem_falha_na_validacao(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_no_disco(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=17,
            titulo="[Croqui | br_mg_araxa] Teste falha dupla",
            corpo="- **Pico / Croqui:** `br_mg_araxa`\n- **Árvore de Navegação:** `Setor (Setor Bem-vindo)`",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    conteudo_quebrado = CONTEUDO_SETOR_VALIDO_7C.replace("BR_7C", "INVALIDO")
    gemini_fake = ClienteGeminiFeedbackFake(
        respostas_proposta=[
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix: tentativa sem spdx",
                resumo_mudanca="Resumo",
                motivo_nao_acionavel="",
                alteracoes=[AlteracaoArquivoProposta("setor_bem_vindo.md", "sem cabecalho spdx")],
            ),
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix: invalido",
                resumo_mudanca="Resumo",
                motivo_nao_acionavel="",
                alteracoes=[AlteracaoArquivoProposta("setor_bem_vindo.md", conteudo_quebrado)],
            ),
        ]
    )

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, a: None,
        validador_croqui=lambda _: ["Erro persistente de compilação Protobuf"],
    )

    resultado = orquestrador.processar_evento(numero_issue_ou_pr=17)

    assert resultado.status == "falha_validacao"
    # Verifica que o arquivo original em disco foi restaurado ao estado íntegro
    assert (pasta_db / "br_mg_araxa" / "setor_bem_vindo.md").read_text(
        encoding="utf-8"
    ) == CONTEUDO_SETOR_VALIDO_7C
    assert "Erro persistente" in github_fake.comentarios_publicados[-1][1]


def test_processa_comando_ai_fix_em_pr_existente_e_bloqueia_usuarios_nao_autorizados(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_no_disco(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=50,
            titulo="fix(br_mg_araxa): ajuste inicial",
            corpo="Closes #15",
            labels=[],
            eh_pull_request=True,
            branch_head="ai-fix/issue-15",
        )
    )
    github_fake.registrar_arquivos_pr(50, ["database/br_mg_araxa/setor_bem_vindo.md"])

    gemini_fake = ClienteGeminiFeedbackFake(
        respostas_proposta=[
            RespostaPropostaGemini(
                acionavel=True,
                titulo_pr="fix(br_mg_araxa): ajuste complementar",
                resumo_mudanca="Ajustado grau conforme revisão.",
                motivo_nao_acionavel="",
                alteracoes=[
                    AlteracaoArquivoProposta("setor_bem_vindo.md", CONTEUDO_SETOR_VALIDO_7B)
                ],
            )
        ]
    )

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, a: None,
        validador_croqui=lambda _: [],
    )

    # 1. Comentário de usuário anônimo (NONE) ou sem comando /ai-fix é ignorado
    res_nao_autorizado = orquestrador.processar_evento(
        numero_issue_ou_pr=50,
        corpo_comentario="/ai-fix Faz algo malicioso",
        associacao_autor="NONE",
    )
    assert res_nao_autorizado.status == "ignorado"

    res_sem_comando = orquestrador.processar_evento(
        numero_issue_ou_pr=50,
        corpo_comentario="Apenas um comentário normal",
        associacao_autor="OWNER",
    )
    assert res_sem_comando.status == "ignorado"

    # 2. Comentário de mantenedor (MEMBER) com /ai-fix na PR atualiza a PR existente
    res_pr = orquestrador.processar_evento(
        numero_issue_ou_pr=50,
        corpo_comentario="/ai-fix Muda para 7b também",
        associacao_autor="MEMBER",
    )
    assert res_pr.status == "pr_atualizada"
    assert res_pr.numero_pr == 50


def test_bloqueia_path_traversal_extensao_invalida_e_remocao_de_spdx(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_no_disco(tmp_path)
    pasta_croqui = pasta_db / "br_mg_araxa"

    assert (
        validar_escopo_e_cabecalho_alteracao(
            pasta_croqui,
            AlteracaoArquivoProposta("../outro.md", CONTEUDO_SETOR_VALIDO_7B),
        )
        is not None
    )
    assert (
        validar_escopo_e_cabecalho_alteracao(
            pasta_croqui,
            AlteracaoArquivoProposta("script.py", CONTEUDO_SETOR_VALIDO_7B),
        )
        is not None
    )
    assert (
        validar_escopo_e_cabecalho_alteracao(
            pasta_croqui,
            AlteracaoArquivoProposta("setor_bem_vindo.md", "sem cabecalho spdx"),
        )
        is not None
    )


def test_comenta_motivo_quando_feedback_nao_for_acionavel_ou_croqui_inexistente(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_no_disco(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=60,
            titulo="[Croqui] Sem ID",
            corpo="Feedback sem croqui_id",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=61,
            titulo="[Croqui | br_mg_araxa] Linha da via",
            corpo="- **Pico / Croqui:** `br_mg_araxa`\n- **Árvore de Navegação:** `Setor (Setor Bem-vindo)`\n## Descrição\nO traçado vetorial está torto.",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )

    gemini_fake = ClienteGeminiFeedbackFake(
        respostas_proposta=[
            RespostaPropostaGemini(
                acionavel=False,
                titulo_pr="",
                resumo_mudanca="",
                motivo_nao_acionavel="Requer edição manual do traçado vetorial no Editor Aresta.",
                alteracoes=[],
            )
        ]
    )

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, a: None,
        validador_croqui=lambda _: [],
    )

    res_sem_croqui = orquestrador.processar_evento(numero_issue_ou_pr=60)
    assert res_sem_croqui.status == "croqui_nao_identificado"

    res_nao_acionavel = orquestrador.processar_evento(numero_issue_ou_pr=61)
    assert res_nao_acionavel.status == "nao_acionavel"
    assert "/ai-fix" in github_fake.comentarios_publicados[-1][1]
