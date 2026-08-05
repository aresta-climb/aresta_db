# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from editor.views.dialogos.dialogo_adicionar_mapa import DialogoAdicionarMapa

def test_dialogo_adicionar_mapa_inicializacao(qapp, tmp_path):
    sugerido = "setor_teste_p0.webp"
    dialog = DialogoAdicionarMapa(nome_sugerido=sugerido, db_dir=tmp_path)
    
    assert dialog.input_nome.text() == sugerido
    assert not dialog.btn_ok.isEnabled() # Só deve estar habilitado se tiver imagem

def test_dialogo_adicionar_mapa_nao_sobrescreve(qapp, tmp_path, monkeypatch):
    sugerido = "setor_teste_p0.webp"
    # Criar um arquivo dummy para simular que já existe
    imagens_dir = tmp_path / "imagens"
    imagens_dir.mkdir(parents=True, exist_ok=True)
    (imagens_dir / sugerido).touch()
    
    dialog = DialogoAdicionarMapa(nome_sugerido=sugerido, db_dir=tmp_path)
    dialog.caminho_imagem_selecionada = "dummy.jpg"
    dialog.btn_ok.setEnabled(True)
    
    # Mock de QMessageBox para não travar o teste
    messages = []
    monkeypatch.setattr("editor.views.dialogos.dialogo_adicionar_mapa.QMessageBox.critical", lambda *args: messages.append(args[2]))
    
    # Tenta aceitar
    dialog.accept()
    
    # Deve ter mostrado erro de arquivo existente e NÃO deve ter fechado (aceito)
    assert len(messages) == 1
    assert "já existe" in messages[0].lower()
    assert not dialog.result()

def test_dialogo_adicionar_mapa_fluxo_sucesso(qapp, tmp_path, monkeypatch):
    sugerido = "setor_teste_p0.webp"
    imagens_dir = tmp_path / "imagens"
    imagens_dir.mkdir(parents=True, exist_ok=True)
    
    dialog = DialogoAdicionarMapa(nome_sugerido=sugerido, db_dir=tmp_path)
    dialog.caminho_imagem_selecionada = "dummy.jpg"
    dialog.btn_ok.setEnabled(True)
    
    dialog.accept()
    
    assert dialog.result() == 1 # QDialog.DialogCode.Accepted
    assert dialog.obter_caminho_final_relativo() == f"imagens/{sugerido}"
    assert dialog.obter_caminho_final_absoluto() == imagens_dir / sugerido
