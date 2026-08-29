# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca pura para processamento, sanitização, compressão e leitura de metadados de imagens
usadas em campos de croqui (como thumbnail e fotos de mapas).
"""

import io
import math
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from PIL import Image



def sanitizar_nome_arquivo_imagem(nome_ou_caminho: str) -> str:
    """
    Sanitiza uma string de caminho ou nome de arquivo gerando um slug limpo com extensão .webp.
    Exemplo: 'Caminho/Foto Setor 01!.jpg' -> 'foto_setor_01.webp'
    """
    if not nome_ou_caminho:
        return "imagem.webp"

    nome_base = os.path.basename(str(nome_ou_caminho))
    nome_sem_ext, _ = os.path.splitext(nome_base)

    # Normaliza caracteres acentuados (NFD -> ASCII)
    slug = unicodedata.normalize("NFKD", nome_sem_ext).encode("ASCII", "ignore").decode("utf-8")
    # Substitui caracteres não alfanuméricos por underline
    slug = re.sub(r"[^\w\s-]", "", slug).strip().lower()
    slug = re.sub(r"[-\s_]+", "_", slug).strip("_")

    if not slug:
        slug = "imagem"

    return f"{slug}.webp"


sanitizar_nome_imagem = sanitizar_nome_arquivo_imagem


def verificar_conflito_nome_imagem(
    nome_arquivo: str,
    pasta_imagens: Optional[Path],
    imagens_em_memoria: Optional[Dict[str, bytes]] = None,
) -> bool:
    """
    Verifica se já existe um arquivo com o nome informado em disco ou no buffer em memória.
    """
    if not nome_arquivo:
        return False

    caminho_relativo = f"imagens/{nome_arquivo}" if not nome_arquivo.startswith("imagens/") else nome_arquivo

    if imagens_em_memoria and caminho_relativo in imagens_em_memoria:
        return True

    if pasta_imagens and pasta_imagens.exists():
        nome_puro = os.path.basename(nome_arquivo)
        caminho_disco = pasta_imagens / nome_puro
        if caminho_disco.exists():
            return True

    return False


def sugerir_nome_arquivo_disponivel(
    nome_base: str,
    pasta_imagens: Optional[Path],
    imagens_em_memoria: Optional[Dict[str, bytes]] = None,
) -> str:
    """
    Se o nome informado já existir, gera um sufixo numérico (ex: 'foto_1.webp', 'foto_2.webp')
    até encontrar um nome livre.
    """
    nome_sanitizado = sanitizar_nome_arquivo_imagem(nome_base)
    if not verificar_conflito_nome_imagem(nome_sanitizado, pasta_imagens, imagens_em_memoria):
        return nome_sanitizado

    nome_sem_ext, ext = os.path.splitext(nome_sanitizado)
    contador = 1
    while True:
        candidato = f"{nome_sem_ext}_{contador}{ext}"
        if not verificar_conflito_nome_imagem(candidato, pasta_imagens, imagens_em_memoria):
            return candidato
        contador += 1


def obter_metadados_imagem(imagem_path_ou_bytes: str | Path | bytes | None) -> Tuple[int, int, int, str]:
    """
    Obtém largura, altura, tamanho em bytes e texto formatado do tamanho para a imagem fornecida.
    Retorna (largura, altura, tamanho_bytes, tamanho_formatado_kb).
    """
    if not imagem_path_ou_bytes:
        return 0, 0, 0, "0 KB"

    tamanho_bytes = 0
    img_stream: Any = None

    try:
        if isinstance(imagem_path_ou_bytes, (str, Path)):
            caminho = Path(imagem_path_ou_bytes)
            if not caminho.exists() or not caminho.is_file():
                return 0, 0, 0, "0 KB"
            tamanho_bytes = caminho.stat().st_size
            img_stream = open(caminho, "rb")
        elif isinstance(imagem_path_ou_bytes, bytes):
            tamanho_bytes = len(imagem_path_ou_bytes)
            img_stream = io.BytesIO(imagem_path_ou_bytes)

        if img_stream is None:
            return 0, 0, 0, "0 KB"

        with Image.open(img_stream) as img:
            w, h = img.width, img.height

        if tamanho_bytes < 1024:
            str_tamanho = f"{tamanho_bytes} B"
        elif tamanho_bytes < 1024 * 1024:
            str_tamanho = f"{tamanho_bytes / 1024:.1f} KB"
        else:
            str_tamanho = f"{tamanho_bytes / (1024 * 1024):.2f} MB"

        return w, h, tamanho_bytes, str_tamanho
    except Exception:
        return 0, 0, 0, "0 KB"
    finally:
        if img_stream is not None and hasattr(img_stream, "close"):
            img_stream.close()


def comprimir_imagem_para_bytes_webp(
    fonte_imagem: str | Path | bytes | Image.Image,
    quality: int = 85,
    max_area: int = 4194304,
) -> Tuple[bytes, int, int]:
    """
    Redimensiona (se exceder max_area) e comprime uma imagem para bytes em formato WebP.
    Retorna uma tupla (bytes_webp, largura, altura).
    """
    if isinstance(fonte_imagem, Image.Image):
        img_temp = fonte_imagem
        if img_temp.mode not in ("RGB", "RGBA"):
            img_temp = img_temp.convert("RGBA" if "transparency" in img_temp.info or img_temp.mode == "P" else "RGB")

        area = img_temp.width * img_temp.height
        if area > max_area:
            escala = math.sqrt(max_area / area)
            nova_largura = max(1, int(img_temp.width * escala))
            nova_altura = max(1, int(img_temp.height * escala))
            img_temp = img_temp.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)

        out_buf = io.BytesIO()
        img_temp.save(out_buf, format="WEBP", quality=quality)
        return out_buf.getvalue(), img_temp.width, img_temp.height

    img_source: Any = None
    if isinstance(fonte_imagem, (str, Path)):
        img_source = Path(fonte_imagem).open("rb")
    elif isinstance(fonte_imagem, bytes):
        img_source = io.BytesIO(fonte_imagem)
    else:
        img_source = fonte_imagem


    try:
        with Image.open(img_source) as img:
            img_proc: Image.Image = img
            # Garante RGB ou RGBA dependendo de transparência
            if img_proc.mode not in ("RGB", "RGBA"):
                img_proc = img_proc.convert("RGBA" if "transparency" in img_proc.info or img_proc.mode == "P" else "RGB")

            area = img_proc.width * img_proc.height
            if area > max_area:
                escala = math.sqrt(max_area / area)
                nova_largura = max(1, int(img_proc.width * escala))
                nova_altura = max(1, int(img_proc.height * escala))
                img_proc = img_proc.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)

            out_buf = io.BytesIO()
            img_proc.save(out_buf, format="WEBP", quality=quality)
            return out_buf.getvalue(), img_proc.width, img_proc.height
    finally:
        if img_source is not None and hasattr(img_source, "close"):
            img_source.close()


