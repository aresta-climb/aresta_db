# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAlterarPrimitivo,
    CmdMacro,
    deserializar_comando,
)
from editor.core.historico import GerenciadorHistorico
from editor.core.diario import GerenciadorDiario


def _criar_model_teste():
    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor 1"
    via = setor.escaladas.add()
    via.via_esportiva.nome = "Via 1"
    return CroquiModel(croqui)


def test_cmd_macro_execucao_redo_e_undo():
    model = _criar_model_teste()
    croqui = model.obter_croqui_readonly()
    pico = croqui.picos[0]
    setor = pico.setores_ou_grupos[0].setor.conteudo

    cmd1 = CmdAlterarPrimitivo(model, pico, "nome", "Pico 1", "Pico Modificado")
    cmd2 = CmdAlterarPrimitivo(model, setor, "nome", "Setor 1", "Setor Modificado")

    macro = CmdMacro(comandos=[cmd1, cmd2], texto="Alterar Nomes")
    assert macro.text() == "Alterar Nomes"
    assert len(macro.comandos) == 2

    # Executa redo
    macro.redo()
    assert pico.nome == "Pico Modificado"
    assert setor.nome == "Setor Modificado"

    # Executa undo (ordem reversa)
    macro.undo()
    assert pico.nome == "Pico 1"
    assert setor.nome == "Setor 1"

    # Executa redo novamente
    macro.redo()
    assert pico.nome == "Pico Modificado"
    assert setor.nome == "Setor Modificado"


def test_cmd_macro_adicionar_comando():
    model = _criar_model_teste()
    pico = model.obter_croqui_readonly().picos[0]

    macro = CmdMacro(texto="Vazio Inicialmente")
    assert len(macro.comandos) == 0

    cmd = CmdAlterarPrimitivo(model, pico, "nome", "Pico 1", "Pico 2")
    macro.adicionar_comando(cmd)
    assert len(macro.comandos) == 1

    macro.redo()
    assert pico.nome == "Pico 2"
    macro.undo()
    assert pico.nome == "Pico 1"


def test_cmd_macro_carregamento_silencioso():
    model = _criar_model_teste()
    pico = model.obter_croqui_readonly().picos[0]

    cmd = CmdAlterarPrimitivo(model, pico, "nome", "Pico 1", "Pico Mutado")
    macro = CmdMacro(comandos=[cmd], texto="Silencioso")
    macro.armar_carregamento_silencioso()

    # Primeiro redo deve ser ignorado silenciosamente
    macro.redo()
    assert pico.nome == "Pico 1"

    # Segundo redo deve executar normalmente
    macro.redo()
    assert pico.nome == "Pico Mutado"


def test_cmd_macro_serializacao_e_deserializacao():
    model = _criar_model_teste()
    croqui = model.obter_croqui_readonly()
    pico = croqui.picos[0]
    setor = pico.setores_ou_grupos[0].setor.conteudo

    cmd1 = CmdAlterarPrimitivo(model, pico, "nome", "Pico 1", "Pico X")
    cmd2 = CmdAlterarPrimitivo(model, setor, "nome", "Setor 1", "Setor Y")

    macro = CmdMacro(comandos=[cmd1, cmd2], texto="Macro Teste")
    dados = macro.serializar()

    assert dados["classe"] == "CmdMacro"
    assert dados["texto"] == "Macro Teste"
    assert len(dados["comandos"]) == 2
    assert dados["comandos"][0]["classe"] == "CmdAlterarPrimitivo"
    assert dados["comandos"][1]["classe"] == "CmdAlterarPrimitivo"

    # Deserializa globalmente
    macro_recriado = deserializar_comando(dados, model)
    assert isinstance(macro_recriado, CmdMacro)
    assert macro_recriado.text() == "Macro Teste"
    assert len(macro_recriado.comandos) == 2

    # Executa o comando recriado
    macro_recriado.redo()
    assert pico.nome == "Pico X"
    assert setor.nome == "Setor Y"
    macro_recriado.undo()
    assert pico.nome == "Pico 1"
    assert setor.nome == "Setor 1"


def test_cmd_macro_persistencia_no_diario(tmp_path):
    model = _criar_model_teste()
    pico = model.obter_croqui_readonly().picos[0]
    diario = GerenciadorDiario(tmp_path)

    cmd = CmdAlterarPrimitivo(model, pico, "nome", "Pico 1", "Pico Gravado")
    macro = CmdMacro(comandos=[cmd], texto="Gravar no Diario")

    diario.gravar_comando_pendente(macro)
    assert diario.tem_alteracoes_pendentes() is True

    lidos = diario.ler_diario_pendente()
    assert len(lidos) == 1
    assert lidos[0]["classe"] == "CmdMacro"
    assert lidos[0]["texto"] == "Gravar no Diario"

    # Substituição no diário
    diario.substituir_comandos_pendentes([macro])
    lidos2 = diario.ler_diario_pendente()
    assert len(lidos2) == 1
    assert lidos2[0]["classe"] == "CmdMacro"


def test_cmd_macro_com_historico_e_sinais(qtbot):
    model = _criar_model_teste()
    pico = model.obter_croqui_readonly().picos[0]
    setor = pico.setores_ou_grupos[0].setor.conteudo

    historico = GerenciadorHistorico()

    sinais_recebidos = []
    historico.sinal_campo_alterado.connect(
        lambda id_msg, campo, val: sinais_recebidos.append((id_msg, campo, val))
    )

    cmd1 = CmdAlterarPrimitivo(model, pico, "nome", "Pico 1", "Pico H")
    cmd2 = CmdAlterarPrimitivo(model, setor, "nome", "Setor 1", "Setor H")
    macro = CmdMacro(comandos=[cmd1, cmd2], texto="Macro com Historico")

    historico.executar(macro)
    assert pico.nome == "Pico H"
    assert setor.nome == "Setor H"
    # Sinais recebidos para ambos os comandos
    campos = [s[1] for s in sinais_recebidos]
    assert "nome" in campos
    assert len(sinais_recebidos) == 2

    # Undo
    sinais_recebidos.clear()
    historico.desfazer()
    assert pico.nome == "Pico 1"
    assert setor.nome == "Setor 1"
    assert len(sinais_recebidos) == 2

    # Redo
    sinais_recebidos.clear()
    historico.refazer()
    assert pico.nome == "Pico H"
    assert setor.nome == "Setor H"
    assert len(sinais_recebidos) == 2
