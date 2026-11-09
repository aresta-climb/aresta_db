# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtGui import QPixmap

from editor.core.servidor_celular_fake import ServidorCelularFake


def test_servidor_celular_fake_ciclo_vida_qr_code_e_recarregamento(qtbot, tmp_path: Path) -> None:
    servidor = ServidorCelularFake(
        pasta_compilado=tmp_path,
        codigo_sessao="abcd2345",
        jwt_token="jwt_teste",
    )

    assert servidor.obter_ip_local() == "127.0.0.1"
    assert servidor.solicitar_sessao_servidor() is True
    servidor.iniciar()
    assert servidor.porta == 8765
    url = servidor.obter_url_previa_canonica()
    assert "127.0.0.1:8765" in url
    assert "abcd2345" in url

    qr_bytes = servidor.gerar_qr_code(url)
    assert qr_bytes.startswith(b"\x89PNG")
    pixmap = QPixmap()
    assert pixmap.loadFromData(qr_bytes) is True

    conexoes: list[bool] = []
    servidor.dispositivo_conectado.connect(lambda: conexoes.append(True))
    servidor.simular_conexao_dispositivo()
    assert servidor.conectado is True
    assert conexoes == [True]

    servidor.emitir_recarregamento("setor_principal")
    assert servidor.recarregamentos_emitidos == ["setor_principal"]

    servidor.parar()
    assert servidor.conectado is False


def test_servidor_celular_fake_simulacao_erro_previa_e_criacao_sessao(tmp_path: Path) -> None:
    import pytest

    servidor_sem_codigo = ServidorCelularFake(pasta_compilado=tmp_path)
    servidor_sem_codigo.codigo_sessao = None
    assert servidor_sem_codigo.solicitar_sessao_servidor() is True
    assert servidor_sem_codigo.codigo_sessao == "abcd2345"

    servidor_erro = ServidorCelularFake(
        pasta_compilado=tmp_path,
        erro_previa=RuntimeError("Falha simulada na prévia"),
    )
    assert servidor_erro.codigo_sessao is None
    assert servidor_erro.solicitar_sessao_servidor() is False
    with pytest.raises(RuntimeError, match="Falha simulada na prévia"):
        servidor_erro.obter_url_previa_canonica()
