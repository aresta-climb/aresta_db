# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
import logging

import pytest
from PIL import Image

from aresta_api.proto.generated import croqui_pb2
from aresta_api.proto.generated.croqui_pb2 import (
    Boulder,
    Coordenada,
    Croqui,
    Patrocinador,
    Pico,
    Trilha,
)
from editor.commands.comandos_protobuf import (
    CmdAdicionarRepeated,
    CmdAlterarAnexo,
    CmdAlterarCampo,
    CmdAlterarImagem,
    CmdMacro,
    CmdMoverRepeated,
    CmdRemoverRepeated,
    ComandoEditor,
    MensagemAlvoNaoEncontradaError,
    _buscar_mensagem_por_uid,
    _validar_campo_se_msg_existir,
    deserializar_comando,
    navegar_para_alvo,
    navegar_para_mensagem,
    resolver_alvo_mensagem,
    resolver_caminho_mensagem,
    validar_pertence_ao_croqui,
)
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import ReadOnlyProxy

# ==============================================================================
# 1. Testes de CmdAlterarCampo (Primitivos, UIDs, Merge, Oneof, Repeated Item)
# ==============================================================================


def test_cmd_alterar_campo_primitivo_e_renomeacao_com_merge():
    """Valida alteração de primitivos, renomeação com sincronização de UID e mergeWith."""
    croqui = Croqui(nome="Croqui Original")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_001"
    setor.nome = "Setor Antigo"

    esc = setor.escaladas.add(uid="esc_001")
    esc.via_esportiva.nome = "Via Velha"

    model = CroquiModel(croqui)

    # 1. Alteração com captura automática de valor_antigo
    cmd1 = CmdAlterarCampo(
        model=model,
        alvo=setor,
        campo_nome="nome",
        valor_novo="Setor Novo",
    )
    assert cmd1.valor_antigo == "Setor Antigo"
    cmd1.executar_redo()
    assert setor.nome == "Setor Novo"
    assert model.indice_uids.obter("set_001").nome_setor == "Setor Novo"

    cmd1.undo()
    assert setor.nome == "Setor Antigo"
    assert model.indice_uids.obter("set_001").nome_setor == "Setor Antigo"

    # 2. Renomeação de escalada via alvo str (UID)
    cmd_renomear = CmdAlterarCampo(
        model=model,
        alvo="esc_001",
        campo_nome="nome",
        valor_novo="Via Nova",
    )
    assert cmd_renomear.valor_antigo == "Via Velha"
    cmd_renomear.executar_redo()
    assert esc.via_esportiva.nome == "Via Nova"
    assert model.indice_uids.obter("esc_001").nome_escalada == "Via Nova"

    cmd_renomear.undo()
    assert esc.via_esportiva.nome == "Via Velha"
    assert model.indice_uids.obter("esc_001").nome_escalada == "Via Velha"

    # 3. Teste de mergeWith com session_id
    cmd_merge1 = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="A",
        pode_mesclar=True,
        session_id="sess_123",
    )
    cmd_merge1.executar_redo()
    assert pico.descricao == "A"

    cmd_merge2 = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="AB",
        pode_mesclar=True,
        session_id="sess_123",
    )
    assert cmd_merge1.mergeWith(cmd_merge2) is True
    assert pico.descricao == "AB"

    # Incompatibilidades de merge
    cmd_incompativel_session = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="ABC",
        pode_mesclar=True,
        session_id="sess_outra",
    )
    assert cmd_merge1.mergeWith(cmd_incompativel_session) is False

    cmd_incompativel_campo = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="nome",
        valor_novo="Outro",
        pode_mesclar=True,
        session_id="sess_123",
    )
    assert cmd_merge1.mergeWith(cmd_incompativel_campo) is False

    # Undo deve reverter para o estado anterior a toda a sessão
    cmd_merge1.undo()
    assert pico.descricao == ""


def test_cmd_alterar_campo_tipos_primitivos_e_nulos():
    """Valida alteração de primitivos opcionais/nulos (strings vazias, booleanos tri-state, inteiros)."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Estacionamento"
    setor.sinal_de_celular = True

    esc = setor.escaladas.add(uid="esc_002")
    via = esc.via_esportiva

    model = CroquiModel(croqui)

    # 1. Esvaziar string opcional limpa o campo no Protobuf
    cmd_str = CmdAlterarCampo(model, setor, "nome", "")
    cmd_str.executar_redo()
    assert not setor.HasField("nome")
    cmd_str.undo()
    assert setor.HasField("nome")
    assert setor.nome == "Setor Estacionamento"

    # 2. Booleano tri-state para None
    cmd_bool = CmdAlterarCampo(model, setor, "sinal_de_celular", None)
    cmd_bool.executar_redo()
    assert not setor.HasField("sinal_de_celular")
    cmd_bool.undo()
    assert setor.HasField("sinal_de_celular")
    assert setor.sinal_de_celular is True

    # 3. Inteiro nullable para 0 (presente!) e depois para None
    cmd_int = CmdAlterarCampo(model, via, "extensao", 0)
    cmd_int.executar_redo()
    assert via.HasField("extensao")
    assert via.extensao == 0
    cmd_int.undo()
    assert not via.HasField("extensao")


def test_cmd_alterar_campo_repeated_item_indexado():
    """Valida alteração de item indexado de lista repeated primitiva e composta."""
    croqui = Croqui()
    croqui.creditos.extend(["Credito 1", "Credito 2"])

    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_rep_001"
    setor.trilhas.add(nome="Trilha A", tempo_aproximacao="15min")

    model = CroquiModel(croqui)

    # 1. Item primitivo em repeated ("creditos.0")
    cmd_prim = CmdAlterarCampo(
        model=model,
        alvo=croqui,
        campo_nome="creditos.0",
        valor_novo="Credito Modificado",
    )
    assert cmd_prim.valor_antigo == "Credito 1"
    cmd_prim.executar_redo()
    assert croqui.creditos[0] == "Credito Modificado"

    cmd_prim.undo()
    assert croqui.creditos[0] == "Credito 1"

    # 2. Item composto em repeated ("trilhas.0")
    nova_trilha = Trilha(nome="Trilha B", tempo_aproximacao="25min")
    cmd_comp = CmdAlterarCampo(
        model=model,
        alvo="set_rep_001",
        campo_nome="trilhas.0",
        valor_novo=nova_trilha,
    )
    assert cmd_comp.valor_antigo.nome == "Trilha A"
    cmd_comp.executar_redo()
    assert setor.trilhas[0].nome == "Trilha B"
    assert setor.trilhas[0].tempo_aproximacao == "25min"

    cmd_comp.undo()
    assert setor.trilhas[0].nome == "Trilha A"
    assert setor.trilhas[0].tempo_aproximacao == "15min"


def test_cmd_alterar_campo_oneof_e_submensagem():
    """Valida alteração e reversão de oneofs e submensagens singulares."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_oneof_001"
    esc = setor.escaladas.add(uid="esc_oneof_001")
    esc.via_esportiva.nome = "Via Teste"

    model = CroquiModel(croqui)

    # 1. Oneof: troca de via_esportiva para boulder
    novo_boulder = Boulder(nome="Bloco Alpha")
    cmd_oneof = CmdAlterarCampo(
        model=model,
        alvo="esc_oneof_001",
        campo_nome="boulder",
        valor_novo=novo_boulder,
    )
    cmd_oneof.executar_redo()
    assert esc.WhichOneof("tipo") == "boulder"
    assert esc.boulder.nome == "Bloco Alpha"

    cmd_oneof.undo()
    assert esc.WhichOneof("tipo") == "via_esportiva"
    assert esc.via_esportiva.nome == "Via Teste"

    # 2. Submensagem singular (Coordenada em Pico)
    coord = Coordenada(latitude=-200000000, longitude=-440000000)
    cmd_sub = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="localizacao",
        valor_novo=coord,
    )
    assert cmd_sub.valor_antigo is None
    cmd_sub.executar_redo()
    assert pico.HasField("localizacao")
    assert pico.localizacao.latitude == -200000000

    cmd_sub.undo()
    assert not pico.HasField("localizacao")

    # 3. Limpeza de submensagem singular para None
    cmd_sub.executar_redo()
    assert pico.HasField("localizacao")
    cmd_sub_limpa = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="localizacao",
        valor_novo=None,
    )
    cmd_sub_limpa.executar_redo()
    assert not pico.HasField("localizacao")
    cmd_sub_limpa.undo()
    assert pico.HasField("localizacao")


def test_cmd_alterar_campo_serializacao_deserializacao():
    """Valida serialização e deserialização para o diário de CmdAlterarCampo."""
    croqui = Croqui(nome="Croqui Serializar")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_ser_001"
    setor.nome = "Setor Original"

    model = CroquiModel(croqui)

    cmd = CmdAlterarCampo(
        model=model,
        alvo="set_ser_001",
        campo_nome="nome",
        valor_novo="Setor Deserializado",
        context_path="set_ser_001.nome",
        pode_mesclar=True,
        session_id="sess_abc",
    )

    dados = cmd.serializar()
    assert dados["classe"] == "CmdAlterarCampo"
    assert dados["caminho_msg"] == "set_ser_001"
    assert dados["campo_nome"] == "nome"
    assert dados["valor_novo"] == "Setor Deserializado"

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarCampo)
    cmd_recriado.executar_redo()
    assert setor.nome == "Setor Deserializado"
    cmd_recriado.undo()
    assert setor.nome == "Setor Original"


# ==============================================================================
# 2. Testes de CmdAlterarImagem e CmdAlterarAnexo
# ==============================================================================


def test_cmd_alterar_imagem_adicao_substituicao_remocao():
    """Valida adições, substituições e remoções de imagens na RAM com CmdAlterarImagem."""
    croqui = Croqui()
    model = CroquiModel(croqui)

    sinais_emitidos: list[str] = []
    model.imagem_alterada.connect(lambda caminho: sinais_emitidos.append(caminho))

    img = Image.new("RGB", (200, 200), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    bytes_webp_1 = buf.getvalue()

    # 1. Adição (bytes_antigos capturado como None)
    cmd_add = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/foto1.webp",
        bytes_novos=bytes_webp_1,
    )
    assert cmd_add.bytes_antigos is None
    cmd_add.executar_redo()
    assert model.obter_bytes_imagem("setores/foto1.webp") == bytes_webp_1
    assert "setores/foto1.webp" in sinais_emitidos

    cmd_add.undo()
    assert model.obter_bytes_imagem("setores/foto1.webp") is None

    # Redo restaura
    cmd_add.executar_redo()
    assert model.obter_bytes_imagem("setores/foto1.webp") == bytes_webp_1

    # 2. Substituição (bytes_antigos capturado automaticamente)
    bytes_webp_2 = b"RIFF_FAKE_WEBP_NOVO_VALOR"
    cmd_subst = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/foto1.webp",
        bytes_novos=bytes_webp_2,
    )
    assert cmd_subst.bytes_antigos == bytes_webp_1
    cmd_subst.executar_redo()
    assert model.obter_bytes_imagem("setores/foto1.webp") == bytes_webp_2

    cmd_subst.undo()
    assert model.obter_bytes_imagem("setores/foto1.webp") == bytes_webp_1

    # 3. Remoção (bytes_novos=None)
    cmd_rem = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/foto1.webp",
        bytes_novos=None,
    )
    assert cmd_rem.bytes_antigos == bytes_webp_1
    cmd_rem.executar_redo()
    assert model.obter_bytes_imagem("setores/foto1.webp") is None

    cmd_rem.undo()
    assert model.obter_bytes_imagem("setores/foto1.webp") == bytes_webp_1

    # 4. Serialização e deserialização com e sem anonimização
    dados = cmd_subst.serializar()
    assert dados["classe"] == "CmdAlterarImagem"
    assert dados["nome_arquivo"] == "setores/foto1.webp"

    dados_anon = cmd_subst.serializar(anonimizado=True)
    assert dados_anon["bytes_novos"] is not None

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarImagem)
    cmd_recriado.executar_redo()
    assert model.obter_bytes_imagem("setores/foto1.webp") == bytes_webp_2


def test_cmd_alterar_anexo_adicao_substituicao_remocao():
    """Valida adições, substituições e remoções de anexos na RAM com CmdAlterarAnexo."""
    croqui = Croqui()
    model = CroquiModel(croqui)

    # 1. Adição
    cmd_add = CmdAlterarAnexo(
        model=model,
        nome_arquivo="documentos/guia.pdf",
        bytes_novos=b"%PDF-1.4-FAKE",
    )
    assert cmd_add.bytes_antigos is None
    cmd_add.executar_redo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") == b"%PDF-1.4-FAKE"

    cmd_add.undo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") is None

    # 2. Substituição
    cmd_add.executar_redo()
    cmd_subst = CmdAlterarAnexo(
        model=model,
        nome_arquivo="documentos/guia.pdf",
        bytes_novos=b"%PDF-2.0-NOVO",
    )
    assert cmd_subst.bytes_antigos == b"%PDF-1.4-FAKE"
    cmd_subst.executar_redo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") == b"%PDF-2.0-NOVO"

    cmd_subst.undo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") == b"%PDF-1.4-FAKE"

    # 3. Remoção
    cmd_rem = CmdAlterarAnexo(
        model=model,
        nome_arquivo="documentos/guia.pdf",
        bytes_novos=None,
    )
    cmd_rem.executar_redo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") is None

    cmd_rem.undo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") == b"%PDF-1.4-FAKE"

    # 4. Serialização e deserialização
    dados = cmd_subst.serializar()
    assert dados["classe"] == "CmdAlterarAnexo"
    assert dados["nome_arquivo"] == "documentos/guia.pdf"

    cmd_recriado = deserializar_comando(dados, model)
    assert isinstance(cmd_recriado, CmdAlterarAnexo)
    cmd_recriado.executar_redo()
    assert model.obter_bytes_anexo("documentos/guia.pdf") == b"%PDF-2.0-NOVO"


# ==============================================================================
# 3. Testes de Repeated (CmdAdicionarRepeated, CmdRemoverRepeated, CmdMoverRepeated)
# ==============================================================================


def test_cmd_adicionar_remover_repeated_primitives():
    """Valida adição e remoção em campos repeated primitivos."""
    croqui = Croqui()
    croqui.creditos.append("Renato")
    model = CroquiModel(croqui)

    # Adicionar "Silva" no índice 1
    cmd_add = CmdAdicionarRepeated(model, croqui, "creditos", 1, "Silva")
    cmd_add.redo()
    assert list(croqui.creditos) == ["Renato", "Silva"]

    cmd_add.undo()
    assert list(croqui.creditos) == ["Renato"]

    # Remover "Renato" no índice 0
    cmd_rem = CmdRemoverRepeated(model, croqui, "creditos", 0, "Renato")
    cmd_rem.redo()
    assert list(croqui.creditos) == []

    cmd_rem.undo()
    assert list(croqui.creditos) == ["Renato"]


def test_cmd_adicionar_remover_repeated_composite():
    """Valida adição e remoção em campos repeated compostos."""
    croqui = Croqui()
    pico = Pico(nome="Pico Falso")
    model = CroquiModel(croqui)

    cmd_add = CmdAdicionarRepeated(model, croqui, "picos", 0, pico)
    cmd_add.redo()
    assert len(croqui.picos) == 1
    assert croqui.picos[0].nome == "Pico Falso"

    cmd_add.undo()
    assert len(croqui.picos) == 0

    # recoloca para poder testar remoção
    cmd_add.redo()

    cmd_rem = CmdRemoverRepeated(model, croqui, "picos", 0, croqui.picos[0])
    cmd_rem.redo()
    assert len(croqui.picos) == 0

    cmd_rem.undo()
    assert len(croqui.picos) == 1
    assert croqui.picos[0].nome == "Pico Falso"


def test_cmd_remover_repeated_limpa_imagens_orfas_da_ram_e_restaura_no_undo():
    """Garante que ao remover uma subárvore com imagens na memória, elas são limpas e restauradas no undo."""
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Fugitivos"
    mapa = setor.mapas.add()
    mapa.caminho_imagem_mapa = "imagens/setor_fugitivos_p0.webp"

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/setor_fugitivos_p0.webp", b"conteudo_bytes_ram")

    cmd_rem = CmdRemoverRepeated(model, setor, "mapas", 0, setor.mapas[0])
    assert "imagens/setor_fugitivos_p0.webp" in cmd_rem.imagens_removidas_ram
    assert cmd_rem.imagens_removidas_ram["imagens/setor_fugitivos_p0.webp"] == b"conteudo_bytes_ram"

    cmd_rem.redo()
    assert len(setor.mapas) == 0
    assert "imagens/setor_fugitivos_p0.webp" not in model.obter_imagens_em_memoria()

    cmd_rem.undo()
    assert len(setor.mapas) == 1
    assert "imagens/setor_fugitivos_p0.webp" in model.obter_imagens_em_memoria()
    assert model.obter_bytes_imagem("imagens/setor_fugitivos_p0.webp") == b"conteudo_bytes_ram"


def test_cmd_remover_repeated_preserva_imagem_compartilhada_em_ram():
    """Garante que imagem compartilhada por mais de uma mensagem não seja removida da RAM."""
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    mapa1 = setor.mapas.add()
    mapa1.caminho_imagem_mapa = "imagens/compartilhada.webp"
    mapa2 = setor.mapas.add()
    mapa2.caminho_imagem_mapa = "imagens/compartilhada.webp"

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/compartilhada.webp", b"conteudo_comp")

    cmd_rem = CmdRemoverRepeated(model, setor, "mapas", 0, setor.mapas[0])
    assert cmd_rem.imagens_removidas_ram == {}

    cmd_rem.redo()
    assert len(setor.mapas) == 1
    assert "imagens/compartilhada.webp" in model.obter_imagens_em_memoria()


def test_cmd_remover_repeated_serializacao_com_imagens_em_ram():
    """Valida serialização e deserialização com imagens de RAM em CmdRemoverRepeated."""
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    mapa = setor.mapas.add()
    mapa.caminho_imagem_mapa = "imagens/mapa.webp"

    model = CroquiModel(croqui)
    model.definir_imagem_memoria("imagens/mapa.webp", b"bytes_teste")

    cmd_rem = CmdRemoverRepeated(model, setor, "mapas", 0, setor.mapas[0])
    dados = cmd_rem.serializar(anonimizado=False)
    assert "imagens_removidas_ram" in dados
    assert dados["imagens_removidas_ram"] == {"imagens/mapa.webp": b"bytes_teste"}

    cmd_deserializado = deserializar_comando(dados, model)
    assert cmd_deserializado.imagens_removidas_ram == {"imagens/mapa.webp": b"bytes_teste"}

    dados_anon = cmd_rem.serializar(anonimizado=True)
    assert "imagens_removidas_ram" in dados_anon
    assert dados_anon["imagens_removidas_ram"]["imagens/mapa.webp"] != b"bytes_teste"


def test_cmd_mover_repeated():
    """Valida reordenação de itens repeated com CmdMoverRepeated."""
    croqui = Croqui()
    croqui.creditos.extend(["A", "B", "C"])
    model = CroquiModel(croqui)

    cmd = CmdMoverRepeated(model, croqui, "creditos", 0, 2)
    cmd.redo()
    assert list(croqui.creditos) == ["B", "C", "A"]
    cmd.undo()
    assert list(croqui.creditos) == ["A", "B", "C"]


def test_cmd_repeated_com_alvo_str_e_uid():
    """Valida CmdAdicionarRepeated, CmdRemoverRepeated e CmdMoverRepeated com alvos por UID string."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_rep_uid"
    setor.nome = "Setor Repeated"

    model = CroquiModel(croqui)

    # 1. CmdAdicionarRepeated com alvo UID string
    t1 = Trilha(nome="Trilha 1", tempo_aproximacao="10min")
    cmd_add = CmdAdicionarRepeated(
        model=model,
        alvo="set_rep_uid",
        campo_nome="trilhas",
        index=0,
        valor=t1,
    )
    cmd_add.executar_redo()
    assert len(setor.trilhas) == 1
    assert setor.trilhas[0].nome == "Trilha 1"

    cmd_add.undo()
    assert len(setor.trilhas) == 0

    cmd_add.executar_redo()

    # Adiciona segunda trilha
    t2 = Trilha(nome="Trilha 2", tempo_aproximacao="20min")
    cmd_add2 = CmdAdicionarRepeated(
        model=model,
        alvo="set_rep_uid",
        campo_nome="trilhas",
        index=1,
        valor=t2,
    )
    cmd_add2.executar_redo()
    assert len(setor.trilhas) == 2

    # 2. CmdMoverRepeated com alvo UID string
    cmd_mov = CmdMoverRepeated(
        model=model,
        alvo="set_rep_uid",
        campo_nome="trilhas",
        index_from=0,
        index_to=1,
    )
    cmd_mov.executar_redo()
    assert setor.trilhas[0].nome == "Trilha 2"
    assert setor.trilhas[1].nome == "Trilha 1"

    cmd_mov.undo()
    assert setor.trilhas[0].nome == "Trilha 1"
    assert setor.trilhas[1].nome == "Trilha 2"

    # 3. CmdRemoverRepeated com alvo UID string (valor_removido capturado automaticamente)
    cmd_rem = CmdRemoverRepeated(
        model=model,
        alvo="set_rep_uid",
        campo_nome="trilhas",
        index=0,
    )
    cmd_rem.executar_redo()
    assert len(setor.trilhas) == 1
    assert setor.trilhas[0].nome == "Trilha 2"

    cmd_rem.undo()
    assert len(setor.trilhas) == 2
    assert setor.trilhas[0].nome == "Trilha 1"


def test_cmd_repeated_serializacao_deserializacao():
    """Valida serialização e deserialização de CmdAdicionarRepeated e CmdMoverRepeated."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_ser_rep"
    setor.nome = "Setor Ser Rep"

    model = CroquiModel(croqui)

    t1 = Trilha(nome="Trilha Serializada")
    cmd_add = CmdAdicionarRepeated(
        model=model,
        alvo="set_ser_rep",
        campo_nome="trilhas",
        index=0,
        valor=t1,
    )
    dados_add = cmd_add.serializar()
    assert dados_add["classe"] == "CmdAdicionarRepeated"
    cmd_add_recriado = deserializar_comando(dados_add, model)
    assert isinstance(cmd_add_recriado, CmdAdicionarRepeated)
    cmd_add_recriado.executar_redo()
    assert len(setor.trilhas) == 1
    assert setor.trilhas[0].nome == "Trilha Serializada"

    t2 = Trilha(nome="Trilha Dois")
    setor.trilhas.append(t2)
    assert len(setor.trilhas) == 2

    cmd_mov = CmdMoverRepeated(
        model=model,
        alvo="set_ser_rep",
        campo_nome="trilhas",
        index_from=0,
        index_to=1,
    )
    dados_mov = cmd_mov.serializar()
    assert dados_mov["classe"] == "CmdMoverRepeated"
    cmd_mov_recriado = deserializar_comando(dados_mov, model)
    assert isinstance(cmd_mov_recriado, CmdMoverRepeated)
    cmd_mov_recriado.executar_redo()
    assert setor.trilhas[0].nome == "Trilha Dois"
    assert setor.trilhas[1].nome == "Trilha Serializada"


# ==============================================================================
# 4. Testes de Resolução em 3 Níveis, Navegação Tardia e Validações
# ==============================================================================


def test_resolucao_alvo_3_niveis_e_navegacao_tardia():
    """Valida resolução e navegação tardia de alvos nos 3 níveis (UID, ancestral com UID, fallback posicional)."""
    croqui = Croqui(nome="Croqui Teste")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_1234567890"
    setor.nome = "Setor A"

    mapa_setor = setor.mapas.add(caminho_imagem_mapa="setor_mapa.webp")
    esc = setor.escaladas.add(uid="esc_1234567890")
    esc.via_esportiva.nome = "Via 1"

    patr = pico.patrocinadores.add(nome="Aresta Equipamentos")
    pico.localizacao.latitude = -200000000

    model = CroquiModel(croqui)
    indice_uids = model.indice_uids

    # 1. Testes de resolver_alvo_mensagem
    assert resolver_alvo_mensagem(croqui, croqui, indice_uids) == ""
    # Nível 1: UID direto
    assert resolver_alvo_mensagem(croqui, setor, indice_uids) == "set_1234567890"
    assert resolver_alvo_mensagem(croqui, esc, indice_uids) == "esc_1234567890"
    # Nível 2: Ancestral mais próximo com UID + subcaminho relativo
    assert resolver_alvo_mensagem(croqui, mapa_setor, indice_uids) == "set_1234567890.mapas.0"
    assert (
        resolver_alvo_mensagem(croqui, esc.via_esportiva, indice_uids)
        == "esc_1234567890.via_esportiva"
    )
    # Nível 3: Fallback posicional desde a raiz
    assert resolver_alvo_mensagem(croqui, pico, indice_uids) == "picos.0"
    assert resolver_alvo_mensagem(croqui, patr, indice_uids) == "picos.0.patrocinadores.0"
    assert resolver_alvo_mensagem(croqui, pico.localizacao, indice_uids) == "picos.0.localizacao"

    # 2. Testes de navegar_para_alvo
    assert navegar_para_alvo(croqui, "", indice_uids) is croqui
    assert navegar_para_alvo(croqui, "root", indice_uids) is croqui
    assert navegar_para_alvo(croqui, "set_1234567890", indice_uids) is setor
    assert navegar_para_alvo(croqui, "esc_1234567890", indice_uids) is esc
    assert navegar_para_alvo(croqui, "set_1234567890.mapas.0", indice_uids) is mapa_setor
    assert (
        navegar_para_alvo(croqui, "esc_1234567890.via_esportiva", indice_uids) is esc.via_esportiva
    )
    assert navegar_para_alvo(croqui, "picos.0", indice_uids) is pico
    assert navegar_para_alvo(croqui, "picos.0.patrocinadores.0", indice_uids) is patr
    assert navegar_para_alvo(croqui, "picos.0.localizacao", indice_uids) is pico.localizacao

    # Casos limites de navegação
    assert navegar_para_alvo(croqui, "uid_inexistente", indice_uids) is None
    assert navegar_para_alvo(croqui, "set_1234567890.campo_inexistente", indice_uids) is None
    assert navegar_para_alvo(croqui, "picos.99", indice_uids) is None
    assert navegar_para_alvo(None, "picos.0", indice_uids) is None

    # 3. Teste da propriedade alvo em ComandoEditor
    cmd = ComandoEditor()
    assert cmd.alvo is None
    cmd.alvo = "set_1234567890"
    assert cmd.alvo == "set_1234567890"
    assert cmd.caminho_msg == "set_1234567890"

    # 4. Testes de validar_pertence_ao_croqui com alvo str e Message
    assert validar_pertence_ao_croqui(model, croqui) == ""
    assert validar_pertence_ao_croqui(model, setor) == "set_1234567890"
    assert validar_pertence_ao_croqui(model, "set_1234567890") == "set_1234567890"
    assert validar_pertence_ao_croqui(model, "set_1234567890.mapas.0") == "set_1234567890.mapas.0"
    assert validar_pertence_ao_croqui(model, "picos.0") == "picos.0"

    # Mensagem órfã e string inválida rejeitadas
    setor_orfa = Croqui().picos.add().setores_ou_grupos.add().setor.conteudo
    setor_orfa.uid = "orfa_12345"
    with pytest.raises(ValueError, match="órfã"):
        validar_pertence_ao_croqui(model, setor_orfa)

    with pytest.raises(ValueError, match="não encontrada"):
        validar_pertence_ao_croqui(model, "alvo_inexistente_123")


def test_buscar_mensagem_por_uid_casos_borda():
    """Valida busca recursiva direta por UID nos casos limites."""
    assert _buscar_mensagem_por_uid(None, "uid_qualquer") is None

    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_uid_1"
    achado = _buscar_mensagem_por_uid(croqui, "set_uid_1")
    assert achado is not None
    assert achado[0] is setor
    assert achado[1] == "picos.0.setores_ou_grupos.0.setor.conteudo"

    assert _buscar_mensagem_por_uid(croqui, "uid_inexistente") is None


def test_comando_editor_carregamento_silencioso():
    """Garante que a armação de carregamento silencioso omite mutação no primeiro redo()."""
    croqui = Croqui(nome="Nome Atual")
    model = CroquiModel(croqui)

    cmd = CmdAlterarCampo(
        model=model,
        alvo=croqui,
        campo_nome="nome",
        valor_novo="Nome Mutado",
        valor_antigo="Nome Antigo",
    )
    cmd.armar_carregamento_silencioso()

    # Primeiro redo (durante push na inicialização) NÃO deve alterar o modelo
    cmd.redo()
    assert croqui.nome == "Nome Atual"

    # Ao desfazer, deve aplicar o valor antigo normalmente
    cmd.undo()
    assert croqui.nome == "Nome Antigo"

    # Ao refazer, a flag já está limpa e deve aplicar a mutação normalmente
    cmd.redo()
    assert croqui.nome == "Nome Mutado"


def test_guarda_integridade_mensagem_orfa_rejeitada():
    """Garante que comandos sobre mensagens desconectadas da árvore são rejeitados na instanciação."""
    croqui = Croqui(nome="Croqui Teste")
    model = CroquiModel(croqui)
    pico_orfa = Pico(nome="Pico Órfão")

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAlterarCampo(model, pico_orfa, "nome", "Novo")

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdAdicionarRepeated(model, pico_orfa, "patrocinadores", 0, Patrocinador(nome="P1"))

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdRemoverRepeated(model, pico_orfa, "patrocinadores", 0, Patrocinador(nome="P1"))

    with pytest.raises(ValueError, match="órfã|árvore"):
        CmdMoverRepeated(model, pico_orfa, "patrocinadores", 0, 1)


def test_guarda_integridade_campo_invalido_rejeitado():
    """Garante que campos inexistentes no DESCRIPTOR Protobuf são rejeitados."""
    croqui = Croqui(nome="Croqui Teste")
    model = CroquiModel(croqui)

    with pytest.raises(ValueError, match="não existe"):
        CmdAlterarCampo(model, croqui, "campo_completamente_inexistente", "B")

    with pytest.raises(ValueError, match="não existe"):
        CmdAdicionarRepeated(model, croqui, "pontos_de_interesse", 0, "algo")


def test_guarda_integridade_mensagem_conectada_valida():
    """Garante que mensagem conectada na árvore é aceita sem erro."""
    croqui = Croqui(nome="Croqui Teste")
    croqui.picos.add(nome="Pico Legítimo")
    model = CroquiModel(croqui)

    proxy_pico = model.obter_croqui_readonly().picos[0]
    cmd_alt = CmdAlterarCampo(model, proxy_pico, "nome", "Pico Modificado")
    assert cmd_alt is not None

    cmd_add = CmdAdicionarRepeated(model, proxy_pico, "patrocinadores", 0, Patrocinador(nome="P1"))
    assert cmd_add is not None


def test_validar_pertence_ao_croqui_casos_limite():
    """Valida tratamentos de parâmetros inválidos em validar_pertence_ao_croqui."""
    with pytest.raises(ValueError, match="inválida"):
        validar_pertence_ao_croqui(None, Croqui())

    with pytest.raises(ValueError, match="inválida"):
        validar_pertence_ao_croqui(CroquiModel(Croqui()), None)

    class ModelSemRoot:
        def obter_croqui_readonly(self):
            return None

    # Se root for None, caminho é vazio
    assert validar_pertence_ao_croqui(ModelSemRoot(), Croqui()) == ""


def test_navegar_para_mensagem_limites_e_oneofs():
    """Valida navegação direta em mensagem Protobuf com oneofs e índices inválidos."""
    croqui = Croqui()

    # 1. Caminho raiz
    assert navegar_para_mensagem(croqui, "") is croqui
    assert navegar_para_mensagem(croqui, "root") is croqui

    # 2. Índice fora de limite em lista vazia deve retornar None com segurança
    assert navegar_para_mensagem(croqui, "picos.0") is None

    # Adiciona um pico e setor com caminho (variante externa do oneof)
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.caminho = "setores/setor1.md"

    # 3. Índice dentro do limite
    assert navegar_para_mensagem(croqui, "picos.0") is pico
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.0.setor") is sg.setor

    # 4. Índice além do tamanho da lista
    assert navegar_para_mensagem(croqui, "picos.1") is None
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.5") is None

    # 5. Oneof inativo: sg.setor tem 'caminho', então acessar 'conteudo' deve retornar None
    assert sg.setor.WhichOneof("arquivo") == "caminho"
    assert navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.0.setor.conteudo") is None
    assert (
        navegar_para_mensagem(croqui, "picos.0.setores_ou_grupos.0.setor.conteudo.mapas.0") is None
    )

    # 6. Campo inexistente
    assert navegar_para_mensagem(croqui, "campo_que_nao_existe") is None
    assert navegar_para_mensagem(croqui, "picos.0.campo_que_nao_existe") is None


def test_comando_editor_resolucao_tardia_e_alvo_inexistente(caplog):
    """Garante que comando instanciado com caminho tardio trata graciosamente alvo apagado."""
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico Antigo"
    model = CroquiModel(croqui)

    # 1. Instanciação direta com caminho_msg (resolução tardia)
    cmd = CmdAlterarCampo(
        model=model,
        alvo="picos.0",
        campo_nome="nome",
        valor_antigo="Pico Antigo",
        valor_novo="Pico Novo",
    )
    assert cmd.caminho_msg == "picos.0"
    assert cmd.msg is pico

    # 2. Executa redo e undo normalmente
    cmd.executar_redo()
    assert pico.nome == "Pico Novo"
    cmd.undo()
    assert pico.nome == "Pico Antigo"

    # 3. Remove o pico da árvore do croqui tornando o caminho inválido
    croqui.ClearField("picos")
    assert len(croqui.picos) == 0

    # 4. Tentar executar undo() com alvo inexistente deve registrar erro e abortar com segurança
    with caplog.at_level(logging.ERROR):
        cmd.undo()
    assert "Falha ao resolver mensagem alvo no caminho 'picos.0'" in caplog.text


def test_deserializar_comando_sem_navegacao_ansiosa():
    """Garante que a deserialização não tenta acessar a mensagem ansiosamente na carga."""
    croqui = Croqui()  # Sem picos cadastrados
    model = CroquiModel(croqui)

    dados = {
        "classe": "CmdAlterarCampo",
        "alvo": "picos.5.setores_ou_grupos.0",
        "campo_nome": "nome",
        "valor_antigo": "Antigo",
        "valor_novo": "Novo",
        "context_path": None,
    }

    cmd = deserializar_comando(dados, model)
    assert isinstance(cmd, CmdAlterarCampo)
    assert cmd.caminho_msg == "picos.5.setores_ou_grupos.0"


def test_mensagem_alvo_nao_encontrada_error_e_msg_cache(caplog):
    """Valida cache de mensagem e comportamento da exceção MensagemAlvoNaoEncontradaError."""
    assert issubclass(MensagemAlvoNaoEncontradaError, LookupError)

    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Pico A"
    model = CroquiModel(croqui)

    # 1. Comando instanciado com mensagem viva (popula _msg_cache)
    cmd = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="nome",
        valor_antigo="Pico A",
        valor_novo="Pico B",
    )
    assert cmd._msg_cache is pico

    # Se a árvore for alterada mas _msg_cache estiver presente:
    croqui.ClearField("picos")
    assert len(croqui.picos) == 0

    caplog.clear()
    with caplog.at_level(logging.ERROR):
        msg_resolvida = cmd.msg
    assert msg_resolvida is pico
    assert "Falha ao resolver mensagem alvo" not in caplog.text

    # 2. Quando _msg_cache é None e o caminho não existe no modelo:
    cmd._msg_cache = None
    with pytest.raises(MensagemAlvoNaoEncontradaError):
        cmd._obter_msg(levantar_se_nao_encontrado=True)

    with caplog.at_level(logging.ERROR):
        assert cmd.msg is None

    # 3. Casos de borda: caminho_msg ou model None
    cmd._caminho_msg = None
    assert cmd._obter_msg() is None

    cmd.model = None
    assert cmd._obter_msg() is None


def test_comando_editor_metodos_base_e_validacao():
    """Valida métodos da classe base ComandoEditor e validador de campos."""
    croqui = Croqui(nome="Croqui Teste")
    model = CroquiModel(croqui)

    # 1. Validação de campo antecipada com parâmetros nulos/vazios
    _validar_campo_se_msg_existir(None, "qualquer", "nome")
    _validar_campo_se_msg_existir(model, None, "nome")
    _validar_campo_se_msg_existir(model, "", "")

    # 2. Validação com campo inexistente na mensagem raiz existente
    with pytest.raises(ValueError, match="não existe na mensagem"):
        _validar_campo_se_msg_existir(model, "", "campo_totalmente_invalido", "CmdTeste")

    # 3. Métodos da classe base ComandoEditor
    cmd = ComandoEditor()
    assert cmd.caminho_msg is None
    assert cmd._obter_msg() is None

    # msg.setter atualiza cache
    cmd.msg = "objeto_cache"
    assert cmd.msg == "objeto_cache"

    # Quando model existe mas caminho_msg é None, retorna cache
    cmd.model = model
    assert cmd._obter_msg() == "objeto_cache"

    # Métodos abstratos levantam NotImplementedError
    with pytest.raises(NotImplementedError):
        cmd.executar_redo()
    with pytest.raises(NotImplementedError):
        cmd.serializar()


def test_deserializar_comando_desconhecido_lanca_erro():
    """Garante que classe desconhecida para deserializar_comando levanta ValueError."""
    croqui = Croqui()
    model = CroquiModel(croqui)

    with pytest.raises(ValueError, match="Classe de comando desconhecida"):
        deserializar_comando({"classe": "ComandoAlien"}, model)


def test_cmd_macro_completo():
    """Valida o ciclo de vida completo de CmdMacro."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Inicial")
    model = CroquiModel(croqui)

    macro = CmdMacro(texto="Macro Teste")
    assert macro.text() == "Macro Teste"
    assert len(macro.comandos) == 0

    cmd1 = CmdAlterarCampo(model, pico, "nome", "Pico Intermediário")
    cmd2 = CmdAlterarCampo(model, pico, "descricao", "Nova Descrição")
    macro.adicionar_comando(cmd1)
    macro.adicionar_comando(cmd2)
    assert len(macro.comandos) == 2

    # Redo
    macro.executar_redo()
    assert pico.nome == "Pico Intermediário"
    assert pico.descricao == "Nova Descrição"

    # Undo
    macro.undo()
    assert pico.nome == "Pico Inicial"
    assert pico.descricao == ""

    # Armar carregamento silencioso
    macro.armar_carregamento_silencioso()
    macro.redo()
    # Primeiro redo com a flag não altera
    assert pico.nome == "Pico Inicial"
    macro.undo()
    macro.redo()
    assert pico.nome == "Pico Intermediário"

    # Serialização e Deserialização
    dados = macro.serializar()
    assert dados["classe"] == "CmdMacro"
    assert len(dados["comandos"]) == 2
    macro_recriado = deserializar_comando(dados, model)
    assert isinstance(macro_recriado, CmdMacro)
    assert len(macro_recriado.comandos) == 2


def test_cmd_alterar_imagem_merge_e_contexto():
    """Valida mergeWith, id() e notificação de foco em CmdAlterarImagem."""
    croqui = Croqui()
    model = CroquiModel(croqui)

    foco_recebido: list[str] = []
    model.foco_requisitado.connect(lambda ctx: foco_recebido.append(ctx))

    cmd1 = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/foto.webp",
        bytes_novos=b"FOTO_1",
        pode_mesclar=True,
        context_path="campo.foto",
    )
    assert cmd1.id() == CmdAlterarImagem.ID_COMANDO
    cmd1.executar_redo()
    assert model.obter_bytes_imagem("setores/foto.webp") == b"FOTO_1"
    assert "campo.foto" in foco_recebido

    cmd2 = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/foto.webp",
        bytes_novos=b"FOTO_2",
        pode_mesclar=True,
        context_path="campo.foto.2",
    )
    assert cmd1.mergeWith(cmd2) is True
    assert model.obter_bytes_imagem("setores/foto.webp") == b"FOTO_2"

    cmd_incompativel = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/outra.webp",
        bytes_novos=b"FOTO_3",
        pode_mesclar=True,
    )
    assert cmd1.mergeWith(cmd_incompativel) is False

    cmd_sem_merge = CmdAlterarImagem(
        model=model,
        nome_arquivo="setores/foto.webp",
        bytes_novos=b"FOTO_4",
        pode_mesclar=False,
    )
    assert cmd_sem_merge.id() == -1
    assert cmd1.mergeWith(cmd_sem_merge) is False
    assert cmd_sem_merge.mergeWith(cmd1) is False

    cmd1.undo()
    assert model.obter_bytes_imagem("setores/foto.webp") is None


def test_cmd_alterar_anexo_merge_e_contexto():
    """Valida mergeWith, id() e notificação de foco em CmdAlterarAnexo."""
    croqui = Croqui()
    model = CroquiModel(croqui)

    foco_recebido: list[str] = []
    model.foco_requisitado.connect(lambda ctx: foco_recebido.append(ctx))

    cmd1 = CmdAlterarAnexo(
        model=model,
        nome_arquivo="docs/manual.pdf",
        bytes_novos=b"PDF_1",
        pode_mesclar=True,
        context_path="campo.manual",
    )
    assert cmd1.id() == CmdAlterarAnexo.ID_COMANDO
    cmd1.executar_redo()
    assert model.obter_bytes_anexo("docs/manual.pdf") == b"PDF_1"
    assert "campo.manual" in foco_recebido

    cmd2 = CmdAlterarAnexo(
        model=model,
        nome_arquivo="docs/manual.pdf",
        bytes_novos=b"PDF_2",
        pode_mesclar=True,
    )
    assert cmd1.mergeWith(cmd2) is True
    assert model.obter_bytes_anexo("docs/manual.pdf") == b"PDF_2"

    cmd_outro = CmdAlterarAnexo(
        model=model,
        nome_arquivo="docs/outro.pdf",
        bytes_novos=b"PDF_3",
        pode_mesclar=True,
    )
    assert cmd1.mergeWith(cmd_outro) is False

    cmd_sem_merge = CmdAlterarAnexo(
        model=model,
        nome_arquivo="docs/manual.pdf",
        bytes_novos=b"PDF_4",
        pode_mesclar=False,
    )
    assert cmd_sem_merge.id() == -1
    assert cmd1.mergeWith(cmd_sem_merge) is False


def test_cmd_alterar_campo_oneof_nome_direto_e_extensao():
    """Valida CmdAlterarCampo com campo_nome sendo o identificador do oneof e extensão de metadados."""
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor, Boulder

    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_oneof_dir"
    esc = setor.escaladas.add(uid="esc_oneof_dir")

    model = CroquiModel(croqui)

    # 1. Ativa variante via tupla (nome_variante, valor) no oneof "tipo"
    cmd_oneof = CmdAlterarCampo(
        model=model,
        alvo="esc_oneof_dir",
        campo_nome="tipo",
        valor_novo=("boulder", Boulder(nome="Bloco Teste")),
    )
    cmd_oneof.executar_redo()
    assert esc.WhichOneof("tipo") == "boulder"
    assert esc.boulder.nome == "Bloco Teste"

    # Limpa o oneof passando valor_novo=None
    cmd_limpa = CmdAlterarCampo(
        model=model,
        alvo="esc_oneof_dir",
        campo_nome="tipo",
        valor_novo=None,
    )
    cmd_limpa.executar_redo()
    assert esc.WhichOneof("tipo") is None

    cmd_limpa.undo()
    assert esc.WhichOneof("tipo") == "boulder"

    # 2. Extensão de metadados caminho_novo
    cmd_ext = CmdAlterarCampo(
        model=model,
        alvo=sg.setor,
        campo_nome="ext_metadados_arquivo",
        valor_novo="setores/novo_caminho.md",
        field_ext=ArquivoSetor.ext_metadados_arquivo,
    )
    cmd_ext.executar_redo()
    assert (
        sg.setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo
        == "setores/novo_caminho.md"
    )
    cmd_ext.undo()
    assert sg.setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == ""


def test_cmd_repeated_context_path_e_casos_alvo_nulo():
    """Valida foco_requisitado e tratamento gracioso de alvo apagado em comandos de repeated."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_rep_ctx"

    model = CroquiModel(croqui)

    focos: list[str] = []
    model.foco_requisitado.connect(lambda ctx: focos.append(ctx))

    t = Trilha(nome="Trilha Foco")
    cmd_add = CmdAdicionarRepeated(
        model=model,
        alvo="set_rep_ctx",
        campo_nome="trilhas",
        index=0,
        valor=t,
        context_path="trilhas.0.foco",
    )
    cmd_add.executar_redo()
    assert "trilhas.0.foco" in focos
    cmd_add.undo()
    assert len(setor.trilhas) == 0

    cmd_add.executar_redo()
    cmd_rem = CmdRemoverRepeated(
        model=model,
        alvo="set_rep_ctx",
        campo_nome="trilhas",
        index=0,
        context_path="trilhas.removida",
    )
    cmd_rem.executar_redo()
    assert "trilhas.removida" in focos
    cmd_rem.undo()

    cmd_mov = CmdMoverRepeated(
        model=model,
        alvo="set_rep_ctx",
        campo_nome="trilhas",
        index_from=0,
        index_to=0,
        context_path="trilhas.movida",
    )
    cmd_mov.executar_redo()
    assert "trilhas.movida" in focos
    cmd_mov.undo()

    # Alvo nulo / apagado não quebra nem propaga exceção
    cmd_add._caminho_msg = "alvo_inexistente"
    cmd_add._msg_cache = None
    cmd_add.undo()
    cmd_add.executar_redo()

    cmd_rem._caminho_msg = "alvo_inexistente"
    cmd_rem._msg_cache = None
    cmd_rem.undo()
    cmd_rem.executar_redo()

    cmd_mov._caminho_msg = "alvo_inexistente"
    cmd_mov._msg_cache = None
    cmd_mov.undo()
    cmd_mov.executar_redo()


def test_resolver_caminho_mensagem_direto():
    """Valida resolver_caminho_mensagem diretamente em todos os seus ramos e tipos de campo."""
    from editor.commands.comandos_protobuf import resolver_caminho_mensagem

    assert resolver_caminho_mensagem(None, None) == ""
    croqui = Croqui()
    assert resolver_caminho_mensagem(croqui, croqui) == ""

    pico = croqui.picos.add(nome="Pico")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    esc = setor.escaladas.add(uid="esc_res")
    via = esc.via_esportiva
    via.nome = "Via Res"

    assert resolver_caminho_mensagem(croqui, pico) == "picos.0"
    assert resolver_caminho_mensagem(croqui, sg) == "picos.0.setores_ou_grupos.0"
    assert resolver_caminho_mensagem(croqui, sg.setor) == "picos.0.setores_ou_grupos.0.setor"
    assert resolver_caminho_mensagem(croqui, setor) == "picos.0.setores_ou_grupos.0.setor.conteudo"
    assert (
        resolver_caminho_mensagem(croqui, esc)
        == "picos.0.setores_ou_grupos.0.setor.conteudo.escaladas.0"
    )
    assert (
        resolver_caminho_mensagem(croqui, via)
        == "picos.0.setores_ou_grupos.0.setor.conteudo.escaladas.0.via_esportiva"
    )

    # Alvo não contido na árvore retorna ""
    outro_pico = Pico(nome="Outro")
    assert resolver_caminho_mensagem(croqui, outro_pico) == ""


def test_deserializar_comando_legado_delegado():
    """Garante que deserializar_comando aceita e delega para comandos legados em COMANDOS_LEGADOS_MAP."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Antigo")
    model = CroquiModel(croqui)

    dados_legado = {
        "classe": "CmdAlterarPrimitivo",
        "caminho_msg": "picos.0",
        "campo_nome": "nome",
        "valor_antigo": "Pico Antigo",
        "valor_novo": "Pico Moderno",
    }
    cmd = deserializar_comando(dados_legado, model)
    assert cmd.__class__.__name__ == "CmdAlterarPrimitivo"
    cmd.executar_redo()
    assert pico.nome == "Pico Moderno"


def test_comandos_protobuf_cobertura_casos_borda():
    """Cobre casos de borda de proxy, parent, validações de campo com ponto e ramificações de merge."""
    from PySide6.QtGui import QUndoCommand

    from editor.commands.comandos_protobuf import (
        _buscar_mensagem_por_uid,
        _validar_campo_se_msg_existir,
        navegar_para_alvo,
        resolver_alvo_mensagem,
        resolver_caminho_mensagem,
        validar_pertence_ao_croqui,
    )
    from editor.models.readonly_proxy import ReadOnlyProxy

    # 1. ComandoEditor com parent
    parent_cmd = QUndoCommand()
    cmd_parent = ComandoEditor(parent=parent_cmd)
    assert cmd_parent is not None

    # 2. ReadOnlyProxy em resoluções
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico Proxy")
    proxy_croqui = ReadOnlyProxy(croqui)
    proxy_pico = ReadOnlyProxy(pico)

    assert resolver_alvo_mensagem(proxy_croqui, proxy_croqui) == ""
    assert resolver_alvo_mensagem(proxy_croqui, proxy_pico) == "picos.0"
    assert resolver_alvo_mensagem(None, None) == ""
    assert resolver_caminho_mensagem(proxy_croqui, proxy_croqui) == ""
    assert resolver_caminho_mensagem(proxy_croqui, proxy_pico) == "picos.0"
    assert resolver_caminho_mensagem(croqui, "objeto_sem_descriptor") == ""

    assert _buscar_mensagem_por_uid(proxy_croqui, "uid_inexistente") is None
    assert _buscar_mensagem_por_uid("objeto_sem_descriptor", "qualquer") is None

    # 3. validar_pertence_ao_croqui com "root", "", e campo com ponto inválido
    model = CroquiModel(croqui)
    assert validar_pertence_ao_croqui(model, "root") == ""
    assert validar_pertence_ao_croqui(model, "") == ""
    with pytest.raises(ValueError, match="não existe"):
        validar_pertence_ao_croqui(model, croqui, "campo_invalido.0")

    with pytest.raises(ValueError, match="não existe"):
        _validar_campo_se_msg_existir(model, "", "campo_invalido.0")

    # 4. navegar_para_alvo com índice uids None e busca por prefixo na árvore
    pico.setores_ou_grupos.add().setor.conteudo.uid = "set_busca_dir"
    assert navegar_para_alvo(croqui, "set_busca_dir", indice_uids=None) is not None
    assert navegar_para_alvo(croqui, "set_busca_dir.mapas.99", indice_uids=None) is None


def test_cmd_alterar_campo_casos_borda_merge_e_variantes():
    """Valida redirecionamento de variante, repeated além do limite e mergeWith."""
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_borda_001"
    esc = setor.escaladas.add(uid="esc_borda_001")
    esc.via_esportiva.nome = "Via Original"

    model = CroquiModel(croqui)

    # 1. Alvo é a própria Escalada (Message), mas campo_nome é "nome" (da variante ativa)
    cmd_var = CmdAlterarCampo(
        model=model,
        alvo=esc,
        campo_nome="nome",
        valor_novo="Via Redirecionada",
    )
    assert cmd_var.caminho_msg == "esc_borda_001.via_esportiva"
    cmd_var.executar_redo()
    assert esc.via_esportiva.nome == "Via Redirecionada"

    # 2. Repeated com índice fora do limite tem valor_antigo inferido como None
    cmd_rep_lim = CmdAlterarCampo(
        model=model,
        alvo=croqui,
        campo_nome="creditos.99",
        valor_novo="Credito Extra",
    )
    assert cmd_rep_lim.valor_antigo is None

    # 3. Limpeza de variante ativa passando nome da variante e None
    cmd_limpa_var = CmdAlterarCampo(
        model=model,
        alvo="esc_borda_001",
        campo_nome="via_esportiva",
        valor_novo=None,
    )
    cmd_limpa_var.executar_redo()
    assert esc.WhichOneof("tipo") is None

    # 4. Extensão inferida automaticamente por nome sem passar field_ext
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor

    # Sem extensão prévia (captura "" como valor_antigo)
    cmd_ext_nova = CmdAlterarCampo(
        model=model,
        alvo=sg.setor,
        campo_nome="ext_metadados_arquivo",
        valor_novo="inicial.md",
    )
    assert cmd_ext_nova.valor_antigo == ""
    cmd_ext_nova.executar_redo()

    # Com extensão prévia (captura "inicial.md" como valor_antigo)
    cmd_ext_auto = CmdAlterarCampo(
        model=model,
        alvo=sg.setor,
        campo_nome="ext_metadados_arquivo",
        valor_novo="novo.md",
    )
    assert cmd_ext_auto.valor_antigo == "inicial.md"
    cmd_ext_auto.executar_redo()
    assert sg.setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo == "novo.md"

    # Restaura variante para testar navegação interna
    cmd_limpa_var.undo()
    assert esc.WhichOneof("tipo") == "via_esportiva"

    # Navegação por UID com resolução de variante ativa interna
    assert navegar_para_alvo(croqui, "esc_borda_001.nome", model.indice_uids) is not None
    # Navegação direta para variante inativa retorna None
    assert navegar_para_mensagem(esc, "boulder") is None

    # 5. mergeWith com context_path, tipos incompatíveis e alvo nulo
    cmd1 = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="A",
        pode_mesclar=True,
        session_id="s1",
    )
    assert cmd1.id() == CmdAlterarCampo.ID_COMANDO

    cmd_sem_merge = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="A",
        pode_mesclar=False,
    )
    assert cmd_sem_merge.id() == -1

    cmd2 = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="AB",
        pode_mesclar=True,
        session_id="s1",
        context_path="desc.foco",
    )
    assert cmd1.mergeWith(cmd2) is True
    assert cmd1.context_path == "desc.foco"

    # mergeWith quando outro não pode mesclar
    cmd2_sem_merge = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="ABC",
        pode_mesclar=False,
        session_id=None,
    )
    assert cmd1.mergeWith(cmd2_sem_merge) is False
    assert cmd_sem_merge.mergeWith(cmd1) is False

    cmd_outro_tipo = CmdAlterarImagem(
        model=model, nome_arquivo="x.webp", bytes_novos=b"1", pode_mesclar=True
    )
    assert cmd1.mergeWith(cmd_outro_tipo) is False

    cmd_outro_alvo = CmdAlterarCampo(
        model=model,
        alvo="set_borda_001",
        campo_nome="descricao",
        valor_novo="Outro",
        pode_mesclar=True,
        session_id="s1",
    )
    assert cmd1.mergeWith(cmd_outro_alvo) is False

    # Alvo nulo / apagado em ambos os comandos
    cmd1._caminho_msg = "inexistente"
    cmd1._msg_cache = None
    cmd_alvo_nulo2 = CmdAlterarCampo(
        model=model,
        alvo=pico,
        campo_nome="descricao",
        valor_novo="ABC",
        pode_mesclar=True,
        session_id="s1",
    )
    cmd_alvo_nulo2._caminho_msg = "inexistente"
    cmd_alvo_nulo2._msg_cache = None
    assert cmd1.mergeWith(cmd_alvo_nulo2) is False

    # 6. mergeWith em CmdAlterarImagem e CmdAlterarAnexo com tipos incompatíveis e context_path
    cmd_img1 = CmdAlterarImagem(
        model=model, nome_arquivo="a.webp", bytes_novos=b"1", pode_mesclar=True
    )
    cmd_img2 = CmdAlterarImagem(
        model=model,
        nome_arquivo="a.webp",
        bytes_novos=b"2",
        pode_mesclar=True,
        context_path="img.foco",
    )
    assert cmd_img1.mergeWith(cmd_img2) is True
    assert cmd_img1.context_path == "img.foco"
    assert cmd_img1.mergeWith(cmd1) is False
    assert cmd_img1.mergeWith("invalido") is False

    cmd_anx1 = CmdAlterarAnexo(
        model=model, nome_arquivo="a.pdf", bytes_novos=b"1", pode_mesclar=True
    )
    cmd_anx2 = CmdAlterarAnexo(
        model=model,
        nome_arquivo="a.pdf",
        bytes_novos=b"2",
        pode_mesclar=True,
        context_path="anx.foco",
    )
    assert cmd_anx1.mergeWith(cmd_anx2) is True
    assert cmd_anx1.context_path == "anx.foco"
    assert cmd_anx1.mergeWith(cmd1) is False
    assert cmd_anx1.mergeWith("invalido") is False

    # Resolução de caminho e alvo com submensagens aninhadas e proxy
    assert resolver_caminho_mensagem(sg, sg.setor.conteudo) == "setor.conteudo"
    assert resolver_caminho_mensagem("string_sem_descriptor", pico) == ""
    proxy_croqui = ReadOnlyProxy(croqui)
    assert (
        resolver_caminho_mensagem(proxy_croqui, sg.setor.conteudo)
        == "picos.0.setores_ou_grupos.0.setor.conteudo"
    )

    class IndiceComProxy:
        def obter_objeto(self, uid):
            if uid == "set_proxy_ancora":
                return ReadOnlyProxy(setor)
            return None

    assert (
        navegar_para_alvo(croqui, "set_proxy_ancora.nome", indice_uids=IndiceComProxy()) is not None
    )
    assert navegar_para_mensagem(None, "picos.0") is None
    assert navegar_para_mensagem(proxy_croqui, "picos.0") is pico
    assert navegar_para_mensagem(object(), "campo_totalmente_inexistente") is None

    # Primitivo escalar sem has_presence (sint32 latitude em Coordenada)
    pico.localizacao.latitude = -200000000
    cmd_coord = CmdAlterarCampo(
        model=model,
        alvo=pico.localizacao,
        campo_nome="latitude",
        valor_novo=-210000000,
    )
    assert cmd_coord.valor_antigo == -200000000
    cmd_coord.executar_redo()
    assert pico.localizacao.latitude == -210000000
    cmd_coord.undo()
    assert pico.localizacao.latitude == -200000000


def test_garantir_uids_em_mensagem_e_comandos_geram_uid_automatico():
    """
    Valida que `garantir_uids_em_mensagem`, `CmdAdicionarRepeated` e `CmdAlterarCampo`
    geram automaticamente UIDs NanoID (14 caracteres Base62) para entidades e submensagens
    ativas com campo `uid` vazio, preservam UIDs existentes, mantêm determinismo em Undo/Redo
    e serialização, indexam imediatamente no `IndiceUidsModel` e não ativam submensagens
    singulares vazias (`HasField`).
    """
    from editor.commands.comandos_protobuf import garantir_uids_em_mensagem
    from scripts.gerenciar_uids_lib import validar_uid

    # 1. Primitivos e None retornam string vazia sem erro
    assert garantir_uids_em_mensagem(None) == ""
    assert garantir_uids_em_mensagem("texto_primitivo") == ""
    assert garantir_uids_em_mensagem(123) == ""

    # 2. Mensagem sem campo uid e com submensagem singular opcional vazia (HasField preservado False)
    pico_isolado = croqui_pb2.Pico(nome="Pico Sem Localização")
    assert not pico_isolado.HasField("localizacao")
    assert garantir_uids_em_mensagem(pico_isolado) == ""
    assert not pico_isolado.HasField("localizacao")

    # E quando a submensagem singular opcional está preenchida, percorre-a sem erro
    pico_isolado.localizacao.latitude = -200000000
    assert pico_isolado.HasField("localizacao")
    assert garantir_uids_em_mensagem(pico_isolado) == ""

    # 3. ArquivoSetor / ArquivoGrupo com caminho externo não devem ter `.conteudo` ativado
    arq_setor_caminho = croqui_pb2.ArquivoSetor(caminho="setor_externo.md")
    assert garantir_uids_em_mensagem(arq_setor_caminho) == ""
    assert arq_setor_caminho.WhichOneof("arquivo") == "caminho"

    arq_grupo_caminho = croqui_pb2.ArquivoGrupo(caminho="grupo_externo.md")
    assert garantir_uids_em_mensagem(arq_grupo_caminho) == ""
    assert arq_grupo_caminho.WhichOneof("arquivo") == "caminho"

    # ArquivoSetor recém-instanciado sem variante explícita gera UID no `.conteudo`
    arq_setor_vazio = croqui_pb2.ArquivoSetor()
    uid_arq_vazio = garantir_uids_em_mensagem(ReadOnlyProxy(arq_setor_vazio))
    assert validar_uid(uid_arq_vazio)
    assert arq_setor_vazio.conteudo.uid == uid_arq_vazio

    # 4. Criação de modelo e adição via CmdAdicionarRepeated
    croqui = croqui_pb2.Croqui(uid="crq_uid_auto01", nome="Croqui Teste UIDs")
    pico = croqui.picos.add(nome="Pico Principal")
    model = CroquiModel(croqui)

    # 4a. Adição de SetorOuGrupo (variante grupo e variante setor) sem UID prévio
    novo_sg_grupo = croqui_pb2.SetorOuGrupo()
    novo_sg_grupo.grupo.conteudo.nome = "Grupo Novo"
    cmd_add_grupo = CmdAdicionarRepeated(
        model=model,
        alvo=pico,
        campo_nome="setores_ou_grupos",
        index=0,
        valor=novo_sg_grupo,
    )
    uid_grupo = novo_sg_grupo.grupo.conteudo.uid
    assert validar_uid(uid_grupo)
    assert cmd_add_grupo.valor.grupo.conteudo.uid == uid_grupo
    cmd_add_grupo.executar_redo()
    assert model.indice_uids.obter_objeto(uid_grupo) is not None

    novo_sg_setor = croqui_pb2.SetorOuGrupo()
    novo_sg_setor.setor.conteudo.nome = "Setor Raiz Novo"
    cmd_add_setor_raiz = CmdAdicionarRepeated(
        model=model,
        alvo=pico,
        campo_nome="setores_ou_grupos",
        index=1,
        valor=novo_sg_setor,
    )
    uid_setor_raiz = novo_sg_setor.setor.conteudo.uid
    assert validar_uid(uid_setor_raiz)
    assert not novo_sg_setor.setor.conteudo.HasField("localizacao_escalada")
    cmd_add_setor_raiz.executar_redo()
    assert model.indice_uids.obter_objeto(uid_setor_raiz) is not None

    # 4b. Adição de ArquivoSetor dentro de Grupo.setores
    grupo_no_modelo = pico.setores_ou_grupos[0].grupo.conteudo
    novo_arq_setor = croqui_pb2.ArquivoSetor()
    novo_arq_setor.conteudo.nome = "Setor Interno"
    cmd_add_setor_interno = CmdAdicionarRepeated(
        model=model,
        alvo=grupo_no_modelo,
        campo_nome="setores",
        index=0,
        valor=novo_arq_setor,
    )
    uid_setor_interno = novo_arq_setor.conteudo.uid
    assert validar_uid(uid_setor_interno)
    cmd_add_setor_interno.executar_redo()
    assert model.indice_uids.obter_objeto(uid_setor_interno) is not None

    # 4c. Adição de Escalada com múltiplas enfiadas aninhadas sem UIDs prévios
    setor_no_modelo = pico.setores_ou_grupos[1].setor.conteudo
    nova_via = croqui_pb2.Escalada()
    nova_via.via_multiplas_enfiadas.nome = "Via Paredão"
    enf1 = nova_via.via_multiplas_enfiadas.enfiadas.add()
    enf1.via_esportiva.nome = "Enfiada 1"
    enf2 = nova_via.via_multiplas_enfiadas.enfiadas.add(uid="enf_uid_fixo02")
    enf2.via_movel.nome = "Enfiada 2"

    cmd_add_via = CmdAdicionarRepeated(
        model=model,
        alvo=setor_no_modelo,
        campo_nome="escaladas",
        index=0,
        valor=nova_via,
    )
    uid_via = nova_via.uid
    uid_enf1 = nova_via.via_multiplas_enfiadas.enfiadas[0].uid
    assert validar_uid(uid_via)
    assert validar_uid(uid_enf1)
    assert uid_via != uid_enf1
    # UID preexistente deve ser preservado
    assert nova_via.via_multiplas_enfiadas.enfiadas[1].uid == "enf_uid_fixo02"

    cmd_add_via.executar_redo()
    assert model.indice_uids.obter_objeto(uid_via) is not None

    # 4d. Ciclo Undo/Redo e serialização/deserialização preservam exatamente o mesmo UID
    cmd_add_via.undo()
    assert model.indice_uids.obter_objeto(uid_via) is None
    cmd_add_via.executar_redo()
    assert setor_no_modelo.escaladas[0].uid == uid_via
    assert setor_no_modelo.escaladas[0].via_multiplas_enfiadas.enfiadas[0].uid == uid_enf1
    assert model.indice_uids.obter_objeto(uid_via) is not None

    dados_ser = cmd_add_via.serializar()
    cmd_add_via.undo()
    cmd_deser = CmdAdicionarRepeated.deserializar(dados_ser, model)
    assert cmd_deser.valor.uid == uid_via
    cmd_deser.executar_redo()
    assert setor_no_modelo.escaladas[0].uid == uid_via

    # 4e. Botao e Mapa.PontoDeInteresse recebem UID automaticamente
    novo_botao = croqui_pb2.Botao(texto="Guia de Bolso")
    cmd_add_botao = CmdAdicionarRepeated(
        model=model,
        alvo=croqui,
        campo_nome="botoes",
        index=0,
        valor=novo_botao,
    )
    assert validar_uid(novo_botao.uid)
    cmd_add_botao.executar_redo()
    assert croqui.botoes[0].uid == novo_botao.uid

    mapa = setor_no_modelo.mapas.add(caminho_imagem_mapa="imagens/parede.webp")
    novo_poi = croqui_pb2.Mapa.PontoDeInteresse(rotulo="P1")
    cmd_add_poi = CmdAdicionarRepeated(
        model=model,
        alvo=mapa,
        campo_nome="pontos_de_interesse",
        index=0,
        valor=novo_poi,
    )
    assert validar_uid(novo_poi.uid)
    cmd_add_poi.executar_redo()
    assert mapa.pontos_de_interesse[0].uid == novo_poi.uid

    # 5. CmdAlterarCampo gera UID em repeated_item e oneof (tupla e variante direta)
    via_substituta = croqui_pb2.Escalada()
    via_substituta.boulder.nome = "Boulder Substituto"
    cmd_alt_item = CmdAlterarCampo(
        model=model,
        alvo=setor_no_modelo,
        campo_nome="escaladas.0",
        valor_novo=via_substituta,
    )
    uid_substituta = via_substituta.uid
    assert validar_uid(uid_substituta)
    cmd_alt_item.executar_redo()
    assert setor_no_modelo.escaladas[0].uid == uid_substituta
    assert model.indice_uids.obter_objeto(uid_substituta) is not None
    cmd_alt_item.undo()
    assert setor_no_modelo.escaladas[0].uid == uid_via

    # CmdAlterarCampo trocando variante oneof por tupla (nome_oneof="tipo") com submensagens com uid
    vme_nova = croqui_pb2.ViaMultiplasEnfiadas(nome="Multi Nova")
    vme_nova.enfiadas.add().via_esportiva.nome = "Enfiada Via Oneof"
    cmd_alt_oneof_tupla = CmdAlterarCampo(
        model=model,
        alvo=setor_no_modelo.escaladas[0],
        campo_nome="tipo",
        valor_novo=("via_multiplas_enfiadas", vme_nova),
    )
    uid_enf_oneof = vme_nova.enfiadas[0].uid
    assert validar_uid(uid_enf_oneof)
    cmd_alt_oneof_tupla.executar_redo()
    assert setor_no_modelo.escaladas[0].via_multiplas_enfiadas.enfiadas[0].uid == uid_enf_oneof

    # CmdAlterarCampo trocando variante oneof pelo nome direto do campo da variante
    arq_grupo_novo = croqui_pb2.ArquivoGrupo()
    arq_grupo_novo.conteudo.nome = "Convertido em Grupo"
    cmd_alt_oneof_direto = CmdAlterarCampo(
        model=model,
        alvo=pico.setores_ou_grupos[1],
        campo_nome="grupo",
        valor_novo=arq_grupo_novo,
    )
    uid_grupo_convertido = arq_grupo_novo.conteudo.uid
    assert validar_uid(uid_grupo_convertido)
    cmd_alt_oneof_direto.executar_redo()
    assert pico.setores_ou_grupos[1].grupo.conteudo.uid == uid_grupo_convertido
    assert model.indice_uids.obter_objeto(uid_grupo_convertido) is not None
    cmd_alt_oneof_direto.undo()
    assert pico.setores_ou_grupos[1].setor.conteudo.uid == uid_setor_raiz


def test_cmd_alterar_campo_rejeita_repeated_sem_indice_e_tipos_incompativeis_fail_fast():
    """
    Valida que CmdAlterarCampo rejeita no __init__ (antes de empilhar no QUndoStack)
    campos repeated sem índice, índices em campos escalares e tipos incompatíveis com o FieldDescriptor.
    """
    croqui = croqui_pb2.Croqui(nome="Croqui Blindado")
    croqui.creditos.append("Autor 1")
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "set_val_01"
    esc = setor.escaladas.add(uid="esc_val_01")
    esc.via_esportiva.nome = "Via 1"
    model = CroquiModel(croqui)

    # 1. Campo repeated sem índice deve falhar no __init__ com ValueError
    with pytest.raises(ValueError, match="repeated"):
        CmdAlterarCampo(model, croqui, "creditos", ["Autor A", "Autor B"])

    with pytest.raises(ValueError, match="repeated"):
        CmdAlterarCampo(model, croqui, "picos", [])

    # 2. Índice em campo que não é repeated ou índice não numérico
    with pytest.raises(ValueError, match="não é uma lista"):
        CmdAlterarCampo(model, croqui, "nome.0", "Outro")

    with pytest.raises(ValueError, match="Índice inválido"):
        CmdAlterarCampo(model, croqui, "creditos.abc", "Outro")

    # 3. Tipos escalares incompatíveis (string, int, bool, float, enum)
    with pytest.raises(TypeError, match="string"):
        CmdAlterarCampo(model, croqui, "nome", 12345)

    with pytest.raises(TypeError, match="inteiro"):
        CmdAlterarCampo(model, esc.via_esportiva, "extensao", "25m")

    with pytest.raises(TypeError, match="inteiro"):
        CmdAlterarCampo(model, esc.via_esportiva, "extensao", True)

    with pytest.raises(TypeError, match="booleano"):
        CmdAlterarCampo(model, setor, "sinal_de_celular", "sim")

    # Enum inválido (string crua ou número inexistente no enum) e válido
    with pytest.raises(TypeError, match="enum"):
        CmdAlterarCampo(model, esc.via_esportiva, "dificuldade", "BR_7A")

    with pytest.raises(ValueError, match="enum"):
        CmdAlterarCampo(model, esc.via_esportiva, "dificuldade", 999999)

    cmd_enum_ok = CmdAlterarCampo(model, esc.via_esportiva, "dificuldade", 1)
    cmd_enum_ok.executar_redo()
    assert esc.via_esportiva.dificuldade == 1

    # 4. Submensagem e Oneof com dict ou classe de mensagem incorreta
    with pytest.raises(TypeError, match="Coordenada"):
        CmdAlterarCampo(model, pico, "localizacao", {"latitude": -20, "longitude": -44})

    with pytest.raises(TypeError, match="Coordenada"):
        CmdAlterarCampo(model, pico, "localizacao", croqui_pb2.Trilha(nome="Errada"))

    with pytest.raises(TypeError, match="oneof"):
        CmdAlterarCampo(model, esc, "tipo", "boulder")

    with pytest.raises(ValueError, match="variante"):
        CmdAlterarCampo(model, esc, "tipo", ("variante_inexistente", croqui_pb2.Boulder()))
