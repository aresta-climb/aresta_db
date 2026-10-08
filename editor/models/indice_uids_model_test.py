# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários e de integração para IndiceUidsModel e RegistroUid.
Segue rigorosamente os Princípios I, II, III, IV e VII de AGENTS.md:
- Tudo em português
- Library-First
- 100% de cobertura
- TDD (Test-Driven Development)
- Sincronização via Comandos e Histórico (Undo/Redo)
"""

import pytest
from PySide6.QtGui import QUndoStack
from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAlterarPrimitivo,
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdMigrarSetor,
    CmdRenomearEscalada,
)
from editor.models.indice_uids_model import (
    TipoEntidadeUid,
    RegistroUid,
    IndiceUidsModel,
)


# ==============================================================================
# 1. Testes de RegistroUid e Formatação
# ==============================================================================

def test_registro_uid_formatacao_grupo():
    reg = RegistroUid(
        uid="grup_1234567890",
        tipo_id=TipoEntidadeUid.GRUPO,
        nome_grupo="Falésia dos Ventos",
    )
    assert reg.obter_caminho_formatado() == "Falésia dos Ventos"


def test_registro_uid_formatacao_setor_isolado():
    reg = RegistroUid(
        uid="setr_1234567890",
        tipo_id=TipoEntidadeUid.SETOR,
        setor_uid="setr_1234567890",
        nome_setor="Setor Principal",
    )
    assert reg.obter_caminho_formatado() == "Setor Principal"


def test_registro_uid_formatacao_setor_em_grupo():
    reg = RegistroUid(
        uid="setr_1234567890",
        tipo_id=TipoEntidadeUid.SETOR,
        grupo_uid="grup_1234567890",
        nome_grupo="Falésia dos Ventos",
        setor_uid="setr_1234567890",
        nome_setor="Setor Principal",
    )
    assert reg.obter_caminho_formatado() == "Falésia dos Ventos > Setor Principal"


def test_registro_uid_formatacao_escalada_isolada():
    reg = RegistroUid(
        uid="esca_1234567890",
        tipo_id=TipoEntidadeUid.ESCALADA,
        setor_uid="setr_1234567890",
        nome_setor="Setor Principal",
        nome_escalada="Fenda Infinita",
    )
    assert reg.obter_caminho_formatado() == "Setor Principal > Fenda Infinita"


def test_registro_uid_formatacao_escalada_em_grupo():
    reg = RegistroUid(
        uid="esca_1234567890",
        tipo_id=TipoEntidadeUid.ESCALADA,
        grupo_uid="grup_1234567890",
        nome_grupo="Falésia dos Ventos",
        setor_uid="setr_1234567890",
        nome_setor="Setor Principal",
        nome_escalada="Fenda Infinita",
    )
    assert reg.obter_caminho_formatado() == "Falésia dos Ventos > Setor Principal > Fenda Infinita"


def test_registro_uid_formatacao_enfiada():
    reg = RegistroUid(
        uid="enfi_1234567890",
        tipo_id=TipoEntidadeUid.ESCALADA,
        grupo_uid="grup_1234567890",
        nome_grupo="Falésia dos Ventos",
        setor_uid="setr_1234567890",
        nome_setor="Setor Principal",
        nome_escalada="Grande Parede",
        indice_enfiada=2,
    )
    assert reg.obter_caminho_formatado() == "Falésia dos Ventos > Setor Principal > Grande Parede (2ª Enfiada)"


def test_registro_uid_formatacao_botao():
    reg = RegistroUid(
        uid="bota_1234567890",
        tipo_id=TipoEntidadeUid.BOTAO,
        texto_botao="Como Chegar",
    )
    assert reg.obter_caminho_formatado() == "🔘 Como Chegar"


def test_registro_uid_formatacao_tipo_desconhecido():
    reg = RegistroUid(
        uid="desconhecido",
        tipo_id=99,
    )
    assert reg.obter_caminho_formatado() == ""


# ==============================================================================
# Helper de Criação de Croqui Estruturado
# ==============================================================================

def _criar_croqui_teste() -> croqui_pb2.Croqui:
    croqui = croqui_pb2.Croqui(uid="croq_1234567890")
    
    # Botão no croqui
    b = croqui.botoes.add()
    b.uid = "bota_0000000001"
    b.texto = "Apoio e Doações"

    pico = croqui.picos.add(nome="Pico Central")

    # 1. Grupo Alfa com Setor Sul e duas escaladas
    sg_grupo = pico.setores_ou_grupos.add()
    grupo = sg_grupo.grupo.conteudo
    grupo.nome = "Grupo Alfa"
    grupo.uid = "grup_0000000001"

    setor_item = grupo.setores.add()
    setor_sul = setor_item.conteudo
    setor_sul.nome = "Setor Sul"
    setor_sul.uid = "setr_0000000001"

    esc1 = setor_sul.escaladas.add()
    esc1.uid = "esca_0000000001"
    esc1.via_esportiva.nome = "Via Simples"

    esc_mult = setor_sul.escaladas.add()
    esc_mult.uid = "esca_0000000002"
    esc_mult.via_multiplas_enfiadas.nome = "Grande Parede"
    enf1 = esc_mult.via_multiplas_enfiadas.enfiadas.add()
    enf1.uid = "enfi_0000000001"
    enf1.via_esportiva.nome = "P1"
    enf2 = esc_mult.via_multiplas_enfiadas.enfiadas.add()
    enf2.uid = "enfi_0000000002"
    enf2.via_esportiva.nome = "P2"

    # 2. Setor Isolado (Norte) direto no Pico
    sg_setor = pico.setores_ou_grupos.add()
    setor_norte = sg_setor.setor.conteudo
    setor_norte.nome = "Setor Norte"
    setor_norte.uid = "setr_0000000002"

    esc_boulder = setor_norte.escaladas.add()
    esc_boulder.uid = "esca_0000000003"
    esc_boulder.boulder.nome = "Dinamico Supremo"

    return croqui


# ==============================================================================
# 2. Testes de Carga Inicial e Busca no IndiceUidsModel
# ==============================================================================

def test_indice_carga_inicial_e_busca(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    # Total: 1 botao + 1 grupo + 2 setores + 3 escaladas + 2 enfiadas = 9 entidades
    assert len(indice) == 9

    # Busca O(1) do grupo
    reg_g = indice.obter("grup_0000000001")
    assert reg_g is not None
    assert reg_g.tipo_id == TipoEntidadeUid.GRUPO
    assert reg_g.nome_grupo == "Grupo Alfa"
    assert indice.obter_caminho("grup_0000000001") == "Grupo Alfa"

    # Busca O(1) de setor em grupo
    reg_s1 = indice.obter("setr_0000000001")
    assert reg_s1 is not None
    assert reg_s1.tipo_id == TipoEntidadeUid.SETOR
    assert reg_s1.grupo_uid == "grup_0000000001"
    assert reg_s1.nome_grupo == "Grupo Alfa"
    assert reg_s1.nome_setor == "Setor Sul"
    assert indice.obter_caminho("setr_0000000001") == "Grupo Alfa > Setor Sul"

    # Busca O(1) de setor isolado
    reg_s2 = indice.obter("setr_0000000002")
    assert reg_s2 is not None
    assert reg_s2.grupo_uid is None
    assert reg_s2.nome_setor == "Setor Norte"
    assert indice.obter_caminho("setr_0000000002") == "Setor Norte"

    # Busca O(1) de escalada em grupo
    reg_e1 = indice.obter("esca_0000000001")
    assert reg_e1 is not None
    assert reg_e1.tipo_id == TipoEntidadeUid.ESCALADA
    assert reg_e1.nome_escalada == "Via Simples"
    assert reg_e1.setor_uid == "setr_0000000001"
    assert reg_e1.nome_setor == "Setor Sul"
    assert reg_e1.grupo_uid == "grup_0000000001"
    assert indice.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Via Simples"

    # Busca O(1) de enfiada
    reg_enf = indice.obter("enfi_0000000002")
    assert reg_enf is not None
    assert reg_enf.nome_escalada == "Grande Parede"
    assert reg_enf.indice_enfiada == 2
    assert indice.obter_caminho("enfi_0000000002") == "Grupo Alfa > Setor Sul > Grande Parede (2ª Enfiada)"

    # Busca O(1) de escalada em setor isolado
    reg_e3 = indice.obter("esca_0000000003")
    assert reg_e3 is not None
    assert reg_e3.grupo_uid is None
    assert reg_e3.nome_setor == "Setor Norte"
    assert reg_e3.nome_escalada == "Dinamico Supremo"
    assert indice.obter_caminho("esca_0000000003") == "Setor Norte > Dinamico Supremo"

    # Busca O(1) de botão
    reg_b = indice.obter("bota_0000000001")
    assert reg_b is not None
    assert reg_b.tipo_id == TipoEntidadeUid.BOTAO
    assert reg_b.texto_botao == "Apoio e Doações"
    assert indice.obter_caminho("bota_0000000001") == "🔘 Apoio e Doações"

    # UID inexistente
    assert indice.obter("nao_existe") is None
    assert indice.obter_caminho("nao_existe") is None
    assert not indice.existe("nao_existe")
    assert indice.existe("esca_0000000001")


# ==============================================================================
# 3. Testes de Mutação Granular no IndiceUidsModel
# ==============================================================================

def test_indice_renomear_escalada(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    indice.atualizar_nome_escalada("esca_0000000001", "Via Renomeada")
    assert indice.obter("esca_0000000001").nome_escalada == "Via Renomeada"
    assert indice.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Via Renomeada"

    # Renomear via de múltiplas enfiadas deve atualizar o nome nas enfiadas também
    indice.atualizar_nome_escalada("esca_0000000002", "Paredão Novo")
    assert indice.obter("enfi_0000000001").nome_escalada == "Paredão Novo"
    assert indice.obter_caminho("enfi_0000000001") == "Grupo Alfa > Setor Sul > Paredão Novo (1ª Enfiada)"


def test_indice_renomear_setor_propaga_para_escaladas(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    indice.atualizar_nome_setor("setr_0000000001", "Setor Sul Reformado")
    assert indice.obter("setr_0000000001").nome_setor == "Setor Sul Reformado"
    assert indice.obter_caminho("setr_0000000001") == "Grupo Alfa > Setor Sul Reformado"

    # Escaladas filhas devem refletir o novo nome do setor imediatamente
    assert indice.obter("esca_0000000001").nome_setor == "Setor Sul Reformado"
    assert indice.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul Reformado > Via Simples"
    assert indice.obter("enfi_0000000001").nome_setor == "Setor Sul Reformado"
    assert indice.obter_caminho("enfi_0000000001") == "Grupo Alfa > Setor Sul Reformado > Grande Parede (1ª Enfiada)"

    # Setor Norte não foi afetado
    assert indice.obter("esca_0000000003").nome_setor == "Setor Norte"


def test_indice_renomear_grupo_propaga_para_setores_e_escaladas(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    indice.atualizar_nome_grupo("grup_0000000001", "Grupo Mega")
    assert indice.obter("grup_0000000001").nome_grupo == "Grupo Mega"
    assert indice.obter_caminho("grup_0000000001") == "Grupo Mega"

    # Setor filho deve refletir
    assert indice.obter("setr_0000000001").nome_grupo == "Grupo Mega"
    assert indice.obter_caminho("setr_0000000001") == "Grupo Mega > Setor Sul"

    # Escaladas do setor devem refletir
    assert indice.obter("esca_0000000001").nome_grupo == "Grupo Mega"
    assert indice.obter_caminho("esca_0000000001") == "Grupo Mega > Setor Sul > Via Simples"


def test_indice_renomear_botao(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    indice.atualizar_texto_botao("bota_0000000001", "Contato e Redes")
    assert indice.obter("bota_0000000001").texto_botao == "Contato e Redes"
    assert indice.obter_caminho("bota_0000000001") == "🔘 Contato e Redes"


def test_indice_mover_setor_para_grupo_e_para_isolado(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    # 1. Mover Setor Norte (que era isolado) para dentro do Grupo Alfa
    indice.mover_setor("setr_0000000002", novo_grupo_uid="grup_0000000001", novo_nome_grupo="Grupo Alfa")
    assert indice.obter("setr_0000000002").grupo_uid == "grup_0000000001"
    assert indice.obter("setr_0000000002").nome_grupo == "Grupo Alfa"
    assert indice.obter_caminho("setr_0000000002") == "Grupo Alfa > Setor Norte"

    # Escalada do Setor Norte agora tem caminho com Grupo Alfa
    assert indice.obter("esca_0000000003").grupo_uid == "grup_0000000001"
    assert indice.obter("esca_0000000003").nome_grupo == "Grupo Alfa"
    assert indice.obter_caminho("esca_0000000003") == "Grupo Alfa > Setor Norte > Dinamico Supremo"

    # 2. Mover Setor Sul (que estava no Grupo Alfa) para fora (isolado)
    indice.mover_setor("setr_0000000001", novo_grupo_uid=None, novo_nome_grupo=None)
    assert indice.obter("setr_0000000001").grupo_uid is None
    assert indice.obter("setr_0000000001").nome_grupo is None
    assert indice.obter_caminho("setr_0000000001") == "Setor Sul"

    assert indice.obter("esca_0000000001").grupo_uid is None
    assert indice.obter_caminho("esca_0000000001") == "Setor Sul > Via Simples"


def test_indice_mover_escalada_de_setor(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    # Move Via Simples do Setor Sul (Grupo Alfa) para o Setor Norte (isolado)
    indice.mover_escalada(
        escalada_uid="esca_0000000001",
        novo_setor_uid="setr_0000000002",
        novo_nome_setor="Setor Norte",
        novo_grupo_uid=None,
        novo_nome_grupo=None,
    )
    reg = indice.obter("esca_0000000001")
    assert reg.setor_uid == "setr_0000000002"
    assert reg.nome_setor == "Setor Norte"
    assert reg.grupo_uid is None
    assert indice.obter_caminho("esca_0000000001") == "Setor Norte > Via Simples"


def test_indice_remover_em_cascata(qapp):
    croqui = _criar_croqui_teste()
    indice = IndiceUidsModel(croqui)

    # Remover escalada com enfiadas remove a via e suas enfiadas
    indice.remover("esca_0000000002")
    assert not indice.existe("esca_0000000002")
    assert not indice.existe("enfi_0000000001")
    assert not indice.existe("enfi_0000000002")

    # Remover setor remove o setor e suas escaladas restantes
    indice.remover("setr_0000000001")
    assert not indice.existe("setr_0000000001")
    assert not indice.existe("esca_0000000001")

    # Remover grupo remove o grupo e tudo que estiver nele
    indice.remover("grup_0000000001")
    assert not indice.existe("grup_0000000001")

    # Botão e Setor Norte continuam intactos
    assert indice.existe("bota_0000000001")
    assert indice.existe("setr_0000000002")
    assert indice.existe("esca_0000000003")


# ==============================================================================
# 4. Testes de Integração com CroquiModel e Histórico Undo/Redo
# ==============================================================================

def test_croqui_model_integra_indice_uids_na_inicializacao(qapp):
    croqui = _criar_croqui_teste()
    model = CroquiModel(croqui)
    
    assert hasattr(model, "indice_uids")
    assert len(model.indice_uids) == 9
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Via Simples"


def test_historico_undo_redo_renomear_escalada_sincroniza_indice(qapp):
    croqui = _criar_croqui_teste()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()

    esc1 = croqui.picos[0].setores_ou_grupos[0].grupo.conteudo.setores[0].conteudo.escaladas[0]
    
    # 1. Executa comando de renomeação de primitivo (nome da via)
    cmd = CmdAlterarPrimitivo(
        model=model,
        msg=esc1.via_esportiva,
        campo_nome="nome",
        valor_antigo="Via Simples",
        valor_novo="Super Fenda 10a",
    )
    undo_stack.push(cmd)

    # Verifica que o índice foi atualizado no Redo
    assert model.indice_uids.obter("esca_0000000001").nome_escalada == "Super Fenda 10a"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Super Fenda 10a"

    # 2. Desfaz (Undo)
    undo_stack.undo()
    assert model.indice_uids.obter("esca_0000000001").nome_escalada == "Via Simples"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Via Simples"

    # 3. Refaz (Redo)
    undo_stack.redo()
    assert model.indice_uids.obter("esca_0000000001").nome_escalada == "Super Fenda 10a"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Super Fenda 10a"


def test_historico_undo_redo_renomear_setor_sincroniza_indice_e_filhos(qapp):
    croqui = _criar_croqui_teste()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()

    setor = croqui.picos[0].setores_ou_grupos[0].grupo.conteudo.setores[0].conteudo

    cmd = CmdAlterarPrimitivo(
        model=model,
        msg=setor,
        campo_nome="nome",
        valor_antigo="Setor Sul",
        valor_novo="Paredão Sul Extremo",
    )
    undo_stack.push(cmd)

    # Redo: Setor e suas vias devem refletir o novo nome
    assert model.indice_uids.obter("setr_0000000001").nome_setor == "Paredão Sul Extremo"
    assert model.indice_uids.obter_caminho("setr_0000000001") == "Grupo Alfa > Paredão Sul Extremo"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Paredão Sul Extremo > Via Simples"

    # Undo: Reverte
    undo_stack.undo()
    assert model.indice_uids.obter("setr_0000000001").nome_setor == "Setor Sul"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Via Simples"

    # Redo: Reaplica
    undo_stack.redo()
    assert model.indice_uids.obter("setr_0000000001").nome_setor == "Paredão Sul Extremo"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Paredão Sul Extremo > Via Simples"


def test_historico_undo_redo_renomear_grupo_sincroniza_indice_e_subarvore(qapp):
    croqui = _criar_croqui_teste()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()

    grupo = croqui.picos[0].setores_ou_grupos[0].grupo.conteudo

    cmd = CmdAlterarPrimitivo(
        model=model,
        msg=grupo,
        campo_nome="nome",
        valor_antigo="Grupo Alfa",
        valor_novo="Setorzao Beta",
    )
    undo_stack.push(cmd)

    assert model.indice_uids.obter("grup_0000000001").nome_grupo == "Setorzao Beta"
    assert model.indice_uids.obter_caminho("setr_0000000001") == "Setorzao Beta > Setor Sul"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Setorzao Beta > Setor Sul > Via Simples"

    undo_stack.undo()
    assert model.indice_uids.obter("grup_0000000001").nome_grupo == "Grupo Alfa"
    assert model.indice_uids.obter_caminho("esca_0000000001") == "Grupo Alfa > Setor Sul > Via Simples"


def test_historico_undo_redo_adicionar_e_remover_escalada(qapp):
    croqui = _criar_croqui_teste()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()

    setor = croqui.picos[0].setores_ou_grupos[0].grupo.conteudo.setores[0].conteudo

    nova_esc = croqui_pb2.Escalada(uid="esca_novissima1")
    nova_esc.via_esportiva.nome = "Rota Recém Aberta"

    # 1. Adicionar escalada
    cmd_add = CmdAdicionarRepeated(
        model=model,
        msg=setor,
        campo_nome="escaladas",
        index=len(setor.escaladas),
        valor=nova_esc,
    )
    undo_stack.push(cmd_add)

    assert model.indice_uids.existe("esca_novissima1")
    assert model.indice_uids.obter_caminho("esca_novissima1") == "Grupo Alfa > Setor Sul > Rota Recém Aberta"

    # 2. Desfazer adição
    undo_stack.undo()
    assert not model.indice_uids.existe("esca_novissima1")
    assert model.indice_uids.obter("esca_novissima1") is None

    # 3. Refazer adição
    undo_stack.redo()
    assert model.indice_uids.existe("esca_novissima1")
    assert model.indice_uids.obter_caminho("esca_novissima1") == "Grupo Alfa > Setor Sul > Rota Recém Aberta"

    # 4. Remover escalada
    cmd_rem = CmdRemoverRepeated(
        model=model,
        msg=setor,
        campo_nome="escaladas",
        index=len(setor.escaladas) - 1,
    )
    undo_stack.push(cmd_rem)
    assert not model.indice_uids.existe("esca_novissima1")

    # 5. Desfazer remoção
    undo_stack.undo()
    assert model.indice_uids.existe("esca_novissima1")
    assert model.indice_uids.obter_caminho("esca_novissima1") == "Grupo Alfa > Setor Sul > Rota Recém Aberta"


def test_historico_undo_redo_migrar_setor_sincroniza_indice(qapp):
    """Testa migração de setor de pico isolado para dentro de um grupo e vice-versa."""
    croqui = _criar_croqui_teste()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()

    pico = croqui.picos[0]
    grupo = pico.setores_ou_grupos[0].grupo.conteudo

    # Setor Norte está no índice 1 de setores_ou_grupos (isolado no Pico)
    # Vamos migrá-lo para dentro de grupo.setores (índice 1)
    cmd_migrar = CmdMigrarSetor(
        model=model,
        pai_origem=pico,
        campo_origem="setores_ou_grupos",
        indice_origem=1,
        pai_destino=grupo,
        campo_destino="setores",
        indice_destino=1,
    )
    undo_stack.push(cmd_migrar)

    # Redo: Setor Norte agora está dentro do Grupo Alfa
    assert model.indice_uids.obter("setr_0000000002").grupo_uid == "grup_0000000001"
    assert model.indice_uids.obter("setr_0000000002").nome_grupo == "Grupo Alfa"
    assert model.indice_uids.obter_caminho("setr_0000000002") == "Grupo Alfa > Setor Norte"
    assert model.indice_uids.obter_caminho("esca_0000000003") == "Grupo Alfa > Setor Norte > Dinamico Supremo"

    # Undo: Setor Norte volta a ser isolado no Pico
    undo_stack.undo()
    assert model.indice_uids.obter("setr_0000000002").grupo_uid is None
    assert model.indice_uids.obter("setr_0000000002").nome_grupo is None
    assert model.indice_uids.obter_caminho("setr_0000000002") == "Setor Norte"
    assert model.indice_uids.obter_caminho("esca_0000000003") == "Setor Norte > Dinamico Supremo"

    # Redo: Reaplica migração
    undo_stack.redo()
    assert model.indice_uids.obter_caminho("esca_0000000003") == "Grupo Alfa > Setor Norte > Dinamico Supremo"
