# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from editor.views.dialogos.dialogo_inserir_botao_markdown import (
    DialogoInserirBotaoMarkdown,
    sanitizar_nome_arquivo_anexo,
)


def test_sanitizar_nome_arquivo_anexo():
    assert (
        sanitizar_nome_arquivo_anexo("Meu Documento de Acesso.pdf") == "meu_documento_de_acesso.pdf"
    )
    assert (
        sanitizar_nome_arquivo_anexo("Ficha Técnica - Versão 1.2!.PDF")
        == "ficha_tecnica_versao_12.pdf"
    )
    assert sanitizar_nome_arquivo_anexo("") == "documento_anexo"
    assert sanitizar_nome_arquivo_anexo("!@#$%.pdf") == "documento_anexo.pdf"
    # Nome longo: trunca tronco em no máximo 40 caracteres
    nome_longo = "autorizacao_especial_de_acesso_ao_parque_nacional_de_minas_gerais.pdf"
    res = sanitizar_nome_arquivo_anexo(nome_longo)
    assert res == "autorizacao_especial_de_acesso_ao_parque.pdf"
    assert len(Path(res).stem) <= 40


def test_dialogo_layout_e_componentes_iniciais(qapp, tmp_path):
    dialogo = DialogoInserirBotaoMarkdown(caminho_db=tmp_path)
    assert dialogo.windowTitle() == "Inserir Botão ou Link no Markdown"
    assert dialogo.input_texto is not None
    assert dialogo.btn_inserir is not None
    assert dialogo.btn_inserir.isEnabled() is False


def test_dialogo_link_externo(qapp, tmp_path):
    dialogo = DialogoInserirBotaoMarkdown(caminho_db=tmp_path)

    # Alterna para aba Link Externo (índice 1)
    dialogo.tab_widget.setCurrentIndex(1)
    dialogo.input_url.setText("https://aresta.app")

    # Sem texto, botão ainda deve estar desabilitado
    assert dialogo.btn_inserir.isEnabled() is False

    # Preenche o texto do botão
    dialogo.input_texto.setText("Acessar Aresta")
    assert dialogo.btn_inserir.isEnabled() is True

    assert dialogo.obter_tag_markdown() == "[Acessar Aresta](https://aresta.app)"
    assert dialogo.obter_caminho_anexo() is None
    assert dialogo.obter_bytes_anexo() is None
    assert dialogo.obter_texto_botao() == "Acessar Aresta"


def test_dialogo_anexos_existentes_listagem_e_selecao(qapp, tmp_path):
    pasta_anexos = tmp_path / "anexos"
    pasta_anexos.mkdir(parents=True, exist_ok=True)

    (pasta_anexos / "ficha_autorizacao.pdf").write_bytes(b"%PDF-1.4 ficha")
    (pasta_anexos / "termo_risco.pdf").write_bytes(b"%PDF-1.4 termo")

    dialogo = DialogoInserirBotaoMarkdown(caminho_db=tmp_path)
    # Aba 0: Anexos
    dialogo.tab_widget.setCurrentIndex(0)

    # Deve listar os 2 arquivos
    assert dialogo.lista_anexos.count() == 2

    # Testa filtro de busca
    dialogo.input_busca_anexo.setText("ficha")
    assert dialogo.lista_anexos.item(0).isHidden() is False
    assert dialogo.lista_anexos.item(1).isHidden() is True

    dialogo.input_busca_anexo.setText("")
    assert dialogo.lista_anexos.item(0).isHidden() is False
    assert dialogo.lista_anexos.item(1).isHidden() is False

    # Seleciona o primeiro arquivo
    dialogo.lista_anexos.setCurrentRow(0)
    dialogo.input_texto.setText("Baixar Ficha de Autorização")

    assert dialogo.btn_inserir.isEnabled() is True
    assert (
        dialogo.obter_tag_markdown()
        == "[Baixar Ficha de Autorização](anexos/ficha_autorizacao.pdf)"
    )
    assert dialogo.obter_caminho_anexo() == "anexos/ficha_autorizacao.pdf"
    assert dialogo.obter_bytes_anexo() is None


def test_dialogo_importar_novo_anexo_arquivo(qapp, tmp_path):
    caminho_db = tmp_path / "croqui_db"
    caminho_db.mkdir()

    pasta_externa = tmp_path / "externo"
    pasta_externa.mkdir()
    pdf_externo = pasta_externa / "Meu Documento de Acesso.pdf"
    conteudo_pdf = b"%PDF-1.4 Documento original externo"
    pdf_externo.write_bytes(conteudo_pdf)

    dialogo = DialogoInserirBotaoMarkdown(caminho_db=caminho_db)
    dialogo.importar_arquivo_anexo(pdf_externo)

    # Nome sanitizado deve ser meu_documento_de_acesso.pdf
    assert dialogo.obter_caminho_anexo() == "anexos/meu_documento_de_acesso.pdf"
    assert dialogo.obter_bytes_anexo() == conteudo_pdf

    dialogo.input_texto.setText("Pedir Autorização")
    assert dialogo.btn_inserir.isEnabled() is True
    assert dialogo.obter_tag_markdown() == "[Pedir Autorização](anexos/meu_documento_de_acesso.pdf)"


def test_dialogo_validacao_campos_obrigatorios(qapp, tmp_path):
    dialogo = DialogoInserirBotaoMarkdown(caminho_db=tmp_path)

    # Inicialmente nada selecionado e sem texto
    assert dialogo.btn_inserir.isEnabled() is False
    dialogo.accept()
    assert dialogo.result() == 0  # Rejeitado/não aceito

    # Define texto sem destino
    dialogo.input_texto.setText("Apenas Texto")
    assert dialogo.btn_inserir.isEnabled() is False

    # Muda para aba URL e define URL
    dialogo.tab_widget.setCurrentIndex(1)
    dialogo.input_url.setText("https://exemplo.com")
    assert dialogo.btn_inserir.isEnabled() is True

    dialogo.accept()
    assert dialogo.result() == 1  # Aceito


def test_dialogo_anexos_em_memoria_e_arquivo_inexistente(qapp, tmp_path):
    class MockModel:
        def obter_anexos_em_memoria(self):
            return {
                "anexos/doc_memoria.pdf": b"pdf1",
                "sem_prefixo.pdf": b"pdf2",
            }

    model = MockModel()
    dialogo = DialogoInserirBotaoMarkdown(caminho_db=tmp_path, model=model)
    assert dialogo.lista_anexos.count() == 2

    # Teste de importação de arquivo inexistente
    dialogo.importar_arquivo_anexo(tmp_path / "nao_existe.pdf")


def test_dialogo_clicar_importar_anexo(qapp, tmp_path, monkeypatch):
    dialogo = DialogoInserirBotaoMarkdown(caminho_db=tmp_path)
    arquivo_teste = tmp_path / "teste_clique.pdf"
    arquivo_teste.write_bytes(b"%PDF teste")

    # Caso 1: usuário selecionou arquivo
    monkeypatch.setattr(
        "editor.views.dialogos.dialogo_inserir_botao_markdown.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: (str(arquivo_teste), "PDF"),
    )
    dialogo._ao_clicar_importar_anexo()
    assert dialogo.obter_caminho_anexo() == "anexos/teste_clique.pdf"

    # Caso 2: usuário cancelou
    monkeypatch.setattr(
        "editor.views.dialogos.dialogo_inserir_botao_markdown.QFileDialog.getOpenFileName",
        lambda *args, **kwargs: ("", ""),
    )
    dialogo._ao_clicar_importar_anexo()

    # Validação de atributo ausente
    del dialogo.btn_inserir
    dialogo._atualizar_estado_botao_inserir()
