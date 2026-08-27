# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import io
from PIL import Image


def gerar_webp_anonimizado(img_bytes: bytes | None) -> bytes:
    """
    Cria uma imagem WebP compacta preservando rigorosamente as dimensões originais (largura x altura),
    com todos os pixels idênticos e homogêneos para atingir compressão máxima (< 150 bytes).
    
    Substitui o conteúdo visual da imagem para envio de telemetria sem expor fotos de usuários.
    """
    if not img_bytes:
        return b""
    try:
        with Image.open(io.BytesIO(img_bytes)) as img:
            largura, altura = img.size
            modo = "RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB"
            cor = (128, 128, 128, 0) if modo == "RGBA" else (128, 128, 128)
            
            dummy = Image.new(modo, (largura, altura), cor)
            buffer = io.BytesIO()
            dummy.save(buffer, format="WEBP", lossless=True, quality=1)
            return buffer.getvalue()
    except Exception:
        return b""
