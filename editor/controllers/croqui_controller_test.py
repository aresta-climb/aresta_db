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
    from editor.commands.comandos_protobuf import CmdMacro

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

    # adicionar_multiplos_repeated: lista vazia não empilha, 1 item empilha direto, N itens empilham CmdMacro
    controller.adicionar_multiplos_repeated(proxy, "creditos", 0, [])
    assert undo_stack.index() == 0

    controller.adicionar_multiplos_repeated(proxy, "creditos", 0, ["Autor Único"])
    assert undo_stack.count() == 1
    assert list(proxy.creditos) == ["Autor Único"]
    undo_stack.undo()
    assert list(proxy.creditos) == []

    controller.adicionar_multiplos_repeated(proxy, "creditos", 0, ["Autor 1", "Autor 2", "Autor 3"])
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdMacro)
    assert list(proxy.creditos) == ["Autor 1", "Autor 2", "Autor 3"]
    undo_stack.undo()
    assert list(proxy.creditos) == []


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
    controller.alterar_campo_imagem(croqui, "caminho_thumbnail", "", None, "thumb.webp", None)
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
    controller.adicionar_mapa_com_arquivo(setor_grupo.conteudo, "mapas", 0, mapa, None, None)
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


def test_croqui_controller_alterar_campo_substituicao_declarativa_repeated(qapp):
    """Valida que alterar_campo substitui listas repeated atomicamente preservando UIDs e imagens em RAM."""
    from aresta_api.proto.generated import croqui_pb2
    from editor.commands.comandos_protobuf import CmdMacro

    croqui = croqui_pb2.Croqui(nome="Croqui Base")
    croqui.creditos.extend(["Antigo 1", "Antigo 2"])
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "setor_uid_1"
    setor.nome = "Setor Original"

    esc1 = setor.escaladas.add(uid="esc_fixo_1")
    esc1.via_esportiva.nome = "Via Antiga"

    mapa_mantido = setor.mapas.add(caminho_imagem_mapa="imagens/mantido.webp")
    poi_orig = mapa_mantido.pontos_de_interesse.add(uid="poi_fixo_1", rotulo="1")
    poi_orig.circulo.x = 10
    poi_orig.circulo.y = 20
    poi_orig.circulo.raio = 15
    setor.mapas.add(caminho_imagem_mapa="imagens/orfao.webp")

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/mantido.webp", b"bytes_mantido")
    model.definir_imagem_memoria("imagens/orfao.webp", b"bytes_orfao")
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 1. Substituição de lista vazia por lista vazia não empilha comando
    controller.alterar_campo(croqui, campo_nome="botoes", valor_novo=[])
    assert undo_stack.count() == 0

    # 2. Substituição de lista repeated primitiva (creditos)
    controller.alterar_campo(
        croqui, campo_nome="creditos", valor_novo=["Novo A", "Novo B", "Novo C"]
    )
    assert undo_stack.count() == 1
    assert list(croqui.creditos) == ["Novo A", "Novo B", "Novo C"]
    undo_stack.undo()
    assert list(croqui.creditos) == ["Antigo 1", "Antigo 2"]
    undo_stack.redo()
    assert list(croqui.creditos) == ["Novo A", "Novo B", "Novo C"]

    # 3. Substituição em lote de Setor com escaladas e mapas (preservando UID existente e gerando novo)
    nova_esc_1 = croqui_pb2.Escalada(uid="esc_fixo_1")
    nova_esc_1.via_esportiva.nome = "Via Atualizada"
    nova_esc_2 = croqui_pb2.Escalada()
    nova_esc_2.boulder.nome = "Boulder Novo Sem UID"

    novo_mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/mantido.webp")
    poi_preservado = novo_mapa.pontos_de_interesse.add(uid="poi_fixo_1", rotulo="1")
    poi_preservado.circulo.x = 100
    poi_preservado.circulo.y = 200
    poi_preservado.circulo.raio = 15
    poi_novo = novo_mapa.pontos_de_interesse.add(rotulo="2")
    poi_novo.circulo.x = 300
    poi_novo.circulo.y = 400
    poi_novo.circulo.raio = 15

    controller.alterar_campo(
        "setor_uid_1",
        campos={
            "nome": "Setor Substituido",
            "escaladas": [nova_esc_1, nova_esc_2],
            "mapas": [novo_mapa],
        },
    )
    assert undo_stack.count() == 2
    assert isinstance(undo_stack.command(1), CmdMacro)
    assert setor.nome == "Setor Substituido"
    assert len(setor.escaladas) == 2
    assert setor.escaladas[0].uid == "esc_fixo_1"
    assert setor.escaladas[0].via_esportiva.nome == "Via Atualizada"
    assert len(setor.escaladas[1].uid) == 14
    assert setor.escaladas[1].boulder.nome == "Boulder Novo Sem UID"
    assert len(setor.mapas) == 1
    assert setor.mapas[0].pontos_de_interesse[0].uid == "poi_fixo_1"
    assert len(setor.mapas[0].pontos_de_interesse[1].uid) == 14
    # A imagem mantida continua na RAM; a imagem órfã foi removida
    assert model.obter_bytes_imagem("imagens/mantido.webp") == b"bytes_mantido"
    assert model.obter_bytes_imagem("imagens/orfao.webp") is None

    # Undo reverte todo o lote em um único passo
    undo_stack.undo()
    assert setor.nome == "Setor Original"
    assert len(setor.escaladas) == 1
    assert setor.escaladas[0].via_esportiva.nome == "Via Antiga"
    assert len(setor.mapas) == 2
    assert model.obter_bytes_imagem("imagens/orfao.webp") == b"bytes_orfao"


def test_croqui_controller_substituir_imagem_mapa_com_reescala_pois_e_undo(qapp):
    """Valida substituição atômica de imagem de mapa com atualização de resolução, reescala de POIs e Undo único."""
    from aresta_api.proto.generated import croqui_pb2

    croqui = croqui_pb2.Croqui(nome="Croqui Mapa")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.uid = "setor_uid_1"
    mapa = sg.setor.conteudo.mapas.add(
        caminho_imagem_mapa="imagens/mapa_antigo.webp",
        largura_mapa=1000,
        altura_mapa=500,
    )
    poi = mapa.pontos_de_interesse.add(uid="poi_1", rotulo="1")
    poi.circulo.x = 200
    poi.circulo.y = 100
    poi.circulo.raio = 20

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/mapa_antigo.webp", b"bytes_antigos")
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]

    # 1. Substituir por nova imagem com dobro da resolução e reescalar POIs
    controller.substituir_imagem_mapa(
        msg_mapa=proxy_mapa,
        caminho_relativo_novo="imagens/mapa_novo.webp",
        bytes_novo=b"bytes_novos",
        largura_nova=2000,
        altura_nova=1000,
        reescalar_pois=True,
    )

    assert undo_stack.count() == 1
    assert mapa.caminho_imagem_mapa == "imagens/mapa_novo.webp"
    assert mapa.largura_mapa == 2000
    assert mapa.altura_mapa == 1000
    assert mapa.pontos_de_interesse[0].circulo.x == 400
    assert mapa.pontos_de_interesse[0].circulo.y == 200
    assert mapa.pontos_de_interesse[0].circulo.raio == 40
    assert model.obter_bytes_imagem("imagens/mapa_novo.webp") == b"bytes_novos"

    # 2. Um único Undo reverte caminho, dimensões, POIs e imagem em RAM
    undo_stack.undo()
    assert mapa.caminho_imagem_mapa == "imagens/mapa_antigo.webp"
    assert mapa.largura_mapa == 1000
    assert mapa.altura_mapa == 500
    assert mapa.pontos_de_interesse[0].circulo.x == 200
    assert mapa.pontos_de_interesse[0].circulo.y == 100
    assert mapa.pontos_de_interesse[0].circulo.raio == 20
    assert model.obter_bytes_imagem("imagens/mapa_novo.webp") is None

    # 3. Substituir mantendo mesma resolução e mesmo caminho (apenas bytes novos) empilha 1 comando
    controller.substituir_imagem_mapa(
        msg_mapa="setor_uid_1.mapas.0",
        caminho_relativo_novo="imagens/mapa_antigo.webp",
        bytes_novo=b"bytes_atualizados",
        largura_nova=1000,
        altura_nova=500,
        reescalar_pois=False,
    )
    assert model.obter_bytes_imagem("imagens/mapa_antigo.webp") == b"bytes_atualizados"
    assert mapa.pontos_de_interesse[0].circulo.x == 200
    undo_stack.undo()
    assert model.obter_bytes_imagem("imagens/mapa_antigo.webp") == b"bytes_antigos"

    # 4. Chamada sem nenhuma alteração efetiva não empilha comando
    count_antes = undo_stack.count()
    controller.substituir_imagem_mapa(
        msg_mapa=proxy_mapa,
        caminho_relativo_novo="imagens/mapa_antigo.webp",
        bytes_novo=None,
        largura_nova=1000,
        altura_nova=500,
        reescalar_pois=False,
    )
    assert undo_stack.count() == count_antes


def test_croqui_controller_migrar_escalada_preserva_uid_e_imagens_ram(qapp):
    """Valida que migrar_escalada move uma Escalada entre setores via CmdMacro, preservando UID e imagens em RAM."""
    import pytest

    from aresta_api.proto.generated import croqui_pb2
    from editor.commands.comandos_protobuf import CmdMacro

    croqui = croqui_pb2.Croqui(nome="Croqui Migracao")
    pico = croqui.picos.add(nome="Pico 1")

    sg1 = pico.setores_ou_grupos.add()
    setor1 = sg1.setor.conteudo
    setor1.uid = "setor_1_uid"
    setor1.nome = "Setor 1"

    sg2 = pico.setores_ou_grupos.add()
    setor2 = sg2.setor.conteudo
    setor2.uid = "setor_2_uid"
    setor2.nome = "Setor 2"

    esc_a = setor1.escaladas.add(uid="esc_uid_a")
    esc_a.via_esportiva.nome = "Via A"
    esc_a.via_esportiva.descricao = "![Foto](imagens/via_a.webp)"

    esc_b = setor1.escaladas.add(uid="esc_uid_b")
    esc_b.via_movel.nome = "Meio Cubanos"

    esc_c = setor2.escaladas.add(uid="esc_uid_c")
    esc_c.via_esportiva.nome = "Via C"

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/via_a.webp", b"bytes_via_a")
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 1. Migrar esc_a (com imagem em RAM) do setor1[0] para o final do setor2 (indice_destino omitido/-1)
    controller.migrar_escalada(
        setor_origem=setor1,
        indice_origem=0,
        setor_destino="setor_2_uid",
    )
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdMacro)
    assert len(setor1.escaladas) == 1
    assert setor1.escaladas[0].uid == "esc_uid_b"
    assert len(setor2.escaladas) == 2
    assert setor2.escaladas[1].uid == "esc_uid_a"
    assert setor2.escaladas[1].via_esportiva.nome == "Via A"
    assert model.obter_bytes_imagem("imagens/via_a.webp") == b"bytes_via_a"

    # Um único Undo reverte a migração mantendo a imagem em RAM e o UID original
    undo_stack.undo()
    assert len(setor1.escaladas) == 2
    assert setor1.escaladas[0].uid == "esc_uid_a"
    assert len(setor2.escaladas) == 1
    assert model.obter_bytes_imagem("imagens/via_a.webp") == b"bytes_via_a"

    # 2. Migrar com indice_destino explícito (0) usando UIDs de setores
    controller.migrar_escalada(
        setor_origem="setor_1_uid",
        indice_origem=1,
        setor_destino="setor_2_uid",
        indice_destino=0,
    )
    assert len(setor1.escaladas) == 1
    assert setor2.escaladas[0].uid == "esc_uid_b"
    assert setor2.escaladas[0].via_movel.nome == "Meio Cubanos"

    # 3. Migrar dentro do mesmo setor reordena sem perder itens
    controller.migrar_escalada(
        setor_origem=setor2,
        indice_origem=0,
        setor_destino=setor2,
        indice_destino=1,
    )
    assert [e.uid for e in setor2.escaladas] == ["esc_uid_c", "esc_uid_b"]

    # 4. Índice fora de alcance lança IndexError sem empilhar comando
    with pytest.raises(IndexError):
        controller.migrar_escalada(
            setor_origem=setor1,
            indice_origem=99,
            setor_destino=setor2,
        )


def test_croqui_controller_alterar_em_lote_multi_alvo_atomico(qapp):
    """Valida que alterar_em_lote aplica mutações em múltiplos alvos em 1 CmdMacro com fail-fast."""
    import pytest

    from aresta_api.proto.generated import croqui_pb2
    from editor.commands.comandos_protobuf import CmdAlterarCampo, CmdMacro

    croqui = croqui_pb2.Croqui(uid="croqui_uid", nome="Croqui Inicial")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "setor_uid"
    setor.nome = "Setor 1"
    esc1 = setor.escaladas.add(uid="via_1_uid")
    esc1.via_esportiva.nome = "Via 1"
    esc2 = setor.escaladas.add(uid="via_2_uid")
    esc2.via_esportiva.nome = "Via 2"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 1. Lista vazia ou operações sem campos não empilham comandos
    controller.alterar_em_lote([])
    controller.alterar_em_lote([{"alvo": "croqui_uid", "campos": {}}])
    assert undo_stack.count() == 0

    # 2. Lote com apenas 1 comando (usando chave 'campo'/'valor') empilha o comando diretamente
    controller.alterar_em_lote([{"alvo": "croqui_uid", "campo": "nome", "valor": "Croqui Único"}])
    assert undo_stack.count() == 1
    assert isinstance(undo_stack.command(0), CmdAlterarCampo)
    assert croqui.nome == "Croqui Único"
    undo_stack.undo()
    assert croqui.nome == "Croqui Inicial"

    # 3. Lote multi-alvo empilha 1 único CmdMacro e reverte tudo em 1 Undo
    controller.alterar_em_lote(
        [
            {"alvo": "croqui_uid", "campos": {"nome": "Croqui Lote", "creditos": ["Autor 1"]}},
            {
                "alvo": "via_1_uid",
                "campos": {
                    "nome": "Via 1 Nova",
                    "dificuldade": croqui_pb2.GrauVia.BR_8A,
                },
            },
            {
                "alvo": "via_2_uid",
                "campos": {
                    "nome": "Via 2 Nova",
                    "data_abertura": "1997",
                },
            },
        ],
        texto_macro="Atualizar Lote Lapinha",
    )
    assert undo_stack.count() == 1
    cmd_macro = undo_stack.command(0)
    assert isinstance(cmd_macro, CmdMacro)
    assert cmd_macro.text() == "Atualizar Lote Lapinha"
    assert croqui.nome == "Croqui Lote"
    assert list(croqui.creditos) == ["Autor 1"]
    assert esc1.via_esportiva.nome == "Via 1 Nova"
    assert esc1.via_esportiva.dificuldade == croqui_pb2.GrauVia.BR_8A
    assert esc2.via_esportiva.nome == "Via 2 Nova"
    assert esc2.via_esportiva.data_abertura == "1997"

    undo_stack.undo()
    assert croqui.nome == "Croqui Inicial"
    assert list(croqui.creditos) == []
    assert esc1.via_esportiva.nome == "Via 1"
    assert esc2.via_esportiva.nome == "Via 2"

    # 4. Erro na última operação do lote aborta antes de tocar no modelo (fail-fast)
    with pytest.raises(ValueError, match="não existe"):
        controller.alterar_em_lote(
            [
                {"alvo": "via_1_uid", "campos": {"nome": "Nao Deve Persistir"}},
                {"alvo": "via_2_uid", "campos": {"campo_invalido": 123}},
            ]
        )
    assert esc1.via_esportiva.nome == "Via 1"
    assert not undo_stack.canUndo()


def test_croqui_controller_ciclo_completo_curadoria_betas_undo_redo(qapp):
    """
    Valida que todas as transições 1 a 1 da curadoria de betas (coleta em betas_nao_scorados,
    promoção para betas_nao_revisados, aprovação para escalada.betas, rejeição para
    betas_rejeitados e restauração) operam via comandos reversíveis no QUndoStack.
    """
    import pytest

    from aresta_api.proto.generated import beta_pb2, croqui_pb2

    croqui = croqui_pb2.Croqui(uid="croqui_uid", nome="Croqui Betas")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "setor_uid"
    setor.nome = "Setor 1"
    esc = setor.escaladas.add(uid="esc_1")
    esc.via_esportiva.nome = "Via Clássica"

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    c1 = beta_pb2.CandidatoMidiaBeta()
    c1.midia.url = "https://www.youtube.com/watch?v=vid1"
    c1.midia.titulo = "Vídeo 1"
    c1.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
    c1.snippets.append("Snippet 1")

    c2 = beta_pb2.CandidatoMidiaBeta()
    c2.midia.url = "https://blogescalada.com/via-classica"
    c2.midia.titulo = "Post no Blog"
    c2.midia.fonte = beta_pb2.FonteMidia.BLOG
    c2.snippets.append("Snippet Blog")

    # 1. Adicionar candidatos em betas_nao_scorados (cria entrada CuradoriaBetasEscalada sob demanda)
    adicionados = controller.adicionar_candidatos_nao_scorados("esc_1", [c1, c2])
    assert adicionados == 2
    assert undo_stack.count() == 1
    curadoria_esc = croqui.curadoria_betas.conteudo.escaladas[0]
    assert curadoria_esc.escalada_uid == "esc_1"
    assert len(curadoria_esc.betas_nao_scorados) == 2

    # Tentar adicionar novamente as mesmas URLs ignora duplicatas e não empilha comando
    assert controller.adicionar_candidatos_nao_scorados("esc_1", [c1]) == 0
    assert undo_stack.count() == 1

    # Undo e Redo da coleta
    undo_stack.undo()
    assert len(croqui.curadoria_betas.conteudo.escaladas) == 0
    undo_stack.redo()
    curadoria_esc = croqui.curadoria_betas.conteudo.escaladas[0]
    assert len(curadoria_esc.betas_nao_scorados) == 2

    # 2. Promover c1 (índice 0) para betas_nao_revisados com score 85 e c2 (agora índice 0) com score 95
    controller.promover_candidato_para_nao_revisado("esc_1", 0, 85, "Bom vídeo")
    controller.promover_candidato_para_nao_revisado("esc_1", 0, 95, "Relato detalhado")
    assert len(curadoria_esc.betas_nao_scorados) == 0
    assert len(curadoria_esc.betas_nao_revisados) == 2
    # Ordenados por score decrescente (95 primeiro, 85 depois)
    assert curadoria_esc.betas_nao_revisados[0].resultado_llm.llm_confidence_score == 95
    assert curadoria_esc.betas_nao_revisados[1].resultado_llm.llm_confidence_score == 85

    undo_stack.undo()
    assert len(curadoria_esc.betas_nao_scorados) == 1
    assert len(curadoria_esc.betas_nao_revisados) == 1
    undo_stack.redo()

    # 3. Aprovar 1 a 1 o primeiro candidato de betas_nao_revisados (Post no Blog, score 95)
    controller.aprovar_beta_curadoria("esc_1", "betas_nao_revisados", 0)
    assert len(esc.betas) == 1
    assert esc.betas[0].url == "https://blogescalada.com/via-classica"
    assert esc.betas[0].fonte == beta_pb2.FonteMidia.BLOG
    assert len(curadoria_esc.betas_nao_revisados) == 1

    undo_stack.undo()
    assert len(esc.betas) == 0
    assert len(curadoria_esc.betas_nao_revisados) == 2
    undo_stack.redo()

    # 4. Rejeitar 1 a 1 o candidato restante em betas_nao_revisados (Vídeo 1)
    controller.rejeitar_beta_curadoria("esc_1", "betas_nao_revisados", 0)
    assert len(curadoria_esc.betas_nao_revisados) == 0
    assert len(curadoria_esc.betas_rejeitados) == 1
    assert curadoria_esc.betas_rejeitados[0].url == "https://youtube.com/watch?v=vid1"

    undo_stack.undo()
    assert len(curadoria_esc.betas_nao_revisados) == 1
    assert len(curadoria_esc.betas_rejeitados) == 0
    undo_stack.redo()

    # 5. Restaurar beta rejeitado de volta para betas_nao_scorados
    controller.restaurar_beta_rejeitado("esc_1", 0)
    assert len(curadoria_esc.betas_rejeitados) == 0
    assert len(curadoria_esc.betas_nao_scorados) == 1
    assert curadoria_esc.betas_nao_scorados[0].midia.url == "https://youtube.com/watch?v=vid1"

    undo_stack.undo()
    assert len(curadoria_esc.betas_rejeitados) == 1
    assert len(curadoria_esc.betas_nao_scorados) == 0
    undo_stack.redo()

    # 6. Também permite rejeitar um beta já aprovado em escalada.betas (movendo para betas_rejeitados)
    controller.rejeitar_beta_curadoria("esc_1", "betas", 0)
    assert len(esc.betas) == 0
    assert len(curadoria_esc.betas_rejeitados) == 1
    assert curadoria_esc.betas_rejeitados[0].url == "https://blogescalada.com/via-classica"

    # 7. Adicionar betas auto-rejeitados em lote (adicionar_betas_rejeitados_lote) com deduplicação e Undo/Redo
    m_rej_novo = beta_pb2.MidiaBeta(
        url="https://pt.scribd.com/document/123/Croqui-PDF",
        titulo="[Query: geral | Auto-filtrado: domínio bloqueado] Croqui PDF",
        fonte=beta_pb2.FonteMidia.BLOG,
    )
    m_rej_dup = beta_pb2.MidiaBeta(
        url="https://blogescalada.com/via-classica",
        titulo="Duplicata já rejeitada",
        fonte=beta_pb2.FonteMidia.BLOG,
    )
    rej_adicionados = controller.adicionar_betas_rejeitados_lote("esc_1", [m_rej_novo, m_rej_dup])
    assert rej_adicionados == 1
    assert len(curadoria_esc.betas_rejeitados) == 2
    assert curadoria_esc.betas_rejeitados[1].titulo.startswith(
        "[Query: geral | Auto-filtrado: domínio bloqueado]"
    )
    assert controller.adicionar_betas_rejeitados_lote("esc_1", [m_rej_novo]) == 0
    undo_stack.undo()
    assert len(curadoria_esc.betas_rejeitados) == 1
    undo_stack.redo()
    assert len(curadoria_esc.betas_rejeitados) == 2

    # Validação de erro para origem inválida ou escalada inexistente
    with pytest.raises(ValueError):
        controller.aprovar_beta_curadoria("esc_1", "origem_invalida", 0)
    with pytest.raises(KeyError):
        controller.aprovar_beta_curadoria("uid_inexistente", "betas_nao_scorados", 0)
    with pytest.raises(IndexError):
        controller.promover_candidato_para_nao_revisado("esc_1", 99, 50, "Fora")
    with pytest.raises(IndexError):
        controller.aprovar_beta_curadoria("esc_1", "betas_nao_scorados", 99)
    with pytest.raises(ValueError):
        controller.rejeitar_beta_curadoria("esc_1", "origem_invalida", 0)
    with pytest.raises(IndexError):
        controller.rejeitar_beta_curadoria("esc_1", "betas", 99)
    with pytest.raises(IndexError):
        controller.rejeitar_beta_curadoria("esc_1", "betas_nao_scorados", 99)
    with pytest.raises(IndexError):
        controller.restaurar_beta_rejeitado("esc_1", 99)

    esc_sem_curadoria = setor.escaladas.add(uid="esc_sem_cur")
    esc_sem_curadoria.via_esportiva.nome = "Sem Curadoria"
    with pytest.raises(IndexError):
        controller.aprovar_beta_curadoria("esc_sem_cur", "betas_nao_scorados", 0)
    with pytest.raises(IndexError):
        controller.rejeitar_beta_curadoria("esc_sem_cur", "betas_nao_scorados", 0)


def test_croqui_controller_aprovar_e_rejeitar_betas_nao_revisados_por_score_em_lote(qapp):
    """Valida aprovação (>= Y) e rejeição (< X) em lote por score da LLM com Undo/Redo atômico."""
    from aresta_api.proto.generated import beta_pb2, croqui_pb2

    croqui = croqui_pb2.Croqui(uid="croqui_lote_score")
    setor = croqui.picos.add(nome="Pico 1").setores_ou_grupos.add().setor.conteudo
    setor.uid = "setor_1"
    esc1 = setor.escaladas.add(uid="esc_1")
    esc1.via_esportiva.nome = "Via 1"
    esc2 = setor.escaladas.add(uid="esc_2")
    esc2.via_esportiva.nome = "Via 2"

    cur1 = croqui.curadoria_betas.conteudo.escaladas.add(escalada_uid="esc_1")
    for score, url in [(95, "https://yt.com/v95"), (80, "https://yt.com/v80"), (40, "https://yt.com/v40")]:
        c = cur1.betas_nao_revisados.add()
        c.midia.url = url
        c.midia.titulo = f"T {score}"
        c.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
        c.resultado_llm.llm_confidence_score = score

    cur2 = croqui.curadoria_betas.conteudo.escaladas.add(escalada_uid="esc_2")
    for score, url in [(85, "https://ig.com/p85"), (20, "https://ig.com/p20")]:
        c = cur2.betas_nao_revisados.add()
        c.midia.url = url
        c.midia.titulo = f"T {score}"
        c.midia.fonte = beta_pb2.FonteMidia.INSTAGRAM
        c.resultado_llm.llm_confidence_score = score

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # Sem itens correspondentes retorna 0 sem empilhar comando
    assert controller.aprovar_betas_nao_revisados_por_score(99) == 0
    assert controller.rejeitar_betas_nao_revisados_por_score(10) == 0
    assert undo_stack.count() == 0

    # Aprova >= 80 filtrando apenas esc_1 (2 itens: 95 e 80) em um único comando Undo
    aprovados_esc1 = controller.aprovar_betas_nao_revisados_por_score(80, escalada_uid="esc_1")
    assert aprovados_esc1 == 2
    assert undo_stack.count() == 1
    assert [b.url for b in esc1.betas] == ["https://yt.com/v95", "https://yt.com/v80"]
    assert len(cur1.betas_nao_revisados) == 1
    assert len(esc2.betas) == 0

    # Undo reverte ambos os itens aprovados de uma vez
    undo_stack.undo()
    assert len(esc1.betas) == 0
    assert len(cur1.betas_nao_revisados) == 3
    undo_stack.redo()
    assert len(esc1.betas) == 2

    # Rejeita < 80 globalmente em todas as escaladas (v40 em esc_1 e p20 em esc_2)
    rejeitados_global = controller.rejeitar_betas_nao_revisados_por_score(80)
    assert rejeitados_global == 2
    assert undo_stack.count() == 2
    assert len(cur1.betas_nao_revisados) == 0
    assert [r.url for r in cur1.betas_rejeitados] == ["https://yt.com/v40"]
    assert len(cur2.betas_nao_revisados) == 1
    assert [r.url for r in cur2.betas_rejeitados] == ["https://ig.com/p20"]

    undo_stack.undo()
    assert len(cur1.betas_nao_revisados) == 1
    assert len(cur1.betas_rejeitados) == 0
    assert len(cur2.betas_nao_revisados) == 2
    assert len(cur2.betas_rejeitados) == 0


def test_croqui_controller_preservar_campos_compativeis_na_troca_de_oneof(qapp):
    """Valida que preservar_campos_compativeis=True copia campos homônimos compatíveis ao trocar variante oneof."""
    from aresta_api.proto.generated import croqui_pb2

    croqui = croqui_pb2.Croqui(uid="croqui_oneof")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "setor_oneof"

    esc = setor.escaladas.add(uid="via_oneof_1")
    esc.via_esportiva.nome = "Meio Cubanos"
    esc.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP
    esc.via_esportiva.extensao = 25
    esc.via_esportiva.conquistadores.extend(["Autor 1", "Autor 2"])

    model = CroquiModel(croqui)
    undo_stack = QUndoStack()
    controller = CroquiController(model, undo_stack)

    # 1. Com preservar_campos_compativeis=False (padrão), não copia campos não informados
    controller.alterar_campo(
        "via_oneof_1",
        campo_nome="via_movel",
        valor_novo=croqui_pb2.ViaMovel(nome="Apenas Nome"),
    )
    assert esc.WhichOneof("tipo") == "via_movel"
    assert esc.via_movel.nome == "Apenas Nome"
    assert not esc.via_movel.HasField("extensao")
    assert list(esc.via_movel.conquistadores) == []
    undo_stack.undo()
    assert esc.WhichOneof("tipo") == "via_esportiva"

    # 2. Com preservar_campos_compativeis=True trocando via_esportiva -> via_movel
    nova_movel = croqui_pb2.ViaMovel(descricao="Fenda clássica")
    controller.alterar_campo(
        "via_oneof_1",
        campo_nome="via_movel",
        valor_novo=nova_movel,
        preservar_campos_compativeis=True,
    )
    assert esc.WhichOneof("tipo") == "via_movel"
    assert esc.via_movel.nome == "Meio Cubanos"
    assert esc.via_movel.dificuldade == croqui_pb2.GrauVia.BR_6SUP
    assert esc.via_movel.extensao == 25
    assert list(esc.via_movel.conquistadores) == ["Autor 1", "Autor 2"]
    assert esc.via_movel.descricao == "Fenda clássica"

    undo_stack.undo()
    assert esc.WhichOneof("tipo") == "via_esportiva"
    assert esc.via_esportiva.extensao == 25

    # 3. Troca via_esportiva -> boulder via tupla de oneof ("tipo") em alterar_em_lote:
    # dificuldade (GrauVia vs GrauBoulder) é ignorada por incompatibilidade de enum, mas nome e conquistadores são copiados
    novo_boulder = croqui_pb2.Boulder(conquistadores=["Sobrescrito"])
    controller.alterar_em_lote(
        [
            {
                "alvo": esc,
                "campos": {
                    "tipo": ("boulder", novo_boulder),
                    "uid": "via_oneof_1",
                },
                "preservar_campos_compativeis": True,
            }
        ]
    )
    assert esc.WhichOneof("tipo") == "boulder"
    assert esc.boulder.nome == "Meio Cubanos"
    assert not esc.boulder.HasField("dificuldade")
    assert list(esc.boulder.conquistadores) == ["Sobrescrito"]
