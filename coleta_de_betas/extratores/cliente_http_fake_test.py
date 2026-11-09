# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest

from coleta_de_betas.extratores.cliente_http_fake import (
    BuscadorWebFake,
    ClienteHttpFake,
)


def test_cliente_http_fake_retorna_json_texto_e_bytes_registrados() -> None:
    cliente = ClienteHttpFake()
    cliente.registrar_json("https://api.exemplo.com/dados", {"ok": True}, status_code=200)
    cliente.registrar_texto("https://blog.exemplo.com/post", "<html>Olá</html>", status_code=200)
    cliente.registrar_bytes("https://img.exemplo.com/foto.jpg", b"\x89PNG", status_code=200)

    resp_json = cliente.get("https://api.exemplo.com/dados", params={"q": "teste"})
    assert resp_json.status_code == 200
    assert resp_json.json() == {"ok": True}
    assert "ok" in resp_json.text

    resp_post = cliente.post(
        "https://api.exemplo.com/dados",
        json={"consulta": 1},
        params={"key": "abc"},
    )
    assert resp_post.status_code == 200
    assert resp_post.json() == {"ok": True}

    resp_txt = cliente.get("https://blog.exemplo.com/post")
    assert resp_txt.status_code == 200
    assert resp_txt.text == "<html>Olá</html>"
    assert resp_txt.content == "<html>Olá</html>".encode()

    resp_bytes = cliente.get("https://img.exemplo.com/foto.jpg")
    assert resp_bytes.status_code == 200
    assert resp_bytes.content == b"\x89PNG"

    resp_404 = cliente.get("https://nao.existe.com/404")
    assert resp_404.status_code == 404
    assert resp_404.json() == {}

    assert len(cliente.chamadas_get) == 4
    assert len(cliente.chamadas_post) == 1


def test_cliente_http_fake_simula_erro_de_conexao() -> None:
    cliente = ClienteHttpFake()
    cliente.registrar_erro("https://falha.exemplo.com", "Timeout simulado")

    with pytest.raises(ConnectionError, match="Timeout simulado"):
        cliente.get("https://falha.exemplo.com")

    with pytest.raises(ConnectionError, match="Timeout simulado"):
        cliente.post("https://falha.exemplo.com", json={})


def test_buscador_web_fake_retorna_resultados_e_simula_erro() -> None:
    buscador = BuscadorWebFake()
    buscador.registrar_resultados(
        "Fenda da Preguiça",
        [{"href": "https://blog.com/fenda", "title": "Blog Fenda", "body": "Relato"}],
    )

    res = buscador.buscar_texto('"Fenda da Preguiça" escalada', max_resultados=5)
    assert len(res) == 1
    assert res[0]["href"] == "https://blog.com/fenda"
    assert buscador.queries_executadas == [('"Fenda da Preguiça" escalada', 5)]

    assert buscador.buscar_texto("Outra Via", max_resultados=5) == []

    buscador.registrar_erro("Falha na busca web")
    with pytest.raises(RuntimeError, match="Falha na busca web"):
        buscador.buscar_texto("Qualquer", max_resultados=5)
