# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Cache compartilhado de miniaturas 96x96 (QIcon) e leitura sob demanda de bytes
das imagens da galeria do croqui para os diálogos de entrada e substituição.
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

_CACHE_MINIATURAS: dict[tuple[Any, ...], QIcon] = {}


def limpar_cache_miniaturas_imagem() -> None:
    """Limpa o cache em memória de miniaturas da galeria de imagens."""
    _CACHE_MINIATURAS.clear()


def _criar_icone_miniatura_de_bytes(bytes_img: bytes, tamanho: int) -> QIcon | None:
    pixmap = QPixmap()
    if not pixmap.loadFromData(bytes_img) or pixmap.isNull():
        return None
    miniatura = pixmap.scaled(
        tamanho,
        tamanho,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    return QIcon(miniatura)


def obter_icone_miniatura_imagem(
    nome_arquivo: str,
    pasta_imagens: Path | None = None,
    model: Any | None = None,
    tamanho: int = 96,
) -> QIcon | None:
    """
    Retorna um QIcon de miniatura (96x96 por padrão) para um arquivo da pasta imagens/
    ou do buffer em memória RAM do CroquiModel, reutilizando cache em memória.
    """
    caminho_rel = f"imagens/{nome_arquivo}"
    if model is not None and hasattr(model, "obter_imagens_em_memoria"):
        imagens_ram = model.obter_imagens_em_memoria()
        if caminho_rel in imagens_ram:
            bytes_ram = imagens_ram[caminho_rel]
            chave_ram = (
                "ram",
                nome_arquivo,
                tamanho,
                len(bytes_ram),
                bytes_ram[:128],
                bytes_ram[-128:],
            )
            if chave_ram in _CACHE_MINIATURAS:
                return _CACHE_MINIATURAS[chave_ram]
            icone = _criar_icone_miniatura_de_bytes(bytes_ram, tamanho)
            if icone is not None:
                _CACHE_MINIATURAS[chave_ram] = icone
            return icone

    if pasta_imagens is not None:
        caminho_abs = Path(pasta_imagens) / nome_arquivo
        try:
            st = caminho_abs.stat()
        except OSError:
            return None

        chave_disco = (
            "disco",
            str(caminho_abs.resolve()),
            tamanho,
            st.st_mtime_ns,
            st.st_size,
        )
        if chave_disco in _CACHE_MINIATURAS:
            return _CACHE_MINIATURAS[chave_disco]

        try:
            bytes_disco = caminho_abs.read_bytes()
        except OSError:
            return None

        icone = _criar_icone_miniatura_de_bytes(bytes_disco, tamanho)
        if icone is not None:
            _CACHE_MINIATURAS[chave_disco] = icone
        return icone

    return None


def obter_bytes_imagem_croqui(
    nome_arquivo: str,
    pasta_imagens: Path | None = None,
    model: Any | None = None,
) -> bytes | None:
    """
    Lê sob demanda os bytes completos de uma imagem da galeria do croqui,
    priorizando o buffer em memória RAM (_imagens_em_memoria) e fazendo fallback para o disco.
    """
    caminho_rel = f"imagens/{nome_arquivo}"
    if model is not None and hasattr(model, "obter_imagens_em_memoria"):
        imagens_ram = model.obter_imagens_em_memoria()
        if caminho_rel in imagens_ram:
            return bytes(imagens_ram[caminho_rel])

    if pasta_imagens is not None:
        caminho_abs = Path(pasta_imagens) / nome_arquivo
        if caminho_abs.is_file():
            try:
                return caminho_abs.read_bytes()
            except OSError:
                return None

    return None
