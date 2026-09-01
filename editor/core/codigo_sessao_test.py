# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Contributors

import pytest
from editor.core.codigo_sessao import (
    formatar_codigo,
    validar_codigo,
    normalizar_codigo,
    obter_url_previa,
    CARACTERES_BASE36,
)


def test_deve_formatar_codigo_com_hifen():
    """Formata um código de 8 caracteres no formato 4x4 (ex: k9x2-p83a)."""
    assert formatar_codigo("k9x2p83a") == "k9x2-p83a"
    assert formatar_codigo("12345678") == "1234-5678"


def test_deve_lancar_erro_ao_formatar_codigo_invalido():
    """Lança ValueError ao tentar formatar código com tamanho diferente de 8 ou não string."""
    with pytest.raises(ValueError, match="O código deve ter exatamente 8 caracteres"):
        formatar_codigo("curto")
    with pytest.raises(ValueError, match="O código deve ter exatamente 8 caracteres"):
        formatar_codigo("muitolongocommaisdeoito")
    with pytest.raises(ValueError, match="O código deve ter exatamente 8 caracteres"):
        formatar_codigo(12345678) # type: ignore


def test_deve_validar_codigo_correto():
    """Valida códigos com e sem hífen, em maiúsculas ou minúsculas."""
    assert validar_codigo("k9x2p83a") is True
    assert validar_codigo("k9x2-p83a") is True
    assert validar_codigo("K9X2-P83A") is True
    assert validar_codigo("K9X2P83A") is True


def test_deve_invalidar_codigo_incorreto():
    """Retorna False para códigos com caracteres ilegais ou tamanho incorreto."""
    assert validar_codigo("k9x2-p83!") is False
    assert validar_codigo("k9x2@83a") is False
    assert validar_codigo("k9x2-p83") is False # 7 chars
    assert validar_codigo("k9x2-p83a1") is False # 9 chars
    assert validar_codigo("") is False
    assert validar_codigo(None) is False # type: ignore


def test_deve_normalizar_codigo():
    """Normaliza o código removendo espaços e hifens e transformando em minúsculas."""
    assert normalizar_codigo("K9X2-P83A") == "k9x2p83a"
    assert normalizar_codigo("  k9x2 p83a  ") == "k9x2p83a"
    assert normalizar_codigo("1234-5678") == "12345678"


def test_deve_lancar_erro_ao_normalizar_codigo_invalido():
    """Lança ValueError ao tentar normalizar código inválido."""
    with pytest.raises(ValueError, match="Código inválido"):
        normalizar_codigo("curto")
    with pytest.raises(ValueError, match="Código inválido"):
        normalizar_codigo("invalido_caractere_especial!")
    with pytest.raises(ValueError, match="Código inválido: deve ser uma string"):
        normalizar_codigo(12345678) # type: ignore


def test_deve_obter_url_previa_canonica():
    """Gera URL com https://previa.arestaclimb.com/k9x2-p83a por padrão."""
    url = obter_url_previa("k9x2p83a")
    assert url == "https://previa.arestaclimb.com/k9x2-p83a"

    url_sem_hifen = obter_url_previa("K9X2-P83A", com_hifen=False)
    assert url_sem_hifen == "https://previa.arestaclimb.com/k9x2p83a"
