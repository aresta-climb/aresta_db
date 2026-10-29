# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes comportamentais para a biblioteca de publicação e limpeza de artefatos de PR no R2."""

from pathlib import Path

from serving.cliente_r2_fake import ClienteR2Fake
from serving.publicador_pr_r2_lib import (
    criar_cliente_r2_do_ambiente,
    limpar_pasta_pr_no_r2,
    obter_tipo_mime_arquivo,
    publicar_diretorio_pr_no_r2,
)


def test_publica_artefatos_da_pr_com_tipos_mime_corretos_e_remove_orfaos_anteriores(
    tmp_path: Path,
) -> None:
    """Deve enviar todos os arquivos compilados sob pr/<id>/ e excluir arquivos órfãos de commits anteriores."""
    fake = ClienteR2Fake()
    # Simula arquivo órfão deixado por um commit anterior na mesma PR #42 e arquivo de outra PR #99
    fake.put_object(Bucket="aresta-serving", Key="pr/42/antigo/orfao.webp", Body=b"velho")
    fake.put_object(Bucket="aresta-serving", Key="pr/99/resumo.html", Body=b"outra_pr")

    dir_compilado = tmp_path / "saida_pr"
    (dir_compilado / "cipo" / "imagens").mkdir(parents=True)
    (dir_compilado / "_base" / "cipo" / "imagens").mkdir(parents=True)
    (dir_compilado / "thumbnails").mkdir(parents=True)

    (dir_compilado / "resumo.html").write_text("<html>Resumo</html>", encoding="utf-8")
    (dir_compilado / "indice.binarypb").write_bytes(b"\x08\x01")
    (dir_compilado / "indice.yaml").write_text("croquis: []\n", encoding="utf-8")
    (dir_compilado / "catalogo.db").write_bytes(b"SQLite format 3")
    (dir_compilado / "cipo" / "compilado.binarypb").write_bytes(b"\x08\x02")
    (dir_compilado / "cipo" / "imagens" / "mapa.webp").write_bytes(b"RIFF....WEBP")
    (dir_compilado / "_base" / "cipo" / "imagens" / "mapa.webp").write_bytes(b"RIFF_BASE_WEBP")
    (dir_compilado / "thumbnails" / "cipo.webp").write_bytes(b"RIFF_THUMB")
    (dir_compilado / "cipo" / "anexo.bin").write_bytes(b"\x00\x01")

    resultado = publicar_diretorio_pr_no_r2(
        diretorio_compilado=dir_compilado,
        numero_pr=42,
        cliente_r2=fake,
        bucket="aresta-serving",
    )

    assert resultado.prefixo == "pr/42/"
    assert len(resultado.arquivos_enviados) == 9
    assert resultado.arquivos_orfaos_removidos == ["pr/42/antigo/orfao.webp"]

    # Verifica que o órfão foi removido, mas outra PR permaneceu intacta
    assert fake.obter_conteudo("aresta-serving", "pr/42/antigo/orfao.webp") is None
    assert fake.obter_conteudo("aresta-serving", "pr/99/resumo.html") == b"outra_pr"

    # Verifica tipos MIME e conteúdos publicados
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/resumo.html")
        == "text/html; charset=utf-8"
    )
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/indice.binarypb")
        == "application/x-protobuf"
    )
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/indice.yaml")
        == "text/yaml; charset=utf-8"
    )
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/catalogo.db")
        == "application/vnd.sqlite3"
    )
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/cipo/imagens/mapa.webp")
        == "image/webp"
    )
    assert (
        fake.obter_conteudo("aresta-serving", "pr/42/_base/cipo/imagens/mapa.webp")
        == b"RIFF_BASE_WEBP"
    )
    assert (
        fake.obter_tipo_conteudo("aresta-serving", "pr/42/cipo/anexo.bin")
        == "application/octet-stream"
    )
    assert obter_tipo_mime_arquivo(Path("teste.yml")) == "text/yaml; charset=utf-8"


def test_limpa_integralmente_pasta_da_pr_no_fechamento() -> None:
    """Deve excluir todos os objetos sob pr/<id>/ quando a PR for fechada e retornar vazio se já limpa."""
    fake = ClienteR2Fake()
    fake.put_object(Bucket="aresta-serving", Key="pr/42/resumo.html", Body=b"1")
    fake.put_object(Bucket="aresta-serving", Key="pr/42/cipo/compilado.binarypb", Body=b"2")
    fake.put_object(Bucket="aresta-serving", Key="pr/43/resumo.html", Body=b"3")

    removidos = limpar_pasta_pr_no_r2(numero_pr=42, cliente_r2=fake, bucket="aresta-serving")
    assert removidos == ["pr/42/cipo/compilado.binarypb", "pr/42/resumo.html"]
    assert fake.listar_chaves("aresta-serving", prefixo="pr/42/") == []
    assert fake.listar_chaves("aresta-serving", prefixo="pr/43/") == ["pr/43/resumo.html"]

    # Segunda chamada com prefixo já vazio
    assert limpar_pasta_pr_no_r2(numero_pr=42, cliente_r2=fake, bucket="aresta-serving") == []


def test_cria_cliente_r2_do_ambiente_ou_retorna_none_sem_credenciais() -> None:
    """Deve retornar None quando faltarem variáveis do R2 e instanciar o cliente S3 quando presentes."""
    assert criar_cliente_r2_do_ambiente({}) is None
    assert criar_cliente_r2_do_ambiente({"AWS_ACCESS_KEY_ID": "k"}) is None

    res = criar_cliente_r2_do_ambiente(
        {
            "AWS_ACCESS_KEY_ID": "chave_id",
            "AWS_SECRET_ACCESS_KEY": "chave_secreta",
            "R2_ENDPOINT_URL": "https://exemplo.r2.cloudflarestorage.com",
            "R2_BUCKET": "meu-bucket",
        }
    )
    assert res is not None
    cliente, bucket = res
    assert bucket == "meu-bucket"
    assert hasattr(cliente, "put_object")
