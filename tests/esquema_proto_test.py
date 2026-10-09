# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários do esquema Protobuf para identificadores estáveis e UIDs universais."""

import pytest
from google.protobuf import descriptor
from aresta_api.proto.generated import croqui_pb2, indice_pb2, croqui_experimental_pb2


def test_resumo_croqui_croqui_uid() -> None:
    """Valida o campo croqui_uid na mensagem ResumoCroqui do índice."""
    campo = indice_pb2.ResumoCroqui.DESCRIPTOR.fields_by_name.get("croqui_uid")
    assert campo is not None, "Campo 'croqui_uid' deve existir em ResumoCroqui"
    assert campo.number == 12, "Tag do campo 'croqui_uid' deve ser 12"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING, "Tipo de 'croqui_uid' deve ser string"


def test_croqui_uid() -> None:
    """Valida o campo uid e suas anotações na mensagem Croqui."""
    campo = croqui_pb2.Croqui.DESCRIPTOR.fields_by_name.get("uid")
    assert campo is not None, "Campo 'uid' deve existir em Croqui"
    assert campo.number == 17, "Tag do campo 'uid' deve ser 17"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING, "Tipo de 'uid' deve ser string"
    
    opcoes = campo.GetOptions()
    formato = opcoes.Extensions[croqui_pb2.formato_na_ui]
    assert formato == croqui_pb2.CampoFormatoUi.INVISIVEL, "Campo 'uid' deve ter formato_na_ui = INVISIVEL"


def test_grupo_uid() -> None:
    """Valida o campo uid e suas anotações na mensagem Grupo."""
    campo = croqui_pb2.Grupo.DESCRIPTOR.fields_by_name.get("uid")
    assert campo is not None, "Campo 'uid' deve existir em Grupo"
    assert campo.number == 10, "Tag do campo 'uid' deve ser 10"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING, "Tipo de 'uid' deve ser string"
    
    opcoes = campo.GetOptions()
    formato = opcoes.Extensions[croqui_pb2.formato_na_ui]
    assert formato == croqui_pb2.CampoFormatoUi.INVISIVEL, "Campo 'uid' deve ter formato_na_ui = INVISIVEL"


def test_setor_uid() -> None:
    """Valida o campo uid e suas anotações na mensagem Setor."""
    campo = croqui_pb2.Setor.DESCRIPTOR.fields_by_name.get("uid")
    assert campo is not None, "Campo 'uid' deve existir em Setor"
    assert campo.number == 16, "Tag do campo 'uid' deve ser 16"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING, "Tipo de 'uid' deve ser string"
    
    opcoes = campo.GetOptions()
    formato = opcoes.Extensions[croqui_pb2.formato_na_ui]
    assert formato == croqui_pb2.CampoFormatoUi.INVISIVEL, "Campo 'uid' deve ter formato_na_ui = INVISIVEL"


def test_escalada_uid() -> None:
    """Valida o campo uid e suas anotações na mensagem Escalada."""
    campo = croqui_pb2.Escalada.DESCRIPTOR.fields_by_name.get("uid")
    assert campo is not None, "Campo 'uid' deve existir em Escalada"
    assert campo.number == 8, "Tag do campo 'uid' deve ser 8"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING, "Tipo de 'uid' deve ser string"
    
    opcoes = campo.GetOptions()
    formato = opcoes.Extensions[croqui_pb2.formato_na_ui]
    assert formato == croqui_pb2.CampoFormatoUi.INVISIVEL, "Campo 'uid' deve ter formato_na_ui = INVISIVEL"


def test_botao_uid() -> None:
    """Valida o campo uid e suas anotações na mensagem Botao."""
    campo = croqui_pb2.Botao.DESCRIPTOR.fields_by_name.get("uid")
    assert campo is not None, "Campo 'uid' deve existir em Botao"
    assert campo.number == 3, "Tag do campo 'uid' deve ser 3"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING, "Tipo de 'uid' deve ser string"
    
    opcoes = campo.GetOptions()
    formato = opcoes.Extensions[croqui_pb2.formato_na_ui]
    assert formato == croqui_pb2.CampoFormatoUi.INVISIVEL, "Campo 'uid' deve ter formato_na_ui = INVISIVEL"


def test_ponto_de_interesse_rotulo_e_uid() -> None:
    """Valida os campos rotulo, uid e a deprecação de label em Mapa.PontoDeInteresse."""
    desc = croqui_pb2.Mapa.PontoDeInteresse.DESCRIPTOR
    
    # Campo rotulo
    campo_rotulo = desc.fields_by_name.get("rotulo")
    assert campo_rotulo is not None, "Campo 'rotulo' deve existir em PontoDeInteresse"
    assert campo_rotulo.number == 12, "Tag de 'rotulo' deve ser 12"
    assert campo_rotulo.type == descriptor.FieldDescriptor.TYPE_STRING
    assert campo_rotulo.GetOptions().Extensions[croqui_pb2.texto_na_ui] == "Rótulo na Imagem"

    # Campo uid
    campo_uid = desc.fields_by_name.get("uid")
    assert campo_uid is not None, "Campo 'uid' deve existir em PontoDeInteresse"
    assert campo_uid.number == 13, "Tag de 'uid' deve ser 13"
    assert campo_uid.type == descriptor.FieldDescriptor.TYPE_STRING
    assert campo_uid.GetOptions().Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.INVISIVEL

    # Campo label depreciado
    campo_label = desc.fields_by_name.get("label")
    assert campo_label is not None
    assert campo_label.GetOptions().deprecated is True, "Campo 'label' deve ser marcado como deprecated"

    # Campo id depreciado
    campo_id = desc.fields_by_name.get("id")
    assert campo_id is not None
    assert campo_id.GetOptions().deprecated is True, "Campo 'id' deve ser marcado como deprecated em favor de uid"


def test_referencia_alvo_uid_e_pontos_uids() -> None:
    """Valida alvo_uid, pontos_uids e a deprecação de strings textuais em Mapa.Referencia."""
    desc = croqui_pb2.Mapa.Referencia.DESCRIPTOR

    # Campo alvo_uid
    campo_alvo = desc.fields_by_name.get("alvo_uid")
    assert campo_alvo is not None, "Campo 'alvo_uid' deve existir em Referencia"
    assert campo_alvo.number == 7, "Tag de 'alvo_uid' deve ser 7"
    assert campo_alvo.type == descriptor.FieldDescriptor.TYPE_STRING
    assert campo_alvo.GetOptions().Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.INVISIVEL

    # Campo pontos_uids
    campo_pontos = desc.fields_by_name.get("pontos_uids")
    assert campo_pontos is not None, "Campo 'pontos_uids' deve existir em Referencia"
    assert campo_pontos.number == 8, "Tag de 'pontos_uids' deve ser 8"
    assert campo_pontos.is_repeated is True, "Campo 'pontos_uids' deve ser repeated"
    assert campo_pontos.type == descriptor.FieldDescriptor.TYPE_STRING
    assert campo_pontos.GetOptions().Extensions[croqui_pb2.formato_na_ui] == croqui_pb2.CampoFormatoUi.INVISIVEL

    # Campos legados depreciados
    for nome in ("escalada", "setor", "grupo", "ids"):
        campo_legado = desc.fields_by_name.get(nome)
        assert campo_legado is not None
        assert campo_legado.GetOptions().deprecated is True, f"Campo '{nome}' deve ser marcado como deprecated"

    # Campo indice_mapa_alvo foi completamente removido do esquema
    assert desc.fields_by_name.get("indice_mapa_alvo") is None, "Campo 'indice_mapa_alvo' deve ser completamente removido"


def test_croqui_experimental_croqui_uid() -> None:
    """Valida o campo croqui_uid na mensagem CroquiExperimental."""
    campo = croqui_experimental_pb2.CroquiExperimental.DESCRIPTOR.fields_by_name.get("croqui_uid")
    assert campo is not None, "Campo 'croqui_uid' deve existir em CroquiExperimental"
    assert campo.number == 10, "Tag de 'croqui_uid' deve ser 10"
    assert campo.type == descriptor.FieldDescriptor.TYPE_STRING


def test_serializacao_desserializacao_uids() -> None:
    """Valida a serialização e desserialização completa de objetos com UIDs e rotulos."""
    croqui = croqui_pb2.Croqui(
        id="br_mg_cipoboulder",
        nome="Serra do Cipó",
        uid="x8siJek3FiG3aB",
    )
    setor = croqui_pb2.Setor(
        nome="Setor Savassinha",
        uid="m7Kv9TwR48aB12",
    )
    escalada = croqui_pb2.Escalada(
        uid="p9Ab8CxY34cD56",
    )
    mapa = croqui_pb2.Mapa()
    poi = mapa.pontos_de_interesse.add(
        id="poi_1",
        label="11",
        rotulo="11",
        uid="k1A2b3C4d5E6f7",
    )
    ref = mapa.referencias.add(
        alvo_uid="p9Ab8CxY34cD56",
        pontos_uids=["k1A2b3C4d5E6f7"],
        escalada="Via Teste",  # legado
    )

    # Serializa e desserializa
    dados_croqui = croqui.SerializeToString()
    croqui_lido = croqui_pb2.Croqui()
    croqui_lido.ParseFromString(dados_croqui)
    assert croqui_lido.uid == "x8siJek3FiG3aB"

    dados_setor = setor.SerializeToString()
    setor_lido = croqui_pb2.Setor()
    setor_lido.ParseFromString(dados_setor)
    assert setor_lido.uid == "m7Kv9TwR48aB12"

    dados_escalada = escalada.SerializeToString()
    escalada_lida = croqui_pb2.Escalada()
    escalada_lida.ParseFromString(dados_escalada)
    assert escalada_lida.uid == "p9Ab8CxY34cD56"

    dados_mapa = mapa.SerializeToString()
    mapa_lido = croqui_pb2.Mapa()
    mapa_lido.ParseFromString(dados_mapa)
    assert mapa_lido.pontos_de_interesse[0].rotulo == "11"
    assert mapa_lido.pontos_de_interesse[0].label == "11"
    assert mapa_lido.pontos_de_interesse[0].uid == "k1A2b3C4d5E6f7"
    assert mapa_lido.referencias[0].alvo_uid == "p9Ab8CxY34cD56"
    assert list(mapa_lido.referencias[0].pontos_uids) == ["k1A2b3C4d5E6f7"]
    assert mapa_lido.referencias[0].escalada == "Via Teste"
