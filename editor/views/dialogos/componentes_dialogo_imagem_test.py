# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes comportamentais para o cache compartilhado de miniaturas 96x96 e leitura
sob demanda de imagens da galeria dos diálogos.
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.views.dialogos.componentes_dialogo_imagem import (
    limpar_cache_miniaturas_imagem,
    obter_bytes_imagem_croqui,
    obter_icone_miniatura_imagem,
)


def _gerar_webp(largura: int, altura: int, cor: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (largura, altura), color=cor).save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _limpar_cache():
    limpar_cache_miniaturas_imagem()
    yield
    limpar_cache_miniaturas_imagem()


def test_obter_icone_miniatura_disco_com_hit_de_cache_sem_releitura(qtbot, tmp_path, monkeypatch):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()
    arq = pasta_imagens / "mapa_grande.webp"
    arq.write_bytes(_gerar_webp(800, 600, (20, 120, 220)))

    leituras = []
    orig_read_bytes = Path.read_bytes

    def monitorar_read_bytes(self: Path) -> bytes:
        leituras.append(self.name)
        return orig_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", monitorar_read_bytes)

    icone_1 = obter_icone_miniatura_imagem("mapa_grande.webp", pasta_imagens=pasta_imagens)
    assert icone_1 is not None
    assert not icone_1.isNull()
    assert len(leituras) == 1

    # Segunda chamada deve atingir o cache sem ler os bytes do disco novamente
    icone_2 = obter_icone_miniatura_imagem("mapa_grande.webp", pasta_imagens=pasta_imagens)
    assert icone_2 is icone_1
    assert len(leituras) == 1


def test_invalidacao_cache_ao_substituir_imagem_em_ram(qtbot, tmp_path):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()
    bytes_disco = _gerar_webp(400, 300, (255, 0, 0))
    (pasta_imagens / "foto.webp").write_bytes(bytes_disco)

    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_caminho_db(tmp_path)

    icone_disco = obter_icone_miniatura_imagem(
        "foto.webp", pasta_imagens=pasta_imagens, model=model
    )
    assert icone_disco is not None

    # Substitui na memória RAM do modelo
    bytes_ram = _gerar_webp(500, 500, (0, 255, 0))
    model.definir_imagem_memoria("imagens/foto.webp", bytes_ram)

    icone_ram_1 = obter_icone_miniatura_imagem(
        "foto.webp", pasta_imagens=pasta_imagens, model=model
    )
    assert icone_ram_1 is not None
    assert icone_ram_1 is not icone_disco

    # Segunda chamada com os mesmos bytes em RAM reutiliza o cache da RAM
    icone_ram_2 = obter_icone_miniatura_imagem(
        "foto.webp", pasta_imagens=pasta_imagens, model=model
    )
    assert icone_ram_2 is icone_ram_1


def test_obter_icone_miniatura_casos_borda_inexistente_ou_corrompido(qtbot, tmp_path, monkeypatch):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()

    # Sem pasta e sem model
    assert obter_icone_miniatura_imagem("qualquer.webp") is None

    # Arquivo ausente
    assert obter_icone_miniatura_imagem("ausente.webp", pasta_imagens=pasta_imagens) is None

    # Arquivo corrompido no disco
    (pasta_imagens / "corrompido.webp").write_bytes(b"dados_invalidos")
    assert obter_icone_miniatura_imagem("corrompido.webp", pasta_imagens=pasta_imagens) is None

    # Imagem corrompida na RAM
    model = CroquiModel(croqui_pb2.Croqui())
    model.definir_imagem_memoria("imagens/corrompida_ram.webp", b"nao_eh_imagem")
    assert (
        obter_icone_miniatura_imagem(
            "corrompida_ram.webp", pasta_imagens=pasta_imagens, model=model
        )
        is None
    )

    # Erro de leitura de disco após stat
    (pasta_imagens / "erro_io.webp").write_bytes(_gerar_webp(100, 100, (10, 10, 10)))
    monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(OSError("Erro IO")))
    assert obter_icone_miniatura_imagem("erro_io.webp", pasta_imagens=pasta_imagens) is None


def test_obter_bytes_imagem_croqui_prioriza_ram_e_fallback_disco(qtbot, tmp_path, monkeypatch):
    pasta_imagens = tmp_path / "imagens"
    pasta_imagens.mkdir()
    bytes_disco = _gerar_webp(200, 150, (10, 20, 30))
    (pasta_imagens / "item.webp").write_bytes(bytes_disco)

    model = CroquiModel(croqui_pb2.Croqui())

    # 1. Lê do disco quando não está na RAM
    assert (
        obter_bytes_imagem_croqui("item.webp", pasta_imagens=pasta_imagens, model=model)
        == bytes_disco
    )

    # 2. Lê da RAM quando presente em _imagens_em_memoria
    bytes_ram = _gerar_webp(300, 250, (90, 80, 70))
    model.definir_imagem_memoria("imagens/item.webp", bytes_ram)
    assert (
        obter_bytes_imagem_croqui("item.webp", pasta_imagens=pasta_imagens, model=model)
        == bytes_ram
    )

    # 3. Arquivo ausente ou sem pasta
    assert obter_bytes_imagem_croqui("inexistente.webp", pasta_imagens=pasta_imagens) is None
    assert obter_bytes_imagem_croqui("inexistente.webp") is None

    # 4. Erro de I/O ao ler do disco
    monkeypatch.setattr(Path, "read_bytes", lambda self: (_ for _ in ()).throw(OSError("Erro IO")))
    assert obter_bytes_imagem_croqui("item.webp", pasta_imagens=pasta_imagens) is None
