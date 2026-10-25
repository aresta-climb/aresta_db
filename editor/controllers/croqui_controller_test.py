# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel
from editor.models.referencias_util import resolver_caminho_referencia


def test_croqui_controller_alterar_primitivo(qapp):
    croqui = Croqui(nome="Antigo")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()

    # A view despacha a intenção
    controller.alterar_primitivo(proxy, "nome", "Antigo", "Novo")

    # O Controller deve ter empurrado um comando, e o comando já rodou redo()
    assert proxy.nome == "Novo"
    assert undo_stack.count() == 1

    # Desfazendo a ação
    undo_stack.undo()
    assert proxy.nome == "Antigo"

    controller.set_contexto("page:dados")
    assert controller.contexto_atual_path == "page:dados"


def test_croqui_controller_adicionar_repeated(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()

    pico = Pico(nome="Novo Pico")
    controller.adicionar_repeated(proxy, "picos", 0, pico)

    assert len(proxy.picos) == 1
    assert proxy.picos[0].nome == "Novo Pico"

    undo_stack.undo()
    assert len(proxy.picos) == 0


def test_croqui_controller_remover_repeated(qapp):
    croqui = Croqui()
    croqui.picos.add(nome="A Remover")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()

    pico_removido = proxy.picos[0]
    controller.remover_repeated(proxy, "picos", 0, pico_removido)

    assert len(proxy.picos) == 0

    undo_stack.undo()
    assert len(proxy.picos) == 1
    assert proxy.picos[0].nome == "A Remover"


def test_croqui_controller_remover_repeated_com_imagens_em_memoria(qapp):
    from aresta_api.proto.generated import croqui_pb2

    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Sul"
    mapa = setor.mapas.add()
    mapa.caminho_imagem_mapa = "imagens/setor_sul_p0.webp"

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/setor_sul_p0.webp", b"conteudo_bytes")
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy_setor = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    mapa_removido = proxy_setor.mapas[0]

    controller.remover_repeated(proxy_setor, "mapas", 0, mapa_removido)

    assert len(proxy_setor.mapas) == 0
    assert "imagens/setor_sul_p0.webp" not in model.obter_imagens_em_memoria()

    undo_stack.undo()
    assert len(proxy_setor.mapas) == 1
    assert "imagens/setor_sul_p0.webp" in model.obter_imagens_em_memoria()
    assert model.obter_bytes_imagem("imagens/setor_sul_p0.webp") == b"conteudo_bytes"


def test_croqui_controller_alterar_oneof(qapp):
    from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo, ArquivoSetor

    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.caminho = "Setor"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()
    proxy_sg = proxy.picos[0].setores_ou_grupos[0]

    novo_grupo = ArquivoGrupo()
    novo_grupo.caminho = "Grupo"

    arq_grupo = ArquivoGrupo()
    arq_grupo.caminho = "Grupo"

    arq_setor = ArquivoSetor()
    arq_setor.caminho = "Setor"

    controller.alterar_oneof(proxy_sg, "tipo", "setor", arq_setor, "grupo", arq_grupo)

    assert proxy_sg.WhichOneof("tipo") == "grupo"
    assert proxy_sg.grupo.caminho == "Grupo"

    undo_stack.undo()
    assert proxy_sg.WhichOneof("tipo") == "setor"
    assert proxy_sg.setor.caminho == "Setor"


def test_croqui_controller_mover_repeated_para_cima(qapp):
    croqui = Croqui()
    croqui.creditos.extend(["Renato", "Silva"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    controller.mover_repeated_para_cima(proxy, "creditos", 0)
    assert undo_stack.count() == 0
    assert list(proxy.creditos) == ["Renato", "Silva"]

    controller.mover_repeated_para_cima(proxy, "creditos", 1)
    assert undo_stack.count() == 1
    assert list(proxy.creditos) == ["Silva", "Renato"]

    undo_stack.undo()
    assert list(proxy.creditos) == ["Renato", "Silva"]


def test_croqui_controller_alterar_metadados_caminho_novo(qapp):
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor

    croqui = Croqui()
    sg = croqui.picos.add().setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()
    proxy_setor = proxy.picos[0].setores_ou_grupos[0].setor

    controller.alterar_metadados_caminho_novo(
        proxy_setor, ArquivoSetor.ext_metadados_arquivo, "", "novo_caminho.md"
    )

    assert proxy_setor.HasExtension(ArquivoSetor.ext_metadados_arquivo)
    assert (
        proxy_setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == "novo_caminho.md"
    )
    assert undo_stack.count() == 1

    undo_stack.undo()
    assert proxy_setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == ""


def test_croqui_controller_mover_repeated_para_baixo(qapp):
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    # Testa mover no último elemento (deve ignorar)
    controller.mover_repeated_para_baixo(proxy, "creditos", 2)
    assert undo_stack.count() == 0

    # Testa mover num elemento válido
    controller.mover_repeated_para_baixo(proxy, "creditos", 0)
    assert undo_stack.count() == 1
    assert list(proxy.creditos) == ["B", "A", "C"]


def test_mover_repeated_para_baixo_quando_ultimo(qapp):
    """Garante que mover o último item para baixo não faz nada."""
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    controller.mover_repeated_para_baixo(proxy, "creditos", 2)
    assert undo_stack.count() == 0


def test_mover_repeated_para_cima_quando_primeiro(qapp):
    """Garante que mover o primeiro item para cima não faz nada."""
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    controller.mover_repeated_para_cima(proxy, "creditos", 0)
    assert undo_stack.count() == 0


def test_mover_repeated_quando_unico_elemento(qapp):
    """Garante que mover para cima ou para baixo num array de um elemento não faz nada."""
    croqui = Croqui()
    croqui.creditos.extend(["Unico"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    controller.mover_repeated_para_cima(proxy, "creditos", 0)
    assert undo_stack.count() == 0

    controller.mover_repeated_para_baixo(proxy, "creditos", 0)
    assert undo_stack.count() == 0


def test_croqui_controller_mover_repeated_para_posicao(qapp):
    """Garante que mover_repeated_para_posicao move o item ou ignora se índices forem iguais."""
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    controller.mover_repeated_para_posicao(proxy, "creditos", 1, 1)
    assert undo_stack.count() == 0

    controller.mover_repeated_para_posicao(proxy, "creditos", 0, 2)
    assert undo_stack.count() == 1
    assert list(proxy.creditos) == ["B", "C", "A"]

    undo_stack.undo()
    assert list(proxy.creditos) == ["A", "B", "C"]


def test_croqui_controller_adicionar_mapa_com_arquivo(qapp, tmp_path):
    from aresta_api.proto.generated.croqui_pb2 import Mapa
    from editor.commands.comandos_protobuf import CmdMacro

    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Mapa"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()
    proxy_setor = proxy.picos[0].setores_ou_grupos[0].setor.conteudo

    img_bytes = b"fake_webp_bytes"
    caminho_absoluto = tmp_path / "mapa.webp"
    novo_mapa = Mapa(caminho_imagem_mapa="imagens/mapa.webp")

    controller.adicionar_mapa_com_arquivo(
        proxy_setor, "mapas", 0, novo_mapa, caminho_absoluto, img_bytes
    )

    assert undo_stack.count() == 1
    cmd = undo_stack.command(0)
    assert isinstance(cmd, CmdMacro)
    assert len(proxy_setor.mapas) == 1
    assert model.obter_bytes_imagem("imagens/mapa.webp") == img_bytes



def test_croqui_controller_substituir_imagem(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    bytes_iniciais = b"antigo"
    bytes_novos = b"novo"
    model.definir_imagem_memoria("imagens/mapa.webp", bytes_iniciais)

    # Substitui a imagem
    controller.substituir_imagem("imagens/mapa.webp", bytes_novos)
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_novos
    assert undo_stack.count() == 1

    # Undo
    undo_stack.undo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_iniciais

    # Redo
    undo_stack.redo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_novos


def test_croqui_controller_alterar_campo_imagem(qapp):
    croqui = Croqui()
    croqui.caminho_thumbnail = "imagens/thumb_antiga.webp"
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    bytes_antigo = b"bytes_antigo"
    bytes_novo = b"bytes_novo"
    model.definir_imagem_memoria("imagens/thumb_antiga.webp", bytes_antigo)

    controller.alterar_campo_imagem(
        croqui,
        "caminho_thumbnail",
        "imagens/thumb_antiga.webp",
        bytes_antigo,
        "imagens/thumb_nova.webp",
        bytes_novo,
    )
    assert croqui.caminho_thumbnail == "imagens/thumb_nova.webp"
    assert model.obter_bytes_imagem("imagens/thumb_nova.webp") == bytes_novo

    undo_stack.undo()
    assert croqui.caminho_thumbnail == "imagens/thumb_antiga.webp"
    assert model.obter_bytes_imagem("imagens/thumb_antiga.webp") == bytes_antigo


def test_croqui_controller_alterar_repeated_item(qapp):
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    pico_novo = Pico(nome="Pico 1 Modificado")
    controller.alterar_repeated_item(croqui, "picos", 0, pico, pico_novo)
    assert croqui.picos[0].nome == "Pico 1 Modificado"

    undo_stack.undo()
    assert croqui.picos[0].nome == "Pico 1"


def test_croqui_controller_alterar_multiplos_repeated_items(qapp):
    """Verifica a alteração simultânea de múltiplos itens repeated com undo/redo."""
    croqui = Croqui()
    croqui.creditos.extend(["Autor 1", "Autor 2", "Autor 3"])
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    # Lista vazia não deve empilhar comando
    controller.alterar_multiplos_repeated_items(proxy, "creditos", [])
    assert undo_stack.count() == 0

    alteracoes = [
        (0, "Autor 1", "Autor A"),
        (2, "Autor 3", "Autor C"),
    ]
    controller.alterar_multiplos_repeated_items(proxy, "creditos", alteracoes)
    assert undo_stack.count() == 1
    assert list(proxy.creditos) == ["Autor A", "Autor 2", "Autor C"]

    undo_stack.undo()
    assert list(proxy.creditos) == ["Autor 1", "Autor 2", "Autor 3"]

    undo_stack.redo()
    assert list(proxy.creditos) == ["Autor A", "Autor 2", "Autor C"]


def test_croqui_controller_grupo_undo_macro(qapp):
    """Verifica que iniciar_grupo_undo e finalizar_grupo_undo agrupam comandos em um único CmdMacro."""
    from editor.commands.comandos_protobuf import CmdMacro

    croqui = Croqui(nome="Original")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)
    proxy = model.obter_croqui_readonly()

    # Finalizar sem iniciar não faz nada
    controller.finalizar_grupo_undo()
    assert undo_stack.count() == 0

    # Iniciar e finalizar vazio não empilha macro vazio
    controller.iniciar_grupo_undo("Macro Vazia")
    controller.finalizar_grupo_undo()
    assert undo_stack.count() == 0

    # Macro com múltiplos comandos e sub-macro aninhado
    controller.iniciar_grupo_undo("Lote MCP")
    controller.alterar_primitivo(proxy, "nome", "Original", "Novo Nome")
    controller.iniciar_grupo_undo("Sub-lote")
    controller.adicionar_repeated(proxy, "creditos", 0, "Crédito 1")
    controller.finalizar_grupo_undo()
    # Enquanto o macro externo está aberto, nada foi para a pilha principal ainda
    assert undo_stack.count() == 0
    assert proxy.nome == "Novo Nome"
    assert list(proxy.creditos) == ["Crédito 1"]

    controller.finalizar_grupo_undo()
    assert undo_stack.count() == 1
    cmd_topo = undo_stack.command(0)
    assert isinstance(cmd_topo, CmdMacro)
    assert cmd_topo.text() == "Lote MCP"

    # Um único undo reverte todas as operações do macro
    undo_stack.undo()
    assert proxy.nome == "Original"
    assert len(proxy.creditos) == 0

    # Um único redo reaplica todas as operações
    undo_stack.redo()
    assert proxy.nome == "Novo Nome"
    assert list(proxy.creditos) == ["Crédito 1"]


def test_croqui_controller_grava_no_diario_com_gerenciador_historico(qapp, tmp_path):
    from editor.core.diario import GerenciadorDiario
    from editor.core.historico import GerenciadorHistorico

    croqui = Croqui(nome="Original")
    model = CroquiModel(croqui)
    diario = GerenciadorDiario(tmp_path)
    historico = GerenciadorHistorico(diario=diario)

    controller = CroquiController(model, historico)
    proxy = model.obter_croqui_readonly()

    # Executa mutação pelo controller
    controller.alterar_primitivo(proxy, "nome", "Original", "Modificado")

    assert proxy.nome == "Modificado"
    assert diario.tem_alteracoes_pendentes()
    comandos_pendentes = diario.ler_diario_pendente()
    assert len(comandos_pendentes) == 1
    assert comandos_pendentes[0]["classe"] == "CmdAlterarCampo"
    assert comandos_pendentes[0]["valor_novo"] == "Modificado"


def test_croqui_controller_alterar_primitivo_escalada_cria_cmd_renomear_escalada(qapp):
    from aresta_api.proto.generated import croqui_pb2
    from editor.commands.comandos_protobuf import CmdAlterarCampo

    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor 1"

    esc = setor.escaladas.add()
    esc.uid = "via_1"
    esc.via_esportiva.nome = "Via Inicial"

    mapa = setor.mapas.add()
    ref = mapa.referencias.add(alvo_uid="via_1", pontos_uids=["linha_1"])

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy_via = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.escaladas[0]
        .via_esportiva
    )
    proxy_ref = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.mapas[0]
        .referencias[0]
    )

    # Altera o nome da via pelo alterar_primitivo
    controller.alterar_primitivo(
        proxy_via, "nome", "Via Inicial", "Via Renomeada", pode_mesclar=True, session_id=42
    )

    # Verifica que o comando gerado foi CmdAlterarCampo
    cmd = undo_stack.command(0)
    assert isinstance(cmd, CmdAlterarCampo)
    assert cmd.session_id == 42
    assert proxy_via.nome == "Via Renomeada"
    assert proxy_ref.alvo_uid == "via_1"
    assert (
        resolver_caminho_referencia(model.obter_croqui_readonly(), proxy_ref)
        == "Setor 1 > Via Renomeada"
    )

    # Undo
    undo_stack.undo()
    assert proxy_via.nome == "Via Inicial"
    assert proxy_ref.alvo_uid == "via_1"
    assert (
        resolver_caminho_referencia(model.obter_croqui_readonly(), proxy_ref)
        == "Setor 1 > Via Inicial"
    )


def test_croqui_controller_renomear_escalada_direto(qapp):
    from aresta_api.proto.generated import croqui_pb2
    from editor.commands.comandos_protobuf import CmdAlterarCampo

    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor 1"

    esc = setor.escaladas.add()
    esc.uid = "boulder_1"
    esc.boulder.nome = "Boulder 1"

    mapa = setor.mapas.add()
    ref = mapa.referencias.add(alvo_uid="boulder_1", pontos_uids=["linha_b"])

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy_boulder = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.escaladas[0]
        .boulder
    )
    proxy_ref = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.mapas[0]
        .referencias[0]
    )

    controller.renomear_escalada(
        proxy_boulder, "Boulder 1", "Boulder Novo", pode_mesclar=False, session_id=10
    )

    cmd = undo_stack.command(0)
    assert isinstance(cmd, CmdAlterarCampo)
    assert cmd.session_id == 10
    assert proxy_boulder.nome == "Boulder Novo"
    assert proxy_ref.alvo_uid == "boulder_1"
    assert (
        resolver_caminho_referencia(model.obter_croqui_readonly(), proxy_ref)
        == "Setor 1 > Boulder Novo"
    )

    # Renomeação subsequente na mesma sessão via renomear_escalada direto
    controller.renomear_escalada(
        proxy_boulder, "Boulder Novo", "Boulder Mesclado", pode_mesclar=True, session_id=20
    )
    controller.renomear_escalada(
        proxy_boulder, "Boulder Mesclado", "Boulder Final", pode_mesclar=True, session_id=20
    )
    assert undo_stack.count() == 2
    assert proxy_boulder.nome == "Boulder Final"


def test_croqui_controller_inserir_imagem_markdown(qapp):
    from editor.commands.comandos_protobuf import CmdMacro

    croqui = Croqui()
    croqui.descricao = "Descricao antes"
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()
    controller.inserir_imagem_markdown(
        proxy,
        "descricao",
        "Descricao antes",
        "Descricao antes\n![Foto](imagens/via.webp)",
        caminho_imagem="imagens/via.webp",
        bytes_imagem=b"bytes_da_imagem",
    )

    assert proxy.descricao == "Descricao antes\n![Foto](imagens/via.webp)"
    assert model.obter_imagens_em_memoria().get("imagens/via.webp") == b"bytes_da_imagem"
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdMacro)

    undo_stack.undo()
    assert proxy.descricao == "Descricao antes"
    assert "imagens/via.webp" not in model.obter_imagens_em_memoria()


def test_croqui_controller_inserir_botao_markdown(qapp):
    from editor.commands.comandos_protobuf import CmdMacro

    croqui = Croqui()
    croqui.descricao = "Texto base"
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy = model.obter_croqui_readonly()
    controller.inserir_botao_markdown(
        proxy,
        "descricao",
        "Texto base",
        "Texto base\n[Guia PDF](anexos/guia.pdf)",
        caminho_anexo="anexos/guia.pdf",
        bytes_anexo=b"pdf_bytes",
    )

    assert proxy.descricao == "Texto base\n[Guia PDF](anexos/guia.pdf)"
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdMacro)

    undo_stack.undo()
    assert proxy.descricao == "Texto base"



def test_croqui_controller_alterar_primitivo_escalada_mescla_mesma_sessao(qapp):
    """Garante que digitações consecutivas com mesmo session_id mesclam no mesmo CmdAlterarCampo."""
    from aresta_api.proto.generated import croqui_pb2

    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor 1"

    esc = setor.escaladas.add()
    esc.uid = "via_1"
    esc.via_esportiva.nome = "Via Inicial"

    esc2 = setor.escaladas.add()
    esc2.uid = "via_2"
    esc2.via_esportiva.nome = "Via Outra"

    mapa = setor.mapas.add()
    ref = mapa.referencias.add(alvo_uid="via_1", pontos_uids=["linha_1"])

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy_via = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.escaladas[0]
        .via_esportiva
    )
    proxy_via2 = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.escaladas[1]
        .via_esportiva
    )
    proxy_ref = (
        model.obter_croqui_readonly()
        .picos[0]
        .setores_ou_grupos[0]
        .setor.conteudo.mapas[0]
        .referencias[0]
    )

    # 1ª digitação: Inicializa sessão com session_id=99
    controller.alterar_primitivo(
        proxy_via, "nome", "Via Inicial", "Via A", pode_mesclar=True, session_id=99
    )
    assert undo_stack.count() == 1
    assert proxy_via.nome == "Via A"
    assert (
        resolver_caminho_referencia(model.obter_croqui_readonly(), proxy_ref) == "Setor 1 > Via A"
    )

    # 2ª digitação consecutiva: mesmo session_id e mesma via -> mescla
    controller.alterar_primitivo(
        proxy_via, "nome", "Via A", "Via AB", pode_mesclar=True, session_id=99
    )
    assert undo_stack.count() == 1
    assert proxy_via.nome == "Via AB"
    assert (
        resolver_caminho_referencia(model.obter_croqui_readonly(), proxy_ref) == "Setor 1 > Via AB"
    )

    # Mesmo session_id mas outra via -> não reutiliza topo da primeira via
    controller.alterar_primitivo(
        proxy_via2, "nome", "Via Outra", "Via Outra 2", pode_mesclar=True, session_id=99
    )
    assert undo_stack.count() == 2
    assert proxy_via2.nome == "Via Outra 2"

    # 3ª digitação: nova sessão (ex: mudou de campo ou perdeu foco e voltou)
    controller.alterar_primitivo(
        proxy_via, "nome", "Via AB", "Via ABC", pode_mesclar=True, session_id=100
    )
    assert undo_stack.count() == 3
    assert proxy_via.nome == "Via ABC"

    # Quando o topo da pilha é outro comando (não CmdAlterarCampo), cria novo CmdAlterarCampo
    controller.alterar_primitivo(proxy_via, "extensao", 0, 25)
    controller.alterar_primitivo(
        proxy_via, "nome", "Via ABC", "Via ABCD", pode_mesclar=True, session_id=100
    )
    assert undo_stack.count() == 5
    assert proxy_via.nome == "Via ABCD"


def test_croqui_controller_migrar_setor(qapp):
    """Testa que controller despacha CmdMacro na pilha de undo."""
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Central"

    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Savassinha"
    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Vale Oculto"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    controller.migrar_setor(
        pai_origem=pico,
        campo_origem="setores_ou_grupos",
        indice_origem=0,
        pai_destino=sg_grupo.grupo.conteudo,
        campo_destino="setores",
        indice_destino=0,
        caminho_novo="grupo_vale_oculto_setor_savassinha.md",
        caminho_antigo="setor_savassinha.md",
    )

    assert undo_stack.count() == 1
    assert len(pico.setores_ou_grupos) == 1
    assert len(sg_grupo.grupo.conteudo.setores) == 1


def test_croqui_controller_comandos_individuais_e_migracao_reversa(qapp):
    """Cobre branches de comando único (len==1) e migração de Grupo para Pico."""
    from aresta_api.proto.generated.croqui_pb2 import Mapa

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Grupo 1"
    setor_grupo = sg_grupo.grupo.conteudo.setores.add()
    setor_grupo.conteudo.nome = "Setor no Grupo"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 1. alterar_campo_imagem com len(comandos) == 1 (só altera caminho, bytes_novo é None)
    controller.alterar_campo_imagem(
        croqui, "caminho_thumbnail", "", None, "thumb.webp", None
    )
    assert croqui.caminho_thumbnail == "thumb.webp"

    # 2. inserir_imagem_markdown sem bytes
    controller.inserir_imagem_markdown(croqui, "descricao", "", "Novo Markdown")
    assert croqui.descricao == "Novo Markdown"

    # 3. inserir_botao_markdown sem bytes
    controller.inserir_botao_markdown(croqui, "descricao", "Novo Markdown", "Botao Markdown")
    assert croqui.descricao == "Botao Markdown"

    # 4. alterar_multiplos_repeated_items com apenas 1 item
    croqui.creditos.append("Antigo")
    controller.alterar_multiplos_repeated_items(croqui, "creditos", [(0, "Antigo", "Novo")])
    assert croqui.creditos[0] == "Novo"

    # 5. adicionar_mapa_com_arquivo sem bytes
    mapa = Mapa(caminho_imagem_mapa="mapa.webp")
    controller.adicionar_mapa_com_arquivo(
        setor_grupo.conteudo, "mapas", 0, mapa, None, None
    )
    assert len(setor_grupo.conteudo.mapas) == 1

    # 6. migrar_setor de Grupo para Pico (campo_origem != setores_ou_grupos e campo_destino == setores_ou_grupos)
    controller.migrar_setor(
        pai_origem=sg_grupo.grupo.conteudo,
        campo_origem="setores",
        indice_origem=0,
        pai_destino=pico,
        campo_destino="setores_ou_grupos",
        indice_destino=1,
        caminho_novo="setor_migrado.md",
    )
    assert len(sg_grupo.grupo.conteudo.setores) == 0
    assert len(pico.setores_ou_grupos) == 2
    assert pico.setores_ou_grupos[1].setor.conteudo.nome == "Setor no Grupo"


def test_croqui_controller_alterar_campo_unico_e_lote_atomico(qapp):
    """Valida alterar_campo canônico com campo único, lote atômico via CmdMacro e rejeição fail-fast."""
    import pytest
    from editor.commands.comandos_protobuf import CmdAlterarCampo, CmdMacro

    croqui = Croqui(nome="Inicial", descricao="Desc Inicial")
    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 1. Chamada vazia não empilha comando
    controller.alterar_campo(croqui)
    controller.alterar_campo(croqui, campos={})
    assert undo_stack.count() == 0

    # 2. Campo único empilha CmdAlterarCampo direto
    controller.alterar_campo(croqui, campo_nome="nome", valor_novo="Modificado")
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdAlterarCampo)
    assert croqui.nome == "Modificado"
    undo_stack.undo()
    assert croqui.nome == "Inicial"

    # 3. Lote de múltiplos campos empilha 1 CmdMacro e reverte atomicamente
    controller.alterar_campo(
        croqui,
        campos={"nome": "Nome Lote", "descricao": "Desc Lote", "publicar_croqui": True},
    )
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdMacro)
    assert croqui.nome == "Nome Lote"
    assert croqui.descricao == "Desc Lote"
    assert croqui.publicar_croqui is True

    undo_stack.undo()
    assert croqui.nome == "Inicial"
    assert croqui.descricao == "Desc Inicial"
    assert croqui.publicar_croqui is False

    # 4. Erro em qualquer campo do lote aborta antes de empilhar ou alterar qualquer campo
    with pytest.raises(TypeError):
        controller.alterar_campo(
            croqui,
            campos={"nome": "Nao Deve Aplicar", "ultima_migracao": "tipo_invalido"},
        )
    assert croqui.nome == "Inicial"
    assert not undo_stack.canUndo()

