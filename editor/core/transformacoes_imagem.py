# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca pura para transformações em imagens (rotação, corte e máscaras) em bytes WebP.
Esta biblioteca é independente de interface gráfica e trabalha exclusivamente com manipulação
de matrizes de pixels através do Pillow.
"""

import io
from typing import Tuple
from PIL import Image, ImageDraw


def _abrir_imagem_segura(bytes_imagem: bytes) -> Image.Image:
    """Abre e valida bytes de imagem, retornando uma instância segura em modo RGB ou RGBA."""
    if not bytes_imagem or not isinstance(bytes_imagem, (bytes, bytearray, memoryview)):
        raise ValueError("Bytes de imagem inválidos ou vazios.")

    try:
        stream = io.BytesIO(bytes_imagem)
        with Image.open(stream) as img:
            if img.mode not in ("RGB", "RGBA"):
                return img.convert("RGBA" if "transparency" in img.info or img.mode == "P" else "RGB")
            return img.copy()
    except Exception as e:
        raise ValueError(f"Bytes de imagem inválidos: {e}") from e


def _salvar_para_webp(img: Image.Image, qualidade: int = 90, sem_perdas: bool = True) -> bytes:
    """
    Converte uma imagem PIL para bytes no formato WebP.
    Por padrão na RAM (sem_perdas=True), utiliza WebP Lossless com method=0 para velocidade
    instantânea (~20ms) e zero degradação por recompressão sucessiva.
    Para gravação em disco (sem_perdas=False), usa modo lossy com alta qualidade (q=90) e method=6.
    """
    buffer = io.BytesIO()
    if sem_perdas:
        img.save(buffer, format="WEBP", lossless=True, method=0)
    else:
        img.save(buffer, format="WEBP", quality=qualidade, method=6)
    return buffer.getvalue()


def converter_para_webp_disco(bytes_imagem: bytes, qualidade: int = 90) -> bytes:
    """Converte bytes de imagem em RAM para o formato final de disco (WebP lossy de alta fidelidade)."""
    img = _abrir_imagem_segura(bytes_imagem)
    return _salvar_para_webp(img, qualidade=qualidade, sem_perdas=False)


def rotacionar_imagem_bytes(
    bytes_imagem: bytes,
    graus: int,
    qualidade: int = 90,
    sem_perdas: bool = True,
) -> bytes:
    """
    Rotaciona a imagem pelo ângulo especificado em graus (deve ser múltiplo de 90).
    Valores positivos representam rotação horária (+90°), valores negativos anti-horária (-90°).
    Retorna os bytes da imagem resultante em formato WebP.
    """
    if graus % 90 != 0:
        raise ValueError(f"O ângulo deve ser múltiplo de 90 graus. Recebido: {graus}")

    img = _abrir_imagem_segura(bytes_imagem)

    # Normaliza o ângulo para [0, 360)
    angulo_normalizado = graus % 360

    if angulo_normalizado == 90:
        # 90° horário = ROTATE_270 no PIL (que mede anti-horário)
        img_rotacionada = img.transpose(Image.Transpose.ROTATE_270)
    elif angulo_normalizado == 180:
        img_rotacionada = img.transpose(Image.Transpose.ROTATE_180)
    elif angulo_normalizado == 270:
        # 270° horário (-90°) = ROTATE_90 no PIL
        img_rotacionada = img.transpose(Image.Transpose.ROTATE_90)
    else:
        img_rotacionada = img

    return _salvar_para_webp(img_rotacionada, qualidade, sem_perdas=sem_perdas)


def cortar_imagem_bytes(
    bytes_imagem: bytes,
    retangulo: Tuple[int, int, int, int],
    qualidade: int = 90,
    sem_perdas: bool = True,
) -> bytes:
    """
    Recorta a imagem com base nas coordenadas (x1, y1, x2, y2).
    Aplica normalização de coordenadas e clamping nos limites da imagem.
    Retorna os bytes da imagem recortada em formato WebP.
    """
    img = _abrir_imagem_segura(bytes_imagem)

    x1, y1, x2, y2 = retangulo
    min_x = max(0, min(int(x1), int(x2)))
    min_y = max(0, min(int(y1), int(y2)))
    max_x = min(img.width, max(int(x1), int(x2)))
    max_y = min(img.height, max(int(y1), int(y2)))

    largura = max_x - min_x
    altura = max_y - min_y

    if largura <= 0 or altura <= 0:
        raise ValueError(f"Área de corte inválida: largura={largura}, altura={altura}")

    img_cortada = img.crop((min_x, min_y, max_x, max_y))
    return _salvar_para_webp(img_cortada, qualidade, sem_perdas=sem_perdas)


def aplicar_mascara_bytes(
    bytes_imagem: bytes,
    retangulo: Tuple[int, int, int, int],
    cor_rgb: Tuple[int, int, int],
    qualidade: int = 90,
    sem_perdas: bool = True,
) -> bytes:
    """
    Pinta um retângulo sólido com a cor RGB informada sobre a imagem.
    Retorna os bytes da imagem modificada em formato WebP.
    """
    img = _abrir_imagem_segura(bytes_imagem)

    x1, y1, x2, y2 = retangulo
    min_x = max(0, min(int(x1), int(x2)))
    min_y = max(0, min(int(y1), int(y2)))
    max_x = min(img.width, max(int(x1), int(x2)))
    max_y = min(img.height, max(int(y1), int(y2)))

    if max_x <= min_x or max_y <= min_y:
        # Região nula não altera a imagem
        return _salvar_para_webp(img, qualidade, sem_perdas=sem_perdas)

    cor_pura = (int(cor_rgb[0]), int(cor_rgb[1]), int(cor_rgb[2]))
    desenhador = ImageDraw.Draw(img)
    desenhador.rectangle([min_x, min_y, max_x, max_y], fill=cor_pura, outline=cor_pura)

    return _salvar_para_webp(img, qualidade, sem_perdas=sem_perdas)



def obter_cor_pixel(bytes_imagem: bytes, x: int, y: int) -> Tuple[int, int, int]:
    """
    Retorna a cor (R, G, B) do pixel localizado na coordenada (x, y) da imagem.
    Lança ValueError se a coordenada estiver fora dos limites.
    """
    img = _abrir_imagem_segura(bytes_imagem)

    px, py = int(x), int(y)
    if not (0 <= px < img.width and 0 <= py < img.height):
        raise ValueError(
            f"Coordenada ({px}, {py}) está fora dos limites da imagem ({img.width}x{img.height})."
        )

    valor = img.getpixel((px, py))
    if isinstance(valor, int):
        return (valor, valor, valor)
    if isinstance(valor, tuple) and len(valor) >= 3:
        return (int(valor[0]), int(valor[1]), int(valor[2]))

    raise ValueError(f"Formato de pixel inesperado: {valor}")
