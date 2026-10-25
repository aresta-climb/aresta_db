# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from aresta_api.proto.generated import croqui_pb2
from editor.commands.comandos_protobuf import MensagemAlvoNaoEncontradaError
from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.models.croqui_model import CroquiModel


def _criar_modelo_completo() -> CroquiModel:
    croqui = croqui_pb2.Croqui(uid="uid_croqui_001", nome="Serra do Cipó")
    botao = croqui.botoes.add(uid="uid_botao_0001", texto="Guia PDF")
    _ = botao

    pico = croqui.picos.add(nome="Pico Principal")

    # Grupo com setor e via esportiva
    sg_grupo = pico.setores_ou_grupos.add()
    grupo = sg_grupo.grupo.conteudo
    grupo.uid = "uid_grupo_0001"
    grupo.nome = "Grupo Norte"

    arq_setor = grupo.setores.add()
    setor = arq_setor.conteudo
    setor.uid = "uid_setor_0001"
    setor.nome = "Setor Falesia"

    mapa = setor.mapas.add(caminho_imagem_mapa="imagens/mapa1.webp")
    poi = mapa.pontos_de_interesse.add(uid="uid_poi_000001", rotulo="P1")
    _ = poi

    esc = setor.escaladas.add(uid="uid_escalada_1")
    esc.via_esportiva.nome = "Fissura Central"
    esc.via_esportiva.extensao = 25

    esc_multi = setor.escaladas.add(uid="uid_escalada_2")
    esc_multi.via_multiplas_enfiadas.nome = "Grande Parede"
    enf = esc_multi.via_multiplas_enfiadas.enfiadas.add(uid="uid_enfiada_01")
    enf.via_esportiva.nome = "Enfiada 1"

    return CroquiModel(croqui)


def test_resolver_alvo_raiz_por_caminho_vazio_ou_uid():
    """Deve resolver o nó raiz tanto por string vazia/root quanto pelo UID do croqui."""
    model = _criar_modelo_completo()

    for identificador in ("", "root", "node:root", "uid_croqui_001"):
        msg, caminho = resolver_alvo_mcp(model, identificador)
        assert msg.nome == "Serra do Cipó"
        assert caminho == ""


def test_resolver_alvo_por_uid_direto():
    """Deve resolver Grupo, Setor, Botao e PontoDeInteresse diretamente por seu UID."""
    model = _criar_modelo_completo()

    msg_grupo, cam_grupo = resolver_alvo_mcp(model, "uid_grupo_0001")
    assert msg_grupo.nome == "Grupo Norte"
    assert cam_grupo == "picos.0.setores_ou_grupos.0.grupo.conteudo"

    msg_setor, cam_setor = resolver_alvo_mcp(model, "uid_setor_0001")
    assert msg_setor.nome == "Setor Falesia"
    assert cam_setor == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo"

    msg_botao, cam_botao = resolver_alvo_mcp(model, "uid_botao_0001")
    assert msg_botao.texto == "Guia PDF"
    assert cam_botao == "botoes.0"

    msg_poi, cam_poi = resolver_alvo_mcp(model, "uid_poi_000001")
    assert msg_poi.rotulo == "P1"
    assert (
        cam_poi
        == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.mapas.0.pontos_de_interesse.0"
    )


def test_resolver_alvo_escalada_e_enfiada_redireciona_para_variante_ativa_quando_campo_pertence_a_ela():
    """Quando o alvo é uma Escalada ou Enfiada e campo_nome pertence à variante oneof ativa, resolve a sub-mensagem."""
    model = _criar_modelo_completo()

    # Campo da variante ativa (via_esportiva.nome)
    msg_via, cam_via = resolver_alvo_mcp(model, "uid_escalada_1", campo_nome="nome")
    assert msg_via.nome == "Fissura Central"
    assert (
        cam_via
        == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.escaladas.0.via_esportiva"
    )

    # Campo da própria mensagem Escalada (mapas)
    msg_esc, cam_esc = resolver_alvo_mcp(model, "uid_escalada_1", campo_nome="mapas")
    assert msg_esc.uid == "uid_escalada_1"
    assert cam_esc == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.escaladas.0"

    # Enfiada com campo da variante ativa
    msg_enf, cam_enf = resolver_alvo_mcp(model, "uid_enfiada_01", campo_nome="nome")
    assert msg_enf.nome == "Enfiada 1"
    assert (
        cam_enf
        == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.escaladas.1.via_multiplas_enfiadas.enfiadas.0.via_esportiva"
    )

    # Escalada com campo indexado da variante ativa (conquistadores.0)
    msg_conq, cam_conq = resolver_alvo_mcp(model, "uid_escalada_1", campo_nome="conquistadores.0")
    assert msg_conq.nome == "Fissura Central"
    assert (
        cam_conq
        == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.escaladas.0.via_esportiva"
    )


def test_resolver_alvo_hibrido_uid_com_subcaminho():
    """Deve resolver <uid>.<subcaminho>, inclusive atravessando a variante ativa de Escalada."""
    model = _criar_modelo_completo()

    msg_mapa, cam_mapa = resolver_alvo_mcp(model, "uid_setor_0001.mapas.0")
    assert msg_mapa.caminho_imagem_mapa == "imagens/mapa1.webp"
    assert cam_mapa == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.mapas.0"

    # Subcaminho relativo à variante ativa de via_multiplas_enfiadas
    msg_enf_via_sub, cam_enf_via_sub = resolver_alvo_mcp(
        model, "uid_escalada_2.enfiadas.0", campo_nome="nome"
    )
    assert msg_enf_via_sub.nome == "Enfiada 1"
    assert (
        cam_enf_via_sub
        == "picos.0.setores_ou_grupos.0.grupo.conteudo.setores.0.conteudo.escaladas.1.via_multiplas_enfiadas.enfiadas.0.via_esportiva"
    )


def test_resolver_alvo_por_caminho_posicional():
    """Deve resolver caminhos posicionais a partir da raiz do croqui."""
    model = _criar_modelo_completo()

    msg_pico, cam_pico = resolver_alvo_mcp(model, "picos.0")
    assert msg_pico.nome == "Pico Principal"
    assert cam_pico == "picos.0"


def test_resolver_alvo_inexistente_lanca_erro():
    """Deve lançar MensagemAlvoNaoEncontradaError quando o UID ou caminho não existir."""
    model = _criar_modelo_completo()

    with pytest.raises(MensagemAlvoNaoEncontradaError, match="uid_inexistente"):
        resolver_alvo_mcp(model, "uid_inexistente")

    with pytest.raises(MensagemAlvoNaoEncontradaError, match="uid_setor_0001.mapas.99"):
        resolver_alvo_mcp(model, "uid_setor_0001.mapas.99")

    with pytest.raises(MensagemAlvoNaoEncontradaError, match="picos.99"):
        resolver_alvo_mcp(model, "picos.99")
