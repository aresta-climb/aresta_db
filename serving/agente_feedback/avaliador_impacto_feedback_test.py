# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais para a guarda determinística de Mudança Maior sobre o diff
semântico de croquis compilados (`avaliador_impacto_feedback`).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from aresta_api.proto.generated import croqui_pb2
from serving.agente_feedback.avaliador_impacto_feedback import (
    AvaliacaoImpactoFeedback,
    avaliar_impacto_alteracao_feedback,
)


def _gravar_compilado(
    pasta_saida_raiz: Path,
    croqui: croqui_pb2.Croqui,
) -> Path:
    pasta_croqui = pasta_saida_raiz / croqui.id
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    if croqui.caminho_thumbnail:
        destino_img = pasta_croqui / croqui.caminho_thumbnail
        destino_img.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (20, 20), color="blue").save(destino_img, "WEBP")
    (pasta_croqui / "compilado.binarypb").write_bytes(croqui.SerializeToString())
    return pasta_saida_raiz


def _construir_croqui_base() -> croqui_pb2.Croqui:
    c = croqui_pb2.Croqui(
        uid="uid_croqui_01",
        id="br_mg_betim_gravata",
        nome="Pedreira Gravatá",
        caminho_thumbnail="imagens/capa.webp",
        publicar_croqui=True,
    )
    b = c.botoes.add(uid="uid_botao_01", texto="Como Chegar")
    b.destino.secao_textual.conteudo = "Acesso fácil"

    p = c.picos.add(nome="Gravatá", estado="MG")
    g = p.setores_ou_grupos.add().grupo.conteudo
    g.uid = "uid_grupo_01"
    g.nome = "Setores"

    s1 = g.setores.add().conteudo
    s1.uid = "uid_setor_treze"
    s1.nome = "Setor das Treze"
    m = s1.mapas.add(
        caminho_imagem_mapa="imagens/capa.webp",
        largura_mapa=20,
        altura_mapa=20,
    )
    m.pontos_de_interesse.add(uid="uid_poi_01", rotulo="1")

    for i in range(1, 8):
        esc = s1.escaladas.add(uid=f"uid_via_{i:02d}")
        esc.via_esportiva.nome = f"Via {i}"
        esc.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A
        esc.via_esportiva.conquistadores.append("Macena, Samuel, Maceninha")
    return c


def test_aprova_edicao_simples_e_cenario_issue_108_criando_um_setor_e_migrando_via(
    tmp_path: Path,
) -> None:
    """Garante que criar 1 setor novo e migrar 1 via preservando UID passa sem bloqueio."""
    base = _construir_croqui_base()
    depois = croqui_pb2.Croqui()
    depois.CopyFrom(base)

    grupo_dep = depois.picos[0].setores_ou_grupos[0].grupo.conteudo
    setor_treze = grupo_dep.setores[0].conteudo
    via_migrada = croqui_pb2.Escalada()
    via_migrada.CopyFrom(setor_treze.escaladas[0])
    del setor_treze.escaladas[0]
    del via_migrada.via_esportiva.conquistadores[:]
    via_migrada.via_esportiva.conquistadores.append("Macena, Samuel")

    setor_palanque = grupo_dep.setores.add().conteudo
    setor_palanque.uid = "uid_setor_palanque"
    setor_palanque.nome = "Setor do Palanque"
    setor_palanque.escaladas.add().CopyFrom(via_migrada)

    dir_base = _gravar_compilado(tmp_path / "base", base)
    dir_depois = _gravar_compilado(tmp_path / "depois", depois)

    aval: AvaliacaoImpactoFeedback = avaliar_impacto_alteracao_feedback(
        dir_compilado_base=dir_base,
        dir_compilado_novo=dir_depois,
        croqui_base=base,
        croqui_novo=depois,
    )
    assert aval.eh_mudanca_maior is False
    assert aval.motivos == []


def test_detecta_exclusoes_liquidas_blast_radius_e_mudancas_raiz(tmp_path: Path) -> None:
    """Bloqueia remoção de via/setor/mapa/botão, >1 setor novo, >5 vias alteradas e mudança de id/publicar_croqui."""
    base = _construir_croqui_base()
    dir_base = _gravar_compilado(tmp_path / "base", base)

    # 1. Exclusão líquida de escalada
    c_del_via = croqui_pb2.Croqui()
    c_del_via.CopyFrom(base)
    del c_del_via.picos[0].setores_ou_grupos[0].grupo.conteudo.setores[0].conteudo.escaladas[0]
    aval_del_via = avaliar_impacto_alteracao_feedback(
        dir_base, _gravar_compilado(tmp_path / "del_via", c_del_via), base, c_del_via
    )
    assert aval_del_via.eh_mudanca_maior is True
    assert any("Exclusão" in m for m in aval_del_via.motivos)

    # 2. Exclusão de Pico, mapa e botão
    c_del_mapa_btn = croqui_pb2.Croqui()
    c_del_mapa_btn.CopyFrom(base)
    del c_del_mapa_btn.picos[0].setores_ou_grupos[0].grupo.conteudo.setores[0].conteudo.mapas[0]
    del c_del_mapa_btn.botoes[0]
    aval_del_mb = avaliar_impacto_alteracao_feedback(
        dir_base, _gravar_compilado(tmp_path / "del_mb", c_del_mapa_btn), base, c_del_mapa_btn
    )
    assert aval_del_mb.eh_mudanca_maior is True
    assert any("mapa" in m.lower() for m in aval_del_mb.motivos)
    assert any("botão" in m.lower() or "botao" in m.lower() for m in aval_del_mb.motivos)

    c_del_pico = croqui_pb2.Croqui()
    c_del_pico.CopyFrom(base)
    del c_del_pico.picos[0]
    aval_del_pico = avaliar_impacto_alteracao_feedback(
        dir_base, _gravar_compilado(tmp_path / "del_pico", c_del_pico), base, c_del_pico
    )
    assert aval_del_pico.eh_mudanca_maior is True
    assert any("pico" in m.lower() for m in aval_del_pico.motivos)

    # 3. Mais de 1 setor adicionado e mais de 5 escaladas modificadas
    c_massa = croqui_pb2.Croqui()
    c_massa.CopyFrom(base)
    grp = c_massa.picos[0].setores_ou_grupos[0].grupo.conteudo
    grp.setores.add().conteudo.uid = "uid_novo_s1"
    grp.setores[-1].conteudo.nome = "Novo Setor 1"
    grp.setores.add().conteudo.uid = "uid_novo_s2"
    grp.setores[-1].conteudo.nome = "Novo Setor 2"
    for esc in grp.setores[0].conteudo.escaladas[:6]:
        esc.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_8B
    aval_massa = avaliar_impacto_alteracao_feedback(
        dir_base, _gravar_compilado(tmp_path / "massa", c_massa), base, c_massa
    )
    assert aval_massa.eh_mudanca_maior is True
    assert any("setor" in m.lower() for m in aval_massa.motivos)
    assert any("escaladas" in m.lower() for m in aval_massa.motivos)

    # 4. Alteração de id do croqui ou publicar_croqui
    c_id = croqui_pb2.Croqui()
    c_id.CopyFrom(base)
    c_id.id = "br_mg_outro_id"
    c_id.publicar_croqui = False
    aval_id = avaliar_impacto_alteracao_feedback(
        dir_base, _gravar_compilado(tmp_path / "id_novo", c_id), base, c_id
    )
    assert aval_id.eh_mudanca_maior is True
    assert any("id" in m.lower() for m in aval_id.motivos)
    assert any("publicar_croqui" in m for m in aval_id.motivos)
