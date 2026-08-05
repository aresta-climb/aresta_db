# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import pytest
from PyQt6.QtWidgets import QPushButton, QListWidget, QLabel, QDialog
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from editor.legacy_views.tela_de_carregamento import TelaDeCarregamento
from unittest.mock import MagicMock, patch
from datetime import datetime
import yaml

def test_tela_de_carregamento_e_um_dialog(qtbot):
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    assert isinstance(tela, QDialog)

def test_tela_de_carregamento_tem_botoes_com_nomes_completos(qtbot):
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    
    # Verifica botões
    botoes = tela.findChildren(QPushButton)
    textos_botoes = [b.text() for b in botoes]
    
    assert "Novo croqui" in textos_botoes
    assert "Importar croqui experimental" in textos_botoes
    assert "Editar croqui oficial" in textos_botoes
    
def test_tela_de_carregamento_carrega_croquis(qtbot, tmp_path):
    # Setup de diretórios temporários
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    (croquis_dir / "20260501_brasil_mg_bh_curral").mkdir()
    
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    tela = TelaDeCarregamento(storage=mock_storage)
    qtbot.addWidget(tela)
    
    tela.carregar_croquis()
    
    assert tela.lista_croquis.count() == 1
    items = []
    for i in range(tela.lista_croquis.count()):
        item = tela.lista_croquis.item(i)
        widget = tela.lista_croquis.itemWidget(item)
        items.append(widget.label_nome.text().lower())
        
    assert any("curral" in item for item in items)

def test_tela_de_carregamento_exibe_mensagem_vazia(qtbot, tmp_path):
    # Setup de diretório vazio
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    tela = TelaDeCarregamento(storage=mock_storage)
    qtbot.addWidget(tela)
    tela.show()
    
    tela.carregar_croquis()
    
    label_vazio = tela.findChild(QLabel, "label_historico_vazio")
    assert label_vazio is not None
    assert label_vazio.isVisible()
    assert "nenhum croqui no histórico" in label_vazio.text().lower()
    assert not tela.lista_croquis.isVisible()

def test_tela_de_carregamento_importar_croqui(qtbot):

    mock_storage = MagicMock()
    
    with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", return_value=("test.croqui", "Arquivos de Croqui (*.croqui)")):
        with patch("editor.legacy_views.tela_de_carregamento.GerenciadorCroquiExperimental") as mock_gen_class:
            mock_gen = mock_gen_class.return_value
            tela = TelaDeCarregamento(storage=mock_storage)
            qtbot.addWidget(tela)
            
            qtbot.mouseClick(tela.btn_importar, Qt.MouseButton.LeftButton)
            mock_gen.importar_croqui.assert_called_once()

def test_tela_de_carregamento_editar_oficial(qtbot):
    mock_storage = MagicMock()
    
    with patch("editor.legacy_views.tela_de_carregamento.DialogoBuscaCroqui") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        mock_dialog.exec.return_value = True
        mock_dialog.obter_id_selecionado.return_value = "br_mg_oficial"
        
        with patch("editor.legacy_views.tela_de_carregamento.GerenciadorCroquiExperimental") as mock_gen_class:
            mock_gen = mock_gen_class.return_value
            tela = TelaDeCarregamento(storage=mock_storage, usuario="TesteUser")
            qtbot.addWidget(tela)
            
            # Simula seleção no diálogo de busca e entrada de resumo
            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Edição de teste", True)):
                qtbot.mouseClick(tela.btn_oficial, Qt.MouseButton.LeftButton)
            
            mock_gen.criar_croqui_a_partir_de_oficial.assert_called_once_with("br_mg_oficial", "TesteUser", "Edição de teste")

def test_tela_de_carregamento_abrir_historico(qtbot, tmp_path):
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    pasta_croqui = croquis_dir / "20260501_brasil_mg_bh_curral"
    pasta_croqui.mkdir()
    
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    with patch("editor.legacy_views.tela_de_carregamento.GerenciadorCroquiExperimental") as mock_gen_class:
        mock_gen = mock_gen_class.return_value
        tela = TelaDeCarregamento(storage=mock_storage, usuario="TesteUser")
        qtbot.addWidget(tela)
        tela.carregar_croquis()
        
        item = tela.lista_croquis.item(0)
        
        # Simula duplo clique emitindo o sinal
        tela.lista_croquis.itemDoubleClicked.emit(item)
        
        # Deve ter chamado abrir_croqui com o caminho correto
        mock_gen.abrir_croqui.assert_called_once()
        chamada = mock_gen.abrir_croqui.call_args[0]
        assert str(chamada[0]) == str(pasta_croqui)
        assert chamada[1] == "TesteUser"

def test_tela_de_carregamento_exibe_data_edicao(qtbot, tmp_path):
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    pasta_croqui = croquis_dir / "20260501_brasil_mg_bh_curral"
    pasta_croqui.mkdir()
    
    # Cria o YAML com data específica e resumo
    yaml_content = {
        "ultima_edicao": "2026-05-01T14:30:00Z",
        "data_criacao": "2026-05-01T10:00:00Z",
        "resumo_edicao": "Teste de resumo"
    }
    with open(pasta_croqui / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
        yaml.dump(yaml_content, f)
        
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    tela = TelaDeCarregamento(storage=mock_storage)
    qtbot.addWidget(tela)
    tela.carregar_croquis()
    
    # Calcula o horário esperado no fuso local
    dt_utc = datetime.fromisoformat("2026-05-01T14:30:00+00:00")
    dt_local = dt_utc.astimezone()
    texto_esperado = dt_local.strftime("%d/%m/%Y %H:%M")
    
    item = tela.lista_croquis.item(0)
    widget = tela.lista_croquis.itemWidget(item)
    
    # Verifica se o nome aparece
    assert "Curral" in widget.label_nome.text()
    # Verifica se o resumo aparece
    assert "Teste de resumo" in widget.label_resumo.text()

def test_tela_de_carregamento_excluir_croqui(qtbot, tmp_path):
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    pasta_croqui = croquis_dir / "20260501_brasil_mg_bh_curral"
    pasta_croqui.mkdir()
    
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    with patch("editor.legacy_views.tela_de_carregamento.GerenciadorCroquiExperimental") as mock_gen_class:
        mock_gen = mock_gen_class.return_value
        tela = TelaDeCarregamento(storage=mock_storage)
        qtbot.addWidget(tela)
        tela.carregar_croquis()
        
        # Encontra o botão de excluir no primeiro item
        item = tela.lista_croquis.item(0)
        widget = tela.lista_croquis.itemWidget(item)
        btn_excluir = widget.btn_excluir
        
        # Simula clique no botão de excluir e aceitação na confirmação
        with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            qtbot.mouseClick(btn_excluir, Qt.MouseButton.LeftButton)
            mock_gen.excluir_croqui.assert_called_once()

def test_tela_de_carregamento_verifica_exaustividade_dos_dados(qtbot, tmp_path):
    """
    Verifica se todas as informações (Nome do croqui.yaml, resumo, ID e data formatada) 
    estão presentes no widget.
    """
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    
    id_pasta = "20260501123000_brasil_mg_bh_popeye"
    pasta_croqui = croquis_dir / id_pasta
    pasta_croqui.mkdir()
    (pasta_croqui / "database").mkdir()
    
    # 1. database/croqui.yaml com o nome real
    with open(pasta_croqui / "database" / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"nome": "Pedra do Popeye"}, f)
        
    # 2. croqui_experimental.yaml com resumo e data fixa
    data_iso = "2026-05-01T14:30:00Z" # UTC
    with open(pasta_croqui / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
        yaml.dump({
            "resumo_edicao": "Limpeza da base",
            "ultima_edicao": data_iso
        }, f)
        
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    tela = TelaDeCarregamento(storage=mock_storage)
    qtbot.addWidget(tela)
    tela.carregar_croquis()
    
    widget = tela.lista_croquis.itemWidget(tela.lista_croquis.item(0))
    
    # Validar Nome
    assert widget.label_nome.text() == "Pedra do Popeye"
    
    # Validar Resumo
    assert "Limpeza da base" in widget.label_resumo.text()
    
    # Validar ID (deve ser o nome da pasta sem o prefixo timestamp)
    assert "ID: brasil_mg_bh_popeye" in widget.lbl_id.text()
    
    # Validar Data (Última Edição formatada no fuso local)
    dt_local = datetime.fromisoformat(data_iso.replace("Z", "+00:00")).astimezone()
    data_formatada = dt_local.strftime('%d/%m/%Y %H:%M')
    assert f"Última Edição: {data_formatada}" in widget.lbl_edicao.text()

def test_tela_de_carregamento_ordenacao_historico(qtbot, tmp_path):
    """Verifica se os croquis são listados em ordem decrescente de edição."""
    croquis_dir = tmp_path / "croquis_experimentais"
    croquis_dir.mkdir()
    
    # Criar 3 croquis com datas diferentes
    datas = [
        "2026-05-01T10:00:00Z", # Mais antigo
        "2026-05-01T15:00:00Z", # Mais novo
        "2026-05-01T12:00:00Z"  # Meio
    ]
    ids = ["antigo", "novo", "meio"]
    
    for i, data in enumerate(datas):
        pasta = croquis_dir / f"20260501_br_mg_{ids[i]}"
        pasta.mkdir()
        with open(pasta / "croqui_experimental.yaml", "w", encoding="utf-8") as f:
            yaml.dump({"ultima_edicao": data}, f)

    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = croquis_dir
    
    tela = TelaDeCarregamento(storage=mock_storage)
    qtbot.addWidget(tela)
    tela.carregar_croquis()
    
    # Verifica a ordem na lista
    ids_na_lista = []
    for i in range(tela.lista_croquis.count()):
        widget = tela.lista_croquis.itemWidget(tela.lista_croquis.item(i))
        ids_na_lista.append(widget.lbl_id.text().split(": ")[1])
        
    # A ordem esperada é: novo (15h), meio (12h), antigo (10h)
    assert ids_na_lista == ["br_mg_novo", "br_mg_meio", "br_mg_antigo"]

def test_tela_de_carregamento_oficial_usa_log_dialog(qtbot):
    """Verifica se o DialogoProgressoLog é instanciado ao importar oficial."""
    mock_storage = MagicMock()
    
    with patch("editor.legacy_views.tela_de_carregamento.DialogoBuscaCroqui") as mock_busc_class:
        mock_busc = mock_busc_class.return_value
        mock_busc.exec.return_value = True
        mock_busc.obter_id_selecionado.return_value = "br_mg_bh_oficial"
        
        with patch("editor.legacy_views.tela_de_carregamento.DialogoProgressoLog") as mock_log_class:
            mock_log = mock_log_class.return_value
            # Simulamos sucesso rápido
            with patch("editor.legacy_views.tela_de_carregamento.GerenciadorCroquiExperimental") as mock_gen_class:
                with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Edição", True)):
                    tela = TelaDeCarregamento(storage=mock_storage)
                    qtbot.addWidget(tela)
                    qtbot.mouseClick(tela.btn_oficial, Qt.MouseButton.LeftButton)
                    
                    # Deve ter instanciado o log dialog
                    mock_log_class.assert_called_once()
                    assert mock_log.show.called
                    assert mock_log.accept.called

def test_tela_de_carregamento_propriedades_janela(qtbot):
    """Verifica se a janela tem as propriedades de redimensionamento corretas."""
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    
    # Verifica tamanho mínimo (deve ser pelo menos 650x600)
    assert tela.minimumWidth() >= 650
    assert tela.minimumHeight() >= 600
    
    # Verifica se as flags de maximizar/minimizar estão presentes
    flags = tela.windowFlags()
    assert flags & Qt.WindowType.WindowMinMaxButtonsHint
    
    # Verifica o stretch factor do layout principal (o segundo item, histórico, deve ser 1)
    layout = tela.layout_principal
    assert layout.stretch(1) == 1
    # O primeiro item (ações) não deve ter stretch (0)
    assert layout.stretch(0) == 0

def test_tela_de_carregamento_fluxo_novo_croqui_completo(qtbot, tmp_path):
    """
    Verifica se o botão 'Novo croqui' abre o diálogo de metadados e
    chama a lógica de criação com os dados corretos.
    """
    mock_storage = MagicMock()
    mock_storage.obter_caminho_croquis_experimentais.return_value = tmp_path
    
    # Mock do Diálogo de Metadados
    with patch("editor.legacy_views.tela_de_carregamento.DialogoNovoCroqui") as mock_dialog_class:
        mock_dialog = mock_dialog_class.return_value
        mock_dialog.exec.return_value = QDialog.DialogCode.Accepted
        dados_esperados = {
            "pico": "Pedra do Baú",
            "cidade": "São Bento do Sapucaí",
            "estado": "SP",
            "pais": "BR",
            "id": "br_sp_sao_bento_do_sapucai_pedra_do_bau"
        }

        mock_dialog.obter_dados.return_value = dados_esperados
        
        # Mock do Diálogo de Progresso
        with patch("editor.legacy_views.tela_de_carregamento.DialogoProgressoLog") as mock_log_class:
            mock_log = mock_log_class.return_value
            
            # Mock do Gerenciador
            with patch("editor.legacy_views.tela_de_carregamento.GerenciadorCroquiExperimental") as mock_gen_class:
                mock_gen = mock_gen_class.return_value
                
                tela = TelaDeCarregamento(storage=mock_storage, usuario="TesteUser")
                qtbot.addWidget(tela)
                
                # Dispara o clique
                qtbot.mouseClick(tela.btn_novo, Qt.MouseButton.LeftButton)
                
                # Verifica se o diálogo foi aberto
                mock_dialog_class.assert_called_once()
                
                # Verifica se chamou a criação com os parâmetros individuais
                mock_gen.criar_novo_croqui.assert_called_once_with(
                    dados_esperados["id"],
                    dados_esperados["pico"],
                    dados_esperados["estado"],
                    "TesteUser",
                    mock_log
                )

def test_tela_de_carregamento_tem_icone_configurado(qtbot):
    """Garante que a Tela de Carregamento carrega o ícone de montanha."""
    tela = TelaDeCarregamento()
    qtbot.addWidget(tela)
    assert not tela.windowIcon().isNull()


