# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import threading
import time

import pytest
from PySide6.QtCore import QCoreApplication, QThread

from editor.mcp.despachante import DespachanteQt


def test_despachante_executa_diretamente_quando_na_thread_principal(qapp):
    """Quando chamado da própria thread principal do Qt, executa imediatamente na thread principal."""
    despachante = DespachanteQt()
    thread_principal = despachante.thread()

    def somar_e_verificar_thread(a: int, b: int, multiplicador: int = 1) -> tuple[int, bool]:
        return (a + b) * multiplicador, QThread.currentThread() == thread_principal

    resultado, executou_na_principal = despachante.executar(
        somar_e_verificar_thread, 3, 4, multiplicador=2
    )
    assert resultado == 14
    assert executou_na_principal is True


def test_despachante_propaga_excecao_na_thread_principal(qapp):
    """Exceções lançadas pela função na thread principal devem ser propagadas ao chamador."""
    despachante = DespachanteQt()

    def falhar() -> None:
        raise ValueError("Erro de validação no modelo")

    with pytest.raises(ValueError, match="Erro de validação no modelo"):
        despachante.executar(falhar)


def test_despachante_executa_na_thread_principal_a_partir_de_thread_secundaria(qapp):
    """Chamadas originadas em threads secundárias (ex: Uvicorn) devem rodar na thread principal do Qt."""
    despachante = DespachanteQt()
    thread_principal = despachante.thread()
    resultado_box: dict[str, object] = {}
    concluido = threading.Event()

    def tarefa_gui(valor: str) -> tuple[str, bool]:
        return f"processado:{valor}", QThread.currentThread() == thread_principal

    def trabalhador() -> None:
        res, na_principal = despachante.executar(tarefa_gui, "croqui", timeout=2.0)
        resultado_box["res"] = res
        resultado_box["na_principal"] = na_principal
        concluido.set()

    t = threading.Thread(target=trabalhador, daemon=True)
    t.start()

    prazo = time.monotonic() + 2.0
    while not concluido.is_set() and time.monotonic() < prazo:
        QCoreApplication.processEvents()
        time.sleep(0.005)

    t.join(timeout=1.0)
    assert concluido.is_set()
    assert resultado_box["res"] == "processado:croqui"
    assert resultado_box["na_principal"] is True


def test_despachante_propaga_excecao_para_thread_secundaria(qapp):
    """Exceções ocorridas na thread principal devem ser relançadas na thread secundária chamadora."""
    despachante = DespachanteQt()
    erro_capturado: list[Exception] = []
    concluido = threading.Event()

    def tarefa_com_erro() -> None:
        raise RuntimeError("Falha ao aplicar comando no histórico")

    def trabalhador() -> None:
        try:
            despachante.executar(tarefa_com_erro, timeout=2.0)
        except Exception as exc:
            erro_capturado.append(exc)
        finally:
            concluido.set()

    t = threading.Thread(target=trabalhador, daemon=True)
    t.start()

    prazo = time.monotonic() + 2.0
    while not concluido.is_set() and time.monotonic() < prazo:
        QCoreApplication.processEvents()
        time.sleep(0.005)

    t.join(timeout=1.0)
    assert len(erro_capturado) == 1
    assert isinstance(erro_capturado[0], RuntimeError)
    assert "Falha ao aplicar comando no histórico" in str(erro_capturado[0])


def test_despachante_lanca_timeout_quando_fila_nao_processa_a_tempo(qapp):
    """Se a thread principal não processar o evento dentro do timeout, deve lançar TimeoutError e cancelar a tarefa."""
    despachante = DespachanteQt()
    executou_apos_timeout = False
    erro_capturado: list[Exception] = []

    def tarefa_atrasada() -> None:
        nonlocal executou_apos_timeout
        executou_apos_timeout = True

    def trabalhador() -> None:
        try:
            despachante.executar(tarefa_atrasada, timeout=0.02)
        except Exception as exc:
            erro_capturado.append(exc)

    t = threading.Thread(target=trabalhador, daemon=True)
    t.start()
    # Não processamos eventos do Qt enquanto a thread aguarda para provocar o timeout
    t.join(timeout=1.0)

    assert len(erro_capturado) == 1
    assert isinstance(erro_capturado[0], TimeoutError)

    # Agora que o evento atrasado é drenado pela thread principal, ele deve ser ignorado pois foi cancelado
    QCoreApplication.processEvents()
    assert executou_apos_timeout is False


def test_despachante_aguarda_execucao_ja_iniciada_sem_split_brain(qapp):
    """
    Se a tarefa já iniciou na thread principal do Qt e ultrapassar o timeout de enfileiramento,
    mas concluir antes de timeout_execucao, deve retornar o resultado real sem falso TimeoutError.
    """
    despachante = DespachanteQt(timeout_execucao_padrao=1.0)
    resultado_box: dict[str, object] = {}
    erro_box: list[Exception] = []
    concluido = threading.Event()
    iniciou_qt = threading.Event()

    def mutacao_longa() -> str:
        iniciou_qt.set()
        time.sleep(0.08)
        return "mutacao_concluida"

    def trabalhador() -> None:
        try:
            resultado_box["res"] = despachante.executar(
                mutacao_longa, timeout=0.02, timeout_execucao=1.0
            )
        except Exception as exc:
            erro_box.append(exc)
        finally:
            concluido.set()

    t = threading.Thread(target=trabalhador, daemon=True)
    t.start()

    # Drena eventos até a função iniciar na thread principal e bloqueia nela por ~80ms
    prazo = time.monotonic() + 1.0
    while not concluido.is_set() and time.monotonic() < prazo:
        QCoreApplication.processEvents()
        time.sleep(0.002)

    t.join(timeout=1.0)
    assert iniciou_qt.is_set()
    assert erro_box == []
    assert resultado_box.get("res") == "mutacao_concluida"


def test_despachante_lanca_timeout_quando_execucao_iniciada_excede_timeout_execucao(qapp):
    """
    Se uma execução já iniciada na thread principal ultrapassar também `timeout_execucao`,
    deve lançar TimeoutError informando explicitamente que a execução já havia iniciado.
    """
    despachante = DespachanteQt(timeout_execucao_padrao=0.05)
    erro_box: list[Exception] = []
    concluido = threading.Event()

    def mutacao_travada() -> str:
        time.sleep(0.15)
        return "tarde_demais"

    def trabalhador() -> None:
        try:
            despachante.executar(mutacao_travada, timeout=0.01, timeout_execucao=0.04)
        except Exception as exc:
            erro_box.append(exc)
        finally:
            concluido.set()

    t = threading.Thread(target=trabalhador, daemon=True)
    t.start()

    prazo = time.monotonic() + 1.0
    while not concluido.is_set() and time.monotonic() < prazo:
        QCoreApplication.processEvents()
        time.sleep(0.002)

    t.join(timeout=1.0)
    assert len(erro_box) == 1
    assert isinstance(erro_box[0], TimeoutError)
    assert "já iniciada" in str(erro_box[0])
