# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QMainWindow

from editor.core.instancia_unica import (
    NOME_SERVIDOR_SELECAO,
    ativar_janela_existente,
    encerrar_servidor_local,
    extrair_id_croqui_de_pasta,
    iniciar_servidor_instancia_unica,
    iniciar_trava_croqui,
    iniciar_trava_selecao,
    obter_nome_servidor_croqui,
    obter_nome_servidor_selecao,
    trava_arquivo_operacao,
    verificar_croqui_ja_aberto,
    verificar_se_ja_em_execucao,
    verificar_selecao_ja_aberta,
)


def test_obter_nomes_servidor_com_e_sem_prefixo_e_validacao_vazia(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica geração de nomes escopados, prefixo IPC em testes e ValueError para ID vazio."""
    monkeypatch.delenv("ARESTA_PREFIXO_IPC", raising=False)
    assert obter_nome_servidor_selecao() == NOME_SERVIDOR_SELECAO
    assert obter_nome_servidor_croqui("br_mg_cipo") == "ArestaEditorCroqui_br_mg_cipo"
    assert obter_nome_servidor_croqui("croqui/com espaco") == "ArestaEditorCroqui_croqui_com_espaco"

    monkeypatch.setenv("ARESTA_PREFIXO_IPC", "TesteUnit_")
    assert obter_nome_servidor_selecao() == f"TesteUnit_{NOME_SERVIDOR_SELECAO}"
    assert obter_nome_servidor_croqui("br_mg_cipo") == "TesteUnit_ArestaEditorCroqui_br_mg_cipo"

    for invalido in ("   ", "///"):
        with pytest.raises(ValueError, match="identificador do croqui"):
            obter_nome_servidor_croqui(invalido)


def test_extrair_id_croqui_de_pasta_cinco_cenarios(tmp_path: Path) -> None:
    """Valida extração de id em modo local, experimental, YAML inválido, sem id e sem arquivo."""
    pasta_local = tmp_path / "pasta_local"
    pasta_local.mkdir()
    (pasta_local / "croqui.yaml").write_text(
        "id: br_mg_local_real\nnome: Local\n", encoding="utf-8"
    )
    assert extrair_id_croqui_de_pasta(pasta_local) == "br_mg_local_real"

    pasta_exp = tmp_path / "uuid_exp"
    (pasta_exp / "database").mkdir(parents=True)
    (pasta_exp / "database" / "croqui.yaml").write_text(
        "id: br_sp_experimental\nnome: Exp\n", encoding="utf-8"
    )
    assert extrair_id_croqui_de_pasta(pasta_exp) == "br_sp_experimental"

    pasta_yaml_erro = tmp_path / "pasta_yaml_invalido"
    pasta_yaml_erro.mkdir()
    (pasta_yaml_erro / "croqui.yaml").write_text("::: [invalido\n", encoding="utf-8")
    assert extrair_id_croqui_de_pasta(pasta_yaml_erro) == "pasta_yaml_invalido"

    pasta_sem_id = tmp_path / "pasta_sem_id"
    pasta_sem_id.mkdir()
    (pasta_sem_id / "croqui.yaml").write_text("nome: Sem ID\n", encoding="utf-8")
    assert extrair_id_croqui_de_pasta(pasta_sem_id) == "pasta_sem_id"

    pasta_vazia = tmp_path / "pasta_sem_yaml"
    pasta_vazia.mkdir()
    assert extrair_id_croqui_de_pasta(pasta_vazia) == "pasta_sem_yaml"


def test_trava_selecao_e_encerrar_servidor_local(qtbot, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica ciclo de vida da trava da tela de seleção isolada e encerramento seguro."""
    prefixo = f"Sel_{uuid.uuid4().hex[:8]}_"
    monkeypatch.setenv("ARESTA_PREFIXO_IPC", prefixo)

    ativacoes: list[str] = []
    assert verificar_selecao_ja_aberta(timeout_ms=50) is False

    srv = iniciar_trava_selecao(callback_ativacao=lambda: ativacoes.append("selecao"))
    assert srv is not None
    try:
        assert verificar_selecao_ja_aberta(timeout_ms=500) is True
        assert ativacoes == ["selecao"]
    finally:
        encerrar_servidor_local(srv)

    assert verificar_selecao_ja_aberta(timeout_ms=50) is False

    # Casos de fronteira de encerrar_servidor_local: None e QLocalServer não iniciado
    encerrar_servidor_local(None)
    srv_nao_iniciado = QLocalServer()
    assert srv_nao_iniciado.serverName() == ""
    encerrar_servidor_local(srv_nao_iniciado)


def test_travas_independentes_por_croqui_permitem_multiplos_croquis(qtbot):
    """
    Verifica que dois croquis distintos ('croqui_a' e 'croqui_b') podem manter travas
    ativas simultaneamente, enquanto tentar abrir 'croqui_a' novamente aciona o callback de elevação.
    """
    id_a = f"croqui_a_{uuid.uuid4().hex[:6]}"
    id_b = f"croqui_b_{uuid.uuid4().hex[:6]}"
    ativacoes_a: list[str] = []
    ativacoes_b: list[str] = []

    srv_a = iniciar_trava_croqui(id_a, callback_ativacao=lambda: ativacoes_a.append(id_a))
    srv_b = iniciar_trava_croqui(id_b, callback_ativacao=lambda: ativacoes_b.append(id_b))
    assert srv_a is not None
    assert srv_b is not None

    try:
        assert verificar_croqui_ja_aberto(id_a, timeout_ms=500) is True
        assert ativacoes_a == [id_a]
        assert ativacoes_b == []

        assert verificar_croqui_ja_aberto(id_b, timeout_ms=500) is True
        assert ativacoes_b == [id_b]

        id_c = f"croqui_c_{uuid.uuid4().hex[:6]}"
        assert verificar_croqui_ja_aberto(id_c, timeout_ms=50) is False
    finally:
        srv_a.close()
        srv_b.close()
        QLocalServer.removeServer(obter_nome_servidor_croqui(id_a))
        QLocalServer.removeServer(obter_nome_servidor_croqui(id_b))


def test_trava_arquivo_operacao_cria_remove_e_recupera_lock_obsoleto(tmp_path: Path):
    """Verifica exclusão mútua via lockfile, limpeza de lock obsoleto e erro de timeout."""
    caminho_lock = tmp_path / "git_operacao.lock"

    with trava_arquivo_operacao(caminho_lock, timeout_s=0.5):
        assert caminho_lock.is_file()
        # Tentar adquirir novamente enquanto ativo e recente deve expirar por timeout
        with pytest.raises(TimeoutError, match="Não foi possível adquirir trava"):
            with trava_arquivo_operacao(caminho_lock, timeout_s=0.05):
                pass

    assert not caminho_lock.exists()

    # Simula lockfile órfão antigo (mtime no passado) -> deve ser limpo e adquirido
    caminho_lock.write_text("orfao", encoding="utf-8")
    import os
    import time

    antigo = time.time() - 3600
    os.utime(caminho_lock, (antigo, antigo))

    with trava_arquivo_operacao(caminho_lock, timeout_s=0.2):
        assert caminho_lock.is_file()
    assert not caminho_lock.exists()


def test_verificar_se_ja_em_execucao_quando_nenhum_servidor_ativo(qtbot):
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    assert verificar_se_ja_em_execucao(nome_servidor, timeout_ms=50) is False


def test_verificar_se_ja_em_execucao_com_servidor_real_ativo(qtbot):
    """Testa que uma instância ativa real responde ao PING com PONG."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"

    server_code = f'''
from PySide6.QtCore import QCoreApplication
from editor.core.instancia_unica import iniciar_servidor_instancia_unica
import sys

app = QCoreApplication(sys.argv)
srv = iniciar_servidor_instancia_unica("{nome_servidor}")
print("SERVER_READY", flush=True)
sys.exit(app.exec())
'''
    proc = subprocess.Popen([sys.executable, "-c", server_code], stdout=subprocess.PIPE, text=True)
    try:
        assert proc.stdout is not None
        linha = proc.stdout.readline()
        assert "SERVER_READY" in linha

        ja_executando = verificar_se_ja_em_execucao(nome_servidor, timeout_ms=1000)
        assert ja_executando is True
    finally:
        proc.terminate()
        proc.wait()
        QLocalServer.removeServer(nome_servidor)


def test_verificar_se_ja_em_execucao_recupera_de_servidor_zumbi(qtbot):
    """Testa que um servidor mudo/zumbi é detectado como não responsivo e a trava é limpa."""
    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"

    server_code = f'''
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer
import sys

app = QCoreApplication(sys.argv)
srv = QLocalServer()
QLocalServer.removeServer("{nome_servidor}")
srv.listen("{nome_servidor}")
print("ZOMBIE_READY", flush=True)
sys.exit(app.exec())
'''
    proc = subprocess.Popen([sys.executable, "-c", server_code], stdout=subprocess.PIPE, text=True)
    try:
        assert proc.stdout is not None
        linha = proc.stdout.readline()
        assert "ZOMBIE_READY" in linha

        ja_executando = verificar_se_ja_em_execucao(nome_servidor, timeout_ms=300)
        assert ja_executando is False
    finally:
        proc.terminate()
        proc.wait()
        QLocalServer.removeServer(nome_servidor)


def test_ativar_janela_existente_comportamento_real(qtbot):
    """Verifica ativar_janela_existente sem janelas, com janela visível e com janela minimizada."""
    from PySide6.QtWidgets import QApplication

    for w in QApplication.topLevelWidgets():
        w.hide()
    QApplication.processEvents()

    assert ativar_janela_existente() is False

    janela = QMainWindow()
    qtbot.addWidget(janela)
    janela.showMinimized()
    assert ativar_janela_existente(janela_alvo=janela) is True
    assert not janela.isMinimized()

    janela.show()
    assert ativar_janela_existente() is True
    janela.hide()
    QApplication.processEvents()


def test_servidor_desconexao_e_rejeicao_sem_janela(qtbot):
    """Testa desconexão de cliente e resposta SEM_JANELA quando fora da tolerância e sem janela."""
    from PySide6.QtWidgets import QApplication

    for w in QApplication.topLevelWidgets():
        w.hide()
    QApplication.processEvents()

    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    srv = iniciar_servidor_instancia_unica(
        nome_servidor, callback_ativacao=None, tempo_tolerancia_inicializacao_s=0.0
    )
    assert srv is not None
    try:
        cliente = QLocalSocket()
        cliente.connectToServer(nome_servidor)
        assert cliente.waitForConnected(500)
        qtbot.wait(30)
        assert len(srv._clientes_ativos) == 1  # type: ignore[attr-defined]

        cliente.write(b"PING\n")
        cliente.flush()
        qtbot.waitUntil(lambda: cliente.bytesAvailable() > 0, timeout=1000)
        resposta = bytes(cliente.readAll().data())
        assert b"SEM_JANELA" in resposta
        assert not srv.isListening()
        cliente.disconnectFromServer()
        qtbot.wait(50)
        assert len(srv._clientes_ativos) == 0  # type: ignore[attr-defined]
    finally:
        srv.close()
        QLocalServer.removeServer(nome_servidor)

    # Também exercita verificar_se_ja_em_execucao recebendo SEM_JANELA direto
    nome_srv2 = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    srv2 = iniciar_servidor_instancia_unica(
        nome_srv2, callback_ativacao=None, tempo_tolerancia_inicializacao_s=0.0
    )
    assert srv2 is not None
    try:
        assert verificar_se_ja_em_execucao(nome_srv2, timeout_ms=300) is False
    finally:
        srv2.close()
        QLocalServer.removeServer(nome_srv2)


def test_servidor_responde_pong_com_janela_visivel(qtbot):
    """Testa que servidor sem callback customizado ativa a janela visível e responde PONG."""
    janela = QMainWindow()
    qtbot.addWidget(janela)
    janela.show()

    nome_servidor = f"aresta_teste_{uuid.uuid4().hex[:8]}"
    srv = iniciar_servidor_instancia_unica(nome_servidor, callback_ativacao=None)
    assert srv is not None
    try:
        cliente = QLocalSocket()
        cliente.connectToServer(nome_servidor)
        assert cliente.waitForConnected(500)
        cliente.write(b"PING\n")
        cliente.flush()
        qtbot.waitUntil(lambda: cliente.bytesAvailable() > 0, timeout=1000)
        resposta = bytes(cliente.readAll().data())
        assert b"PONG" in resposta
        cliente.disconnectFromServer()
    finally:
        janela.hide()
        srv.close()
        QLocalServer.removeServer(nome_servidor)


def test_servidor_nome_invalido_retorna_none():
    """Garante retorno None quando QLocalServer.listen falhar por nome vazio."""
    assert iniciar_servidor_instancia_unica("") is None
