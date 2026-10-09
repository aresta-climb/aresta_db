# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários da biblioteca pura de gerenciamento de UIDs e URLs aresta.cc."""

import pytest
import string
from scripts.gerenciar_uids_lib import (
    ALFABETO_BASE62,
    TAMANHO_UID,
    DOMINIO_CURTO,
    gerar_uid,
    validar_uid,
    formatar_url_aresta,
    extrair_uid_de_url,
)


def test_constantes() -> None:
    """Valida as constantes fundamentais da biblioteca."""
    assert TAMANHO_UID == 14
    assert len(ALFABETO_BASE62) == 62
    assert set(ALFABETO_BASE62) == set(string.digits + string.ascii_letters)
    assert DOMINIO_CURTO == "aresta.cc"


def test_gerar_uid_formato_e_tamanho() -> None:
    """Garante que gerar_uid produz uma string de 14 caracteres em Base62."""
    uid = gerar_uid()
    assert isinstance(uid, str)
    assert len(uid) == 14
    assert validar_uid(uid) is True
    # Não deve conter separadores de Base64 padrão como '-' ou '_'
    assert "-" not in uid
    assert "_" not in uid


def test_gerar_uid_unicidade_estatistica() -> None:
    """Garante que a geração de múltiplos UIDs não produz colisões."""
    uids = {gerar_uid() for _ in range(1000)}
    assert len(uids) == 1000


def test_validar_uid_casos_validos() -> None:
    """Valida identificadores válidos de 14 caracteres alfanuméricos."""
    assert validar_uid("x8siJek3FiG3aB") is True
    assert validar_uid("0123456789ABCD") is True
    assert validar_uid("abcdefghijklmn") is True
    assert validar_uid("ABCDEFGHIJKLMN") is True


def test_validar_uid_casos_invalidos() -> None:
    """Valida rejeição de identificadores com tamanho incorreto ou caracteres inválidos."""
    # Tamanho menor
    assert validar_uid("x8siJek3FiG3a") is False
    assert validar_uid("") is False

    # Tamanho maior
    assert validar_uid("x8siJek3FiG3aBC") is False

    # Caracteres inválidos (hífen, underline, símbolos, espaços)
    assert validar_uid("x8si-ek3FiG3aB") is False
    assert validar_uid("x8si_ek3FiG3aB") is False
    assert validar_uid("x8siJek3FiG3a ") is False
    assert validar_uid(" x8siJek3FiG3a") is False
    assert validar_uid("x8siJek3FiG3a@") is False
    assert validar_uid("x8siJek3FiG3aã") is False

    # Tipo não-string
    assert validar_uid(None) is False  # type: ignore[arg-type]
    assert validar_uid(12345678901234) is False  # type: ignore[arg-type]


def test_formatar_url_aresta_valido() -> None:
    """Garante que formatar_url_aresta gera URLs canônicas de exatamente 32 caracteres."""
    url = formatar_url_aresta("x8siJek3FiG3aB")
    assert url == "https://aresta.cc/x8siJek3FiG3aB"
    assert len(url) == 32


def test_formatar_url_aresta_invalido() -> None:
    """Garante que formatar_url_aresta rejeita UIDs inválidos levantando ValueError."""
    with pytest.raises(ValueError, match="UID inválido"):
        formatar_url_aresta("curto")

    with pytest.raises(ValueError, match="UID inválido"):
        formatar_url_aresta("invalido_com_underline")


def test_extrair_uid_de_url_validas() -> None:
    """Testa a extração de UIDs a partir de diversas variações de URLs aresta.cc."""
    assert extrair_uid_de_url("https://aresta.cc/x8siJek3FiG3aB") == "x8siJek3FiG3aB"
    assert extrair_uid_de_url("https://www.aresta.cc/x8siJek3FiG3aB") == "x8siJek3FiG3aB"
    assert extrair_uid_de_url("http://aresta.cc/x8siJek3FiG3aB") == "x8siJek3FiG3aB"
    assert extrair_uid_de_url("https://aresta.cc/x8siJek3FiG3aB/") == "x8siJek3FiG3aB"
    assert extrair_uid_de_url("aresta.cc/x8siJek3FiG3aB") == "x8siJek3FiG3aB"
    assert extrair_uid_de_url("https://aresta.cc/x8siJek3FiG3aB?src=qrcode#detalhes") == "x8siJek3FiG3aB"


def test_extrair_uid_de_url_invalidas() -> None:
    """Testa rejeição de URLs com domínio incorreto, caminhos inexistentes ou UIDs inválidos."""
    # Outro domínio
    assert extrair_uid_de_url("https://google.com/x8siJek3FiG3aB") is None
    assert extrair_uid_de_url("https://arestaclimb.com/x8siJek3FiG3aB") is None

    # Sem caminho / sem UID
    assert extrair_uid_de_url("https://aresta.cc/") is None
    assert extrair_uid_de_url("https://aresta.cc") is None

    # UID no caminho com tamanho inválido
    assert extrair_uid_de_url("https://aresta.cc/curto") is None
    assert extrair_uid_de_url("https://aresta.cc/uidMuitoLongoParaOMunicipioDeSeteLagoas") is None

    # UID com caracteres inválidos
    assert extrair_uid_de_url("https://aresta.cc/x8si_ek3FiG3aB") is None
    assert extrair_uid_de_url("https://aresta.cc/x8si-ek3FiG3aB") is None

    # String vazia ou inválida
    assert extrair_uid_de_url("") is None
    assert extrair_uid_de_url("   ") is None
    assert extrair_uid_de_url(None) is None  # type: ignore[arg-type]

    # URL sintaticamente malformada levantando exceção no urlparse
    assert extrair_uid_de_url("http://[") is None


def test_sanear_uids_croqui_completo(tmp_path) -> None:
    """Testa sanear_uids_croqui gerando UIDs para entidades e resolvendo referências."""
    from scripts.gerenciar_uids_lib import sanear_uids_croqui

    pico = tmp_path / "croqui_teste"
    pico.mkdir()

    yaml_conteudo = """\
id: "br_mg_teste"
nome: "Pico de Teste"
botoes:
  - texto: "Capa"
    destino:
      secao_textual:
        caminho: "capa.md"
"""
    (pico / "croqui.yaml").write_text(yaml_conteudo, encoding="utf-8")

    setor_conteudo = """\
---
nome: "Setor Inicial"
escaladas:
  - via_esportiva:
      nome: "Via do Sol"
mapas:
  - caminho_imagem_mapa: "mapas/m1.webp"
    pontos_de_interesse:
      - id: "p1"
        label: "01"
        circulo: {x: 10, y: 10, raio: 5}
    referencias:
      - escalada: "Via do Sol"
        ids: ["p1"]
---
Texto do setor.
"""
    (pico / "setor1.md").write_text(setor_conteudo, encoding="utf-8")

    # 1. Executa saneamento
    modificado = sanear_uids_croqui(pico)
    assert modificado is True

    # 2. Verifica se UIDs foram gerados e referências migradas
    texto_yaml = (pico / "croqui.yaml").read_text(encoding="utf-8")
    assert "uid:" in texto_yaml

    texto_md = (pico / "setor1.md").read_text(encoding="utf-8")
    assert "uid:" in texto_md
    assert "rotulo: '01'" in texto_md or 'rotulo: "01"' in texto_md or 'rotulo: 01' in texto_md
    assert "alvo_uid:" in texto_md
    assert "pontos_uids:" in texto_md

    # 3. Idempotência: rodar novamente não deve modificar o disco
    modificado_novamente = sanear_uids_croqui(pico)
    assert modificado_novamente is False

