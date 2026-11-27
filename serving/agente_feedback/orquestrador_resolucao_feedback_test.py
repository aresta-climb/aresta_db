# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais e de integração para `OrquestradorResolucaoFeedback`,
validando resolução em 1 turno, resolução multi-turno (Issue #108 e mapas com lupa),
autoretry de compilação, Circuit Breaker, desistência voluntária, guarda determinística
de Mudança Maior (e seu destravamento por `/ai-fix`) e Hard Jail de diretório.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from serving.agente_feedback.cliente_gemini_feedback import (
    NOME_FERRAMENTA_FINALIZAR,
    ChamadaFerramentaAgente,
)
from serving.agente_feedback.cliente_gemini_feedback_fake import ClienteGeminiFeedbackFake
from serving.agente_feedback.cliente_github_feedback import DadosIssueOuPr
from serving.agente_feedback.cliente_github_feedback_fake import ClienteGithubFeedbackFake
from serving.agente_feedback.orquestrador_resolucao_feedback import (
    OrquestradorResolucaoFeedback,
    validar_diretorio_croqui_pos_edicao,
)


def _preparar_croqui_gravata(tmp_path: Path) -> Path:
    pasta_db = tmp_path / "database"
    pasta_croqui = pasta_db / "br_mg_betim_pedreira_dr_gravata"
    (pasta_croqui / "imagens").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 80), color="gray").save(
        pasta_croqui / "imagens" / "thumbnail.webp", "WEBP"
    )

    (pasta_croqui / "croqui.yaml").write_text(
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        "uid: IueFHQqpIFT4cY\n"
        "id: br_mg_betim_pedreira_dr_gravata\n"
        "nome: Pedreira Dr. Gravatá\n"
        "ultima_migracao: 5\n"
        "caminho_thumbnail: imagens/thumbnail.webp\n"
        "publicar_croqui: true\n"
        "botoes:\n"
        "- uid: TPwpXHpSFVkDEy\n"
        "  texto: Como Chegar\n"
        "  destino:\n"
        "    secao_textual:\n"
        "      caminho: como_chegar.md\n"
        "picos:\n"
        "- nome: Pedreira Dr. Gravatá\n"
        "  estado: MG\n"
        "  cidade: Betim\n"
        "  setores_ou_grupos:\n"
        "  - grupo:\n"
        "      caminho: grupo_setores.md\n",
        encoding="utf-8",
    )
    (pasta_croqui / "como_chegar.md").write_text(
        "Acesso pela estrada principal.\n",
        encoding="utf-8",
    )
    (pasta_croqui / "grupo_setores.md").write_text(
        "---\n"
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        "uid: QtxIGEyTkA9Q5c\n"
        "nome: Setores\n"
        "setores:\n"
        "- caminho: setor_das_treze.md\n"
        "---\n",
        encoding="utf-8",
    )
    (pasta_croqui / "setor_das_treze.md").write_text(
        "---\n"
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        "uid: 8SUSM2sgVKSevu\n"
        "nome: Setor das Treze\n"
        "mapas:\n"
        "- caminho_imagem_mapa: imagens/thumbnail.webp\n"
        "  largura_mapa: 120\n"
        "  altura_mapa: 80\n"
        "  pontos_de_interesse:\n"
        "  - uid: poiConfusao001\n"
        "    rotulo: '9'\n"
        "    circulo:\n"
        "      x: 40\n"
        "      y: 40\n"
        "      raio: 10\n"
        "escaladas:\n"
        "- uid: b3vo1qYPGndTMI\n"
        "  via_esportiva:\n"
        "    nome: PRIMEIRINHA\n"
        "    dificuldade: BR_6SUP\n"
        "- uid: TC8Wd0pa4YopiM\n"
        "  via_esportiva:\n"
        "    nome: CONFUSAO MENTAL\n"
        "    dificuldade: BR_7A\n"
        "    conquistadores:\n"
        "    - Macena, Samuel, Maceninha\n"
        "---\n",
        encoding="utf-8",
    )
    return pasta_db


def test_resolve_edicao_direta_em_apenas_1_turno_de_ia(tmp_path: Path) -> None:
    """Caso simples (~85% dos feedbacks): 1 única chamada de IA edita via UID e finaliza PR."""
    pasta_db = _preparar_croqui_gravata(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=15,
            titulo="[Croqui | br_mg_betim_pedreira_dr_gravata] Grau da Confusão Mental",
            corpo=(
                "## Descrição\nO grau da Confusão Mental é 7b\n\n"
                "### Captura de Tela\n"
                '<a href="https://feedback.arestaclimb.com/anexos/15/screenshot.webp">img</a>\n\n'
                "## Informações Gerais\n"
                "- **Pico / Croqui:** `br_mg_betim_pedreira_dr_gravata`\n"
                "- **Árvore de Navegação:** `Setor (Setor das Treze) -> Via (CONFUSAO MENTAL)`\n"
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
        turnos_programados=[
            [
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {"alvo": "TC8Wd0pa4YopiM", "campo": "dificuldade", "valor": "BR_7B"},
                ),
                ChamadaFerramentaAgente(
                    NOME_FERRAMENTA_FINALIZAR,
                    {
                        "acao": "abrir_pr",
                        "titulo_pr": "fix(br_mg_betim_pedreira_dr_gravata): ajusta grau da via Confusão Mental",
                        "resumo_mudanca": "Atualiza dificuldade da via CONFUSAO MENTAL para BR_7B.",
                    },
                ),
            ]
        ]
    )

    commits: list[tuple[str, str, Path]] = []
    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda branch, msg, pasta: commits.append((branch, msg, pasta)),
    )

    resultado = orquestrador.processar_evento(numero_issue_ou_pr=15)
    assert resultado.status == "pr_criada"
    assert resultado.numero_pr == 100
    assert len(gemini_fake.chamadas_turnos) == 1
    assert "BR_7B" in (
        pasta_db / "br_mg_betim_pedreira_dr_gravata" / "setor_das_treze.md"
    ).read_text(encoding="utf-8")
    assert len(commits) == 1
    assert commits[0][0] == "ai-fix/issue-15"
    assert commits[0][2] == pasta_db / "br_mg_betim_pedreira_dr_gravata"


def test_resolve_issue_108_multi_turno_criando_setor_do_palanque_e_migrando_via(
    tmp_path: Path,
) -> None:
    """Reproduz fielmente a Issue #108 em 2 turnos: cria Setor do Palanque, migra via preservando UID e remove Maceninha."""
    pasta_db = _preparar_croqui_gravata(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=108,
            titulo="[Croqui | br_mg_betim_pedreira_dr_gravata] Essa via pertence ao setor do palanque...",
            corpo=(
                "## Descrição\n"
                "Essa via pertence ao setor do palanque e o Maceninha nao participou da conquista\n\n"
                "## Informações Gerais\n"
                "- **Pico / Croqui:** `br_mg_betim_pedreira_dr_gravata`\n"
                "- **Árvore de Navegação:** `Início -> Pico (br_mg_betim_pedreira_dr_gravata) -> Grupo (Setores) -> Setor (Setor das Treze) -> Via (CONFUSAO MENTAL)`\n"
            ),
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )

    def roteiro_issue_108(
        historico: list[dict[str, Any]], indice_turno: int
    ) -> list[ChamadaFerramentaAgente]:
        if indice_turno == 0:
            return [
                ChamadaFerramentaAgente(
                    "aresta_adicionar_repeated",
                    {
                        "alvo": "QtxIGEyTkA9Q5c",
                        "campo": "setores",
                        "valor": {"nome": "Setor do Palanque"},
                    },
                ),
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {
                        "alvo": "TC8Wd0pa4YopiM",
                        "campo": "conquistadores",
                        "valor": ["Macena, Samuel"],
                    },
                ),
            ]
        # Turno 2: extrai o UID real do Setor do Palanque retornado pelo Editor no Turno 1
        partes_resp = historico[-1]["parts"]
        uid_palanque = partes_resp[0]["functionResponse"]["response"]["structuredContent"]["uid"]
        return [
            ChamadaFerramentaAgente(
                "aresta_migrar_escalada",
                {
                    "alvo_escalada": "TC8Wd0pa4YopiM",
                    "alvo_setor_destino": uid_palanque,
                },
            ),
            ChamadaFerramentaAgente(
                NOME_FERRAMENTA_FINALIZAR,
                {
                    "acao": "abrir_pr",
                    "titulo_pr": "fix(br_mg_betim_pedreira_dr_gravata): move Confusão Mental para Setor do Palanque",
                    "resumo_mudanca": "Cria o Setor do Palanque, migra a via CONFUSAO MENTAL preservando seu UID e ajusta os conquistadores.",
                },
            ),
        ]

    gemini_fake = ClienteGeminiFeedbackFake(roteiro_dinamico=roteiro_issue_108)
    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )

    resultado = orquestrador.processar_evento(numero_issue_ou_pr=108)
    assert resultado.status == "pr_criada"
    assert len(gemini_fake.chamadas_turnos) == 2

    pasta_croqui = pasta_db / "br_mg_betim_pedreira_dr_gravata"
    novos_md = [
        p
        for p in pasta_croqui.glob("*.md")
        if p.name not in {"como_chegar.md", "grupo_setores.md", "setor_das_treze.md"}
    ]
    assert len(novos_md) == 1
    conteudo_palanque = novos_md[0].read_text(encoding="utf-8")
    assert "Setor do Palanque" in conteudo_palanque
    assert "TC8Wd0pa4YopiM" in conteudo_palanque
    assert "Macena, Samuel" in conteudo_palanque
    assert "Maceninha" not in conteudo_palanque


def test_renderiza_mapa_sob_demanda_e_autocorrige_erro_de_ferramenta_no_turno_seguinte(
    tmp_path: Path,
) -> None:
    """Valida retorno multimodal de aresta_renderizar_mapa e autocorreção quando Turno 1 envia enum inválido."""
    pasta_db = _preparar_croqui_gravata(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=20,
            titulo="[Croqui | br_mg_betim_pedreira_dr_gravata] Ajuste POI",
            corpo="- **Pico / Croqui:** `br_mg_betim_pedreira_dr_gravata`\n## Descrição\nO ponto 9 está deslocado.",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )

    gemini_fake = ClienteGeminiFeedbackFake(
        turnos_programados=[
            # Turno 1: pede renderização do mapa
            [ChamadaFerramentaAgente("aresta_renderizar_mapa", {"alvo": "8SUSM2sgVKSevu"})],
            # Turno 2: envia enum inválido junto com finalizar -> recebe erro e não fecha
            [
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {"alvo": "TC8Wd0pa4YopiM", "campo": "dificuldade", "valor": "ENUM_INVALIDO"},
                ),
                ChamadaFerramentaAgente(
                    NOME_FERRAMENTA_FINALIZAR,
                    {"acao": "abrir_pr", "titulo_pr": "fix: erro", "resumo_mudanca": "erro"},
                ),
            ],
            # Turno 3: corrige coordenada do POI e finaliza com sucesso
            [
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {
                        "alvo": "poiConfusao001",
                        "campo": "circulo",
                        "valor": {"x": 55, "y": 45, "raio": 10},
                    },
                ),
                ChamadaFerramentaAgente(
                    NOME_FERRAMENTA_FINALIZAR,
                    {
                        "acao": "abrir_pr",
                        "titulo_pr": "fix(gravata): ajusta POI 9",
                        "resumo_mudanca": "Move POI 9 para (55, 45).",
                    },
                ),
            ],
        ]
    )

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    resultado = orquestrador.processar_evento(numero_issue_ou_pr=20)
    assert resultado.status == "pr_criada"
    assert len(gemini_fake.chamadas_turnos) == 3
    # Verifica que no Turno 2 as imagens PNG do mapa renderizado foram injetadas no histórico
    partes_mapa = gemini_fake.chamadas_turnos[1][2]["parts"]
    assert any("inlineData" in p for p in partes_mapa)


def test_autocorrige_erro_real_do_compilador_no_aresta_salvar_com_rollback_de_arquivo_novo(
    tmp_path: Path,
) -> None:
    """Se aresta_salvar falhar no compilador (ex: thumbnail inexistente + setor rascunho criado), desfaz arquivos novos no disco e permite autocorreção no turno seguinte."""
    pasta_db = _preparar_croqui_gravata(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=21,
            titulo="[Croqui | br_mg_betim_pedreira_dr_gravata] Ajuste thumbnail",
            corpo="- **Pico / Croqui:** `br_mg_betim_pedreira_dr_gravata`\n## Descrição\nCorrige grau.",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )

    gemini_fake = ClienteGeminiFeedbackFake(
        turnos_programados=[
            # Turno 1: cria setor extra e define caminho_thumbnail inexistente -> falha no deploy() durante aresta_salvar!
            [
                ChamadaFerramentaAgente(
                    "aresta_adicionar_repeated",
                    {
                        "alvo": "QtxIGEyTkA9Q5c",
                        "campo": "setores",
                        "valor": {"nome": "Setor Rascunho"},
                    },
                ),
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {"alvo": "", "campo": "caminho_thumbnail", "valor": "imagens/inexistente.webp"},
                ),
                ChamadaFerramentaAgente(
                    NOME_FERRAMENTA_FINALIZAR,
                    {"acao": "abrir_pr", "titulo_pr": "fix: erro deploy", "resumo_mudanca": "erro"},
                ),
            ],
            # Turno 2: remove o setor rascunho, restaura caminho_thumbnail válido, ajusta grau e finaliza!
            [
                ChamadaFerramentaAgente(
                    "aresta_remover_repeated",
                    {"alvo": "QtxIGEyTkA9Q5c", "campo": "setores", "indice": 1},
                ),
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {"alvo": "", "campo": "caminho_thumbnail", "valor": "imagens/thumbnail.webp"},
                ),
                ChamadaFerramentaAgente(
                    "aresta_alterar_campo",
                    {"alvo": "TC8Wd0pa4YopiM", "campo": "dificuldade", "valor": "BR_7B"},
                ),
                ChamadaFerramentaAgente(
                    NOME_FERRAMENTA_FINALIZAR,
                    {
                        "acao": "abrir_pr",
                        "titulo_pr": "fix(gravata): corrige grau",
                        "resumo_mudanca": "Ajusta dificuldade para BR_7B.",
                    },
                ),
            ],
        ]
    )

    orquestrador = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=gemini_fake,
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    resultado = orquestrador.processar_evento(numero_issue_ou_pr=21)
    assert resultado.status == "pr_criada"
    assert len(gemini_fake.chamadas_turnos) == 2
    pasta_croqui = pasta_db / "br_mg_betim_pedreira_dr_gravata"
    assert not list(pasta_croqui.glob("*rascunho*.md"))


def test_bloqueia_mudanca_maior_em_issue_automatica_e_libera_com_ai_fix_em_issue_e_pr(
    tmp_path: Path,
) -> None:
    """Exclusão líquida de via pede confirmação na Issue automática, mas executa quando autorizada por /ai-fix."""
    pasta_db = _preparar_croqui_gravata(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=30,
            titulo="[Croqui | br_mg_betim_pedreira_dr_gravata] Via duplicada",
            corpo="- **Pico / Croqui:** `br_mg_betim_pedreira_dr_gravata`\n## Descrição\nRemover via Primeirinha duplicada.",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )

    turnos_remover_via = [
        [
            ChamadaFerramentaAgente(
                "aresta_remover_repeated",
                {"alvo": "8SUSM2sgVKSevu", "campo": "escaladas", "indice": 0},
            ),
            ChamadaFerramentaAgente(
                NOME_FERRAMENTA_FINALIZAR,
                {
                    "acao": "abrir_pr",
                    "titulo_pr": "fix(gravata): remove via Primeirinha",
                    "resumo_mudanca": "Remove a via Primeirinha do Setor das Treze.",
                },
            ),
        ]
    ]

    orq_auto = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(turnos_programados=turnos_remover_via),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )

    # 1. Sem /ai-fix -> bloqueado como Mudança Maior (tanto exclusão de via quanto mudança de ID raiz), disco restaurado intacto!
    res_bloqueado = orq_auto.processar_evento(numero_issue_ou_pr=30)
    assert res_bloqueado.status == "confirmacao_necessaria"
    assert "PRIMEIRINHA" in (
        pasta_db / "br_mg_betim_pedreira_dr_gravata" / "setor_das_treze.md"
    ).read_text(encoding="utf-8")
    assert "/ai-fix" in github_fake.comentarios_publicados[-1][1]

    orq_rename_id = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(
            turnos_programados=[
                [
                    ChamadaFerramentaAgente(
                        "aresta_alterar_campo",
                        {"alvo": "", "campo": "id", "valor": "br_mg_betim_id_renomeado"},
                    ),
                    ChamadaFerramentaAgente(
                        NOME_FERRAMENTA_FINALIZAR,
                        {"acao": "abrir_pr", "titulo_pr": "fix: id", "resumo_mudanca": "muda id"},
                    ),
                ]
            ]
        ),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    res_rename = orq_rename_id.processar_evento(numero_issue_ou_pr=30)
    assert res_rename.status == "confirmacao_necessaria"
    assert (pasta_db / "br_mg_betim_pedreira_dr_gravata" / "croqui.yaml").is_file()
    assert not (pasta_db / "br_mg_betim_id_renomeado").exists()

    # 2. Com /ai-fix de mantenedor (OWNER) -> autorizado e cria PR!
    orq_aut = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(turnos_programados=turnos_remover_via),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    res_liberado = orq_aut.processar_evento(
        numero_issue_ou_pr=30,
        corpo_comentario="/ai-fix Pode remover a via Primeirinha",
        associacao_autor="OWNER",
    )
    assert res_liberado.status == "pr_criada"
    assert "PRIMEIRINHA" not in (
        pasta_db / "br_mg_betim_pedreira_dr_gravata" / "setor_das_treze.md"
    ).read_text(encoding="utf-8")

    # 3. Novo /ai-fix na mesma Issue quando a PR já está aberta -> atualiza PR existente!
    orq_pr_existente = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(
            turnos_programados=[
                [
                    ChamadaFerramentaAgente(
                        "aresta_alterar_campo",
                        {
                            "alvo": "TPwpXHpSFVkDEy",
                            "campo": "texto",
                            "valor": "Como Chegar (Atualizado)",
                        },
                    ),
                    ChamadaFerramentaAgente(
                        NOME_FERRAMENTA_FINALIZAR,
                        {
                            "acao": "abrir_pr",
                            "titulo_pr": "fix(gravata): atualiza acesso",
                            "resumo_mudanca": "Atualiza texto de como chegar.",
                        },
                    ),
                ]
            ]
        ),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    res_atualizada = orq_pr_existente.processar_evento(
        numero_issue_ou_pr=30,
        corpo_comentario="/ai-fix Atualiza como chegar",
        associacao_autor="MEMBER",
    )
    assert res_atualizada.status == "pr_atualizada"


def test_circuit_breaker_desistencia_sem_alteracao_pr_direta_e_permissoes(
    tmp_path: Path,
) -> None:
    """Cobre Circuit Breaker (max_turnos), nao_acionavel, abrir_pr sem mudança, PR direta e bloqueio de usuário sem permissão."""
    pasta_db = _preparar_croqui_gravata(tmp_path)
    github_fake = ClienteGithubFeedbackFake()
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=40,
            titulo="Sem ID",
            corpo="Sem croqui",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=41,
            titulo="[Croqui | br_mg_betim_pedreira_dr_gravata] Loop infinito",
            corpo="- **Pico / Croqui:** `br_mg_betim_pedreira_dr_gravata`\n## Descrição\nTeste",
            labels=["feedback:croqui"],
            eh_pull_request=False,
            branch_head=None,
        )
    )
    github_fake.registrar_issue_ou_pr(
        DadosIssueOuPr(
            numero=42,
            titulo="fix(gravata): PR aberta",
            corpo="PR direta",
            labels=[],
            eh_pull_request=True,
            branch_head="ai-fix/issue-41",
        )
    )
    github_fake.registrar_arquivos_pr(
        42, ["README.md", "database/br_mg_betim_pedreira_dr_gravata/setor_das_treze.md"]
    )

    # 1. Permissão negada e comentário sem /ai-fix
    orq_base = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(
            turnos_programados=[[ChamadaFerramentaAgente("aresta_obter_arvore", {"alvo": ""})]]
        ),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
        max_turnos=2,
    )
    assert (
        orq_base.processar_evento(41, corpo_comentario="/ai-fix x", associacao_autor="NONE").status
        == "ignorado"
    )
    assert (
        orq_base.processar_evento(
            41, corpo_comentario="sem comando", associacao_autor="OWNER"
        ).status
        == "ignorado"
    )

    # 2. Croqui não identificado
    assert orq_base.processar_evento(40).status == "croqui_nao_identificado"

    # 3. Circuit Breaker (2 turnos só inspecionando árvore sem finalizar)
    res_cb = orq_base.processar_evento(41)
    assert res_cb.status == "falha_validacao"

    # 4. Desistência voluntária (nao_acionavel)
    orq_desiste = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(
            turnos_programados=[
                [
                    ChamadaFerramentaAgente(
                        NOME_FERRAMENTA_FINALIZAR,
                        {"acao": "nao_acionavel", "motivo": "Exige desenho vetorial manual."},
                    )
                ]
            ]
        ),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    assert orq_desiste.processar_evento(41).status == "nao_acionavel"

    # 5. abrir_pr sem ter modificado nenhum arquivo -> tratado como nao_acionavel sem commit vazio
    orq_vazio = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(
            turnos_programados=[
                [
                    ChamadaFerramentaAgente(
                        NOME_FERRAMENTA_FINALIZAR,
                        {"acao": "abrir_pr", "titulo_pr": "fix: nada", "resumo_mudanca": "nada"},
                    )
                ]
            ]
        ),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    assert orq_vazio.processar_evento(41).status == "nao_acionavel"

    # 6. /ai-fix diretamente em uma Pull Request existente (extrai croqui_id dos arquivos da PR)
    orq_pr_direta = OrquestradorResolucaoFeedback(
        diretorio_database=pasta_db,
        cliente_gemini=ClienteGeminiFeedbackFake(
            turnos_programados=[
                [
                    ChamadaFerramentaAgente(
                        "aresta_alterar_campo",
                        {"alvo": "TC8Wd0pa4YopiM", "campo": "extensao", "valor": 22},
                    ),
                    ChamadaFerramentaAgente(
                        NOME_FERRAMENTA_FINALIZAR,
                        {"acao": "abrir_pr", "titulo_pr": "fix: ext", "resumo_mudanca": "22m"},
                    ),
                ]
            ]
        ),
        cliente_github=github_fake,
        executor_git=lambda b, m, p: None,
    )
    res_pr = orq_pr_direta.processar_evento(
        42, corpo_comentario="/ai-fix Extensão 22m", associacao_autor="COLLABORATOR"
    )
    assert res_pr.status == "pr_atualizada"
    assert res_pr.numero_pr == 42


def test_hard_jail_rejeita_extensao_invalida_subpasta_proibida_e_remocao_de_spdx(
    tmp_path: Path,
) -> None:
    pasta_db = _preparar_croqui_gravata(tmp_path)
    pasta_croqui = pasta_db / "br_mg_betim_pedreira_dr_gravata"
    snapshot = {
        p.relative_to(pasta_croqui).as_posix(): p.read_bytes()
        for p in pasta_croqui.rglob("*")
        if p.is_file()
    }

    assert validar_diretorio_croqui_pos_edicao(pasta_croqui, snapshot) == []

    # Novo documento textual sem frontmatter (ex: nova seção textual de botão) é aceito sem exigir SPDX
    arq_secao = pasta_croqui / "nova_secao.md"
    arq_secao.write_text("Texto livre de seção.", encoding="utf-8")
    assert validar_diretorio_croqui_pos_edicao(pasta_croqui, snapshot) == []
    arq_secao.unlink()

    # Arquivo com extensão proibida na raiz
    arq_py = pasta_croqui / "malicioso.py"
    arq_py.write_text("print(1)", encoding="utf-8")
    erros_ext = validar_diretorio_croqui_pos_edicao(pasta_croqui, snapshot)
    assert any("Extensão" in e for e in erros_ext)
    arq_py.unlink()

    # Subdiretório inesperado fora de imagens/
    sub_proibida = pasta_croqui / "scripts" / "x.md"
    sub_proibida.parent.mkdir()
    sub_proibida.write_text("x", encoding="utf-8")
    erros_sub = validar_diretorio_croqui_pos_edicao(pasta_croqui, snapshot)
    assert any("Subdiretório" in e for e in erros_sub)
    sub_proibida.unlink()
    sub_proibida.parent.rmdir()

    # Remoção de cabeçalho SPDX em arquivo com frontmatter
    (pasta_croqui / "setor_das_treze.md").write_text("---\nnome: Sem SPDX\n---\n", encoding="utf-8")
    erros_spdx = validar_diretorio_croqui_pos_edicao(pasta_croqui, snapshot)
    assert any("SPDX" in e for e in erros_spdx)
