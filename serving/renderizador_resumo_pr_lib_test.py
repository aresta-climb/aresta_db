# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes comportamentais para o renderizador de resumo HTML e comentário Markdown da PR."""

from serving.diff_croqui_pr_lib import (
    AlteracaoCampo,
    DiffCroqui,
    DiffEntidade,
    DiffImagem,
    DiffMapa,
    DiffPontoMapa,
    PontoMapaVisual,
    ResumoDiffPullRequest,
)
from serving.renderizador_resumo_pr_lib import (
    ASSINATURA_COMENTARIO_PR,
    renderizar_comentario_falha_pr_markdown,
    renderizar_comentario_pr_markdown,
    renderizar_resumo_html,
)


def _construir_resumo_exemplo() -> ResumoDiffPullRequest:
    ponto_antes = PontoMapaVisual(
        uid="p1",
        rotulo="1",
        tipo_geometria="circulo",
        x=100,
        y=200,
        raio=12,
    )
    ponto_depois = PontoMapaVisual(
        uid="p1",
        rotulo="1",
        tipo_geometria="circulo",
        x=140,
        y=250,
        raio=12,
    )
    ponto_add_linha = PontoMapaVisual(
        uid="p2",
        rotulo="L2",
        tipo_geometria="linha",
        x=0,
        y=0,
        caminho_svg_linha="M 10 20 C 30 40 50 60 70 80",
    )
    ponto_rem_pol = PontoMapaVisual(
        uid="p3",
        rotulo="P3",
        tipo_geometria="poligono",
        x=10,
        y=10,
        coordenadas_poligono=((10, 10), (50, 10), (30, 40)),
    )
    ponto_inalterado_ret = PontoMapaVisual(
        uid="p4",
        rotulo="R4",
        tipo_geometria="retangulo",
        x=300,
        y=300,
        largura=40,
        altura=20,
    )

    mapa_sem_mudanca_foto = DiffMapa(
        caminho_imagem="imagens/mapa_parede.webp",
        contexto="Serra > Setor Principal",
        status="modificado",
        imagem_alterada=False,
        caminho_imagem_base_relativo=None,
        largura_antes=1000,
        altura_antes=800,
        largura_depois=1000,
        altura_depois=800,
        tamanho_kb_antes=120.5,
        tamanho_kb_depois=120.5,
        pontos=[
            DiffPontoMapa(
                uid="p1",
                status="modificado",
                ponto_antes=ponto_antes,
                ponto_depois=ponto_depois,
            ),
            DiffPontoMapa(
                uid="p2",
                status="adicionado",
                ponto_antes=None,
                ponto_depois=ponto_add_linha,
            ),
            DiffPontoMapa(
                uid="p3",
                status="removido",
                ponto_antes=ponto_rem_pol,
                ponto_depois=None,
            ),
            DiffPontoMapa(
                uid="p4",
                status="inalterado",
                ponto_antes=ponto_inalterado_ret,
                ponto_depois=ponto_inalterado_ret,
            ),
        ],
    )

    mapa_com_mudanca_foto = DiffMapa(
        caminho_imagem="imagens/mapa_cortado.webp",
        contexto="Serra > Setor Anexo",
        status="modificado",
        imagem_alterada=True,
        caminho_imagem_base_relativo="_base/serra_cipo/imagens/mapa_cortado.webp",
        largura_antes=1200,
        altura_antes=900,
        largura_depois=960,
        altura_depois=720,
        tamanho_kb_antes=210.0,
        tamanho_kb_depois=145.0,
        pontos=[],
    )

    croqui = DiffCroqui(
        id_croqui="serra_cipo",
        uid="uid_cipo",
        nome="Serra do Cipó",
        status="modificado",
        alteracoes_metadados=[
            AlteracaoCampo(
                nome_campo="Descrição do Croqui",
                valor_antes="Linha antiga\nOutra linha",
                valor_depois="Linha nova\nOutra linha",
                eh_markdown=True,
            )
        ],
        entidades=[
            DiffEntidade(
                tipo_entidade="setor",
                uid="uid_setor_1",
                nome_antes="Setor Antigo",
                nome_depois="Setor Principal",
                contexto="Serra",
                status="modificado",
                alteracoes_campos=[
                    AlteracaoCampo("Nome", "Setor Antigo", "Setor Principal"),
                ],
            ),
            DiffEntidade(
                tipo_entidade="escalada",
                uid="uid_via_1",
                nome_antes="Via 1",
                nome_depois="Via 1 Revisada",
                contexto="Serra > Setor Principal",
                status="modificado",
                subtipo_antes="via_esportiva",
                subtipo_depois="via_esportiva",
                resumo_curto="BR_6SUP · 25m",
                alteracoes_campos=[
                    AlteracaoCampo("Nome", "Via 1", "Via 1 Revisada"),
                    AlteracaoCampo("Dificuldade", "BR_6", "BR_6SUP"),
                    AlteracaoCampo("Descrição", "Beta antigo", "Beta novo", eh_markdown=True),
                ],
            ),
            DiffEntidade(
                tipo_entidade="escalada",
                uid="uid_via_2",
                nome_antes="",
                nome_depois="Via Nova",
                contexto="Serra > Setor Principal",
                status="adicionado",
                subtipo_depois="boulder",
                resumo_curto="V5",
            ),
            DiffEntidade(
                tipo_entidade="escalada",
                uid="uid_via_3",
                nome_antes="Via Removida",
                nome_depois="",
                contexto="Serra > Setor Principal",
                status="removido",
                subtipo_antes="via_movel",
                resumo_curto="BR_5",
            ),
        ],
        mapas=[mapa_sem_mudanca_foto, mapa_com_mudanca_foto],
        imagens=[
            DiffImagem(
                caminho_relativo="imagens/capa.webp",
                categoria="capa",
                onde_usada="Capa do Setor Principal",
                status="modificado",
                caminho_pr_relativo="serra_cipo/imagens/capa.webp",
                caminho_base_relativo="_base/serra_cipo/imagens/capa.webp",
                largura_antes=800,
                altura_antes=600,
                largura_depois=800,
                altura_depois=600,
                tamanho_kb_antes=95.0,
                tamanho_kb_depois=82.0,
            ),
            DiffImagem(
                caminho_relativo="imagens/nova.webp",
                categoria="markdown",
                onde_usada="Markdown",
                status="adicionado",
                caminho_pr_relativo="serra_cipo/imagens/nova.webp",
                caminho_base_relativo=None,
                largura_depois=500,
                altura_depois=400,
                tamanho_kb_depois=45.0,
            ),
            DiffImagem(
                caminho_relativo="imagens/antiga.webp",
                categoria="markdown",
                onde_usada="Markdown",
                status="removido",
                caminho_pr_relativo=None,
                caminho_base_relativo="_base/serra_cipo/imagens/antiga.webp",
                largura_antes=500,
                altura_antes=400,
                tamanho_kb_antes=50.0,
            ),
        ],
    )
    return ResumoDiffPullRequest(croquis=[croqui])


def test_renderiza_resumo_html_autocontido_com_mapas_svg_modos_imagem_e_qrcode() -> None:
    """Deve gerar HTML autocontido com código pr00-0042, QR Code SVG, overlays de mapa e comparador Antes/Depois."""
    resumo = _construir_resumo_exemplo()

    html = renderizar_resumo_html(
        resumo=resumo,
        numero_pr=42,
        url_base_serving="https://serving.arestaclimb.com",
        url_base_previa="https://previa.arestaclimb.com",
        commit_sha="abcdef1234567890",
    )

    assert "<!DOCTYPE html>" in html
    assert "pr00-0042" in html
    assert "https://previa.arestaclimb.com/pr00-0042" in html
    assert "<svg" in html
    # Controles do mapa sem mudança de foto
    assert "Diff" in html
    assert "Antes" in html
    assert "Depois" in html
    assert "Ocultar" in html
    # Controles do mapa com mudança de foto
    assert "Lado a Lado" in html
    assert "Slider Cortina" in html
    assert "1200x900" in html
    assert "960x720" in html
    # Links de imagens apontando para o namespace da PR e _base
    assert "https://serving.arestaclimb.com/pr/42/serra_cipo/imagens/mapa_parede.webp" in html
    assert "https://serving.arestaclimb.com/pr/42/_base/serra_cipo/imagens/mapa_cortado.webp" in html
    assert "https://serving.arestaclimb.com/pr/42/_base/serra_cipo/imagens/capa.webp" in html
    assert "https://serving.arestaclimb.com/pr/42/serra_cipo/imagens/capa.webp" in html
    # Entidades e diffs
    assert "Via 1 Revisada" in html
    assert "BR_6SUP" in html


def test_renderiza_comentario_markdown_com_assinatura_links_e_aviso_sem_r2() -> None:
    """Deve gerar o comentário Markdown enxuto contendo a assinatura invisível e os links da prévia."""
    resumo = _construir_resumo_exemplo()

    md_com_r2 = renderizar_comentario_pr_markdown(
        resumo=resumo,
        numero_pr=42,
        url_base_previa="https://previa.arestaclimb.com",
        publicado_no_r2=True,
    )
    assert md_com_r2.startswith(ASSINATURA_COMENTARIO_PR)
    assert "`pr00-0042`" in md_com_r2
    assert "https://previa.arestaclimb.com/pr00-0042" in md_com_r2
    assert "https://previa.arestaclimb.com/resumo/pr00-0042" in md_com_r2
    assert "Serra do Cipó" in md_com_r2

    md_sem_r2 = renderizar_comentario_pr_markdown(
        resumo=resumo,
        numero_pr=42,
        url_base_previa="https://previa.arestaclimb.com",
        publicado_no_r2=False,
    )
    assert ASSINATURA_COMENTARIO_PR in md_sem_r2
    assert "Credenciais do R2 ausentes" in md_sem_r2

    md_falha = renderizar_comentario_falha_pr_markdown(["Erro de schema no croqui X"])
    assert md_falha.startswith(ASSINATURA_COMENTARIO_PR)
    assert "Erro de schema no croqui X" in md_falha
