# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand

import editor.legacy_views.area_principal as modulo_area_principal
from editor.core.workspace import ExperimentalWorkspace
from editor.legacy_views.area_principal import JanelaPrincipal


class _ComandoEdicaoTeste(QUndoCommand):
    """Comando real de histórico para sujar/limpar a pilha sem mocks."""

    def redo(self) -> None:
        pass

    def undo(self) -> None:
        pass


class ServidorFake(QObject):
    dispositivo_conectado = Signal()

    Instancias: list["ServidorFake"] = []

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.iniciado_vezes = 0
        self.parado_vezes = 0
        self.recarregamentos: list[str] = []
        self.porta = 8080
        self.conectado = False
        ServidorFake.Instancias.append(self)

    def iniciar(self) -> None:
        self.iniciado_vezes += 1

    def parar(self) -> None:
        self.parado_vezes += 1

    def obter_ip_local(self) -> str:
        return "192.168.1.5"

    def gerar_qr_code(self) -> bytes:
        return b"fake_png_data"

    def emitir_recarregamento(self, setor_id: str) -> None:
        self.recarregamentos.append(setor_id)


class DialogoFake(QObject):
    solicitar_encerrar = Signal()

    Instancias: list["DialogoFake"] = []

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.exec_vezes = 0
        DialogoFake.Instancias.append(self)

    def exec(self) -> int:
        self.exec_vezes += 1
        return 0

    def encerrar_tarefa(self) -> None:
        pass

    def close(self) -> bool:
        return True


@pytest.fixture
def ambiente_ui_celular(monkeypatch):
    ServidorFake.Instancias.clear()
    DialogoFake.Instancias.clear()
    monkeypatch.setattr(modulo_area_principal, "ServidorCelular", ServidorFake)
    monkeypatch.setattr(modulo_area_principal, "DialogoConexaoCelular", DialogoFake)


@pytest.fixture
def janela(qtbot, tmp_path):
    pasta_croqui = tmp_path / "41aea39b"
    (pasta_croqui / "database").mkdir(parents=True)
    (pasta_croqui / "metadados.json").write_text(
        '{"id_croqui": "br_mg_igarape_pedra_grande", "usuario": "Teste"}',
        encoding="utf-8",
    )
    (pasta_croqui / "database" / "croqui.yaml").write_text(
        "id: br_mg_igarape_pedra_grande\nnome: Pedra Grande\nultima_migracao: 5\n",
        encoding="utf-8",
    )
    janela = JanelaPrincipal()
    janela.workspace = ExperimentalWorkspace(pasta_croqui)
    janela._forcar_fechamento = True
    qtbot.addWidget(janela)
    return janela


def test_deve_iniciar_servidor_e_abrir_dialogo_ao_clicar_celular(
    qtbot, janela, ambiente_ui_celular
):
    janela.acao_celular.trigger()

    assert len(ServidorFake.Instancias) == 1
    assert janela.servidor_celular.iniciado_vezes == 1
    assert len(DialogoFake.Instancias) == 1
    assert janela.dialogo_celular.exec_vezes == 1


def test_deve_parar_servidor_ao_encerrar_dialogo(qtbot, janela, ambiente_ui_celular):
    janela.acao_celular.trigger()

    servidor_antes = janela.servidor_celular
    janela.dialogo_celular.solicitar_encerrar.emit()

    assert servidor_antes.parado_vezes == 1
    assert janela.servidor_celular is None


def test_deve_ativar_autosave_quando_celular_conectado(qtbot, janela, ambiente_ui_celular):
    chamadas_salvar: list[object] = []
    janela.salvar_croqui = lambda callback_sucesso=None: chamadas_salvar.append(callback_sucesso)

    janela.acao_celular.trigger()
    assert janela.monitor_inatividade is not None
    assert janela.monitor_inatividade.timer.isActive()

    # Como indice.binarypb e catalogo.db ainda não existem em compilado/, a inatividade dispara salvar
    janela.monitor_inatividade.inatividade_detectada.emit()
    assert len(chamadas_salvar) == 1


def test_nao_deve_disparar_autosave_por_inatividade_quando_historico_limpo_e_artefatos_presentes(
    qtbot, janela, ambiente_ui_celular
):
    pasta_comp = janela.workspace.obter_pasta_servidor_celular()
    pasta_comp.mkdir(parents=True, exist_ok=True)
    (pasta_comp / "indice.binarypb").write_bytes(b"pb")
    (pasta_comp / "catalogo.db").write_bytes(b"db")
    janela.croqui_data = {"id": "br_mg_igarape_pedra_grande"}

    chamadas_salvar: list[object] = []
    janela.salvar_croqui = lambda callback_sucesso=None: chamadas_salvar.append(callback_sucesso)

    janela.acao_celular.trigger()
    assert chamadas_salvar == []

    # 1. Histórico limpo e artefatos presentes -> inatividade de 10s NÃO deve salvar nem apagar compilado/
    janela.monitor_inatividade.inatividade_detectada.emit()
    assert chamadas_salvar == []

    # 2. Ao realizar uma edição no histórico (isClean() == False), a inatividade DEVE salvar
    janela.historico.push(_ComandoEdicaoTeste("Editar via"))
    assert not janela.historico.obter_pilha().isClean()

    janela.monitor_inatividade.inatividade_detectada.emit()
    assert len(chamadas_salvar) == 1


def test_deve_emitir_recarregamento_ao_salvar_sucesso_com_servidor_celular_ativo(qtbot, janela):
    servidor_fake = ServidorFake()
    janela.servidor_celular = servidor_fake
    janela.croqui_data = {"id": "br_mg_igarape_pedra_grande"}

    notificacoes: list[str] = []
    janela.exibir_notificacao = notificacoes.append

    janela._on_salvar_sucesso(Path("fake_caminho"), [], False, 0)
    assert notificacoes == ["Croqui salvo e compilado com sucesso!"]
    assert servidor_fake.recarregamentos == ["br_mg_igarape_pedra_grande"]


def test_deve_exibir_notificacao_e_emitir_recarregamento_mesmo_com_avisos_de_compilacao(
    qtbot, janela
):
    servidor_fake = ServidorFake()
    janela.servidor_celular = servidor_fake
    janela.croqui_data = {"id": "br_mg_igarape_pedra_grande"}

    notificacoes: list[str] = []
    janela.exibir_notificacao = notificacoes.append

    janela._on_salvar_sucesso(Path("fake_caminho"), ["Aviso: campo opcional vazio"], False, 0)
    assert len(notificacoes) == 1
    assert "avisos" in notificacoes[0].lower() or "sucesso" in notificacoes[0].lower()
    assert servidor_fake.recarregamentos == ["br_mg_igarape_pedra_grande"]


def test_acao_salvar_deve_possuir_atalho_ctrl_s_registrado_na_janela(qtbot, janela):
    from PySide6.QtGui import QKeySequence

    atalhos = [s.toString() for s in janela.acao_salvar.shortcuts()]
    atalho_padrao = QKeySequence(QKeySequence.StandardKey.Save).toString()
    assert atalho_padrao in atalhos or "Ctrl+S" in atalhos
    assert janela.acao_salvar in janela.actions()


def test_deve_salvar_croqui_antes_de_conectar_celular_quando_houver_modificacoes_pendentes(
    qtbot, janela, ambiente_ui_celular
):
    pasta_comp = janela.workspace.obter_pasta_servidor_celular()
    pasta_comp.mkdir(parents=True, exist_ok=True)
    (pasta_comp / "indice.binarypb").write_bytes(b"pb")
    (pasta_comp / "catalogo.db").write_bytes(b"db")
    janela.croqui_data = {"id": "br_mg_igarape_pedra_grande"}
    janela.historico.push(_ComandoEdicaoTeste("Alterar nome"))

    chamadas_salvar: list[object] = []
    janela.salvar_croqui = lambda callback_sucesso=None: chamadas_salvar.append(callback_sucesso)

    janela.acao_celular.trigger()
    assert chamadas_salvar == [janela._abrir_dialogo_conexao_celular]
    assert DialogoFake.Instancias == []


def test_deve_salvar_croqui_antes_de_conectar_celular_quando_catalogo_db_ausente(
    qtbot, janela, ambiente_ui_celular
):
    pasta_comp = janela.workspace.obter_pasta_servidor_celular()
    pasta_comp.mkdir(parents=True, exist_ok=True)
    (pasta_comp / "indice.binarypb").write_bytes(b"pb")
    # catalogo.db ausente
    janela.croqui_data = {"id": "br_mg_igarape_pedra_grande"}

    chamadas_salvar: list[object] = []
    janela.salvar_croqui = lambda callback_sucesso=None: chamadas_salvar.append(callback_sucesso)

    janela.acao_celular.trigger()
    assert chamadas_salvar == [janela._abrir_dialogo_conexao_celular]
    assert DialogoFake.Instancias == []


def test_deve_abrir_dialogo_direto_quando_limpo_e_artefatos_presentes(
    qtbot, janela, ambiente_ui_celular
):
    pasta_comp = janela.workspace.obter_pasta_servidor_celular()
    pasta_comp.mkdir(parents=True, exist_ok=True)
    (pasta_comp / "indice.binarypb").write_bytes(b"pb")
    (pasta_comp / "catalogo.db").write_bytes(b"db")
    janela.croqui_data = {"id": "br_mg_igarape_pedra_grande"}

    chamadas_salvar: list[object] = []
    janela.salvar_croqui = lambda callback_sucesso=None: chamadas_salvar.append(callback_sucesso)

    janela.acao_celular.trigger()
    assert chamadas_salvar == []
    assert len(DialogoFake.Instancias) == 1


def test_salvar_croqui_usa_id_atual_do_workspace_sem_confundir_pasta_uuid(qtbot, janela):
    """Garante que salvar_croqui obtém id_atual via workspace.obter_id_croqui_atual() e não do nome UUID da pasta."""
    from PIL import Image

    from scripts.gerenciar_uids_lib import gerar_uid
    from scripts.migrador import obter_ultima_versao_migracao

    pasta_db = janela.workspace.obter_caminho_database()
    (pasta_db / "imagens").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), color="green").save(pasta_db / "imagens" / "capa.webp", "WEBP")

    janela.croqui_data = {
        "uid": gerar_uid(),
        "id": "br_mg_igarape_pedra_grande",
        "nome": "Pedra Grande",
        "ultima_migracao": obter_ultima_versao_migracao(),
        "caminho_thumbnail": "imagens/capa.webp",
        "picos": [{"uid": gerar_uid(), "nome": "Pedra Grande", "estado": "MG"}],
    }
    janela.croqui_model = None
    janela.exibir_notificacao = lambda _msg: None

    with qtbot.waitSignal(janela.salvamento_finalizado, timeout=5000):
        janela.salvar_croqui()

    assert janela._worker_salvar.id_atual == "br_mg_igarape_pedra_grande"
    assert janela._worker_salvar.novo_id == "br_mg_igarape_pedra_grande"
