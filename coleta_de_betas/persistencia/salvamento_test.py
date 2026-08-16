# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Aresta Contributors

import pytest
import yaml
from pathlib import Path
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.persistencia.salvamento import (
    injetar_betas_no_markdown,
    persistir_aprovacoes
)

def test_injetar_betas_no_markdown(tmp_path):
    arquivo_md = tmp_path / "setor_teste.md"
    conteudo_inicial = """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Contributors
nome: Setor Teste
escaladas:
  - via_esportiva:
      nome: Fusca Azul
      grau: V4
  - boulder:
      nome: Prato Feito
---
Este é o texto descritivo do setor.
"""
    arquivo_md.write_text(conteudo_inicial, encoding="utf-8")

    m1 = beta_pb2.MidiaBeta()
    m1.url = "https://youtube.com/watch?v=123"
    m1.titulo = "Beta Fusca Azul"
    m1.fonte = beta_pb2.FonteMidia.YOUTUBE
    m1.thumbnail_url = "https://img.youtube.com/vi/123/hqdefault.jpg"
    m1.meta.resumo_do_movimento = "Pegue a reglete"
    m1.meta.llm_confidence_score = 95
    m1.meta.llm_reasoning = "Perfeito"
    m1.match_multiplas_fontes = True
    m1.match_nome_no_snippet = True

    alterou = injetar_betas_no_markdown(arquivo_md, {"Fusca Azul": [m1]})
    assert alterou is True

    # Lê o arquivo e valida integridade
    conteudo_pos = arquivo_md.read_text(encoding="utf-8")
    assert "Este é o texto descritivo do setor." in conteudo_pos
    assert "# SPDX-License-Identifier: ODbL-1.0" in conteudo_pos

    # Valida YAML gerado
    partes = conteudo_pos.split("---")
    frontmatter = yaml.safe_load(partes[1])
    assert len(frontmatter["escaladas"]) == 2
    
    esc1 = frontmatter["escaladas"][0]
    assert esc1["via_esportiva"]["nome"] == "Fusca Azul"
    assert "betas" in esc1
    assert len(esc1["betas"]) == 1
    assert esc1["betas"][0]["url"] == "https://youtube.com/watch?v=123"
    assert esc1["betas"][0]["fonte"] == "YOUTUBE"
    assert esc1["betas"][0]["meta"]["llm_confidence_score"] == 95


def test_persistir_aprovacoes_e_limpar_staging(tmp_path):
    pico_dir = tmp_path / "br_mg_croqui"
    pico_dir.mkdir()

    setor_md = pico_dir / "grupo_1_setor_1.md"
    setor_md.write_text("""---
nome: Setor 1
escaladas:
  - via_esportiva:
      nome: Fusca Azul
---
Descricao
""", encoding="utf-8")

    staging_pb = pico_dir / "betas_pendentes.binarypb"
    staging_pb.write_bytes(b"dummy")

    m = beta_pb2.MidiaBeta()
    m.url = "https://instagram.com/p/123"
    m.titulo = "Post Insta"
    m.fonte = beta_pb2.FonteMidia.INSTAGRAM

    total_injetado = persistir_aprovacoes(pico_dir, {"Fusca Azul": [m]}, limpar_staging=True)
    assert total_injetado == 1
    assert not staging_pb.exists()
