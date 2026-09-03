# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from unittest.mock import MagicMock
import pytest
from editor.core.temporizador_coalescencia import TemporizadorCoalescencia


class TestTemporizadorCoalescencia:
    def test_agendamento_e_disparo_apos_intervalo(self, qtbot):
        callback = MagicMock()
        temporizador = TemporizadorCoalescencia(atraso_padrao_ms=50)

        assert temporizador.esta_ativo() is False

        temporizador.agendar(callback)
        assert temporizador.esta_ativo() is True

        # Aguarda a expiração do temporizador
        qtbot.waitUntil(lambda: callback.call_count == 1, timeout=1000)
        assert temporizador.esta_ativo() is False
        assert callback.call_count == 1

    def test_reagendamento_reinicia_contagem(self, qtbot):
        callback = MagicMock()
        temporizador = TemporizadorCoalescencia(atraso_padrao_ms=80)

        temporizador.agendar(callback)
        qtbot.wait(40)
        assert callback.call_count == 0

        # Reagenda antes de expirar
        temporizador.agendar(callback)
        qtbot.wait(50)
        # 40ms + 50ms = 90ms total, mas o timer reiniciou aos 40ms, então ainda não expirou
        assert callback.call_count == 0

        # Aguarda o restante do segundo ciclo
        qtbot.waitUntil(lambda: callback.call_count == 1, timeout=1000)
        assert callback.call_count == 1

    def test_descartar_cancela_execucao(self, qtbot):
        callback = MagicMock()
        temporizador = TemporizadorCoalescencia(atraso_padrao_ms=50)

        temporizador.agendar(callback)
        assert temporizador.esta_ativo() is True

        temporizador.descartar()
        assert temporizador.esta_ativo() is False

        qtbot.wait(100)
        assert callback.call_count == 0

    def test_forcar_descarga_executa_imediatamente(self):
        callback = MagicMock()
        temporizador = TemporizadorCoalescencia(atraso_padrao_ms=10000)

        temporizador.agendar(callback)
        assert temporizador.esta_ativo() is True

        temporizador.forcar_descarga()
        assert callback.call_count == 1
        assert temporizador.esta_ativo() is False

    def test_forcar_descarga_sem_agendamento_nao_falha(self):
        temporizador = TemporizadorCoalescencia(atraso_padrao_ms=50)
        assert temporizador.esta_ativo() is False
        temporizador.forcar_descarga()
        assert temporizador.esta_ativo() is False

    def test_agendar_substitui_callback_anterior(self, qtbot):
        callback_antigo = MagicMock()
        callback_novo = MagicMock()
        temporizador = TemporizadorCoalescencia(atraso_padrao_ms=60)

        temporizador.agendar(callback_antigo)
        temporizador.agendar(callback_novo)

        qtbot.waitUntil(lambda: callback_novo.call_count == 1, timeout=1000)
        assert callback_antigo.call_count == 0
        assert callback_novo.call_count == 1
