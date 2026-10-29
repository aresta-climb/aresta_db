# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

import pytest

from editor.core.codigo_sessao import (
    eh_codigo_pull_request,
    extrair_numero_pull_request,
    formatar_codigo,
    gerar_codigo_pull_request,
    normalizar_codigo,
    obter_url_previa,
    obter_url_resumo_previa,
    validar_codigo,
    validar_codigo_sessao_editor,
)


def test_deve_formatar_codigo_com_hifen_oito_ou_mais_caracteres():
    """Formata códigos de 8 ou mais caracteres adicionando hífen após o quarto caractere."""
    assert formatar_codigo("k9x2p83a") == "k9x2-p83a"
    assert formatar_codigo("12345678") == "1234-5678"
    assert formatar_codigo("pr000042") == "pr00-0042"
    assert formatar_codigo("pr1234567") == "pr12-34567"


def test_deve_lancar_erro_ao_formatar_codigo_invalido():
    """Lança ValueError ao tentar formatar código com menos de 8 caracteres ou não string."""
    with pytest.raises(ValueError, match="O código deve ter pelo menos 8 caracteres"):
        formatar_codigo("curto")
    with pytest.raises(ValueError, match="O código deve ter pelo menos 8 caracteres"):
        formatar_codigo(12345678)  # type: ignore


def test_deve_validar_codigo_correto_oito_ou_mais_caracteres():
    """Valida códigos com e sem hífen, de 8 ou mais caracteres, em maiúsculas ou minúsculas."""
    assert validar_codigo("k9x2p83a") is True
    assert validar_codigo("k9x2-p83a") is True
    assert validar_codigo("K9X2-P83A") is True
    assert validar_codigo("K9X2P83A") is True
    assert validar_codigo("pr00-0042") is True
    assert validar_codigo("pr12-34567") is True
    assert validar_codigo("k9x2p83a123") is True


def test_deve_invalidar_codigo_incorreto():
    """Retorna False para códigos com caracteres ilegais ou menos de 8 caracteres."""
    assert validar_codigo("k9x2-p83!") is False
    assert validar_codigo("k9x2@83a") is False
    assert validar_codigo("k9x2-p83") is False  # 7 chars
    assert validar_codigo("") is False
    assert validar_codigo(None) is False  # type: ignore


def test_deve_normalizar_codigo():
    """Normaliza o código removendo espaços e hifens e transformando em minúsculas."""
    assert normalizar_codigo("K9X2-P83A") == "k9x2p83a"
    assert normalizar_codigo("  k9x2 p83a  ") == "k9x2p83a"
    assert normalizar_codigo("1234-5678") == "12345678"
    assert normalizar_codigo("PR12-34567") == "pr1234567"


def test_deve_lancar_erro_ao_normalizar_codigo_invalido():
    """Lança ValueError ao tentar normalizar código inválido."""
    with pytest.raises(ValueError, match="Código inválido"):
        normalizar_codigo("curto")
    with pytest.raises(ValueError, match="Código inválido"):
        normalizar_codigo("invalido_caractere_especial!")
    with pytest.raises(ValueError, match="Código inválido: deve ser uma string"):
        normalizar_codigo(12345678)  # type: ignore


def test_deve_obter_url_previa_canonica():
    """Gera URL com https://previa.arestaclimb.com/k9x2-p83a por padrão."""
    url = obter_url_previa("k9x2p83a")
    assert url == "https://previa.arestaclimb.com/k9x2-p83a"

    url_sem_hifen = obter_url_previa("K9X2-P83A", com_hifen=False)
    assert url_sem_hifen == "https://previa.arestaclimb.com/k9x2p83a"

    url_pr_longo = obter_url_previa("pr1234567")
    assert url_pr_longo == "https://previa.arestaclimb.com/pr12-34567"


def test_deve_obter_url_resumo_previa():
    """Gera URL do relatório visual de resumo em https://previa.arestaclimb.com/resumo/<codigo>."""
    assert obter_url_resumo_previa("pr000042") == "https://previa.arestaclimb.com/resumo/pr00-0042"
    assert (
        obter_url_resumo_previa("pr00-0042", com_hifen=False)
        == "https://previa.arestaclimb.com/resumo/pr000042"
    )


def test_deve_gerar_codigo_pull_request_com_zero_padding_e_unbounded():
    """Gera código de PR com 8 caracteres por padrão até 6 dígitos e unbounded acima disso."""
    assert gerar_codigo_pull_request(42) == "pr00-0042"
    assert gerar_codigo_pull_request(42, formatado=False) == "pr000042"
    assert gerar_codigo_pull_request(999999) == "pr99-9999"
    assert gerar_codigo_pull_request(1234567) == "pr12-34567"
    assert gerar_codigo_pull_request(1234567, formatado=False) == "pr1234567"


def test_deve_rejeitar_numero_pull_request_invalido():
    """Lança ValueError se o número da PR não for um inteiro positivo."""
    with pytest.raises(ValueError, match="O número da Pull Request deve ser um inteiro positivo"):
        gerar_codigo_pull_request(0)
    with pytest.raises(ValueError, match="O número da Pull Request deve ser um inteiro positivo"):
        gerar_codigo_pull_request(-5)
    with pytest.raises(ValueError, match="O número da Pull Request deve ser um inteiro positivo"):
        gerar_codigo_pull_request("42")  # type: ignore
    with pytest.raises(ValueError, match="O número da Pull Request deve ser um inteiro positivo"):
        gerar_codigo_pull_request(True)  # type: ignore


def test_deve_extrair_numero_pull_request_e_identificar_codigo_pr():
    """Extrai o número inteiro da PR de códigos iniciados por 'pr' seguidos de dígitos."""
    assert extrair_numero_pull_request("pr00-0042") == 42
    assert extrair_numero_pull_request("PR000042") == 42
    assert extrair_numero_pull_request("pr12-34567") == 1234567
    assert extrair_numero_pull_request("k9x2-p83a") is None
    assert extrair_numero_pull_request("pr000000") is None
    assert extrair_numero_pull_request("prabcdef") is None
    assert extrair_numero_pull_request("curto") is None
    assert extrair_numero_pull_request(None) is None

    assert eh_codigo_pull_request("pr00-0042") is True
    assert eh_codigo_pull_request("pr1234567") is True
    assert eh_codigo_pull_request("k9x2-p83a") is False
    assert eh_codigo_pull_request(None) is False


def test_deve_reservar_prefixo_pr_nas_sessoes_do_editor():
    """Impede que sessões normais do Editor Desktop utilizem códigos iniciados por 'pr'."""
    assert validar_codigo_sessao_editor("k9x2-p83a") is True
    assert validar_codigo_sessao_editor("k9x2p83a99") is True
    assert validar_codigo_sessao_editor("pr00-0042") is False
    assert validar_codigo_sessao_editor("prabcdef") is False
    assert validar_codigo_sessao_editor("curto") is False
    assert validar_codigo_sessao_editor(None) is False
