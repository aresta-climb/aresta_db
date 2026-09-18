# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Biblioteca de geração de QR Codes e placas físicas de sinalização para o Aresta Climb.

Permite gerar QR Codes com o logo oficial centralizado e renderizar placas em PNG
de alta resolução e SVG vetorial para impressão, adesivos e corte a laser.
"""

import base64
from io import BytesIO
from pathlib import Path
import re
import sys
from typing import Any, cast
import unicodedata

_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)  # pragma: no cover

from PIL import Image, ImageChops, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont, ImageFont as PILImageFont
import qrcode
import qrcode.constants
import yaml

from aresta_api.proto.generated import croqui_pb2

LARGURA_PADRAO_A4_600DPI = 4960
ALTURA_PADRAO_A4_600DPI = 7016
DPI_PADRAO = 600
DIRETORIO_RAIZ_PADRAO: Path = Path(__file__).resolve().parent.parent


def slugify(texto: str) -> str:
    """Normaliza um texto para slug determinístico em minúsculas sem diacríticos."""
    if not texto or not texto.strip():
        return ""

    # Normaliza em decomposição canônica (NFD) e remove acentos
    texto_normalizado = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(
        c for c in texto_normalizado if unicodedata.category(c) != "Mn"
    )

    # Substitui caracteres especiais por underline e converte para minúsculas
    limpo = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acentos.lower())
    return limpo.strip("_")


def montar_url_deep_link(
    pico: str,
    grupo: str | None = None,
    setor: str | None = None,
    via: str | None = None,
    host: str = "app.arestaclimb.com",
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
) -> str:
    """Monta a URL hierárquica canônica de deep link para o Aresta Climb com suporte a parâmetros UTM."""
    if not pico or not pico.strip():
        raise ValueError("O identificador do pico é obrigatório.")

    partes = [slugify(pico)]

    if grupo and grupo.strip():
        partes.append(slugify(grupo))
        if setor and setor.strip():
            partes.append(slugify(setor))
    elif setor and setor.strip():
        partes.append(slugify(setor))

    if via and via.strip():
        partes.append(slugify(via))

    url_base = f"https://{host}/{'/'.join(partes)}"

    parametros: list[str] = []
    if utm_source and utm_source.strip():
        parametros.append(f"utm_source={utm_source.strip()}")
    if utm_medium and utm_medium.strip():
        parametros.append(f"utm_medium={utm_medium.strip()}")
    if utm_campaign and utm_campaign.strip():
        parametros.append(f"utm_campaign={utm_campaign.strip()}")

    if parametros:
        return f"{url_base}?{'&'.join(parametros)}"
    return url_base


def resolver_cor_borda_logo(
    cor: str | tuple[int, ...],
) -> tuple[tuple[int, int, int, int], str]:
    """Retorna a cor da borda do logo em formato RGBA (para Pillow) e hex (para SVG)."""
    if isinstance(cor, tuple):
        r, g, b = cor[:3]
        a = cor[3] if len(cor) > 3 else 255
        hex_cor = f"#{r:02x}{g:02x}{b:02x}"
        return (r, g, b, a), hex_cor

    cor_normalizada = str(cor).strip().lower()
    if cor_normalizada in ("laranja", "orange", "marca"):
        return (234, 83, 65, 255), "#ea5341"
    if cor_normalizada in ("cinza", "gray", "grey"):
        return (203, 213, 225, 255), "#cbd5e1"
    if cor_normalizada.startswith("#") and len(cor_normalizada) in (4, 7):
        hex_limpo = cor_normalizada.lstrip("#")
        if len(hex_limpo) == 3:
            hex_limpo = "".join(c * 2 for c in hex_limpo)
        r = int(hex_limpo[0:2], 16)
        g = int(hex_limpo[2:4], 16)
        b = int(hex_limpo[4:6], 16)
        return (r, g, b, 255), f"#{hex_limpo}"

    # Padrão escolhido: preto para contraste máximo com os módulos do QR Code
    return (17, 24, 39, 255), "#111827"


def gerar_qrcode_com_logo(
    url: str,
    caminho_logo: Path | str | None = None,
    tamanho_px: int = 500,
    cor_borda: str = "preta",
    border: int = 2,
) -> Image.Image:
    """Gera o QR Code com correção de erro nível H e insere o logo oficial centralizado."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img_raw = qr.make_image(fill_color="black", back_color="white")
    if hasattr(img_raw, "get_image"):
        imagem_qr: Image.Image = cast(Any, img_raw).get_image().convert("RGBA")
    else:
        buffer = BytesIO()
        img_raw.save(buffer, "PNG")
        buffer.seek(0)
        imagem_qr = Image.open(buffer).convert("RGBA")

    # Determina o logo a ser utilizado
    logo_path: Path | None = None
    if caminho_logo is not None:
        logo_path = Path(caminho_logo)
    else:
        raiz = Path(__file__).resolve().parent.parent
        padrao = raiz / "editor" / "recursos" / "logo_app.png"
        if padrao.exists():
            logo_path = padrao

    if logo_path is not None and logo_path.exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            largura_total = int(imagem_qr.size[0] * 0.22)
            fundo = Image.new("RGBA", (largura_total, largura_total), (0, 0, 0, 0))
            desenho_fundo = ImageDraw.Draw(fundo)
            raio_fundo = int(largura_total * 0.24)
            espessura_linha = max(3, int(largura_total * 0.035))
            cor_rgba, _ = resolver_cor_borda_logo(cor_borda)

            # Caixa branca com cantos arredondados e linha delimitadora
            desenho_fundo.rounded_rectangle(
                [(0, 0), (largura_total - 1, largura_total - 1)],
                radius=raio_fundo,
                fill=(255, 255, 255, 255),
                outline=cor_rgba,
                width=espessura_linha,
            )

            padding = max(4, int(largura_total * 0.08))
            tam_inner = largura_total - (2 * padding)
            logo_inner = logo.resize((tam_inner, tam_inner), Image.Resampling.LANCZOS)

            # Máscara arredondada para o ícone laranja interno do Aresta
            mascara_inner = Image.new("L", (tam_inner, tam_inner), 0)
            desenho_mask = ImageDraw.Draw(mascara_inner)
            desenho_mask.rounded_rectangle(
                [(0, 0), (tam_inner, tam_inner)],
                radius=int(tam_inner * 0.22),
                fill=255,
            )

            fundo.paste(logo_inner, (padding, padding), mascara_inner)

            pos_x = (imagem_qr.size[0] - largura_total) // 2
            pos_y = (imagem_qr.size[1] - largura_total) // 2
            imagem_qr.paste(fundo, (pos_x, pos_y), fundo)
        except Exception:
            pass

    if imagem_qr.size != (tamanho_px, tamanho_px):
        imagem_qr = imagem_qr.resize(
            (tamanho_px, tamanho_px), Image.Resampling.LANCZOS
        )

    return imagem_qr


def recortar_bordas_vazias(img: Image.Image) -> Image.Image:
    """Recorta bordas vazias (transparentes ou brancas) para alinhamento e proporções precisas."""
    if "A" in img.mode:
        extrema = img.getchannel("A").getextrema()
        if isinstance(extrema, tuple) and isinstance(extrema[0], (int, float)):
            if extrema[0] < 255:
                bbox_alpha = img.getbbox()
                return img.crop(bbox_alpha) if bbox_alpha else img

    img_rgb = img.convert("RGB")
    bg = Image.new("RGB", img_rgb.size, (255, 255, 255))
    diff = ImageChops.difference(img_rgb, bg)
    bbox_diff = diff.getbbox()
    if bbox_diff:
        return img.crop(bbox_diff)
    return img


def carregar_imagem_topo(
    caminho: Path | str | None, dpi: int = 300
) -> Image.Image | None:
    """Carrega uma imagem ou vetor PDF para o cabeçalho/topo da placa."""
    if caminho is None:
        return None
    path = Path(caminho)
    if not path.exists():
        return None

    if path.suffix.lower() == ".pdf":
        try:
            import pymupdf

            doc = cast(Any, pymupdf).open(str(path))
            page = doc[0]
            pix = page.get_pixmap(dpi=dpi, alpha=True)
            img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
            return recortar_bordas_vazias(img)
        except Exception:
            return None

    try:
        img = Image.open(path).convert("RGBA")
        return recortar_bordas_vazias(img)
    except Exception:
        return None


def obter_logo_aresta_padrao(raiz_projeto: Path | None = None) -> Path | None:
    """Retorna o caminho do logo oficial do Aresta Climb para o cabeçalho."""
    if raiz_projeto is None:
        raiz_projeto = DIRETORIO_RAIZ_PADRAO
    candidatos = [
        raiz_projeto / "editor" / "recursos" / "logo_splash.png",
        raiz_projeto.parent / "aresta_app" / "frontend" / "assets" / "logo_splash.png",
        raiz_projeto / "editor" / "recursos" / "logo_aresta_frontal.png",
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


def obter_logo_topo_padrao(
    pico_id: str | None = None, raiz_projeto: Path | None = None
) -> Path | None:
    """Verifica se existe um logo de cabeçalho padrão para o pico informado."""
    if not pico_id:
        return None
    if raiz_projeto is None:
        raiz_projeto = DIRETORIO_RAIZ_PADRAO
    if "igarape" in pico_id or "pedra_grande" in pico_id:
        candidatos = [
            raiz_projeto.parent / "aresta_data" / "logo_igarameca.pdf",
            raiz_projeto / "editor" / "recursos" / "logo_igarameca.pdf",
        ]
        for c in candidatos:
            if c.exists():
                return c
    return None



def _obter_fonte(tamanho: int, negrito: bool = False) -> FreeTypeFont | PILImageFont:
    """Tenta carregar fonte do sistema com tamanho especificado ou recorre à padrão."""
    nomes_fontes = [
        "arialbd.ttf" if negrito else "arial.ttf",
        "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf",
        "SegoeUI-Bold.ttf" if negrito else "SegoeUI.ttf",
    ]
    for nome in nomes_fontes:
        try:
            return ImageFont.truetype(nome, tamanho)
        except OSError:
            continue
    return ImageFont.load_default()


def _desenhar_titulo_com_escala(
    desenho: ImageDraw.ImageDraw,
    texto: str,
    centro_x: int,
    centro_y: int,
    largura_maxima: int,
    tamanho_inicial: int = 340,
    cor: tuple[int, int, int] = (17, 24, 39),
    stroke_width: int = 0,
) -> None:
    """Desenha o título ajustando o tamanho da fonte para caber na largura máxima."""
    tamanho = tamanho_inicial
    fonte = _obter_fonte(tamanho, negrito=True)
    bbox = desenho.textbbox((0, 0), texto, font=fonte, stroke_width=stroke_width)
    largura_texto = bbox[2] - bbox[0]
    limite_minimo = max(24, int(tamanho_inicial * 0.35))
    while largura_texto > largura_maxima and tamanho > limite_minimo:
        tamanho -= 10
        fonte = _obter_fonte(tamanho, negrito=True)
        bbox = desenho.textbbox((0, 0), texto, font=fonte, stroke_width=stroke_width)
        largura_texto = bbox[2] - bbox[0]

    desenho.text(
        (centro_x, centro_y),
        texto,
        fill=cor,
        font=fonte,
        anchor="mm",
        stroke_width=stroke_width,
        stroke_fill=cor if stroke_width > 0 else None,
    )


SVG_ICONE_FOLHA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 3C12 3 7 7.5 6 13c-.7 3.5 1 6 2 7" />
    <path d="M19 3c0 7-4.5 12-11 17" />
    <line x1="4" y1="22" x2="12" y2="14" />
  </g>
</svg>"""

SVG_ICONE_ROCHA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 19h16a2 2 0 0 0 1.8-2.9L13.8 4.6a2 2 0 0 0-3.6 0L2.2 16.1A2 2 0 0 0 4 19z" />
    <path d="M12 5.5l-1 5.5v4" />
  </g>
</svg>"""

SVG_ICONE_LIXEIRA = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 6h16" />
    <path d="M9.5 6V4a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2" />
    <path d="M5.5 6l1.2 13a2 2 0 0 0 2 2h6.6a2 2 0 0 0 2-2L18.5 6" />
    <line x1="9" y1="10" x2="9" y2="16" />
    <line x1="12" y1="10" x2="12" y2="16" />
    <line x1="15" y1="10" x2="15" y2="16" />
  </g>
</svg>"""

SVG_ICONE_PESSOAS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="7.5" cy="7.5" r="3.2" />
    <circle cx="16.5" cy="7.5" r="3.2" />
    <path d="M3 20.5h18" />
    <path d="M3 20.5v-1a4.5 4.5 0 0 1 4.5-4.5h0a4.5 4.5 0 0 1 4.5 3.5" />
    <path d="M12 18.5a4.5 4.5 0 0 1 4.5-3.5h0a4.5 4.5 0 0 1 4.5 4.5v1" />
    <line x1="12" y1="18.5" x2="12" y2="20.5" />
  </g>
</svg>"""


def _renderizar_icone_svg(svg_str: str, largura: int, altura: int) -> Image.Image:
    """Renderiza um ícone SVG em uma imagem RGBA PIL usando PyMuPDF com fallback vetorial."""
    try:
        import pymupdf

        fitz = cast(Any, pymupdf)
        doc = fitz.open(stream=svg_str.encode("utf-8"), filetype="svg")
        page = doc[0]
        mat = fitz.Matrix(largura / page.rect.width, altura / page.rect.height)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        return Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
    except Exception:
        fallback = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
        d = ImageDraw.Draw(fallback)
        d.ellipse(
            [(2, 2), (largura - 2, altura - 2)],
            outline=(17, 24, 39, 255),
            width=max(2, int(largura * 0.08)),
        )
        return fallback


COR_VERMELHO = (194, 35, 35)
HEX_VERMELHO = "#c22323"
COR_TERRACOTA = COR_VERMELHO
HEX_TERRACOTA = HEX_VERMELHO
COR_TEXTO_ESCURO = (17, 24, 39)
HEX_TEXTO_ESCURO = "#111827"
COR_CINZA_LINHA = (190, 190, 191)
HEX_CINZA_LINHA = "#bebebf"
COR_BRACKETS = (0, 0, 0)


def gerar_placa_png(
    url: str,
    titulo: str,
    subtitulo: str = "",
    caminho_logo: Path | str | None = None,
    caminho_logo_topo: Path | str | None = None,
    caminho_logo_aresta: Path | str | None = None,
    largura: int = LARGURA_PADRAO_A4_600DPI,
    altura: int = ALTURA_PADRAO_A4_600DPI,
    cor_borda_logo: str = "preta",
) -> Image.Image:
    """Desenha a placa física completa no modelo oficial A4 de alta resolução (600 DPI)."""
    placa = Image.new("RGB", (largura, altura), color=(255, 255, 255))
    desenho = ImageDraw.Draw(placa)

    fator = largura / 4960.0

    borda_offset = int(140 * fator)
    raio_borda = int(100 * fator)
    espessura_borda = int(32 * fator)

    # 1. Borda externa decorativa com cantos arredondados na cor terracota
    desenho.rounded_rectangle(
        [(borda_offset, borda_offset), (largura - borda_offset, altura - borda_offset)],
        radius=raio_borda,
        outline=COR_TERRACOTA,
        width=espessura_borda,
    )

    # 2. Resolução dos caminhos de logo do cabeçalho
    caminho_aresta_resolvido = (
        obter_logo_aresta_padrao()
        if caminho_logo_aresta is None
        else (Path(caminho_logo_aresta) if caminho_logo_aresta else None)
    )

    img_parceiro = carregar_imagem_topo(caminho_logo_topo, dpi=int(300 * fator))
    img_aresta = carregar_imagem_topo(caminho_aresta_resolvido, dpi=int(300 * fator))

    topo_y = int(460 * fator)
    altura_topo = int(580 * fator)
    y_centro = topo_y + altura_topo // 2

    if img_parceiro is not None and img_aresta is not None:
        # Modo Duplo: Logo oficial do Aresta Climb à esquerda e logo do parceiro/pico à direita
        margem_x = int(480 * fator)

        # Redimensionamento Parceiro / Igarameca (direita)
        max_w_dir = int(1950 * fator)
        h_dir_alvo = altura_topo
        prop_dir = min(max_w_dir / img_parceiro.width, h_dir_alvo / img_parceiro.height)
        w_dir = int(img_parceiro.width * prop_dir)
        h_dir = int(img_parceiro.height * prop_dir)
        img_dir_redim = img_parceiro.resize((w_dir, h_dir), Image.Resampling.LANCZOS)
        x_dir = largura - margem_x - w_dir
        y_dir = y_centro - h_dir // 2
        placa.paste(img_dir_redim, (x_dir, y_dir), img_dir_redim)

        # Redimensionamento Aresta Climb (esquerda)
        max_w_esq = int(1700 * fator)
        h_esq_alvo = int(altura_topo * 1.35)
        prop_esq = min(max_w_esq / img_aresta.width, h_esq_alvo / img_aresta.height)
        w_esq = int(img_aresta.width * prop_esq)
        h_esq = int(img_aresta.height * prop_esq)
        img_esq_redim = img_aresta.resize((w_esq, h_esq), Image.Resampling.LANCZOS)
        x_esq = margem_x
        # Alinhamento da linha de base do texto ARESTA com o texto do parceiro
        # No logo_splash.png, a base da palavra ARESTA fica em ~77.2% da altura total
        # No logo do parceiro (ex: Igarameca), a base do texto fica em ~98% da altura total
        y_base_dir = y_dir + int(h_dir * 0.98)
        y_esq = y_base_dir - int(h_esq * 0.772)
        placa.paste(img_esq_redim, (x_esq, y_esq), img_esq_redim)

        y_titulo = topo_y + altura_topo + int(420 * fator)

    elif img_parceiro is not None or img_aresta is not None:
        # Modo Único: Centraliza a única logo disponível
        img_unica = img_aresta if img_aresta is not None else img_parceiro
        assert img_unica is not None
        max_w = int(largura * 0.72)
        max_h = int(1150 * fator)
        proporcao = min(max_w / img_unica.width, max_h / img_unica.height)
        w_novo = int(img_unica.width * proporcao)
        h_novo = int(img_unica.height * proporcao)
        img_redim = img_unica.resize((w_novo, h_novo), Image.Resampling.LANCZOS)
        x_topo = (largura - w_novo) // 2
        y_topo = int(450 * fator)
        placa.paste(img_redim, (x_topo, y_topo), img_redim)
        y_titulo = y_topo + h_novo + int(420 * fator)

    else:
        # Marca institucional textual ARESTA CLIMB quando não houver imagem
        fonte_marca = _obter_fonte(max(14, int(150 * fator)), negrito=True)
        desenho.text(
            (largura // 2, int(500 * fator)),
            "ARESTA CLIMB",
            fill=(217, 119, 6),
            font=fonte_marca,
            anchor="mm",
        )
        y_titulo = int(1200 * fator)

    # 3. Título (Categoria com linhas vermelhas em cima, Nome em vermelho em baixo)
    prefixos_conhecidos = ("SETOR ", "BLOCO ", "GRUPO ", "PICO ", "VIA ")
    titulo_upper = titulo.strip().upper()
    tem_prefixo = any(titulo_upper.startswith(p) for p in prefixos_conhecidos)

    if tem_prefixo:
        cat_texto, nome_texto = titulo_upper.split(" ", 1)
    else:
        cat_texto = "SETOR"
        nome_texto = titulo_upper

    y_cat = y_titulo
    stroke_cat = int(8 * fator)
    fonte_cat = _obter_fonte(max(16, int(250 * fator)), negrito=True)
    cat_bbox = desenho.textbbox((0, 0), cat_texto, font=fonte_cat, stroke_width=stroke_cat)
    w_cat = cat_bbox[2] - cat_bbox[0]

    largura_linha_cat = int(950 * fator)
    gap_linha = int(80 * fator)
    espessura_linha_cat = int(18 * fator)

    x_linha_esq_fim = (largura - w_cat) // 2 - gap_linha
    x_linha_esq_ini = x_linha_esq_fim - largura_linha_cat
    x_linha_dir_ini = (largura + w_cat) // 2 + gap_linha
    x_linha_dir_fim = x_linha_dir_ini + largura_linha_cat

    desenho.line([(x_linha_esq_ini, y_cat), (x_linha_esq_fim, y_cat)], fill=COR_VERMELHO, width=espessura_linha_cat)
    desenho.text(
        (largura // 2, y_cat),
        cat_texto,
        fill=COR_TEXTO_ESCURO,
        font=fonte_cat,
        anchor="mm",
        stroke_width=stroke_cat,
        stroke_fill=COR_TEXTO_ESCURO,
    )
    desenho.line([(x_linha_dir_ini, y_cat), (x_linha_dir_fim, y_cat)], fill=COR_VERMELHO, width=espessura_linha_cat)

    y_nome = y_cat + int(360 * fator)
    stroke_nome = int(10 * fator)
    _desenhar_titulo_com_escala(
        desenho=desenho,
        texto=nome_texto,
        centro_x=largura // 2,
        centro_y=y_nome,
        largura_maxima=int(largura - 600 * fator),
        tamanho_inicial=max(36, int(350 * fator)),
        cor=COR_VERMELHO,
        stroke_width=stroke_nome,
    )

    # 4. Instrução superior (antes do QR Code)
    y_inst = y_nome + int(290 * fator)
    fonte_inst = _obter_fonte(max(14, int(120 * fator)), negrito=False)
    desenho.text(
        (largura // 2, y_inst),
        "Aponte a câmera para abrir no Aresta",
        fill=COR_TEXTO_ESCURO,
        font=fonte_inst,
        anchor="mm",
    )

    # 5. QR Code + Moldura Retangular Preta Arredondada
    tam_moldura = int(2600 * fator)
    tamanho_qr = int(2520 * fator)
    x_moldura = (largura - tam_moldura) // 2
    y_moldura = y_inst + int(260 * fator)
    raio_moldura = int(50 * fator)
    espessura_moldura = int(22 * fator)

    qr_img = gerar_qrcode_com_logo(
        url=url,
        caminho_logo=caminho_logo,
        tamanho_px=tamanho_qr,
        cor_borda=cor_borda_logo,
        border=2,
    )
    x_qr = (largura - tamanho_qr) // 2
    y_qr = y_moldura + (tam_moldura - tamanho_qr) // 2
    placa.paste(qr_img.convert("RGB"), (x_qr, y_qr))

    desenho.rounded_rectangle(
        [(x_moldura, y_moldura), (x_moldura + tam_moldura, y_moldura + tam_moldura)],
        radius=raio_moldura,
        outline=(0, 0, 0),
        width=espessura_moldura,
    )

    # 6. Seção de Diretrizes: ── MÍNIMO IMPACTO NO LOCAL ──
    y_sec = y_moldura + tam_moldura + int(360 * fator)
    fonte_sec = _obter_fonte(max(16, int(155 * fator)), negrito=True)
    sec_texto = "MÍNIMO IMPACTO NO LOCAL"
    sec_bbox = desenho.textbbox((0, 0), sec_texto, font=fonte_sec)
    w_sec = sec_bbox[2] - sec_bbox[0]

    gap_sec = int(60 * fator)
    esp_linha_sec = int(8 * fator)
    margem_linha_sec = int(350 * fator)
    x_lsec_esq_ini = margem_linha_sec
    x_lsec_esq_fim = (largura - w_sec) // 2 - gap_sec
    x_lsec_dir_ini = (largura + w_sec) // 2 + gap_sec
    x_lsec_dir_fim = largura - margem_linha_sec

    desenho.line([(x_lsec_esq_ini, y_sec), (x_lsec_esq_fim, y_sec)], fill=COR_CINZA_LINHA, width=esp_linha_sec)
    desenho.text((largura // 2, y_sec), sec_texto, fill=COR_TEXTO_ESCURO, font=fonte_sec, anchor="mm")
    desenho.line([(x_lsec_dir_ini, y_sec), (x_lsec_dir_fim, y_sec)], fill=COR_CINZA_LINHA, width=esp_linha_sec)

    # 7. Quatro Regras com Ícones Vetoriais
    tam_icon = int(155 * fator)
    icon_leaf = _renderizar_icone_svg(SVG_ICONE_FOLHA, tam_icon, tam_icon)
    icon_rock = _renderizar_icone_svg(SVG_ICONE_ROCHA, tam_icon, tam_icon)
    icon_trash = _renderizar_icone_svg(SVG_ICONE_LIXEIRA, tam_icon, tam_icon)
    icon_users = _renderizar_icone_svg(SVG_ICONE_PESSOAS, tam_icon, tam_icon)

    fonte_regra = _obter_fonte(max(14, int(130 * fator)), negrito=True)
    esp_regras = int(210 * fator)
    y_base_regras = y_sec + int(270 * fator)

    regras_textos = [
        "Deixe a menor marca possível na natureza",
        "Preserve a rocha: não quebre nem altere agarras",
        "Leve todo o seu lixo de volta com você",
        "Preserve o entorno: faça suas necessidades",
        "nos sanitários disponibilizados pelo evento",
    ]
    max_w_regra = max(
        desenho.textbbox((0, 0), r, font=fonte_regra)[2]
        - desenho.textbbox((0, 0), r, font=fonte_regra)[0]
        for r in regras_textos
    )
    largura_bloco_regras = tam_icon + int(80 * fator) + int(max_w_regra)
    x_bloco = int((largura - largura_bloco_regras) // 2)
    x_texto_regra = int(x_bloco + tam_icon + 80 * fator)

    # Regra 1: Folha
    y1 = y_base_regras
    placa.paste(icon_leaf, (x_bloco, y1 - tam_icon // 2), icon_leaf)
    desenho.text((x_texto_regra, y1), "Deixe a menor marca possível na natureza", fill=COR_TEXTO_ESCURO, font=fonte_regra, anchor="lm")

    # Regra 2: Rocha
    y2 = y1 + esp_regras
    placa.paste(icon_rock, (x_bloco, y2 - tam_icon // 2), icon_rock)
    desenho.text((x_texto_regra, y2), "Preserve a rocha: não quebre nem altere agarras", fill=COR_TEXTO_ESCURO, font=fonte_regra, anchor="lm")

    # Regra 3: Lixo
    y3 = y2 + esp_regras
    placa.paste(icon_trash, (x_bloco, y3 - tam_icon // 2), icon_trash)
    desenho.text((x_texto_regra, y3), "Leve todo o seu lixo de volta com você", fill=COR_TEXTO_ESCURO, font=fonte_regra, anchor="lm")

    # Regra 4: Entorno (duas linhas)
    y4 = y3 + esp_regras
    altura_linha_regra4 = int(140 * fator)
    placa.paste(icon_users, (x_bloco, y4 + altura_linha_regra4 // 2 - tam_icon // 2), icon_users)
    desenho.text((x_texto_regra, y4), "Preserve o entorno: faça suas necessidades", fill=COR_TEXTO_ESCURO, font=fonte_regra, anchor="lm")
    desenho.text((x_texto_regra, y4 + altura_linha_regra4), "nos sanitários disponibilizados pelo evento", fill=COR_TEXTO_ESCURO, font=fonte_regra, anchor="lm")

    return placa


def gerar_placa_svg(
    url: str,
    titulo: str,
    subtitulo: str = "",
    caminho_logo: Path | str | None = None,
    caminho_logo_topo: Path | str | None = None,
    caminho_logo_aresta: Path | str | None = None,
    largura: int = LARGURA_PADRAO_A4_600DPI,
    altura: int = ALTURA_PADRAO_A4_600DPI,
    cor_borda_logo: str = "preta",
) -> str:
    """Gera a placa completa em formato vetorial SVG puro no modelo oficial com regras e logo."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    fator = largura / 4960.0

    matriz = qr.get_matrix()
    qtd_modulos = len(matriz)
    tamanho_qr = int(2520 * fator)
    tamanho_modulo = tamanho_qr / qtd_modulos

    caminhos_modulos: list[str] = []
    for y, linha in enumerate(matriz):
        for x, ativo in enumerate(linha):
            if ativo:
                px = x * tamanho_modulo
                py = y * tamanho_modulo
                caminhos_modulos.append(
                    f'<rect x="{px:.2f}" y="{py:.2f}" width="{tamanho_modulo:.2f}" height="{tamanho_modulo:.2f}" fill="#000000" />'
                )

    svg_modulos = "\n      ".join(caminhos_modulos)

    logo_path: Path | None = None
    if caminho_logo is not None:
        logo_path = Path(caminho_logo)
    else:
        raiz = Path(__file__).resolve().parent.parent
        padrao = raiz / "editor" / "recursos" / "logo_app.png"
        if padrao.exists():
            logo_path = padrao

    _, hex_borda = resolver_cor_borda_logo(cor_borda_logo)

    svg_logo = ""
    if logo_path is not None and logo_path.exists():
        try:
            with open(logo_path, "rb") as f:
                b64_logo = base64.b64encode(f.read()).decode("ascii")
            largura_total = int(tamanho_qr * 0.22)
            pos_fundo = (tamanho_qr - largura_total) / 2
            raio_fundo = int(largura_total * 0.24)
            espessura_linha = max(3, int(largura_total * 0.035))
            padding = max(4, int(largura_total * 0.08))
            tam_inner = largura_total - (2 * padding)
            pos_inner = pos_fundo + padding
            raio_inner = int(tam_inner * 0.22)
            svg_logo = f"""
      <rect x="{pos_fundo:.2f}" y="{pos_fundo:.2f}" width="{largura_total}" height="{largura_total}" rx="{raio_fundo}" ry="{raio_fundo}" fill="#ffffff" stroke="{hex_borda}" stroke-width="{espessura_linha}" />
      <clipPath id="logo-inner-clip">
        <rect x="{pos_inner:.2f}" y="{pos_inner:.2f}" width="{tam_inner}" height="{tam_inner}" rx="{raio_inner}" ry="{raio_inner}" />
      </clipPath>
      <image href="data:image/png;base64,{b64_logo}" x="{pos_inner:.2f}" y="{pos_inner:.2f}" width="{tam_inner}" height="{tam_inner}" clip-path="url(#logo-inner-clip)" />
"""
        except Exception:
            pass

    def escapar(t: str) -> str:
        return (
            t.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    caminho_aresta_resolvido = (
        obter_logo_aresta_padrao()
        if caminho_logo_aresta is None
        else (Path(caminho_logo_aresta) if caminho_logo_aresta else None)
    )

    img_parceiro = carregar_imagem_topo(caminho_logo_topo, dpi=int(300 * fator))
    img_aresta = carregar_imagem_topo(caminho_aresta_resolvido, dpi=int(300 * fator))

    topo_y = int(460 * fator)
    altura_topo = int(580 * fator)
    y_centro = topo_y + altura_topo // 2

    if img_parceiro is not None and img_aresta is not None:
        margem_x = int(480 * fator)

        max_w_dir = int(1950 * fator)
        h_dir_alvo = altura_topo
        prop_dir = min(max_w_dir / img_parceiro.width, h_dir_alvo / img_parceiro.height)
        w_dir = int(img_parceiro.width * prop_dir)
        h_dir = int(img_parceiro.height * prop_dir)
        img_dir_redim = img_parceiro.resize((w_dir, h_dir), Image.Resampling.LANCZOS)
        buf_dir = BytesIO()
        img_dir_redim.save(buf_dir, "PNG")
        b64_dir = base64.b64encode(buf_dir.getvalue()).decode("ascii")
        x_dir = largura - margem_x - w_dir
        y_dir = y_centro - h_dir // 2

        max_w_esq = int(1700 * fator)
        h_esq_alvo = int(altura_topo * 1.35)
        prop_esq = min(max_w_esq / img_aresta.width, h_esq_alvo / img_aresta.height)
        w_esq = int(img_aresta.width * prop_esq)
        h_esq = int(img_aresta.height * prop_esq)
        img_esq_redim = img_aresta.resize((w_esq, h_esq), Image.Resampling.LANCZOS)
        buf_esq = BytesIO()
        img_esq_redim.save(buf_esq, "PNG")
        b64_esq = base64.b64encode(buf_esq.getvalue()).decode("ascii")
        x_esq = margem_x
        # Alinhamento da linha de base do texto ARESTA com o texto do parceiro
        y_base_dir = y_dir + int(h_dir * 0.98)
        y_esq = y_base_dir - int(h_esq * 0.772)

        svg_cabecalho = f"""<image href="data:image/png;base64,{b64_esq}" x="{x_esq:.2f}" y="{y_esq:.2f}" width="{w_esq}" height="{h_esq}" />
  <image href="data:image/png;base64,{b64_dir}" x="{x_dir:.2f}" y="{y_dir:.2f}" width="{w_dir}" height="{h_dir}" />"""
        y_titulo = topo_y + altura_topo + int(420 * fator)

    elif img_parceiro is not None or img_aresta is not None:
        img_unica = img_aresta if img_aresta is not None else img_parceiro
        assert img_unica is not None
        max_w = int(largura * 0.72)
        max_h = int(1150 * fator)
        proporcao = min(max_w / img_unica.width, max_h / img_unica.height)
        w_novo = int(img_unica.width * proporcao)
        h_novo = int(img_unica.height * proporcao)
        buf = BytesIO()
        img_redim = img_unica.resize((w_novo, h_novo), Image.Resampling.LANCZOS)
        img_redim.save(buf, "PNG")
        b64_topo = base64.b64encode(buf.getvalue()).decode("ascii")
        x_topo = (largura - w_novo) / 2
        y_topo = int(450 * fator)
        svg_cabecalho = f'<image href="data:image/png;base64,{b64_topo}" x="{x_topo:.2f}" y="{y_topo:.2f}" width="{w_novo}" height="{h_novo}" />'
        y_titulo = y_topo + h_novo + int(420 * fator)

    else:
        sub_svg = (
            f'<text class="subtitulo" x="{largura / 2}" y="{int(750 * fator)}">{escapar(subtitulo)}</text>'
            if subtitulo
            else ""
        )
        svg_cabecalho = f"""<text class="marca" x="{largura / 2}" y="{int(500 * fator)}">ARESTA CLIMB</text>
  {sub_svg}"""
        y_titulo = int(1200 * fator)

    prefixos_conhecidos = ("SETOR ", "BLOCO ", "GRUPO ", "PICO ", "VIA ")
    titulo_upper = titulo.strip().upper()
    tem_prefixo = any(titulo_upper.startswith(p) for p in prefixos_conhecidos)
    if tem_prefixo:
        cat_texto, nome_texto = titulo_upper.split(" ", 1)
    else:
        cat_texto = "SETOR"
        nome_texto = titulo_upper

    y_cat = y_titulo

    stroke_cat = int(8 * fator)
    stroke_nome = int(10 * fator)
    desenho_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    fonte_cat = _obter_fonte(max(16, int(250 * fator)), negrito=True)
    cat_bbox = desenho_temp.textbbox((0, 0), cat_texto, font=fonte_cat, stroke_width=stroke_cat)
    w_cat = cat_bbox[2] - cat_bbox[0]

    largura_linha_cat = int(950 * fator)
    gap_linha = int(80 * fator)
    espessura_linha_cat = int(18 * fator)

    x_linha_esq_fim = (largura - w_cat) / 2 - gap_linha
    x_linha_esq_ini = x_linha_esq_fim - largura_linha_cat
    x_linha_dir_ini = (largura + w_cat) / 2 + gap_linha
    x_linha_dir_fim = x_linha_dir_ini + largura_linha_cat

    y_nome = y_cat + int(360 * fator)

    tam_inicial_nome = max(36, int(350 * fator))
    tam_fonte_nome = tam_inicial_nome
    limite_min_nome = max(24, int(tam_inicial_nome * 0.35))
    largura_max_nome = int(largura - 600 * fator)
    fonte_teste = _obter_fonte(tam_fonte_nome, negrito=True)
    bb_nome = desenho_temp.textbbox((0, 0), nome_texto, font=fonte_teste, stroke_width=stroke_nome)
    w_nome = bb_nome[2] - bb_nome[0]
    while w_nome > largura_max_nome and tam_fonte_nome > limite_min_nome:
        tam_fonte_nome -= 10
        fonte_teste = _obter_fonte(tam_fonte_nome, negrito=True)
        bb_nome = desenho_temp.textbbox((0, 0), nome_texto, font=fonte_teste, stroke_width=stroke_nome)
        w_nome = bb_nome[2] - bb_nome[0]

    y_inst = y_nome + int(290 * fator)

    tam_moldura = int(2600 * fator)
    tamanho_qr = int(2520 * fator)
    x_moldura = (largura - tam_moldura) / 2
    y_moldura = y_inst + int(260 * fator)
    raio_moldura = int(50 * fator)
    espessura_moldura = int(22 * fator)

    x_qr = (largura - tamanho_qr) / 2
    y_qr = y_moldura + (tam_moldura - tamanho_qr) / 2

    borda_offset = int(140 * fator)
    raio_borda = int(100 * fator)
    espessura_borda = int(32 * fator)

    y_sec = y_moldura + tam_moldura + int(360 * fator)
    sec_texto = "MÍNIMO IMPACTO NO LOCAL"
    fonte_sec = _obter_fonte(max(16, int(155 * fator)), negrito=True)
    sec_bbox = desenho_temp.textbbox((0, 0), sec_texto, font=fonte_sec)
    w_sec = sec_bbox[2] - sec_bbox[0]

    gap_sec = int(60 * fator)
    esp_linha_sec = int(8 * fator)
    margem_linha_sec = int(350 * fator)
    x_lsec_esq_ini = margem_linha_sec
    x_lsec_esq_fim = (largura - w_sec) / 2 - gap_sec
    x_lsec_dir_ini = (largura + w_sec) / 2 + gap_sec
    x_lsec_dir_fim = largura - margem_linha_sec

    tam_icon = int(155 * fator)
    esp_regras = int(210 * fator)
    y_base_regras = y_sec + int(270 * fator)

    regras_textos = [
        "Deixe a menor marca possível na natureza",
        "Preserve a rocha: não quebre nem altere agarras",
        "Leve todo o seu lixo de volta com você",
        "Preserve o entorno: faça suas necessidades",
        "nos sanitários disponibilizados pelo evento",
    ]
    fonte_regra_medicao = _obter_fonte(max(14, int(130 * fator)), negrito=True)
    max_w_regra = max(
        desenho_temp.textbbox((0, 0), r, font=fonte_regra_medicao)[2]
        - desenho_temp.textbbox((0, 0), r, font=fonte_regra_medicao)[0]
        for r in regras_textos
    )
    largura_bloco_regras = tam_icon + int(80 * fator) + max_w_regra
    x_bloco = int((largura - largura_bloco_regras) / 2)
    x_texto_regra = x_bloco + tam_icon + int(80 * fator)
    altura_linha_regra4 = int(140 * fator)

    y1 = y_base_regras
    y2 = y1 + esp_regras
    y3 = y2 + esp_regras
    y4 = y3 + esp_regras

    escala_icon = f"{tam_icon / 24:.4f}"
    subtitulo_tag = f'<text class="subtitulo" style="display:none">{escapar(subtitulo)}</text>' if subtitulo else ''

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}">
  <defs>
    <style>
      .fundo {{ fill: #ffffff; }}
      .borda {{ fill: none; stroke: {HEX_VERMELHO}; stroke-width: {espessura_borda}; }}
      .marca {{ font-family: Arial, Helvetica, sans-serif; font-size: {int(150 * fator)}px; font-weight: 800; letter-spacing: 4px; fill: #d97706; text-anchor: middle; dominant-baseline: middle; }}
      .subtitulo {{ font-family: Arial, Helvetica, sans-serif; font-size: {int(125 * fator)}px; font-weight: 500; fill: #6b7280; text-anchor: middle; dominant-baseline: middle; }}
      .categoria {{ font-family: Arial, Helvetica, sans-serif; font-size: {int(250 * fator)}px; font-weight: 900; fill: #111827; text-anchor: middle; dominant-baseline: middle; }}
      .nome {{ font-family: Arial, Helvetica, sans-serif; font-size: {tam_fonte_nome}px; font-weight: 900; fill: {HEX_VERMELHO}; text-anchor: middle; dominant-baseline: middle; }}
      .instrucao {{ font-family: Arial, Helvetica, sans-serif; font-size: {int(120 * fator)}px; font-weight: 400; fill: #111827; text-anchor: middle; dominant-baseline: middle; }}
      .secao-txt {{ font-family: Arial, Helvetica, sans-serif; font-size: {int(155 * fator)}px; font-weight: 800; fill: #111827; text-anchor: middle; dominant-baseline: middle; }}
      .regra-txt {{ font-family: Arial, Helvetica, sans-serif; font-size: {int(130 * fator)}px; font-weight: 700; fill: #111827; text-anchor: start; dominant-baseline: middle; }}
    </style>
  </defs>

  <rect class="fundo" fill="#ffffff" x="0" y="0" width="{largura}" height="{altura}" rx="{raio_borda}" ry="{raio_borda}" />
  <rect class="borda" fill="none" stroke="{HEX_VERMELHO}" stroke-width="{espessura_borda}" x="{borda_offset}" y="{borda_offset}" width="{largura - 2 * borda_offset}" height="{altura - 2 * borda_offset}" rx="{raio_borda}" ry="{raio_borda}" />

  {svg_cabecalho}
  {subtitulo_tag}

  <!-- Título: Categoria com linhas vermelhas e Nome em vermelho -->
  <line x1="{x_linha_esq_ini:.2f}" y1="{y_cat}" x2="{x_linha_esq_fim:.2f}" y2="{y_cat}" stroke="{HEX_VERMELHO}" stroke-width="{espessura_linha_cat}" stroke-linecap="round" />
  <text class="categoria" fill="#111827" stroke="#111827" stroke-width="{stroke_cat}" paint-order="stroke fill" font-family="Arial, Helvetica, sans-serif" font-size="{int(250 * fator)}px" font-weight="900" text-anchor="middle" dominant-baseline="middle" x="{largura / 2}" y="{y_cat}">{escapar(cat_texto)}</text>
  <line x1="{x_linha_dir_ini:.2f}" y1="{y_cat}" x2="{x_linha_dir_fim:.2f}" y2="{y_cat}" stroke="{HEX_VERMELHO}" stroke-width="{espessura_linha_cat}" stroke-linecap="round" />

  <text class="nome" fill="{HEX_VERMELHO}" stroke="{HEX_VERMELHO}" stroke-width="{stroke_nome}" paint-order="stroke fill" font-family="Arial, Helvetica, sans-serif" font-size="{tam_fonte_nome}px" font-weight="900" text-anchor="middle" dominant-baseline="middle" x="{largura / 2}" y="{y_nome}">{escapar(nome_texto)}</text>

  <text class="instrucao" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(120 * fator)}px" font-weight="400" text-anchor="middle" dominant-baseline="middle" x="{largura / 2}" y="{y_inst}">Aponte a câmera para abrir no Aresta</text>

  <!-- Moldura do QR Code Retangular Arredondada -->
  <rect x="{x_moldura:.2f}" y="{y_moldura:.2f}" width="{tam_moldura}" height="{tam_moldura}" rx="{raio_moldura}" ry="{raio_moldura}" fill="#ffffff" stroke="#000000" stroke-width="{espessura_moldura}" />

  <g transform="translate({x_qr:.2f}, {y_qr:.2f})">
    <rect width="{tamanho_qr}" height="{tamanho_qr}" fill="#ffffff" />
    <g>
      {svg_modulos}
      {svg_logo}
    </g>
  </g>

  <!-- Seção MÍNIMO IMPACTO NO LOCAL -->
  <line x1="{x_lsec_esq_ini:.2f}" y1="{y_sec}" x2="{x_lsec_esq_fim:.2f}" y2="{y_sec}" stroke="{HEX_CINZA_LINHA}" stroke-width="{esp_linha_sec}" stroke-linecap="round" />
  <text class="secao-txt" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(155 * fator)}px" font-weight="800" text-anchor="middle" dominant-baseline="middle" x="{largura / 2}" y="{y_sec}">{sec_texto}</text>
  <line x1="{x_lsec_dir_ini:.2f}" y1="{y_sec}" x2="{x_lsec_dir_fim:.2f}" y2="{y_sec}" stroke="{HEX_CINZA_LINHA}" stroke-width="{esp_linha_sec}" stroke-linecap="round" />

  <!-- Diretrizes e Regras com Ícones Vetoriais -->
  <g class="regras">
    <!-- Regra 1: Folha -->
    <g transform="translate({x_bloco}, {y1 - tam_icon // 2}) scale({escala_icon})">
      <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 3C12 3 7 7.5 6 13c-.7 3.5 1 6 2 7" />
        <path d="M19 3c0 7-4.5 12-11 17" />
        <line x1="4" y1="22" x2="12" y2="14" />
      </g>
    </g>
    <text class="regra-txt" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(130 * fator)}px" font-weight="700" text-anchor="start" dominant-baseline="middle" x="{x_texto_regra}" y="{y1}">Deixe a menor marca possível na natureza</text>

    <!-- Regra 2: Rocha -->
    <g transform="translate({x_bloco}, {y2 - tam_icon // 2}) scale({escala_icon})">
      <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19h16a2 2 0 0 0 1.8-2.9L13.8 4.6a2 2 0 0 0-3.6 0L2.2 16.1A2 2 0 0 0 4 19z" />
        <path d="M12 5.5l-1 5.5v4" />
      </g>
    </g>
    <text class="regra-txt" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(130 * fator)}px" font-weight="700" text-anchor="start" dominant-baseline="middle" x="{x_texto_regra}" y="{y2}">Preserve a rocha: não quebre nem altere agarras</text>

    <!-- Regra 3: Lixo -->
    <g transform="translate({x_bloco}, {y3 - tam_icon // 2}) scale({escala_icon})">
      <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 6h16" />
        <path d="M9.5 6V4a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2" />
        <path d="M5.5 6l1.2 13a2 2 0 0 0 2 2h6.6a2 2 0 0 0 2-2L18.5 6" />
        <line x1="9" y1="10" x2="9" y2="16" />
        <line x1="12" y1="10" x2="12" y2="16" />
        <line x1="15" y1="10" x2="15" y2="16" />
      </g>
    </g>
    <text class="regra-txt" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(130 * fator)}px" font-weight="700" text-anchor="start" dominant-baseline="middle" x="{x_texto_regra}" y="{y3}">Leve todo o seu lixo de volta com você</text>

    <!-- Regra 4: Entorno (duas linhas) -->
    <g transform="translate({x_bloco}, {y4 + altura_linha_regra4 // 2 - tam_icon // 2}) scale({escala_icon})">
      <g stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="7.5" cy="7.5" r="3.2" />
        <circle cx="16.5" cy="7.5" r="3.2" />
        <path d="M3 20.5h18" />
        <path d="M3 20.5v-1a4.5 4.5 0 0 1 4.5-4.5h0a4.5 4.5 0 0 1 4.5 3.5" />
        <path d="M12 18.5a4.5 4.5 0 0 1 4.5-3.5h0a4.5 4.5 0 0 1 4.5 4.5v1" />
        <line x1="12" y1="18.5" x2="12" y2="20.5" />
      </g>
    </g>
    <text class="regra-txt" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(130 * fator)}px" font-weight="700" text-anchor="start" dominant-baseline="middle" x="{x_texto_regra}" y="{y4}">Preserve o entorno: faça suas necessidades</text>
    <text class="regra-txt" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="{int(130 * fator)}px" font-weight="700" text-anchor="start" dominant-baseline="middle" x="{x_texto_regra}" y="{y4 + altura_linha_regra4}">nos sanitários disponibilizados pelo evento</text>
  </g>
</svg>"""


def _formatar_grau_via(grau_val: Any) -> str:
    """Converte enum numérico de GrauVia ou string em texto legível de graduação brasileira."""
    if not grau_val:
        return ""
    if isinstance(grau_val, str):
        return grau_val
    if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauVia.GrauVia.values():
        nome = croqui_pb2.GrauVia.GrauVia.Name(grau_val)
        if nome.startswith("BR_"):
            nome = nome[3:]
        return nome.replace("_BARRA_", "/").lower()
    return str(grau_val)


def _formatar_grau_boulder(grau_val: Any) -> str:
    """Converte enum numérico de GrauBoulder ou string em texto legível de graduação de boulder (V)."""
    if not grau_val:
        return ""
    if isinstance(grau_val, str):
        return grau_val
    if isinstance(grau_val, int) and grau_val in croqui_pb2.GrauBoulder.GrauBoulder.values():
        nome = croqui_pb2.GrauBoulder.GrauBoulder.Name(grau_val)
        return nome.replace("_BARRA_", "/")
    return str(grau_val)


def extrair_itens_croqui(
    pico_id: str,
    raiz_projeto: Path | None = None,
    incluir_vias: bool = False,
) -> list[dict[str, Any]]:
    """Extrai a lista de elementos (pico, grupos, setores e vias) a partir do compilado.binarypb ou croqui.yaml."""
    if raiz_projeto is None:
        raiz_projeto = DIRETORIO_RAIZ_PADRAO

    # Tenta carregar primeiro a versão compilada em Protobuf
    caminho_pb = raiz_projeto / "generated" / pico_id / "compilado.binarypb"
    if caminho_pb.exists():
        croqui = croqui_pb2.Croqui()
        with open(caminho_pb, "rb") as f:
            croqui.ParseFromString(f.read())

        nome_pico = croqui.nome or pico_id
        itens: list[dict[str, Any]] = []

        # Item principal do pico
        itens.append(
            {
                "tipo": "pico",
                "id": f"placa_pico_{pico_id}",
                "pico": pico_id,
                "titulo": nome_pico,
                "subtitulo": "Croqui Oficial · Aresta Climb",
            }
        )

        for p in croqui.picos:
            for elem in p.setores_ou_grupos:
                if elem.HasField("setor"):
                    setor = elem.setor.conteudo
                    setor_slug = slugify(setor.nome)
                    itens.append(
                        {
                            "tipo": "setor",
                            "id": f"placa_setor_{setor_slug}",
                            "pico": pico_id,
                            "grupo": None,
                            "setor": setor_slug,
                            "titulo": setor.nome,
                            "subtitulo": f"{nome_pico} · Setor",
                        }
                    )
                    if incluir_vias:
                        for esc in setor.escaladas:
                            nome_via = ""
                            grau = ""
                            if esc.HasField("via_esportiva"):
                                nome_via = esc.via_esportiva.nome
                                grau = _formatar_grau_via(esc.via_esportiva.dificuldade)
                            elif esc.HasField("boulder"):
                                nome_via = esc.boulder.nome
                                grau = _formatar_grau_boulder(esc.boulder.dificuldade)
                            if nome_via:
                                via_slug = slugify(nome_via)
                                itens.append(
                                    {
                                        "tipo": "via",
                                        "id": f"placa_via_{via_slug}",
                                        "pico": pico_id,
                                        "grupo": None,
                                        "setor": setor_slug,
                                        "via": via_slug,
                                        "titulo": nome_via,
                                        "subtitulo": f"{setor.nome} · {grau}"
                                        if grau
                                        else setor.nome,
                                    }
                                )
                elif elem.HasField("grupo"):
                    grupo = elem.grupo.conteudo
                    grupo_slug = slugify(grupo.nome)
                    itens.append(
                        {
                            "tipo": "grupo",
                            "id": f"placa_grupo_{grupo_slug}",
                            "pico": pico_id,
                            "grupo": grupo_slug,
                            "setor": None,
                            "titulo": grupo.nome,
                            "subtitulo": f"{nome_pico} · Grupo",
                        }
                    )
                    for arq_setor in grupo.setores:
                        setor_filho = arq_setor.conteudo
                        setor_filho_slug = slugify(setor_filho.nome)
                        itens.append(
                            {
                                "tipo": "setor",
                                "id": f"placa_setor_{setor_filho_slug}",
                                "pico": pico_id,
                                "grupo": grupo_slug,
                                "setor": setor_filho_slug,
                                "titulo": setor_filho.nome,
                                "subtitulo": f"{grupo.nome} · Setor",
                            }
                        )
                        if incluir_vias:
                            for esc in setor_filho.escaladas:
                                nome_via = ""
                                grau = ""
                                if esc.HasField("via_esportiva"):
                                    nome_via = esc.via_esportiva.nome
                                    grau = _formatar_grau_via(esc.via_esportiva.dificuldade)
                                elif esc.HasField("boulder"):
                                    nome_via = esc.boulder.nome
                                    grau = _formatar_grau_boulder(esc.boulder.dificuldade)
                                if nome_via:
                                    via_slug = slugify(nome_via)
                                    itens.append(
                                        {
                                            "tipo": "via",
                                            "id": f"placa_via_{via_slug}",
                                            "pico": pico_id,
                                            "grupo": grupo_slug,
                                            "setor": setor_filho_slug,
                                            "via": via_slug,
                                            "titulo": nome_via,
                                            "subtitulo": f"{setor_filho.nome} · {grau}"
                                            if grau
                                            else setor_filho.nome,
                                        }
                                    )
        return itens

    # 2. Se não houver compilado, lê a pasta database/
    caminho_yaml = raiz_projeto / "database" / pico_id / "croqui.yaml"
    if caminho_yaml.exists():
        with open(caminho_yaml, "r", encoding="utf-8") as f:
            dados_yaml = yaml.safe_load(f)

        nome_pico = dados_yaml.get("nome", pico_id)
        itens = [
            {
                "tipo": "pico",
                "id": f"placa_pico_{pico_id}",
                "pico": pico_id,
                "titulo": nome_pico,
                "subtitulo": "Croqui Oficial · Aresta Climb",
            }
        ]

        for p_yaml in dados_yaml.get("picos", []):
            for sg in p_yaml.get("setores_ou_grupos", []):
                if "setor" in sg:
                    caminho_setor = sg["setor"].get("caminho", "")
                    slug = caminho_setor.replace(".md", "").replace(
                        "setor_", ""
                    )
                    titulo = slug.replace("_", " ").title()
                    itens.append(
                        {
                            "tipo": "setor",
                            "id": f"placa_setor_{slug}",
                            "pico": pico_id,
                            "grupo": None,
                            "setor": slug,
                            "titulo": titulo,
                            "subtitulo": f"{nome_pico} · Setor",
                        }
                    )
                elif "grupo" in sg:
                    caminho_grupo = sg["grupo"].get("caminho", "")
                    slug = caminho_grupo.replace(".md", "")
                    titulo = slug.replace("_", " ").title()
                    itens.append(
                        {
                            "tipo": "grupo",
                            "id": f"placa_grupo_{slug}",
                            "pico": pico_id,
                            "grupo": slug,
                            "setor": None,
                            "titulo": titulo,
                            "subtitulo": f"{nome_pico} · Grupo",
                        }
                    )
        return itens

    raise FileNotFoundError(
        f"O croqui do pico '{pico_id}' não foi encontrado em generated/ ou database/."
    )


def exportar_placas_pico(
    pico_id: str,
    diretorio_saida: Path | str,
    raiz_projeto: Path | None = None,
    incluir_vias: bool = False,
    caminho_logo: Path | str | None = None,
    caminho_logo_topo: Path | str | None = None,
    caminho_logo_aresta: Path | str | None = None,
    limite_itens: int | None = None,
    largura: int = LARGURA_PADRAO_A4_600DPI,
    altura: int = ALTURA_PADRAO_A4_600DPI,
    dpi: int = DPI_PADRAO,
    gerar_svg: bool = False,
    gerar_pdf: bool = False,
    cor_borda_logo: str = "preta",
    utm_source: str | None = "setor_igarameca",
    utm_medium: str | None = "qrcode",
    utm_campaign: str | None = None,
) -> list[dict[str, Any]]:
    """Gera e salva em disco todas as placas em formato A4 de alta resolução (PNG e opcionalmente SVG/PDF)."""
    destino = Path(diretorio_saida)
    destino.mkdir(parents=True, exist_ok=True)

    if raiz_projeto is None:
        raiz_projeto = DIRETORIO_RAIZ_PADRAO

    itens = extrair_itens_croqui(
        pico_id, raiz_projeto=raiz_projeto, incluir_vias=incluir_vias
    )
    if limite_itens is not None:
        itens = itens[:limite_itens]

    if caminho_logo_topo is None:
        caminho_logo_topo = obter_logo_topo_padrao(
            pico_id, raiz_projeto=raiz_projeto
        )
    if caminho_logo_aresta is None:
        caminho_logo_aresta = obter_logo_aresta_padrao(
            raiz_projeto=raiz_projeto
        )

    arquivos_gerados: list[dict[str, Any]] = []

    for item in itens:
        url = montar_url_deep_link(
            pico=item["pico"],
            grupo=item.get("grupo"),
            setor=item.get("setor"),
            via=item.get("via"),
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )

        caminho_png = destino / f"{item['id']}.png"
        img_png = gerar_placa_png(
            url=url,
            titulo=item["titulo"],
            subtitulo=item["subtitulo"],
            caminho_logo=caminho_logo,
            caminho_logo_topo=caminho_logo_topo,
            caminho_logo_aresta=caminho_logo_aresta,
            largura=largura,
            altura=altura,
            cor_borda_logo=cor_borda_logo,
        )
        img_png.save(caminho_png, "PNG", dpi=(dpi, dpi))

        registro: dict[str, Any] = {
            "id": item["id"],
            "url": url,
            "png": caminho_png,
        }

        if gerar_svg:
            caminho_svg = destino / f"{item['id']}.svg"
            svg_conteudo = gerar_placa_svg(
                url=url,
                titulo=item["titulo"],
                subtitulo=item["subtitulo"],
                caminho_logo=caminho_logo,
                caminho_logo_topo=caminho_logo_topo,
                caminho_logo_aresta=caminho_logo_aresta,
                largura=largura,
                altura=altura,
                cor_borda_logo=cor_borda_logo,
            )
            caminho_svg.write_text(svg_conteudo, encoding="utf-8")
            registro["svg"] = caminho_svg

        if gerar_pdf:
            caminho_pdf = destino / f"{item['id']}.pdf"
            img_png.convert("RGB").save(caminho_pdf, "PDF", resolution=float(dpi))
            registro["pdf"] = caminho_pdf

        arquivos_gerados.append(registro)

    return arquivos_gerados
