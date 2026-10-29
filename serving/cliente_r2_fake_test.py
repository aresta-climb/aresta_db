# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes comportamentais para a biblioteca de Fake determinístico do cliente R2/S3."""

import pytest

from serving.cliente_r2_fake import ClienteR2Fake, ErroOperacaoR2Fake


def test_armazena_recupera_e_lista_objetos_por_prefixo_em_memoria() -> None:
    """Deve armazenar bytes e Content-Type no bucket em memória e listar chaves filtradas por prefixo."""
    fake = ClienteR2Fake()

    fake.put_object(
        Bucket="aresta-serving",
        Key="pr/42/resumo.html",
        Body=b"<html>ok</html>",
        ContentType="text/html; charset=utf-8",
    )
    fake.put_object(
        Bucket="aresta-serving",
        Key="pr/42/cipo/compilado.binarypb",
        Body=b"\x08\x01",
        ContentType="application/x-protobuf",
    )
    fake.put_object(
        Bucket="aresta-serving",
        Key="pr/99/outro.txt",
        Body="texto",
        ContentType="text/plain",
    )

    assert fake.obter_conteudo("aresta-serving", "pr/42/resumo.html") == b"<html>ok</html>"
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/resumo.html")
        == "text/html; charset=utf-8"
    )
    assert fake.obter_conteudo("aresta-serving", "pr/99/outro.txt") == b"texto"

    resposta = fake.list_objects_v2(Bucket="aresta-serving", Prefix="pr/42/")
    chaves = [item["Key"] for item in resposta["Contents"]]
    assert chaves == ["pr/42/cipo/compilado.binarypb", "pr/42/resumo.html"]
    assert fake.listar_chaves("aresta-serving", prefixo="pr/42/") == [
        "pr/42/cipo/compilado.binarypb",
        "pr/42/resumo.html",
    ]

    leitura = fake.get_object(Bucket="aresta-serving", Key="pr/42/resumo.html")
    assert leitura["Body"].read() == b"<html>ok</html>"
    assert leitura["ContentType"] == "text/html; charset=utf-8"


def test_exclui_objetos_em_lote_e_retorna_lista_vazia_quando_prefixo_inexistente() -> None:
    """Deve remover múltiplos objetos via delete_objects e retornar listagem sem Contents quando vazio."""
    fake = ClienteR2Fake()
    fake.put_object(Bucket="b1", Key="pr/10/a.webp", Body=b"123")
    fake.put_object(Bucket="b1", Key="pr/10/b.webp", Body=b"456")

    resultado = fake.delete_objects(
        Bucket="b1",
        Delete={"Objects": [{"Key": "pr/10/a.webp"}, {"Key": "pr/10/b.webp"}]},
    )
    assert len(resultado["Deleted"]) == 2
    assert fake.list_objects_v2(Bucket="b1", Prefix="pr/10/") == {"KeyCount": 0}


def test_simula_falha_deterministica_de_io_quando_configurado() -> None:
    """Deve lançar ErroOperacaoR2Fake ao executar uma operação configurada para falhar."""
    fake = ClienteR2Fake()
    fake.configurar_falha("put_object", "Falha simulada de rede no upload")

    with pytest.raises(ErroOperacaoR2Fake, match="Falha simulada de rede no upload"):
        fake.put_object(Bucket="b1", Key="k1", Body=b"dados")

    fake.limpar_falhas()
    fake.put_object(Bucket="b1", Key="k1", Body=b"dados")
    assert fake.obter_conteudo("b1", "k1") == b"dados"

    with pytest.raises(ErroOperacaoR2Fake, match="Objeto não encontrado"):
        fake.get_object(Bucket="b1", Key="inexistente")
