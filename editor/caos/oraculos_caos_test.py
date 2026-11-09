# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import shiboken6
from PySide6.QtGui import QUndoCommand
from PySide6.QtWidgets import QWidget

from aresta_api.proto.generated import croqui_pb2
from editor.caos.oraculos_caos import OraculosCaos
from editor.commands.comandos_protobuf import CmdAlterarCampo
from editor.core.diario import GerenciadorDiario
from editor.core.historico import GerenciadorHistorico
from editor.models.croqui_model import CroquiModel
from scripts.gerenciar_uids_lib import gerar_uid


def test_oraculo_captura_excecao_em_sys_e_threading_excepthook() -> None:
    oraculos = OraculosCaos()
    with oraculos.monitorar_excecoes():
        try:
            raise RuntimeError("Internal C++ object (QTreeView) already deleted.")
        except RuntimeError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)

    falha = oraculos.obter_primeira_falha()
    assert falha is not None
    assert falha.oraculo == "excecao_nao_tratada"
    assert falha.tipo_excecao == "RuntimeError"
    assert "QTreeView" in falha.mensagem
    assert "oraculos_caos_test.py" in falha.frame_principal

    oraculos.limpar_falhas()
    assert oraculos.obter_primeira_falha() is None

    with oraculos.monitorar_excecoes():
        try:
            raise ValueError("Falha em QThread worker")
        except ValueError as exc:
            args = SimpleNamespace(
                exc_type=type(exc),
                exc_value=exc,
                exc_traceback=exc.__traceback__,
                thread=threading.current_thread(),
            )
            threading.excepthook(args)  # type: ignore[arg-type]

    falha_thread = oraculos.obter_primeira_falha()
    assert falha_thread is not None
    assert falha_thread.tipo_excecao == "ValueError"

    oraculos.limpar_falhas()
    falha_sem_tb = oraculos.registrar_excecao(RuntimeError, RuntimeError("Sem TB"), None)
    assert falha_sem_tb.frame_principal == "frame_desconhecido:0"
    assert falha_sem_tb.excecao_original is not None
    assert falha_sem_tb.excecao_original.__traceback__ is not None


def test_oraculo_detecta_objeto_qt_cpp_deletado(qtbot) -> None:  # type: ignore[no-untyped-def]
    oraculos = OraculosCaos()
    widget_vivo = QWidget()
    qtbot.addWidget(widget_vivo)
    assert oraculos.verificar_integridade_objetos_qt([widget_vivo]) is None

    widget_morto = QWidget()
    shiboken6.delete(widget_morto)
    falha = oraculos.verificar_integridade_objetos_qt([widget_morto])
    assert falha is not None
    assert falha.oraculo == "objeto_cpp_deletado"
    assert falha.excecao_original is not None
    assert falha.excecao_original.__traceback__ is not None
    assert "Traceback (most recent call last):" in falha.stacktrace


def test_oraculo_simetria_undo_redo_aprova_comandos_simetricos_e_coalescencia() -> None:
    croqui = croqui_pb2.Croqui(id="br_mg_teste", uid=gerar_uid(), nome="Inicial")
    model = CroquiModel(croqui)
    historico = GerenciadorHistorico()
    historico.intervalo_debounce_ms = 0

    oraculos = OraculosCaos()
    oraculos.ressincronizar_estado_base(model, historico)

    # 1. Primeiro comando normal
    cmd_1 = CmdAlterarCampo(model, croqui, "nome", valor_novo="Editado 1", pode_mesclar=True)
    historico.executar(cmd_1)
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False) is None

    # 2. Segundo comando coalescido (mergeWith mantém o mesmo índice na pilha!)
    cmd_2 = CmdAlterarCampo(model, croqui, "nome", valor_novo="Editado 2", pode_mesclar=True)
    historico.executar(cmd_2)
    assert historico.obter_pilha().index() == 1
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False) is None

    # 3. Passo que não altera nem o índice nem o estado (no-op de visualização)
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False) is None

    # 4. Empilha segundo comando distinto (índice 2), desfaz 2 vezes (volta ao 0) e empilha ramo novo (índice 1 < 2)
    cmd_extra = CmdAlterarCampo(model, croqui, "descricao", valor_novo="Desc 2")
    historico.executar(cmd_extra)
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False) is None

    historico.desfazer()
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=True) is None
    historico.desfazer()
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=True) is None

    model.definir_imagem_memoria("imagens/teste.png", b"png_bytes")
    model.definir_anexo_memoria("anexos/doc.md", b"md_bytes")
    cmd_3 = CmdAlterarCampo(model, croqui, "nome", valor_novo="Ramo Novo")
    historico.executar(cmd_3)
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False) is None


def test_oraculo_simetria_detecta_mutacao_sem_comando_e_undo_assimetrico() -> None:
    croqui = croqui_pb2.Croqui(id="br_mg_teste", uid=gerar_uid(), nome="Original")
    model = CroquiModel(croqui)
    historico = GerenciadorHistorico()
    oraculos = OraculosCaos()
    oraculos.ressincronizar_estado_base(model, historico)

    # Violação do Princípio VIII: mutação direta no modelo sem empilhar comando
    croqui.nome = "Mutado Fora do Historico"
    falha_viii = oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False)
    assert falha_viii is not None
    assert falha_viii.oraculo == "violacao_principio_viii"
    assert falha_viii.excecao_original is not None
    assert falha_viii.excecao_original.__traceback__ is not None
    assert "Traceback (most recent call last):" in falha_viii.stacktrace

    # Ressincroniza e testa um comando com undo() defeituoso (assimétrico)
    oraculos.ressincronizar_estado_base(model, historico)

    class _CmdAssimetricoBugado(QUndoCommand):
        def __init__(self) -> None:
            super().__init__("Comando Bugado")

        def redo(self) -> None:
            croqui.descricao = "Nova Descricao"

        def undo(self) -> None:
            # Bug: esqueceu de limpar ou colocou valor diferente do estado anterior
            croqui.descricao = "Descricao Suja Residual"

    historico.executar(_CmdAssimetricoBugado())
    assert oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=False) is None

    historico.desfazer()
    falha_undo = oraculos.auditar_passo_historico(model, historico, foi_undo_ou_redo=True)
    assert falha_undo is not None
    assert falha_undo.oraculo == "assimetria_undo_redo"
    assert "Comando Bugado" in falha_undo.mensagem
    assert falha_undo.excecao_original is not None
    assert falha_undo.excecao_original.__traceback__ is not None
    assert "Traceback (most recent call last):" in falha_undo.stacktrace


def test_oraculo_diario_valida_diario_integro_e_detecta_corrupcao(
    tmp_path: Path,
) -> None:
    diario = GerenciadorDiario(tmp_path)
    oraculos = OraculosCaos()

    assert oraculos.verificar_integridade_diario(None) is None
    assert oraculos.verificar_integridade_diario(diario) is None

    diario.gravar_comando_pendente({"tipo": "CmdAlterarCampo", "campo_nome": "nome"})
    assert oraculos.verificar_integridade_diario(diario) is None

    diario.consolidar_salvamento()
    assert oraculos.verificar_integridade_diario(diario) is None

    # Corrompe diario_pendente.bin com um objeto pickle malformado (dicionário vazio / não-dict)
    import pickle

    with open(diario.caminho_pendente, "wb") as f:
        pickle.dump({}, f)

    falha_malformado = oraculos.verificar_integridade_diario(diario)
    assert falha_malformado is not None
    assert falha_malformado.oraculo == "corrupcao_diario"
    assert falha_malformado.excecao_original is not None
    assert falha_malformado.excecao_original.__traceback__ is not None
    assert "Traceback (most recent call last):" in falha_malformado.stacktrace


def test_oraculo_captura_erros_e_excecoes_registrados_no_logger() -> None:
    from editor.core.registro_log import obter_logger

    log = obter_logger("teste_caos")
    oraculos = OraculosCaos()

    with oraculos.monitorar_excecoes():
        try:
            raise OSError(22, "Invalid argument")
        except OSError:
            log.critical("Erro durante o salvamento do croqui", exc_info=True)

    falha_com_exc = oraculos.obter_primeira_falha()
    assert falha_com_exc is not None
    assert falha_com_exc.oraculo == "erro_registrado_log"
    assert falha_com_exc.tipo_excecao == "OSError"
    assert "Invalid argument" in falha_com_exc.mensagem
    assert falha_com_exc.excecao_original is not None
    assert falha_com_exc.excecao_original.__traceback__ is not None

    oraculos.limpar_falhas()
    with oraculos.monitorar_excecoes():
        log.error("Falha sem exc_info ao processar comando")

    falha_sem_exc = oraculos.obter_primeira_falha()
    assert falha_sem_exc is not None
    assert falha_sem_exc.oraculo == "erro_registrado_log"
    assert falha_sem_exc.tipo_excecao == "LogError"
    assert "Falha sem exc_info" in falha_sem_exc.mensagem
    assert falha_sem_exc.excecao_original is not None
    assert falha_sem_exc.excecao_original.__traceback__ is not None
    assert "Traceback (most recent call last):" in falha_sem_exc.stacktrace
