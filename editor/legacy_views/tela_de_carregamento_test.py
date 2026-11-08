# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QPushButton, QWidget

from editor.core.cliente_auth_supabase_fake import ClienteAuthSupabaseFake
from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.gerenciador_sessao_fake import GerenciadorSessaoFake
from editor.core.serializacao_util import carregar_yaml, serializar_yaml
from editor.core.storage import GerenciadorCaminhos
from editor.legacy_views.dialogo_busca_croqui import DialogoBuscaCroqui
from editor.legacy_views.tela_de_carregamento import DialogoNovoCroqui, TelaDeCarregamento
from editor.views.dialogos.dialogo_perfil_autor import DialogoPerfilAutor


def _interagir_com_modal_ativo(parent: QWidget, acao: Callable[[QWidget], None]) -> None:
    """Aguarda a abertura de um modal filho e executa `acao`, fechando-o com segurança em caso de erro."""
    timer = QTimer(parent)
    timer.setInterval(10)

    def _verificar() -> None:
        modal = QApplication.activeModalWidget()
        if modal is not None and modal is not parent:
            timer.stop()
            try:
                acao(modal)
            except Exception:
                modal.reject()
                raise

    timer.timeout.connect(_verificar)
    timer.start()


@pytest.fixture
def storage_real(tmp_path: Path) -> GerenciadorCaminhos:
    storage = GerenciadorCaminhos(diretorio_base=tmp_path / "editor_aresta")
    storage.inicializar_diretorios()
    return storage


def test_tela_de_carregamento_e_um_dialog(qtbot):
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    assert isinstance(tela, QDialog)


def test_tela_de_carregamento_tem_botoes_com_nomes_completos(qtbot):
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)

    botoes = tela.findChildren(QPushButton)
    textos_botoes = [b.text() for b in botoes]

    assert "Novo croqui" in textos_botoes
    assert "Editar croqui oficial" in textos_botoes
    assert "Importar croqui experimental" not in textos_botoes


def test_tela_de_carregamento_carrega_croquis(qtbot, storage_real: GerenciadorCaminhos):
    croquis_dir = storage_real.obter_caminho_croquis_experimentais()
    (croquis_dir / "20260501_brasil_mg_bh_curral").mkdir(parents=True, exist_ok=True)

    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)

    tela.carregar_croquis()

    assert tela.lista_croquis.count() == 1
    items = []
    for i in range(tela.lista_croquis.count()):
        item = tela.lista_croquis.item(i)
        widget = tela.lista_croquis.itemWidget(item)
        items.append(widget.label_nome.text().lower())

    assert any("curral" in item for item in items)


def test_tela_de_carregamento_exibe_mensagem_vazia(qtbot, storage_real: GerenciadorCaminhos):
    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)
    tela.show()

    tela.carregar_croquis()

    label_vazio = tela.findChild(QLabel, "label_historico_vazio")
    assert label_vazio is not None
    assert label_vazio.isVisible()
    assert "nenhum croqui no histórico" in label_vazio.text().lower()
    assert not tela.lista_croquis.isVisible()


def test_tela_de_carregamento_editar_oficial_sem_prompt_resumo(
    qtbot, storage_real: GerenciadorCaminhos
):
    """
    Garante que clicar em 'Editar croqui oficial' abre o DialogoBuscaCroqui com o primeiro
    item já pré-selecionado e, ao confirmar, importa o croqui diretamente sem QInputDialog.
    """
    pasta_oficial = storage_real.obter_caminho_base_repo() / "database" / "br_mg_oficial"
    pasta_oficial.mkdir(parents=True, exist_ok=True)
    (pasta_oficial / "croqui.yaml").write_text(
        "id: br_mg_oficial\nnome: Croqui Oficial\nultima_migracao: 5\n"
        "picos:\n  - nome: Croqui Oficial\n    estado: MG\n",
        encoding="utf-8",
    )

    tela = TelaDeCarregamento(storage=storage_real, usuario="TesteUser")
    qtbot.addWidget(tela)

    def _confirmar_dialogo_busca(modal: QWidget) -> None:
        assert isinstance(modal, DialogoBuscaCroqui)
        assert modal.obter_id_selecionado() == "br_mg_oficial"
        modal.accept()

    _interagir_com_modal_ativo(tela, _confirmar_dialogo_busca)
    qtbot.mouseClick(tela.btn_oficial, Qt.MouseButton.LeftButton)

    assert tela.caminho_croqui_selecionado is not None
    assert (tela.caminho_croqui_selecionado / "database" / "croqui.yaml").is_file()
    dados_meta = carregar_yaml(
        (tela.caminho_croqui_selecionado / "croqui_experimental.yaml").read_text(encoding="utf-8")
    )
    assert "TesteUser" in dados_meta["autores"]
    assert "resumo_edicao" not in dados_meta


def test_tela_de_carregamento_abrir_historico(qtbot, storage_real: GerenciadorCaminhos):
    croquis_dir = storage_real.obter_caminho_croquis_experimentais()
    pasta_croqui = croquis_dir / "20260501_brasil_mg_bh_curral"
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    with open(pasta_croqui / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"autores": ["Outro"]}, f)

    tela = TelaDeCarregamento(storage=storage_real, usuario="TesteUser")
    qtbot.addWidget(tela)
    tela.carregar_croquis()

    item = tela.lista_croquis.item(0)
    tela.lista_croquis.itemDoubleClicked.emit(item)

    assert tela.caminho_croqui_selecionado == pasta_croqui
    dados_meta = carregar_yaml((pasta_croqui / "croqui_experimental.yaml").read_text("utf-8"))
    assert "TesteUser" in dados_meta["autores"]


def test_tela_de_carregamento_exibe_data_edicao_sem_label_resumo(
    qtbot, storage_real: GerenciadorCaminhos
):
    croquis_dir = storage_real.obter_caminho_croquis_experimentais()
    pasta_croqui = croquis_dir / "20260501_brasil_mg_bh_curral"
    pasta_croqui.mkdir(parents=True, exist_ok=True)

    yaml_content = {
        "ultima_edicao": "2026-05-01T14:30:00Z",
        "data_criacao": "2026-05-01T10:00:00Z",
    }
    with open(pasta_croqui / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
        serializar_yaml(yaml_content, f)

    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)
    tela.carregar_croquis()

    dt_utc = datetime.fromisoformat("2026-05-01T14:30:00+00:00")
    dt_local = dt_utc.astimezone()
    texto_esperado = dt_local.strftime("%d/%m/%Y %H:%M")

    item = tela.lista_croquis.item(0)
    widget = tela.lista_croquis.itemWidget(item)

    assert "Curral" in widget.label_nome.text()
    assert texto_esperado in widget.lbl_edicao.text()
    assert not hasattr(widget, "label_resumo")


def test_tela_de_carregamento_excluir_croqui(qtbot, storage_real: GerenciadorCaminhos):
    croquis_dir = storage_real.obter_caminho_croquis_experimentais()
    pasta_croqui = croquis_dir / "20260501_brasil_mg_bh_curral"
    pasta_croqui.mkdir(parents=True, exist_ok=True)

    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)
    tela.carregar_croquis()

    item = tela.lista_croquis.item(0)
    widget = tela.lista_croquis.itemWidget(item)
    btn_excluir = widget.btn_excluir

    def _confirmar_exclusao(modal: QWidget) -> None:
        assert isinstance(modal, QMessageBox)
        btn_yes = modal.button(QMessageBox.StandardButton.Yes)
        assert btn_yes is not None
        btn_yes.click()

    _interagir_com_modal_ativo(tela, _confirmar_exclusao)
    qtbot.mouseClick(btn_excluir, Qt.MouseButton.LeftButton)

    assert not pasta_croqui.exists()
    assert tela.lista_croquis.count() == 0


def test_tela_de_carregamento_verifica_exaustividade_dos_dados(
    qtbot, storage_real: GerenciadorCaminhos
):
    """
    Verifica se Nome do croqui.yaml, ID e data formatada estão presentes no widget,
    sem exibir subtítulo de resumo de edição.
    """
    croquis_dir = storage_real.obter_caminho_croquis_experimentais()

    id_pasta = "20260501123000_brasil_mg_bh_popeye"
    pasta_croqui = croquis_dir / id_pasta
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    (pasta_croqui / "database").mkdir()

    with open(pasta_croqui / "database" / "croqui.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"nome": "Pedra do Popeye", "id": "br_mg_bh_popeye_logico"}, f)

    data_iso = "2026-05-01T14:30:00Z"
    with open(pasta_croqui / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
        serializar_yaml({"ultima_edicao": data_iso}, f)

    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)
    tela.carregar_croquis()

    widget = tela.lista_croquis.itemWidget(tela.lista_croquis.item(0))

    assert widget.label_nome.text() == "Pedra do Popeye"
    assert not hasattr(widget, "label_resumo")
    assert widget.lbl_id.text() == f"ID: {id_pasta}"

    dt_local = datetime.fromisoformat(data_iso.replace("Z", "+00:00")).astimezone()
    data_formatada = dt_local.strftime("%d/%m/%Y %H:%M")
    assert f"Última Edição: {data_formatada}" in widget.lbl_edicao.text()


def test_tela_de_carregamento_ordenacao_historico(qtbot, storage_real: GerenciadorCaminhos):
    """Verifica se os croquis são listados em ordem decrescente de edição."""
    croquis_dir = storage_real.obter_caminho_croquis_experimentais()

    datas = [
        "2026-05-01T10:00:00Z",  # Mais antigo
        "2026-05-01T15:00:00Z",  # Mais novo
        "2026-05-01T12:00:00Z",  # Meio
    ]
    ids = ["antigo", "novo", "meio"]

    for i, data in enumerate(datas):
        pasta = croquis_dir / f"20260501_br_mg_{ids[i]}"
        pasta.mkdir(parents=True, exist_ok=True)
        with open(pasta / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
            serializar_yaml({"ultima_edicao": data}, f)

    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)
    tela.carregar_croquis()

    ids_na_lista = []
    for i in range(tela.lista_croquis.count()):
        widget = tela.lista_croquis.itemWidget(tela.lista_croquis.item(i))
        ids_na_lista.append(widget.lbl_id.text().split(": ")[1])

    assert ids_na_lista == ["20260501_br_mg_novo", "20260501_br_mg_meio", "20260501_br_mg_antigo"]


def test_dialogo_novo_croqui_limite_id(qtbot):
    """Verifica se o ID gerado é truncado para no máximo 100 caracteres para evitar WinError 123."""
    dialog = DialogoNovoCroqui()
    qtbot.addWidget(dialog)

    dialog.edit_pais.setText("br")
    dialog.edit_estado.setText("sp")
    dialog.edit_cidade.setText("sao bento do sapucai da serra da mantiqueira paulista")

    texto_pico_enorme = (
        "pedra do bau queijo com suico sociedade da felicidade grande"
    )
    dialog.edit_pico.setText(texto_pico_enorme)

    id_gerado = dialog.edit_id.text()
    assert len(id_gerado) <= 100
    assert len(id_gerado) >= 90
    assert not id_gerado.endswith("_")


def test_tela_de_carregamento_propriedades_janela(qtbot):
    """Verifica se a janela tem as propriedades de redimensionamento corretas."""
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)

    assert tela.minimumWidth() >= 650
    assert tela.minimumHeight() >= 600

    flags = tela.windowFlags()
    assert flags & Qt.WindowType.WindowMinMaxButtonsHint

    layout = tela.layout_principal
    assert layout.stretch(1) == 1
    assert layout.stretch(0) == 0


def test_tela_de_carregamento_fluxo_novo_croqui_completo(
    qtbot, storage_real: GerenciadorCaminhos
):
    """
    Verifica se o botão 'Novo croqui' abre o diálogo de metadados e cria o croqui experimental
    sem gravar resumo_edicao.
    """
    tela = TelaDeCarregamento(storage=storage_real, usuario="TesteUser")
    qtbot.addWidget(tela)

    def _preencher_e_confirmar_novo(modal: QWidget) -> None:
        assert isinstance(modal, DialogoNovoCroqui)
        modal.edit_pico.setText("Pedra do Baú")
        modal.edit_cidade.setText("São Bento do Sapucaí")
        modal.edit_estado.setText("SP")
        modal.edit_pais.setText("BR")
        assert modal.btn_criar.isEnabled() is True
        modal.accept()

    _interagir_com_modal_ativo(tela, _preencher_e_confirmar_novo)
    qtbot.mouseClick(tela.btn_novo, Qt.MouseButton.LeftButton)

    assert tela.caminho_croqui_selecionado is not None
    croqui_yaml = tela.caminho_croqui_selecionado / "database" / "croqui.yaml"
    assert croqui_yaml.is_file()
    dados_croqui = carregar_yaml(croqui_yaml.read_text(encoding="utf-8"))
    assert dados_croqui["id"] == "br_sp_sao_bento_do_sapucai_pedra_do_bau"
    assert dados_croqui["nome"] == "Pedra do Baú"


def test_tela_de_carregamento_tem_icone_configurado(qtbot):
    """Garante que a Tela de Carregamento carrega o ícone de montanha."""
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    assert not tela.windowIcon().isNull()


def test_tela_de_carregamento_botao_desconectar_limpa_sessao_e_emite_sinal(qtbot):
    sessao_inicial = SessaoUsuario(
        email="renato@exemplo.com",
        nome_completo="Renato Autor",
        jwt_supabase="jwt_fake",
        token_atualizacao="refresh_fake",
        token_github=None,
    )
    gerenciador_sessao = GerenciadorSessaoFake(sessao_inicial=sessao_inicial)
    tela = TelaDeCarregamento(usuario="Renato Autor", gerenciador_sessao=gerenciador_sessao)
    qtbot.addWidget(tela)

    assert hasattr(tela, "btn_desconectar")
    assert "Renato Autor" in tela.label_usuario_logado.text()

    def _confirmar_logout(modal: QWidget) -> None:
        assert isinstance(modal, QMessageBox)
        btn_yes = modal.button(QMessageBox.StandardButton.Yes)
        assert btn_yes is not None
        btn_yes.click()

    _interagir_com_modal_ativo(tela, _confirmar_logout)
    with qtbot.waitSignal(tela.solicitar_logout, timeout=1000):
        qtbot.mouseClick(tela.btn_desconectar, Qt.MouseButton.LeftButton)

    assert gerenciador_sessao.obter_sessao() is None


def test_tela_de_carregamento_desconectar_cancelado(qtbot):
    sessao_inicial = SessaoUsuario(
        email="renato@exemplo.com",
        nome_completo="Renato Autor",
        jwt_supabase="jwt_fake",
        token_atualizacao="refresh_fake",
        token_github=None,
    )
    gerenciador_sessao = GerenciadorSessaoFake(sessao_inicial=sessao_inicial)
    tela = TelaDeCarregamento(usuario="Renato Autor", gerenciador_sessao=gerenciador_sessao)
    qtbot.addWidget(tela)

    def _cancelar_logout(modal: QWidget) -> None:
        assert isinstance(modal, QMessageBox)
        btn_no = modal.button(QMessageBox.StandardButton.No)
        assert btn_no is not None
        btn_no.click()

    _interagir_com_modal_ativo(tela, _cancelar_logout)
    qtbot.mouseClick(tela.btn_desconectar, Qt.MouseButton.LeftButton)

    assert gerenciador_sessao.obter_sessao() is not None


def test_tela_de_carregamento_alterar_nome_usuario(qtbot):
    sessao_inicial = SessaoUsuario(
        email="renato@exemplo.com",
        nome_completo="Renato Antigo",
        jwt_supabase="jwt_fake_1",
        token_atualizacao="refresh_fake_1",
        token_github=None,
    )
    gerenciador_sessao = GerenciadorSessaoFake(sessao_inicial=sessao_inicial)
    cliente_auth = ClienteAuthSupabaseFake()
    cliente_auth.usuarios_por_jwt["jwt_fake_1"] = {
        "email": "renato@exemplo.com",
        "user_metadata": {"nome_completo": "Renato Antigo"},
    }

    tela = TelaDeCarregamento(
        usuario="Renato Antigo",
        gerenciador_sessao=gerenciador_sessao,
        cliente_auth=cliente_auth,
    )
    qtbot.addWidget(tela)

    assert hasattr(tela, "btn_alterar_nome")
    assert "Renato Antigo" in tela.label_usuario_logado.text()

    def _preencher_novo_nome(modal: QWidget) -> None:
        assert isinstance(modal, DialogoPerfilAutor)
        modal.edit_nome.setText("Renato Novo")
        modal.confirmar_e_fechar()

    _interagir_com_modal_ativo(tela, _preencher_novo_nome)
    qtbot.mouseClick(tela.btn_alterar_nome, Qt.MouseButton.LeftButton)

    assert tela.usuario == "Renato Novo"
    assert "Renato Novo" in tela.label_usuario_logado.text()
    sessao_salva = gerenciador_sessao.obter_sessao()
    assert sessao_salva is not None
    assert sessao_salva.nome_completo == "Renato Novo"
    assert (
        cliente_auth.usuarios_por_jwt["jwt_fake_1"]["user_metadata"]["nome_completo"]
        == "Renato Novo"
    )


def test_tela_de_carregamento_estilo_define_contraste_legivel(qtbot):
    """Garante que a folha de estilo da TelaDeCarregamento define explicitamente cores de texto para botões e grupos."""
    import re

    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    estilo = tela.styleSheet()

    assert "color:" in estilo
    assert "#grupo_acoes QPushButton" in estilo or "QGroupBox QPushButton" in estilo
    assert not re.search(r"(?m)^\s*QPushButton\s*\{", estilo), (
        "O seletor genérico QPushButton vaza para diálogos filhos"
    )


def test_tela_de_carregamento_titulo_e_icone_canal_beta(qtbot, monkeypatch):
    """Garante que a tela de carregamento adote o nome do canal Beta e seu respectivo ícone."""
    monkeypatch.setenv("ARESTA_CANAL", "beta")
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)

    assert "Beta" in tela.windowTitle()
    assert tela.windowTitle() == "Iniciar Editor Aresta (Beta)"
    assert not tela.windowIcon().isNull()
    tela.close()


def test_tela_de_carregamento_possui_botao_conectar_mcp_e_abre_croqui_via_mcp(qtbot, tmp_path):
    """
    Garante que a TelaDeCarregamento exibe o botão 'Conectar Agente de IA (MCP)...',
    inicia o servidor MCP em modo sem croqui aberto e permite abrir croqui via callback MCP.
    """
    tela = TelaDeCarregamento(diretorio_sessao_mcp=tmp_path)
    qtbot.addWidget(tela)

    assert hasattr(tela, "btn_mcp")
    assert tela.btn_mcp.text() == "Conectar Agente de IA (MCP)..."

    servidor = tela.garantir_servidor_mcp(iniciar_rede=False)
    assert servidor.croqui_aberto is False
    assert "aresta_listar_croquis" in servidor.ferramentas
    assert "aresta_criar_novo_croqui" in servidor.ferramentas

    pasta_croqui = tmp_path / "croqui_mcp_teste"
    pasta_croqui.mkdir()
    res = tela._abrir_croqui_via_mcp(pasta_croqui)
    assert res["janela_aberta"] is True
    assert tela.caminho_croqui_selecionado == pasta_croqui


def test_dialogo_novo_croqui_detecta_id_duplicado_e_campos_vazios(
    qtbot, storage_real: GerenciadorCaminhos
):
    """Garante que o DialogoNovoCroqui bloqueia ID já existente no histórico e limpa validação quando campos esvaziam."""
    pasta_existente = (
        storage_real.obter_caminho_croquis_experimentais()
        / "20260501_br_sp_sao_bento_pedra_do_bau"
    )
    pasta_existente.mkdir(parents=True, exist_ok=True)

    dialog = DialogoNovoCroqui(storage=storage_real)
    qtbot.addWidget(dialog)

    dialog.edit_pais.setText("BR")
    dialog.edit_estado.setText("SP")
    dialog.edit_cidade.setText("São Bento")
    dialog.edit_pico.setText("Pedra do Baú")

    assert dialog.btn_criar.isEnabled() is False
    assert "já existe" in dialog.lbl_validacao.text()

    dialog.edit_pico.setText("")
    assert dialog.edit_id.text() == ""
    assert dialog.btn_criar.isEnabled() is False


def test_tela_de_carregamento_sem_storage_e_metadados_invalidos(
    qtbot, storage_real: GerenciadorCaminhos
):
    """Garante resiliência ao carregar histórico sem storage, sem pasta ou com YAMLs/datas inválidos."""
    tela_sem_storage = TelaDeCarregamento(storage=None)
    qtbot.addWidget(tela_sem_storage)
    tela_sem_storage.carregar_croquis()
    qtbot.mouseClick(tela_sem_storage.btn_novo, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tela_sem_storage.btn_oficial, Qt.MouseButton.LeftButton)
    assert tela_sem_storage.caminho_croqui_selecionado is None

    # Quando a pasta de croquis experimentais foi removida
    import shutil

    caminho_exp = storage_real.obter_caminho_croquis_experimentais()
    shutil.rmtree(caminho_exp)
    tela = TelaDeCarregamento(storage=storage_real)
    qtbot.addWidget(tela)
    assert tela.lista_croquis.count() == 0

    # Quando existem pastas com YAML corrompido ou datas malformadas
    caminho_exp.mkdir(parents=True, exist_ok=True)
    pasta_datas_invalidas = caminho_exp / "croqui_datas_invalidas"
    (pasta_datas_invalidas / "database").mkdir(parents=True)
    (pasta_datas_invalidas / "database" / "croqui.yaml").write_text(
        "[yaml_invalido", encoding="utf-8"
    )
    (pasta_datas_invalidas / "croqui_experimental.yaml").write_text(
        "data_criacao: data_invalida\nultima_edicao: outra_data_invalida\n",
        encoding="utf-8",
    )

    pasta_yaml_corrompido = caminho_exp / "croqui_yaml_corrompido"
    pasta_yaml_corrompido.mkdir(parents=True)
    (pasta_yaml_corrompido / "croqui_experimental.yaml").write_text(
        "[yaml_invalido", encoding="utf-8"
    )

    tela.carregar_croquis()
    assert tela.lista_croquis.count() == 2


def test_tela_de_carregamento_erros_ao_importar_oficial_e_abrir_item(
    qtbot, storage_real: GerenciadorCaminhos
):
    """Garante exibição de alerta de erro quando oficial falha na compilação ou histórico está corrompido."""
    pasta_oficial = storage_real.obter_caminho_base_repo() / "database" / "br_mg_invalido"
    pasta_oficial.mkdir(parents=True, exist_ok=True)
    # croqui.yaml inválido (sem campos obrigatórios/YAML quebrado) para falhar na compilação
    (pasta_oficial / "croqui.yaml").write_text(":::yaml_quebrado\n[\n", encoding="utf-8")

    pasta_hist = storage_real.obter_caminho_croquis_experimentais() / "20260501_hist_corrompido"
    pasta_hist.mkdir(parents=True, exist_ok=True)
    (pasta_hist / "croqui_experimental.yaml").write_text("autores: 12345\n", encoding="utf-8")

    tela = TelaDeCarregamento(storage=storage_real, usuario="TesteUser")
    qtbot.addWidget(tela)

    def _aceitar_busca_e_fechar_erro(modal: QWidget) -> None:
        assert isinstance(modal, DialogoBuscaCroqui)
        _interagir_com_modal_ativo(
            tela,
            lambda msg_box: msg_box.accept() if isinstance(msg_box, QMessageBox) else None,
        )
        modal.accept()

    _interagir_com_modal_ativo(tela, _aceitar_busca_e_fechar_erro)
    qtbot.mouseClick(tela.btn_oficial, Qt.MouseButton.LeftButton)
    assert tela.caminho_croqui_selecionado is None

    # Testar erro ao abrir item corrompido do histórico
    _interagir_com_modal_ativo(
        tela,
        lambda msg_box: msg_box.accept() if isinstance(msg_box, QMessageBox) else None,
    )
    item = tela.lista_croquis.item(0)
    tela.lista_croquis.itemDoubleClicked.emit(item)
    assert tela.caminho_croqui_selecionado is None


def test_tela_de_carregamento_alterar_nome_offline_e_dialogo_mcp(qtbot, tmp_path):
    """Garante resiliência ao alterar nome em modo offline e abertura do diálogo de conexão MCP."""
    sessao_inicial = SessaoUsuario(
        email="renato@exemplo.com",
        nome_completo="Renato Antigo",
        jwt_supabase="jwt_fake_1",
        token_atualizacao="refresh_fake_1",
        token_github=None,
    )
    gerenciador_sessao = GerenciadorSessaoFake(sessao_inicial=sessao_inicial)
    cliente_auth = ClienteAuthSupabaseFake()
    cliente_auth.modo_offline = True

    from editor.mcp.despachante import DespachanteQt
    from editor.mcp.servidor import ServidorMCP

    servidor_injetado = ServidorMCP(despachante=DespachanteQt(), diretorio_sessao=tmp_path)
    tela = TelaDeCarregamento(
        usuario="Renato Antigo",
        gerenciador_sessao=gerenciador_sessao,
        cliente_auth=cliente_auth,
        servidor_mcp=servidor_injetado,
        diretorio_sessao_mcp=tmp_path,
    )
    qtbot.addWidget(tela)

    def _preencher_nome(modal: QWidget) -> None:
        assert isinstance(modal, DialogoPerfilAutor)
        modal.edit_nome.setText("Renato Offline")
        modal.confirmar_e_fechar()

    _interagir_com_modal_ativo(tela, _preencher_nome)
    qtbot.mouseClick(tela.btn_alterar_nome, Qt.MouseButton.LeftButton)
    assert tela.usuario == "Renato Offline"

    _interagir_com_modal_ativo(tela, lambda modal: modal.accept())
    try:
        qtbot.mouseClick(tela.btn_mcp, Qt.MouseButton.LeftButton)
        assert servidor_injetado.esta_ativo is True
    finally:
        servidor_injetado.parar()
