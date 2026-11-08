# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes para a biblioteca test-only `ClienteGeminiFeedbackFake`, garantindo
que o Fake determinístico cumpre fielmente o contrato do cliente Gemini real.
"""

from __future__ import annotations

import pytest

from serving.agente_feedback.cliente_gemini_feedback import (
    AlteracaoArquivoProposta,
    ErroComunicacaoGemini,
    RespostaPropostaGemini,
)
from serving.agente_feedback.cliente_gemini_feedback_fake import ClienteGeminiFeedbackFake


def test_fake_retorna_arquivos_desambiguados_e_registra_chamadas() -> None:
    fake = ClienteGeminiFeedbackFake(arquivos_desambiguados=["setor_a.md", "setor_b.md"])

    arquivos = fake.desambiguar_arquivos_croqui(
        indice_compacto="- setor_a.md",
        descricao_feedback="Grau errado na via 1",
        instrucao_extra="Ver setor A",
        screenshot_bytes=b"img",
    )

    assert arquivos == ["setor_a.md", "setor_b.md"]
    assert len(fake.chamadas_desambiguacao) == 1
    assert fake.chamadas_desambiguacao[0]["descricao_feedback"] == "Grau errado na via 1"


def test_fake_retorna_fila_de_respostas_em_ordem_para_suportar_autoretry() -> None:
    resposta_1 = RespostaPropostaGemini(
        acionavel=True,
        titulo_pr="fix(croqui): tentativa 1 com erro",
        resumo_mudanca="Tentativa 1",
        motivo_nao_acionavel="",
        alteracoes=[AlteracaoArquivoProposta("setor_a.md", "conteudo_invalido")],
    )
    resposta_2 = RespostaPropostaGemini(
        acionavel=True,
        titulo_pr="fix(croqui): tentativa 2 corrigida",
        resumo_mudanca="Tentativa 2",
        motivo_nao_acionavel="",
        alteracoes=[AlteracaoArquivoProposta("setor_a.md", "conteudo_valido")],
    )
    fake = ClienteGeminiFeedbackFake(respostas_proposta=[resposta_1, resposta_2])

    r1 = fake.gerar_proposta_alteracao(
        croqui_id="br_mg_teste",
        descricao_feedback="Grau 7b",
        instrucao_extra="",
        arquivos_atuais={"setor_a.md": "orig"},
    )
    r2 = fake.gerar_proposta_alteracao(
        croqui_id="br_mg_teste",
        descricao_feedback="Grau 7b",
        instrucao_extra="",
        arquivos_atuais={"setor_a.md": "orig"},
        erro_validacao_anterior="Enum inválido",
    )
    # Quando a fila chega ao último elemento, repete o último elemento de forma determinística
    r3 = fake.gerar_proposta_alteracao(
        croqui_id="br_mg_teste",
        descricao_feedback="Grau 7b",
        instrucao_extra="",
        arquivos_atuais={"setor_a.md": "orig"},
    )

    assert r1.titulo_pr == "fix(croqui): tentativa 1 com erro"
    assert r2.titulo_pr == "fix(croqui): tentativa 2 corrigida"
    assert r3.titulo_pr == "fix(croqui): tentativa 2 corrigida"
    assert fake.chamadas_proposta[1]["erro_validacao_anterior"] == "Enum inválido"


def test_fake_simula_falha_deterministica_de_rede_ou_cota() -> None:
    fake = ClienteGeminiFeedbackFake(erro_simulado="HTTP 429: RESOURCE_EXHAUSTED")

    with pytest.raises(ErroComunicacaoGemini, match="RESOURCE_EXHAUSTED"):
        fake.desambiguar_arquivos_croqui(
            indice_compacto="indice",
            descricao_feedback="desc",
        )

    with pytest.raises(ErroComunicacaoGemini, match="RESOURCE_EXHAUSTED"):
        fake.gerar_proposta_alteracao(
            croqui_id="br_mg_teste",
            descricao_feedback="desc",
            instrucao_extra="",
            arquivos_atuais={},
        )
