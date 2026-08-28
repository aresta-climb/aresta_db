# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Tuple, Union
from PIL import Image

from editor.core.processamento_imagem_campo import comprimir_imagem_para_bytes_webp


def sanitizar_nome_imagem(nome_bruto: str) -> str:
    """
    Sanitiza uma string ou nome de arquivo para o padrão snake_case em minúsculas
    sem acentos e com extensão .webp obrigatória.
    """
    if not nome_bruto:
        return "imagem.webp"

    # Remove o caminho se vier com diretório
    nome_base = Path(nome_bruto).stem

    # Normaliza caracteres Unicode e remove acentuação
    nome_normalizado = unicodedata.normalize("NFKD", nome_base)
    nome_sem_acento = "".join(c for c in nome_normalizado if not unicodedata.combining(c))

    # Converte para minúsculas
    nome_lower = nome_sem_acento.lower()

    # Substitui qualquer caractere não alfanumérico por underscore
    nome_limpo = re.sub(r"[^a-z0-9]+", "_", nome_lower)

    # Remove underscores duplicados e das extremidades
    nome_limpo = re.sub(r"_+", "_", nome_limpo).strip("_")

    if not nome_limpo:
        nome_limpo = "imagem"

    return f"{nome_limpo}.webp"


def gerar_nome_imagem_padrao(nome_orig: str, pasta_destino: Path) -> str:
    """
    Gera um nome de arquivo padronizado para a imagem e adiciona um sufixo numérico
    caso já exista um arquivo com o mesmo nome no diretório de destino.
    """
    nome_sanitizado = sanitizar_nome_imagem(nome_orig)
    caminho_pasta = Path(pasta_destino)

    if not (caminho_pasta / nome_sanitizado).exists():
        return nome_sanitizado

    stem = nome_sanitizado[:-5]  # remove '.webp'
    contador = 1
    while (caminho_pasta / f"{stem}_{contador}.webp").exists():
        contador += 1

    return f"{stem}_{contador}.webp"


def gerar_nome_imagem_clipboard(pasta_destino: Path) -> str:
    """
    Gera um nome sugerido com timestamp para imagens coladas da área de transferência,
    garantindo que não haja colisão de arquivo na pasta de destino.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_base = f"imagem_{timestamp}"
    return gerar_nome_imagem_padrao(nome_base, pasta_destino)


def formatar_tag_markdown(nome_arquivo: str, legenda: str = "") -> str:
    """
    Retorna a tag de inserção Markdown formatada no padrão ![legenda](imagens/arquivo.webp).
    """
    texto_legenda = (legenda or "").strip()
    return f"![{texto_legenda}](imagens/{nome_arquivo})"


def salvar_imagem_otimizada(
    fonte_imagem: Union[str, Path, bytes, Image.Image],
    caminho_destino: Path,
    qualidade: int = 85,
    area_maxima: int = 4194304,
) -> Tuple[int, int]:
    """
    Comprime a imagem para o formato WebP otimizado (padrão quality=85 e max_area=4kk)
    e grava diretamente no arquivo de destino. Retorna (largura, altura).
    """
    bytes_webp, largura, altura = comprimir_imagem_para_bytes_webp(
        fonte_imagem,
        quality=qualidade,
        max_area=area_maxima,
    )

    caminho = Path(caminho_destino)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(bytes_webp)

    return largura, altura
