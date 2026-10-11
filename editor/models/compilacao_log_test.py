# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from editor.models.compilacao_log import CompilacaoLog


def test_compilacao_log_estado_inicial():
    log = CompilacaoLog()
    assert log.obter_logs() == []
    assert log.tem_avisos_ou_erros() is False


def test_compilacao_log_adicionar_logs_sem_erro():
    log = CompilacaoLog()
    mensagens = ["Compilando...", "Tudo certo."]

    log.atualizar(mensagens)

    assert log.obter_logs() == mensagens
    assert log.tem_avisos_ou_erros() is False


def test_compilacao_log_adicionar_logs_com_aviso():
    log = CompilacaoLog()
    mensagens = ["Compilando...", "Aviso: mapa vazio."]

    log.atualizar(mensagens)

    assert log.obter_logs() == mensagens
    assert log.tem_avisos_ou_erros() is True


def test_compilacao_log_adicionar_logs_com_erro():
    log = CompilacaoLog()
    mensagens = ["Erro: arquivo yaml invalido."]

    log.atualizar(mensagens)

    assert log.obter_logs() == mensagens
    assert log.tem_avisos_ou_erros() is True


def test_compilacao_log_case_insensitive_e_keywords():
    log = CompilacaoLog()
    # "error", "erro", "falhou", "aviso"
    mensagens = [
        "The compilation failed to start.",
        "ERROR 500",
        "Um ErRo Aconteceu",
        "Falhou miserablemente",
    ]

    for msg in mensagens:
        log.atualizar([msg])
        assert log.tem_avisos_ou_erros() is True, f"Falhou para: {msg}"


def test_compilacao_log_ignora_ferros_sem_erro():
    log = CompilacaoLog()
    mensagens = [
        "Alvos específicos  : [WindowsPath('database/br_mg_ferros_ferros')]",
        "[br_mg_ferros_ferros] (1/1)",
        "  Gerando thumbnail: imagens/capa_p0_i0.webp -> thumbnails/br_mg_ferros_ferros.webp",
        "  Imagens copiadas: generated/br_mg_ferros_ferros/imagens",
        "  107 imagem(ns) indexada(s) em arquivos_externos",
    ]
    log.atualizar(mensagens)
    assert log.tem_avisos_ou_erros() is False
