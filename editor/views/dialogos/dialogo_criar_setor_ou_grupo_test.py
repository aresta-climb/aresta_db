# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from PyQt6.QtWidgets import QApplication, QRadioButton, QLineEdit, QPushButton
from PyQt6.QtCore import Qt
from editor.views.dialogos.dialogo_criar_setor_ou_grupo import DialogoCriarSetorOuGrupo

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dialogo_criar_setor_ou_grupo_inicializacao_modo_ambos(qapp):
    """Verifica se no modo 'ambos' exibe as opções de Setor e Grupo, com Setor selecionado por padrão."""
    dialogo = DialogoCriarSetorOuGrupo(modo="ambos")
    dialogo.show()

    assert dialogo.radio_setor.isChecked() is True
    assert dialogo.radio_grupo.isChecked() is False
    assert dialogo.edit_nome.text() == ""
    assert dialogo.edit_arquivo.text() == ""
    assert dialogo.btn_criar.isEnabled() is False


def test_dialogo_criar_setor_ou_grupo_inicializacao_modo_setor(qapp):
    """Verifica se no modo 'setor' a opção de Grupo não fica visível e o tipo fica fixado em Setor."""
    dialogo = DialogoCriarSetorOuGrupo(modo="setor")
    dialogo.show()

    assert dialogo.radio_grupo.isVisible() is False
    assert dialogo.obter_tipo_selecionado() == "setor"


def test_dialogo_criar_setor_ou_grupo_auto_proposicao_arquivo(qapp):
    """Verifica se ao digitar o nome, o nome do arquivo é auto-gerado e auto-proposto em snake_case."""
    dialogo = DialogoCriarSetorOuGrupo(modo="ambos")
    dialogo.show()

    dialogo.edit_nome.setText("Falésia dos Olhos d'Água")
    
    assert dialogo.edit_arquivo.text() == "setor_falesia_dos_olhos_dagua.md"
    assert dialogo.btn_criar.isEnabled() is True

    # Troca para grupo e verifica atualização do prefixo
    dialogo.radio_grupo.setChecked(True)
    assert dialogo.edit_arquivo.text() == "grupo_falesia_dos_olhos_dagua.md"

    # Troca de volta para setor
    dialogo.radio_setor.setChecked(True)
    assert dialogo.edit_arquivo.text() == "setor_falesia_dos_olhos_dagua.md"


def test_dialogo_criar_setor_ou_grupo_edicao_manual_arquivo(qapp):
    """Verifica se o usuário editar manualmente o arquivo, a auto-proposição não sobrescreve."""
    dialogo = DialogoCriarSetorOuGrupo(modo="ambos")
    dialogo.show()

    dialogo.edit_nome.setText("Setor do Meio")
    assert dialogo.edit_arquivo.text() == "setor_setor_do_meio.md"

    # Usuário edita manualmente
    dialogo.edit_arquivo.setText("meu_setor_customizado.md")

    # Altera o nome; o arquivo customizado deve ser preservado
    dialogo.edit_nome.setText("Setor do Meio Alterado")
    assert dialogo.edit_arquivo.text() == "meu_setor_customizado.md"


def test_dialogo_criar_setor_ou_grupo_garante_extensao_md(qapp):
    """Verifica se ao confirmar, caso o usuário tenha esquecido a extensão .md, ela é adicionada."""
    dialogo = DialogoCriarSetorOuGrupo(modo="ambos")
    dialogo.show()

    dialogo.edit_nome.setText("Setor Teste")
    dialogo.edit_arquivo.setText("arquivo_sem_extensao")

    tipo, nome, arquivo, ok = dialogo.obter_dados_confirmados()
    assert tipo == "setor"
    assert nome == "Setor Teste"
    assert arquivo == "arquivo_sem_extensao.md"


def test_dialogo_criar_setor_ou_grupo_modo_grupo_e_nome_sugerido(qapp):
    """Verifica a inicialização no modo 'grupo' e com nome pré-sugerido."""
    dialogo = DialogoCriarSetorOuGrupo(modo="grupo", nome_sugerido="Complexo Principal")
    dialogo.show()

    assert dialogo.radio_setor.isVisible() is False
    assert dialogo.obter_tipo_selecionado() == "grupo"
    assert dialogo.edit_nome.text() == "Complexo Principal"
    assert dialogo.edit_arquivo.text() == "grupo_complexo_principal.md"
    assert dialogo.btn_criar.isEnabled() is True


def test_dialogo_criar_setor_ou_grupo_nome_vazio_e_caracteres_especiais(qapp):
    """Verifica comportamento ao limpar o campo nome ou digitar caracteres sem slug."""
    dialogo = DialogoCriarSetorOuGrupo(modo="ambos")
    dialogo.show()

    dialogo.edit_nome.setText("Teste")
    assert dialogo.edit_arquivo.text() == "setor_teste.md"

    # Limpa o texto
    dialogo.edit_nome.setText("")
    assert dialogo.edit_arquivo.text() == ""
    assert dialogo.btn_criar.isEnabled() is False

    # Caracteres que resultam em slug vazio (ex: pontuação apenas)
    dialogo.edit_nome.setText("???")
    assert dialogo.edit_arquivo.text() == "setor.md"


def test_dialogo_criar_setor_ou_grupo_metodo_obter_dados_estatico(qapp, monkeypatch):
    """Verifica a execução do método estático obter_dados."""
    from PyQt6.QtWidgets import QDialog
    monkeypatch.setattr(QDialog, "exec", lambda self: self.setResult(QDialog.DialogCode.Accepted))

    tipo, nome, arquivo, ok = DialogoCriarSetorOuGrupo.obter_dados(modo="ambos", nome_sugerido="Falésia")
    assert tipo == "setor"
    assert nome == "Falésia"
    assert arquivo == "setor_falesia.md"
    assert ok is True


def test_dialogo_criar_setor_ou_grupo_validacao_duplicidade(qapp):
    """Verifica se o diálogo detecta duplicidade de nome ou de arquivo e bloqueia criação."""
    nomes_existentes = ["Falésia Central", "Bloco do Lago"]
    arquivos_existentes = ["setor_falesia_central.md", "grupo_bloco_do_lago.md"]

    dialogo = DialogoCriarSetorOuGrupo(
        nomes_existentes=nomes_existentes,
        arquivos_existentes=arquivos_existentes
    )
    dialogo.show()

    # Nome duplicado
    dialogo.edit_nome.setText("Falésia Central")
    assert dialogo.btn_criar.isEnabled() is False
    assert "já existe" in dialogo.lbl_aviso.text().lower()

    # Nome novo mas arquivo duplicado
    dialogo.edit_nome.setText("Novo Bloco")
    dialogo.edit_arquivo.setText("grupo_bloco_do_lago.md")
    assert dialogo.btn_criar.isEnabled() is False
    assert "já existe" in dialogo.lbl_aviso.text().lower()

    # Inédito
    dialogo.edit_arquivo.setText("setor_novo_bloco.md")
    assert dialogo.btn_criar.isEnabled() is True
    assert dialogo.lbl_aviso.text() == ""


