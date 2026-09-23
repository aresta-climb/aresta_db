# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdRenomearEscalada,
    deserializar_comando,
)
from editor.core.historico import GerenciadorHistorico
from editor.core.diario import GerenciadorDiario


def _criar_model_com_escalada_e_mapas():
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")

    # Mapa de pico geral
    mapa_geral = pico.mapas_gerais.conteudo.mapas.add()
    ref_geral = mapa_geral.referencias.add(
        setor="Setor 1",
        escalada="Via Inicial",
        ids=["linha_1"]
    )

    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor 1"

    # Escaladas
    via1 = setor.escaladas.add()
    via1.via_esportiva.nome = "Via Inicial"

    via2 = setor.escaladas.add()
    via2.boulder.nome = "Boulder 2"

    # Mapa de setor
    mapa_setor = setor.mapas.add()
    ref_setor = mapa_setor.referencias.add(
        escalada="Via Inicial",
        ids=["linha_2"]
    )

    return CroquiModel(croqui), ref_geral, ref_setor


def test_cmd_renomear_escalada_basico_redo_undo():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Renomeada",
        referencias=[ref_geral, ref_setor],
    )

    assert cmd.text() == "Renomear escalada para Via Renomeada"
    assert cmd.id() == CmdRenomearEscalada.ID_COMANDO

    # 1. Redo
    cmd.redo()
    assert via.nome == "Via Renomeada"
    assert ref_geral.escalada == "Via Renomeada"
    assert ref_setor.escalada == "Via Renomeada"

    # 2. Undo
    cmd.undo()
    assert via.nome == "Via Inicial"
    assert ref_geral.escalada == "Via Inicial"
    assert ref_setor.escalada == "Via Inicial"

    # 3. Redo novamente
    cmd.redo()
    assert via.nome == "Via Renomeada"
    assert ref_geral.escalada == "Via Renomeada"
    assert ref_setor.escalada == "Via Renomeada"


def test_cmd_renomear_escalada_com_nome_vazio():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="",
        referencias=[ref_geral],
    )

    cmd.redo()
    assert via.nome == ""
    assert ref_geral.escalada == ""

    cmd.undo()
    assert via.nome == "Via Inicial"
    assert ref_geral.escalada == "Via Inicial"


def test_cmd_renomear_escalada_merge_with_mesma_sessao():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Ren",
        referencias=[ref_geral, ref_setor],
        session_id=10,
        pode_mesclar=True,
    )
    cmd1.redo()
    assert via.nome == "Via Ren"
    assert ref_geral.escalada == "Via Ren"

    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Ren",
        nome_novo="Via Renomeada Final",
        referencias=[ref_geral, ref_setor],
        session_id=10,
        pode_mesclar=True,
    )

    mesclou = cmd1.mergeWith(cmd2)
    assert mesclou is True
    assert cmd1.nome_novo == "Via Renomeada Final"
    assert via.nome == "Via Renomeada Final"
    assert ref_geral.escalada == "Via Renomeada Final"
    assert ref_setor.escalada == "Via Renomeada Final"

    # Undo deve voltar direto para o nome inicial
    cmd1.undo()
    assert via.nome == "Via Inicial"
    assert ref_geral.escalada == "Via Inicial"
    assert ref_setor.escalada == "Via Inicial"


def test_cmd_renomear_escalada_merge_with_sessao_diferente():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via 1",
        referencias=[ref_geral],
        session_id=1,
    )
    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via 1",
        nome_novo="Via 2",
        referencias=[ref_geral],
        session_id=2,
    )

    assert cmd1.mergeWith(cmd2) is False


def test_cmd_renomear_escalada_merge_with_alvo_diferente():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    setor = croqui.picos[0].setores_ou_grupos[0].setor.conteudo
    via1 = setor.escaladas[0].via_esportiva
    via2 = setor.escaladas[1].boulder

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via1,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via 1",
        referencias=[],
        session_id=1,
    )
    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via2,
        campo_nome="nome",
        nome_antigo="Boulder 2",
        nome_novo="Boulder 2 Editado",
        referencias=[],
        session_id=1,
    )

    assert cmd1.mergeWith(cmd2) is False


def test_cmd_renomear_escalada_merge_with_pode_mesclar_falso():
    model, ref_geral, _ = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="A",
        nome_novo="B",
        referencias=[ref_geral],
        pode_mesclar=False,
    )
    assert cmd1.id() == -1

    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="B",
        nome_novo="C",
        referencias=[ref_geral],
        pode_mesclar=True,
    )

    assert cmd1.mergeWith(cmd2) is False

    cmd3 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="B",
        nome_novo="C",
        referencias=[ref_geral],
        pode_mesclar=False,
    )
    cmd_mesclavel = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="A",
        nome_novo="B",
        referencias=[ref_geral],
        pode_mesclar=True,
    )
    assert cmd_mesclavel.mergeWith(cmd3) is False


def test_cmd_renomear_escalada_serializacao_e_deserializacao():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Restaurada",
        referencias=[ref_geral, ref_setor],
        context_path="rota:1",
        session_id=99,
    )

    dados = cmd.serializar()
    assert dados["classe"] == "CmdRenomearEscalada"
    assert dados["campo_nome"] == "nome"
    assert dados["nome_antigo"] == "Via Inicial"
    assert dados["nome_novo"] == "Via Restaurada"
    assert dados["context_path"] == "rota:1"
    assert dados["session_id"] == 99
    assert len(dados["caminhos_referencias"]) == 2

    # Deserializa
    cmd_restaurado = deserializar_comando(dados, model)
    assert isinstance(cmd_restaurado, CmdRenomearEscalada)
    assert cmd_restaurado.nome_antigo == "Via Inicial"
    assert cmd_restaurado.nome_novo == "Via Restaurada"
    assert cmd_restaurado.context_path == "rota:1"
    assert cmd_restaurado.session_id == 99
    assert len(cmd_restaurado.referencias) == 2

    # Executa redo e undo na instância restaurada
    cmd_restaurado.redo()
    assert via.nome == "Via Restaurada"
    assert ref_geral.escalada == "Via Restaurada"
    assert ref_setor.escalada == "Via Restaurada"

    cmd_restaurado.undo()
    assert via.nome == "Via Inicial"
    assert ref_geral.escalada == "Via Inicial"
    assert ref_setor.escalada == "Via Inicial"


def test_cmd_renomear_escalada_notificacao_foco():
    model, ref_geral, _ = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    focos_recebidos = []
    model.foco_requisitado.connect(lambda ctx: focos_recebidos.append(ctx))

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Foco",
        referencias=[ref_geral],
        context_path="campo:nome_via",
    )

    cmd.redo()
    assert focos_recebidos == ["campo:nome_via"]

    cmd.undo()
    assert focos_recebidos == ["campo:nome_via", "campo:nome_via"]


def test_cmd_renomear_escalada_mensagem_orfa_dispara_erro():
    model, ref_geral, _ = _criar_model_com_escalada_e_mapas()
    via_orfa = croqui_pb2.ViaEsportiva(nome="Orfa")

    with pytest.raises(ValueError, match="não pertence à árvore ativa"):
        CmdRenomearEscalada(
            model=model,
            msg_escalada=via_orfa,
            campo_nome="nome",
            nome_antigo="Orfa",
            nome_novo="Orfa 2",
            referencias=[ref_geral],
        )

    ref_orfa = croqui_pb2.Mapa.Referencia(escalada="Via Inicial")
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    with pytest.raises(ValueError, match="não pertence à árvore ativa"):
        CmdRenomearEscalada(
            model=model,
            msg_escalada=via,
            campo_nome="nome",
            nome_antigo="Via Inicial",
            nome_novo="Via 2",
            referencias=[ref_orfa],
        )


def test_cmd_renomear_escalada_roundtrip_diario(tmp_path):
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    diario = GerenciadorDiario(tmp_path)
    historico = GerenciadorHistorico(diario=diario)

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Intermediaria",
        referencias=[ref_geral, ref_setor],
        session_id=5,
    )
    historico.executar(cmd1)

    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Intermediaria",
        nome_novo="Via Final",
        referencias=[ref_geral, ref_setor],
        session_id=5,
    )
    historico.executar(cmd2)

    assert historico.obter_pilha().count() == 1
    assert via.nome == "Via Final"
    assert ref_geral.escalada == "Via Final"

    # Valida comandos pendentes no diário
    pendentes = diario.ler_diario_pendente()
    assert len(pendentes) == 1
    cmd_restaurado = deserializar_comando(pendentes[0], model)
    assert cmd_restaurado.nome_novo == "Via Final"

    historico.obter_pilha().undo()
    assert via.nome == "Via Inicial"
    assert ref_geral.escalada == "Via Inicial"


def test_cmd_renomear_escalada_merge_with_outro_tipo_comando():
    from editor.commands.comandos_protobuf import CmdAlterarPrimitivo
    model, ref_geral, _ = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="A",
        nome_novo="B",
        referencias=[ref_geral],
    )
    cmd2 = CmdAlterarPrimitivo(
        model=model,
        msg=via,
        campo_nome="nome",
        valor_antigo="B",
        valor_novo="C",
        pode_mesclar=True,
    )
    assert cmd1.mergeWith(cmd2) is False


def test_cmd_renomear_escalada_merge_with_atualiza_context_path():
    model, ref_geral, _ = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd1 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="A",
        nome_novo="B",
        referencias=[ref_geral],
        context_path="ctx_1",
        session_id=1,
    )
    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="B",
        nome_novo="C",
        referencias=[ref_geral],
        context_path="ctx_2",
        session_id=1,
    )
    assert cmd1.mergeWith(cmd2) is True
    assert cmd1.context_path == "ctx_2"


def test_historico_despacha_sinal_renomear_escalada():
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    historico = GerenciadorHistorico()
    sinais_recebidos = []
    historico.sinal_campo_alterado.connect(
        lambda obj_id, campo, val: sinais_recebidos.append((obj_id, campo, val))
    )

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Sinalizada",
        referencias=[ref_geral, ref_setor],
    )
    historico.executar(cmd)

    # Verifica se os sinais foram emitidos no redo
    id_via = id(via)
    id_ref_geral = id(ref_geral)
    id_ref_setor = id(ref_setor)

    assert (id_via, "nome", "Via Sinalizada") in sinais_recebidos
    assert (id_ref_geral, "escalada", "Via Sinalizada") in sinais_recebidos
    assert (id_ref_setor, "escalada", "Via Sinalizada") in sinais_recebidos

    sinais_recebidos.clear()
    historico.obter_pilha().undo()

    # Verifica se os sinais foram emitidos no undo
    assert (id_via, "nome", "Via Inicial") in sinais_recebidos
    assert (id_ref_geral, "escalada", "Via Inicial") in sinais_recebidos
    assert (id_ref_setor, "escalada", "Via Inicial") in sinais_recebidos


def test_cmd_renomear_escalada_preserva_cache_de_referencias_pre_resolvidas():
    """Garante que quando referências e seus caminhos são fornecidos juntos, o cache de objetos em RAM é preservado."""
    model, ref_geral, ref_setor = _criar_model_com_escalada_e_mapas()
    croqui = model.obter_croqui_readonly()
    via = croqui.picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        caminho_msg="picos[0].setores_ou_grupos[0].setor.conteudo.escaladas[0].via_esportiva",
        campo_nome="nome",
        nome_antigo="Via Inicial",
        nome_novo="Via Cache",
        referencias=[ref_geral, ref_setor],
        caminhos_referencias=[
            "picos[0].mapas_gerais.conteudo.mapas[0].referencias[0]",
            "picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0].referencias[0]",
        ],
    )

    # O cache em memória deve conter os objetos passados sem esvaziá-los
    assert cmd._referencias_cache == [ref_geral, ref_setor]
    assert cmd.referencias == [ref_geral, ref_setor]
    assert cmd._msg_cache is via
