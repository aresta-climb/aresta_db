# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais dos comandos legados do histórico (editor/commands/comandos_legados.py).
Garante que comandos descontinuados continuem suportando Undo, Redo, serialização e deserialização
para preservar a retrocompatibilidade com arquivos diario_pendente.bin e diario_salvo.bin existentes.
"""

import io

from PIL import Image
from PySide6.QtGui import QUndoStack

from aresta_api.proto.generated import croqui_pb2
from aresta_api.proto.generated.croqui_pb2 import (
    ArquivoGrupo,
    ArquivoSetor,
    Croqui,
    Setor,
    ViaEsportiva,
)
from editor.commands.comandos_legados import (
    COMANDOS_LEGADOS_MAP,
    CmdAdicionarMapaArquivo,
    CmdAlterarCampoImagem,
    CmdAlterarMetadadosCaminhoNovo,
    CmdAlterarMultiplosRepeatedItems,
    CmdAlterarOneof,
    CmdAlterarPrimitivo,
    CmdAlterarRepeatedItem,
    CmdInserirBotaoMarkdown,
    CmdInserirImagemMarkdown,
    CmdMigrarSetor,
    CmdRenomearEscalada,
    CmdSubstituirImagemMemoria,
)
from editor.commands.comandos_protobuf import deserializar_comando
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import ReadOnlyProxy


def _gerar_bytes_imagem_webp() -> bytes:
    """Gera bytes de uma imagem WebP válida em memória para testes."""
    buf = io.BytesIO()
    img = Image.new("RGB", (20, 20), color="blue")
    img.save(buf, format="WEBP")
    return buf.getvalue()


def test_mapa_comandos_legados_completo():
    """Garante que as 12 classes legadas constam no mapa de deserialização de comandos legados."""
    esperadas = {
        "CmdAlterarPrimitivo",
        "CmdAlterarOneof",
        "CmdAlterarRepeatedItem",
        "CmdAlterarMultiplosRepeatedItems",
        "CmdMigrarSetor",
        "CmdAlterarMetadadosCaminhoNovo",
        "CmdAlterarCampoImagem",
        "CmdSubstituirImagemMemoria",
        "CmdInserirImagemMarkdown",
        "CmdInserirBotaoMarkdown",
        "CmdAdicionarMapaArquivo",
        "CmdRenomearEscalada",
    }
    assert set(COMANDOS_LEGADOS_MAP.keys()) == esperadas


def test_cmd_alterar_primitivo_undo_redo_e_merge():
    """Valida CmdAlterarPrimitivo com strings, strings vazias, valores nulos e mergeWith."""
    croqui = Croqui()
    croqui.nome = "Antigo Nome"
    model = CroquiModel(croqui)

    foco_requisitado = []
    model.foco_requisitado.connect(lambda ctx: foco_requisitado.append(ctx))

    cmd = CmdAlterarPrimitivo(
        model,
        croqui,
        "nome",
        "Antigo Nome",
        "Novo Nome",
        context_path="pico.nome",
        pode_mesclar=True,
    )
    assert cmd.id() == CmdAlterarPrimitivo.ID_COMANDO
    cmd.redo()
    assert croqui.nome == "Novo Nome"

    cmd.undo()
    assert croqui.nome == "Antigo Nome"
    assert "pico.nome" in foco_requisitado

    # mergeWith bem-sucedido
    cmd2 = CmdAlterarPrimitivo(
        model,
        croqui,
        "nome",
        "Novo Nome",
        "Nome Mesclado",
        context_path="pico.nome2",
        pode_mesclar=True,
    )
    assert cmd.mergeWith(cmd2) is True
    assert croqui.nome == "Nome Mesclado"

    # mergeWith rejeitado (campos ou caminhos diferentes, ou sem permissão de mescla)
    cmd_outro_campo = CmdAlterarPrimitivo(model, croqui, "descricao", "", "Desc", pode_mesclar=True)
    assert cmd.mergeWith(cmd_outro_campo) is False

    cmd_outro_nao_mesclavel = CmdAlterarPrimitivo(
        model, croqui, "nome", "A", "B", pode_mesclar=False
    )
    assert cmd.mergeWith(cmd_outro_nao_mesclavel) is False

    cmd_sem_mescla = CmdAlterarPrimitivo(model, croqui, "nome", "A", "B", pode_mesclar=False)
    assert cmd_sem_mescla.id() == -1
    assert cmd_sem_mescla.mergeWith(cmd) is False

    # Outro tipo de comando no mergeWith com pode_mesclar=True (linha 75)
    cmd_outro_tipo_mesclavel = CmdAlterarRepeatedItem(
        model, croqui, "creditos", 0, "A", "B", pode_mesclar=True
    )
    assert cmd.mergeWith(cmd_outro_tipo_mesclavel) is False

    # Esvaziar string (remove campo do Protobuf)
    setor = Setor()
    setor.nome = "Setor Estacionamento"
    model_setor = CroquiModel(setor)
    cmd_vazio = CmdAlterarPrimitivo(model_setor, setor, "nome", "Setor Estacionamento", "")
    cmd_vazio.redo()
    assert not setor.HasField("nome")
    cmd_vazio.undo()
    assert setor.HasField("nome")
    assert setor.nome == "Setor Estacionamento"

    # Booleano tri-state para None
    setor.sinal_de_celular = True
    cmd_bool = CmdAlterarPrimitivo(model_setor, setor, "sinal_de_celular", True, None)
    cmd_bool.redo()
    assert not setor.HasField("sinal_de_celular")
    cmd_bool.undo()
    assert setor.sinal_de_celular is True

    # Inteiro nullable para 0
    via = ViaEsportiva()
    model_via = CroquiModel(via)
    cmd_int = CmdAlterarPrimitivo(model_via, via, "extensao", None, 0)
    cmd_int.redo()
    assert via.HasField("extensao")
    assert via.extensao == 0
    cmd_int.undo()
    assert not via.HasField("extensao")


def test_cmd_alterar_primitivo_caminho_inexistente_e_deserializacao():
    """Valida resolução com caminho_msg inexistente e deserialização."""
    croqui = Croqui(nome="Original")
    model = CroquiModel(croqui)

    cmd_invalido = CmdAlterarPrimitivo(
        model=model,
        caminho_msg="caminho.inexistente",
        campo_nome="nome",
        valor_novo="X",
        pode_mesclar=True,
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()
    cmd2 = CmdAlterarPrimitivo(
        model=model,
        caminho_msg="caminho.inexistente",
        campo_nome="nome",
        valor_novo="Y",
        pode_mesclar=True,
    )
    assert cmd_invalido.mergeWith(cmd2) is False

    cmd = CmdAlterarPrimitivo(
        model, croqui, "nome", "Original", "Modificado", context_path="campo.nome"
    )
    dados = cmd.serializar()
    assert dados["classe"] == "CmdAlterarPrimitivo"
    assert dados["campo_nome"] == "nome"
    assert dados["valor_novo"] == "Modificado"

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarPrimitivo)
    cmd_recriado.redo()
    assert croqui.nome == "Modificado"
    cmd_recriado.undo()
    assert croqui.nome == "Original"


def test_cmd_alterar_oneof():
    """Valida alteração de opções de oneof, undo, redo, serialização e deserialização."""
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    model = CroquiModel(croqui)

    setor = ArquivoSetor(caminho="caminho/setor.md")
    cmd1 = CmdAlterarOneof(model, sg, "tipo", None, None, "setor", setor, context_path="sg.0")
    cmd1.redo()
    assert sg.WhichOneof("tipo") == "setor"
    assert sg.setor.caminho == "caminho/setor.md"

    cmd1.undo()
    assert sg.WhichOneof("tipo") is None

    # Muda para grupo
    grupo = ArquivoGrupo(caminho="caminho/grupo.md")
    cmd2 = CmdAlterarOneof(model, sg, "tipo", "setor", setor, "grupo", grupo, context_path="sg.0")
    cmd2.redo()
    assert sg.WhichOneof("tipo") == "grupo"
    assert not sg.HasField("setor")

    cmd2.undo()
    assert sg.WhichOneof("tipo") == "setor"

    # Serialização e deserialização
    dados = cmd2.serializar()
    assert dados["classe"] == "CmdAlterarOneof"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarOneof)
    cmd_recriado.executar_redo()
    assert sg.WhichOneof("tipo") == "grupo"

    # Caminho inválido
    cmd_invalido = CmdAlterarOneof(
        model=model, caminho_msg="caminho.inexistente", oneof_nome="tipo"
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_alterar_repeated_item():
    """Valida alteração pontual em item de repeated, undo, redo, serialização, merge e erros."""
    croqui = Croqui()
    croqui.creditos.append("Renato")
    model = CroquiModel(croqui)

    cmd = CmdAlterarRepeatedItem(
        model, croqui, "creditos", 0, "Renato", "Silva", context_path="cred.0", pode_mesclar=True
    )
    assert cmd.id() == CmdAlterarRepeatedItem.ID_COMANDO
    cmd.redo()
    assert list(croqui.creditos) == ["Silva"]

    # mergeWith
    cmd2 = CmdAlterarRepeatedItem(
        model, croqui, "creditos", 0, "Silva", "Silveira", context_path="cred.0", pode_mesclar=True
    )
    assert cmd.mergeWith(cmd2) is True
    assert list(croqui.creditos) == ["Silveira"]

    # mergeWith rejeitado
    cmd_outro = CmdAlterarRepeatedItem(model, croqui, "creditos", 1, "A", "B", pode_mesclar=True)
    assert cmd.mergeWith(cmd_outro) is False

    # Outro tipo de comando no mergeWith com pode_mesclar=True (linha 253)
    cmd_outro_tipo = CmdAlterarPrimitivo(model, croqui, "nome", "A", "B", pode_mesclar=True)
    assert cmd.mergeWith(cmd_outro_tipo) is False

    cmd_sem_mescla = CmdAlterarRepeatedItem(
        model, croqui, "creditos", 0, "A", "B", pode_mesclar=False
    )
    assert cmd_sem_mescla.id() == -1
    assert cmd_sem_mescla.mergeWith(cmd) is False
    assert cmd.mergeWith(cmd_sem_mescla) is False

    cmd.undo()
    assert list(croqui.creditos) == ["Renato"]

    dados = cmd.serializar()
    assert dados["classe"] == "CmdAlterarRepeatedItem"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarRepeatedItem)
    cmd_recriado.executar_redo()
    assert list(croqui.creditos) == ["Silveira"]

    # Caminho inválido
    cmd_invalido = CmdAlterarRepeatedItem(
        model=model,
        caminho_msg="caminho.inexistente",
        campo_nome="creditos",
        index=0,
        pode_mesclar=True,
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()
    cmd_invalido2 = CmdAlterarRepeatedItem(
        model=model,
        caminho_msg="caminho.inexistente",
        campo_nome="creditos",
        index=0,
        pode_mesclar=True,
    )
    assert cmd_invalido.mergeWith(cmd_invalido2) is False


def test_cmd_alterar_multiplos_repeated_items():
    """Valida alteração múltipla em lista repeated, undo, redo, serialização e deserialização."""
    croqui = Croqui()
    croqui.creditos.extend(["Um", "Dois", "Tres"])
    model = CroquiModel(croqui)

    alteracoes = [(0, "Um", "NovoUm"), (2, "Tres", "NovoTres")]
    cmd = CmdAlterarMultiplosRepeatedItems(
        model, croqui, "creditos", alteracoes, context_path="cred.mult"
    )
    cmd.redo()
    assert list(croqui.creditos) == ["NovoUm", "Dois", "NovoTres"]

    cmd.undo()
    assert list(croqui.creditos) == ["Um", "Dois", "Tres"]

    dados = cmd.serializar()
    assert dados["classe"] == "CmdAlterarMultiplosRepeatedItems"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarMultiplosRepeatedItems)
    cmd_recriado.executar_redo()
    assert list(croqui.creditos) == ["NovoUm", "Dois", "NovoTres"]

    # Caminho inválido
    cmd_invalido = CmdAlterarMultiplosRepeatedItems(
        model=model, caminho_msg="caminho.inexistente", campo_nome="creditos"
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_alterar_metadados_caminho_novo():
    """Valida alteração de extensões Protobuf de metadados, undo, redo, serialização e deserialização."""
    croqui = Croqui()
    sg = croqui.picos.add().setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor 1"
    model = CroquiModel(croqui)

    cmd = CmdAlterarMetadadosCaminhoNovo(
        model=model,
        msg=sg.setor,
        field_ext=croqui_pb2.ArquivoSetor.ext_metadados_arquivo,
        valor_antigo="",
        valor_novo="novo_caminho.md",
        context_path="setor.ext",
    )
    cmd.redo()
    assert (
        sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo
        == "novo_caminho.md"
    )

    cmd.undo()
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == ""

    dados = cmd.serializar()
    assert dados["classe"] == "CmdAlterarMetadadosCaminhoNovo"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarMetadadosCaminhoNovo)
    cmd_recriado.executar_redo()
    assert (
        sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo
        == "novo_caminho.md"
    )

    # Deserialização sem containing_type (linha 629)
    dados_sem_tipo = dict(dados)
    dados_sem_tipo.pop("containing_type", None)
    cmd_sem_tipo = deserializar_comando(dados_sem_tipo, model)
    assert isinstance(cmd_sem_tipo, CmdAlterarMetadadosCaminhoNovo)

    # Caminho inválido
    cmd_invalido = CmdAlterarMetadadosCaminhoNovo(
        model=model,
        caminho_msg="caminho.inexistente",
        field_ext=croqui_pb2.ArquivoSetor.ext_metadados_arquivo,
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_alterar_campo_imagem():
    """Valida alteração de campo de imagem e buffer em RAM, anonimização e deserialização."""
    croqui = Croqui()
    croqui.caminho_thumbnail = "imagens/antiga.webp"
    model = CroquiModel(croqui)

    bytes_novos = _gerar_bytes_imagem_webp()
    bytes_antigos = _gerar_bytes_imagem_webp()
    cmd = CmdAlterarCampoImagem(
        model=model,
        msg=croqui,
        campo_nome="caminho_thumbnail",
        caminho_antigo="imagens/antiga.webp",
        bytes_antigo=bytes_antigos,
        caminho_novo="imagens/nova.webp",
        bytes_novo=bytes_novos,
        context_path="thumb",
    )

    cmd.redo()
    assert croqui.caminho_thumbnail == "imagens/nova.webp"
    assert model.obter_bytes_imagem("imagens/nova.webp") == bytes_novos

    cmd.undo()
    assert croqui.caminho_thumbnail == "imagens/antiga.webp"
    assert model.obter_bytes_imagem("imagens/antiga.webp") == bytes_antigos

    # Serialização normal e anonimizada
    dados = cmd.serializar(anonimizado=False)
    assert dados["classe"] == "CmdAlterarCampoImagem"
    assert dados["bytes_novo"] == bytes_novos

    dados_anon = cmd.serializar(anonimizado=True)
    assert dados_anon["bytes_novo"] != bytes_novos

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarCampoImagem)
    cmd_recriado.executar_redo()
    assert croqui.caminho_thumbnail == "imagens/nova.webp"

    # Caminho inválido
    cmd_invalido = CmdAlterarCampoImagem(
        model=model, caminho_msg="caminho.inexistente", campo_nome="caminho_thumbnail"
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_substituir_imagem_memoria():
    """Valida substituição direta de buffer na memória RAM do modelo, merge e anonimização."""
    croqui = Croqui()
    model = CroquiModel(croqui)

    bytes_antigos = _gerar_bytes_imagem_webp()
    bytes_novos = _gerar_bytes_imagem_webp()
    model.definir_imagem_memoria("imagens/mapa.webp", bytes_antigos)

    cmd = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="imagens/mapa.webp",
        bytes_antigo=bytes_antigos,
        bytes_novo=bytes_novos,
        context_path="mapa.ram",
        pode_mesclar=True,
    )
    assert cmd.id() == CmdSubstituirImagemMemoria.ID_COMANDO

    cmd.redo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_novos

    # mergeWith
    bytes_mais_novos = _gerar_bytes_imagem_webp()
    cmd2 = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="imagens/mapa.webp",
        bytes_antigo=bytes_novos,
        bytes_novo=bytes_mais_novos,
        context_path="mapa.ram2",
        pode_mesclar=True,
    )
    assert cmd.mergeWith(cmd2) is True
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_mais_novos

    # mergeWith rejeitado (outro caminho)
    cmd_outro = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="outra.webp",
        bytes_antigo=None,
        bytes_novo=bytes_mais_novos,
        pode_mesclar=True,
    )
    assert cmd.mergeWith(cmd_outro) is False

    # Outro tipo de comando no mergeWith com pode_mesclar=True (linha 768)
    cmd_outro_tipo = CmdAlterarPrimitivo(model, croqui, "nome", "A", "B", pode_mesclar=True)
    assert cmd.mergeWith(cmd_outro_tipo) is False

    cmd_sem_mescla = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="imagens/mapa.webp",
        bytes_antigo=None,
        bytes_novo=bytes_mais_novos,
        pode_mesclar=False,
    )
    assert cmd_sem_mescla.id() == -1
    assert cmd_sem_mescla.mergeWith(cmd) is False
    assert cmd.mergeWith(cmd_sem_mescla) is False

    cmd.undo()
    assert model.obter_bytes_imagem("imagens/mapa.webp") == bytes_antigos

    # Undo quando bytes_antigo é None (remove imagem)
    cmd_novo = CmdSubstituirImagemMemoria(
        model=model,
        caminho_relativo="imagens/nova_direta.webp",
        bytes_antigo=None,
        bytes_novo=bytes_novos,
    )
    cmd_novo.redo()
    assert model.obter_bytes_imagem("imagens/nova_direta.webp") == bytes_novos
    cmd_novo.undo()
    assert model.obter_bytes_imagem("imagens/nova_direta.webp") is None

    # Serialização com anonimização
    dados = cmd.serializar(anonimizado=True)
    assert dados["classe"] == "CmdSubstituirImagemMemoria"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdSubstituirImagemMemoria)


def test_cmd_inserir_imagem_markdown():
    """Valida inserção de tag Markdown com persistência em RAM de imagem e anonimização."""
    croqui = Croqui()
    setor = croqui.picos.add().setores_ou_grupos.add().setor.conteudo
    setor.descricao = "Descricao inicial."
    model = CroquiModel(croqui)

    bytes_img = _gerar_bytes_imagem_webp()
    cmd = CmdInserirImagemMarkdown(
        model=model,
        msg=setor,
        campo_nome="descricao",
        texto_antigo="Descricao inicial.",
        texto_novo="Descricao inicial.\n![Foto](img_md.webp)",
        caminho_imagem="img_md.webp",
        bytes_imagem=bytes_img,
        context_path="desc",
    )

    cmd.redo()
    assert "![Foto](img_md.webp)" in setor.descricao
    assert model.obter_bytes_imagem("img_md.webp") == bytes_img

    cmd.undo()
    assert setor.descricao == "Descricao inicial."
    assert model.obter_bytes_imagem("img_md.webp") is None

    # Serialização com anonimização
    dados = cmd.serializar(anonimizado=True)
    assert dados["classe"] == "CmdInserirImagemMarkdown"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdInserirImagemMarkdown)
    cmd_recriado.executar_redo()
    assert model.obter_bytes_imagem("img_md.webp") is not None

    # Caminho inválido
    cmd_invalido = CmdInserirImagemMarkdown(
        model=model, caminho_msg="caminho.inexistente", campo_nome="descricao"
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_inserir_botao_markdown():
    """Valida inserção de botão/link Markdown e anexo em RAM."""
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.descricao = "Descricao antiga."
    model = CroquiModel(croqui)

    bytes_anexo = b"%PDF-1.4 dummy pdf bytes"
    cmd = CmdInserirBotaoMarkdown(
        model=model,
        msg=pico,
        campo_nome="descricao",
        texto_antigo="Descricao antiga.",
        texto_novo="Descricao antiga.\n[Guia de Acesso](guia.pdf)",
        caminho_anexo="guia.pdf",
        bytes_anexo=bytes_anexo,
        context_path="desc.botao",
    )

    cmd.redo()
    assert "[Guia de Acesso](guia.pdf)" in pico.descricao
    assert model.obter_bytes_anexo("guia.pdf") == bytes_anexo

    cmd.undo()
    assert pico.descricao == "Descricao antiga."
    assert model.obter_bytes_anexo("guia.pdf") is None

    dados = cmd.serializar()
    assert dados["classe"] == "CmdInserirBotaoMarkdown"
    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdInserirBotaoMarkdown)
    cmd_recriado.executar_redo()
    assert model.obter_bytes_anexo("guia.pdf") == bytes_anexo

    # Caminho inválido
    cmd_invalido = CmdInserirBotaoMarkdown(
        model=model, caminho_msg="caminho.inexistente", campo_nome="descricao"
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_adicionar_mapa_arquivo(tmp_path):
    """Valida CmdAdicionarMapaArquivo com adição a repeated e registro de imagem em RAM."""
    croqui = Croqui()
    setor = croqui.picos.add().setores_ou_grupos.add().setor.conteudo
    setor.nome = "Setor Principal"
    model = CroquiModel(croqui)

    mapa = croqui_pb2.Mapa()
    mapa.caminho_imagem_mapa = "imagens/mapa1.webp"
    mapa.largura_mapa = 800
    mapa.altura_mapa = 600

    img_bytes = _gerar_bytes_imagem_webp()
    caminho_abs = tmp_path / "mapa1.webp"
    caminho_abs.write_bytes(img_bytes)

    cmd = CmdAdicionarMapaArquivo(
        model=model,
        msg=setor,
        campo_nome="mapas",
        index=0,
        valor=mapa,
        caminho_absoluto=caminho_abs,
        img_bytes=img_bytes,
        context_path="setores.0.mapas",
    )

    cmd.redo()
    assert len(setor.mapas) == 1
    assert setor.mapas[0].caminho_imagem_mapa == "imagens/mapa1.webp"
    assert model.obter_bytes_imagem("imagens/mapa1.webp") == img_bytes

    cmd.undo()
    assert len(setor.mapas) == 0
    assert model.obter_bytes_imagem("imagens/mapa1.webp") is None

    # Serialização com e sem anonimização
    dados = cmd.serializar(anonimizado=False)
    assert dados["classe"] == "CmdAdicionarMapaArquivo"
    assert dados["img_bytes"] == img_bytes

    dados_anon = cmd.serializar(anonimizado=True)
    assert dados_anon["caminho_absoluto"] == "[ARQUIVO_MAPA_ANONIMIZADO]"

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAdicionarMapaArquivo)
    cmd_recriado.redo()
    assert len(setor.mapas) == 1

    # Caminho inválido
    cmd_invalido = CmdAdicionarMapaArquivo(
        model=model, caminho_msg="caminho.inexistente", campo_nome="mapas", valor=croqui_pb2.Mapa()
    )
    cmd_invalido.undo()
    cmd_invalido.executar_redo()


def test_cmd_migrar_setor():
    """Valida CmdMigrarSetor entre Pico e Grupo, com undo, redo, serialização, foco e casos de borda."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Central")

    sg_setor = pico.setores_ou_grupos.add()
    sg_setor.setor.conteudo.nome = "Setor Movel"
    sg_setor.setor.Extensions[
        croqui_pb2.ArquivoSetor.ext_metadados_arquivo
    ].caminho_original = "setor_movel.md"
    sg_setor.setor.Extensions[
        croqui_pb2.ArquivoSetor.ext_metadados_arquivo
    ].caminho_novo = "setor_movel.md"

    sg_grupo = pico.setores_ou_grupos.add()
    sg_grupo.grupo.conteudo.nome = "Grupo Alto"

    model = CroquiModel(croqui)
    pilha = QUndoStack()

    cmd = CmdMigrarSetor(
        model=model,
        pai_origem=ReadOnlyProxy(pico),
        campo_origem="setores_ou_grupos",
        indice_origem=0,
        pai_destino=ReadOnlyProxy(sg_grupo.grupo.conteudo),
        campo_destino="setores",
        indice_destino=0,
        caminho_novo="grupo_alto_setor_movel.md",
        caminho_antigo="setor_movel.md",
        context_path="destino.0",
    )
    dados = cmd.serializar()
    pilha.push(cmd)

    assert len(pico.setores_ou_grupos) == 1
    assert len(sg_grupo.grupo.conteudo.setores) == 1
    assert (
        sg_grupo.grupo.conteudo.setores[0]
        .Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo]
        .caminho_novo
        == "grupo_alto_setor_movel.md"
    )

    pilha.undo()
    assert len(pico.setores_ou_grupos) == 2
    assert len(sg_grupo.grupo.conteudo.setores) == 0

    pilha.redo()
    assert len(pico.setores_ou_grupos) == 1
    assert len(sg_grupo.grupo.conteudo.setores) == 1

    # Deserialização e execução em modelo correspondente
    pilha.undo()
    assert len(pico.setores_ou_grupos) == 2

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdMigrarSetor)
    assert cmd_recriado.caminho_novo == "grupo_alto_setor_movel.md"
    cmd_recriado.executar_redo()
    assert len(pico.setores_ou_grupos) == 1
    cmd_recriado.undo()
    assert len(pico.setores_ou_grupos) == 2

    # Casos de borda: pai inexistente e model None
    cmd_borda = CmdMigrarSetor(
        model=model,
        caminho_msg_origem="caminho.invalido",
        caminho_msg_destino="caminho.invalido",
    )
    assert cmd_borda.pai_origem is None
    cmd_borda.undo()
    cmd_borda.executar_redo()

    cmd_borda.model = None
    assert cmd_borda._obter_pai(None, "_cache") is None

    # Raiz vazia ("")
    cmd_borda.model = model
    assert cmd_borda._obter_pai("", "_cache_raiz") == croqui

    # Construtor com origem e destino vazios (linhas 441 e 450)
    cmd_sem_pais = CmdMigrarSetor(
        model=model,
        pai_origem=None,
        caminho_msg_origem=None,
        pai_destino=None,
        caminho_msg_destino=None,
    )
    assert cmd_sem_pais.caminho_msg_origem is None
    assert cmd_sem_pais.caminho_msg_destino is None

    # Destino reverso (Grupo para Pico)
    sg_grupo.grupo.conteudo.setores.add().conteudo.nome = "Setor Grupo"
    cmd_reverso = CmdMigrarSetor(
        model=model,
        pai_origem=sg_grupo.grupo.conteudo,
        campo_origem="setores",
        indice_origem=0,
        pai_destino=pico,
        campo_destino="setores_ou_grupos",
        indice_destino=0,
        caminho_novo="setor_grupo.md",
    )
    cmd_reverso.executar_redo()
    assert len(sg_grupo.grupo.conteudo.setores) == 0
    cmd_reverso.undo()
    assert len(sg_grupo.grupo.conteudo.setores) == 1


def test_cmd_renomear_escalada():
    """Valida CmdRenomearEscalada com sincronização, mergeWith por session_id e deserialização."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    via = setor.escaladas.add().via_esportiva
    via.nome = "Nome Antigo"

    mapa = setor.mapas.add()
    ref = mapa.referencias.add()

    model = CroquiModel(croqui)

    cmd = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Nome Antigo",
        nome_novo="Nome Novo",
        referencias=[ref],
        session_id=123,
        context_path="via.nome",
        pode_mesclar=True,
    )
    assert cmd.id() == CmdRenomearEscalada.ID_COMANDO
    assert cmd.referencias == [ref]
    cmd.executar_redo()
    assert via.nome == "Nome Novo"

    cmd.undo()
    assert via.nome == "Nome Antigo"

    # mergeWith bem-sucedido
    cmd2 = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        campo_nome="nome",
        nome_antigo="Nome Novo",
        nome_novo="Nome Final",
        session_id=123,
        context_path="via.nome2",
        pode_mesclar=True,
    )
    assert cmd.mergeWith(cmd2) is True
    assert via.nome == "Nome Final"

    # mergeWith rejeitados
    cmd_outro_sessao = CmdRenomearEscalada(
        model=model, msg_escalada=via, nome_novo="X", session_id=999, pode_mesclar=True
    )
    assert cmd.mergeWith(cmd_outro_sessao) is False

    cmd_outro_campo = CmdRenomearEscalada(
        model=model,
        caminho_msg="caminho.falso",
        campo_nome="outro_campo",
        session_id=123,
        pode_mesclar=True,
    )
    assert cmd.mergeWith(cmd_outro_campo) is False

    # Outro tipo de comando no mergeWith com pode_mesclar=True (linha 1197)
    cmd_outro_tipo = CmdAlterarPrimitivo(model, croqui, "nome", "A", "B", pode_mesclar=True)
    assert cmd.mergeWith(cmd_outro_tipo) is False

    cmd_sem_mescla = CmdRenomearEscalada(
        model=model, msg_escalada=via, nome_novo="Y", session_id=123, pode_mesclar=False
    )
    assert cmd_sem_mescla.id() == -1
    assert cmd_sem_mescla.mergeWith(cmd) is False
    assert cmd.mergeWith(cmd_sem_mescla) is False

    # Construtor com caminho_msg e msg_escalada fornecidos simultaneamente (linha 1136)
    cmd_cache = CmdRenomearEscalada(
        model=model,
        msg_escalada=via,
        caminho_msg="picos.0.setores_ou_grupos.0.setor.conteudo.escaladas.0.via_esportiva",
    )
    assert cmd_cache._msg_cache is via

    # Serialização e deserialização com resolução lazy de referências
    dados = cmd.serializar()
    assert dados["classe"] == "CmdRenomearEscalada"
    assert dados["session_id"] == 123

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdRenomearEscalada)
    cmd_recriado._referencias_cache = []
    assert len(cmd_recriado.referencias) == 1
    assert cmd_recriado.referencias[0] == ref

    cmd_recriado.undo()
    assert via.nome == "Nome Antigo"
    cmd_recriado.executar_redo()
    assert via.nome == "Nome Final"

    # Caminho inválido
    cmd_invalido = CmdRenomearEscalada(
        model=model, caminho_msg="caminho.inexistente", session_id=123, pode_mesclar=True
    )
    assert cmd_invalido.msg_escalada is None
    cmd_invalido.undo()
    cmd_invalido.executar_redo()
    cmd_invalido2 = CmdRenomearEscalada(
        model=model, caminho_msg="caminho.inexistente", session_id=123, pode_mesclar=True
    )
    assert cmd_invalido.mergeWith(cmd_invalido2) is False

    cmd_sem_ref = CmdRenomearEscalada(model=model, caminho_msg="", caminhos_referencias=[])
    assert cmd_sem_ref.referencias == []
