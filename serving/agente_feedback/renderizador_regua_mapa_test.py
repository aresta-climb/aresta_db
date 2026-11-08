# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento para a renderização de régua cartesiana
e pontos de interesse em imagens de mapa de setor.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from serving.agente_feedback.renderizador_regua_mapa import (
    MARGEM_REGUA_PX,
    MapaAnotadoEmMemoria,
    extrair_e_renderizar_mapas_do_setor,
    renderizar_mapa_com_regua_bytes,
)


def _criar_imagem_webp_teste(caminho: Path, largura: int = 300, altura: int = 200) -> bytes:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (largura, altura), color=(40, 60, 80))
    img.save(caminho, format="WEBP")
    return caminho.read_bytes()


def test_renderiza_mapa_com_margem_de_regua_grade_e_pontos_sem_alterar_disco(
    tmp_path: Path,
) -> None:
    caminho_img = tmp_path / "imagens" / "setor_p1.webp"
    bytes_originais = _criar_imagem_webp_teste(caminho_img, largura=300, altura=200)

    png_bytes = renderizar_mapa_com_regua_bytes(
        caminho_imagem=caminho_img,
        largura_mapa=300,
        altura_mapa=200,
        pontos_de_interesse=[
            {
                "uid": "p1",
                "rotulo": "01",
                "circulo": {"x": 150, "y": 100, "raio": 20},
            },
            {
                "uid": "p2_sem_circulo",
                "rotulo": "02",
            },
        ],
    )

    # Verifica que o arquivo original em disco permanece intacto
    assert caminho_img.read_bytes() == bytes_originais

    # Verifica que a imagem gerada em memória é um PNG válido com as margens da régua somadas
    img_gerada = Image.open(io.BytesIO(png_bytes))
    assert img_gerada.format == "PNG"
    assert img_gerada.size == (300 + 2 * MARGEM_REGUA_PX, 200 + 2 * MARGEM_REGUA_PX)

    # Verifica que o centro do círculo (150 + MARGEM, 100 + MARGEM) ou sua borda teve pixels desenhados
    # diferentes da cor de fundo original (40, 60, 80)
    cor_borda_circulo = img_gerada.getpixel((150 + MARGEM_REGUA_PX + 20, 100 + MARGEM_REGUA_PX))
    assert cor_borda_circulo != (40, 60, 80)


def test_extrai_e_renderiza_todos_os_mapas_existentes_de_um_arquivo_setor_md(
    tmp_path: Path,
) -> None:
    pasta_croqui = tmp_path / "br_mg_teste"
    _criar_imagem_webp_teste(pasta_croqui / "imagens" / "mapa1.webp", largura=240, altura=180)

    conteudo_md = """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: setor1
nome: Setor Teste
mapas:
- caminho_imagem_mapa: imagens/mapa1.webp
  largura_mapa: 480
  altura_mapa: 360
  pontos_de_interesse:
  - uid: pt1
    rotulo: '01'
    circulo:
      x: 240
      y: 180
      raio: 24
- caminho_imagem_mapa: imagens/mapa_inexistente.webp
  largura_mapa: 400
  altura_mapa: 300
---

Descrição do setor.
"""
    caminho_md = pasta_croqui / "setor_teste.md"
    caminho_md.write_text(conteudo_md, encoding="utf-8")

    mapas_anotados: list[MapaAnotadoEmMemoria] = extrair_e_renderizar_mapas_do_setor(
        pasta_croqui=pasta_croqui,
        caminho_relativo_md="setor_teste.md",
    )

    assert len(mapas_anotados) == 1
    assert mapas_anotados[0].caminho_imagem_mapa == "imagens/mapa1.webp"
    assert mapas_anotados[0].largura_mapa == 480
    assert mapas_anotados[0].altura_mapa == 360
    assert mapas_anotados[0].mime_type == "image/png"

    img_anotada = Image.open(io.BytesIO(mapas_anotados[0].dados_imagem))
    assert img_anotada.size == (480 + 2 * MARGEM_REGUA_PX, 360 + 2 * MARGEM_REGUA_PX)


def test_retorna_lista_vazia_para_arquivo_md_sem_mapas_ou_inexistente(tmp_path: Path) -> None:
    pasta_croqui = tmp_path / "br_mg_vazio"
    pasta_croqui.mkdir(parents=True)
    (pasta_croqui / "capa.md").write_text("Apenas texto sem frontmatter.", encoding="utf-8")
    (pasta_croqui / "sem_mapas.md").write_text(
        "---\nnome: Setor Sem Mapa\n---\nTexto.", encoding="utf-8"
    )

    assert extrair_e_renderizar_mapas_do_setor(pasta_croqui, "capa.md") == []
    assert extrair_e_renderizar_mapas_do_setor(pasta_croqui, "sem_mapas.md") == []
    assert extrair_e_renderizar_mapas_do_setor(pasta_croqui, "nao_existe.md") == []
