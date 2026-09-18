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
) -> Image.Image:
    """Gera o QR Code com correção de erro nível H e insere o logo oficial centralizado."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
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
            largura_total = int(imagem_qr.size[0] * 0.25)
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


def obter_logo_aresta_padrao() -> Path | None:
    """Retorna o caminho do logo oficial do Aresta Climb para o cabeçalho."""
    raiz = Path(__file__).resolve().parent.parent
    candidatos = [
        raiz / "editor" / "recursos" / "logo_splash.png",
        raiz.parent / "aresta_app" / "frontend" / "assets" / "logo_splash.png",
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


def obter_logo_topo_padrao(pico_id: str | None = None) -> Path | None:
    """Verifica se existe um logo de cabeçalho padrão para o pico informado."""
    if not pico_id:
        return None
    raiz = Path(__file__).resolve().parent.parent
    if "igarape" in pico_id or "pedra_grande" in pico_id:
        candidatos = [
            raiz.parent / "aresta_data" / "logo_igarameca.pdf",
            raiz / "editor" / "recursos" / "logo_igarameca.pdf",
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
) -> None:
    """Desenha o título ajustando o tamanho da fonte para caber na largura máxima."""
    tamanho = tamanho_inicial
    fonte = _obter_fonte(tamanho, negrito=True)
    bbox = desenho.textbbox((0, 0), texto, font=fonte)
    largura_texto = bbox[2] - bbox[0]
    limite_minimo = max(24, int(tamanho_inicial * 0.35))
    while largura_texto > largura_maxima and tamanho > limite_minimo:
        tamanho -= 10
        fonte = _obter_fonte(tamanho, negrito=True)
        bbox = desenho.textbbox((0, 0), texto, font=fonte)
        largura_texto = bbox[2] - bbox[0]

    desenho.text(
        (centro_x, centro_y),
        texto,
        fill=(17, 24, 39),
        font=fonte,
        anchor="mm",
    )


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
    """Desenha a placa física completa em formato A4 de alta resolução (600 DPI)."""
    placa = Image.new("RGB", (largura, altura), color=(255, 255, 255))
    desenho = ImageDraw.Draw(placa)

    fator = largura / 4960.0

    borda_offset = max(8, int(120 * fator))
    raio_borda = max(12, int(160 * fator))
    espessura_borda = max(2, int(28 * fator))

    # Borda externa decorativa com cantos arredondados
    desenho.rounded_rectangle(
        [(borda_offset, borda_offset), (largura - borda_offset, altura - borda_offset)],
        radius=raio_borda,
        outline=(17, 24, 39),
        width=espessura_borda,
    )

    # Resolução dos caminhos de logo do cabeçalho
    caminho_aresta_resolvido = (
        obter_logo_aresta_padrao()
        if caminho_logo_aresta is None
        else (Path(caminho_logo_aresta) if caminho_logo_aresta else None)
    )

    img_esq = carregar_imagem_topo(caminho_logo_topo, dpi=int(300 * fator))
    img_dir = carregar_imagem_topo(caminho_aresta_resolvido, dpi=int(300 * fator))

    if img_esq is not None and img_dir is not None:
        # Modo Duplo: Logo do parceiro/pico à esquerda e logo oficial do Aresta Climb à direita
        margem_x = int(420 * fator)
        topo_y = int(460 * fator)
        altura_topo = int(820 * fator)
        y_centro = topo_y + altura_topo // 2

        # Redimensionamento Igarameca / parceiro (esquerda)
        max_w_esq = int(1950 * fator)
        h_esq_alvo = int(780 * fator)
        prop_esq = min(max_w_esq / img_esq.width, h_esq_alvo / img_esq.height)
        w_esq = int(img_esq.width * prop_esq)
        h_esq = int(img_esq.height * prop_esq)
        img_esq_redim = img_esq.resize((w_esq, h_esq), Image.Resampling.LANCZOS)
        x_esq = margem_x
        y_esq = y_centro - h_esq // 2
        placa.paste(img_esq_redim, (x_esq, y_esq), img_esq_redim)

        # Redimensionamento Aresta Climb (direita)
        max_w_dir = int(1450 * fator)
        h_dir_alvo = int(880 * fator)
        prop_dir = min(max_w_dir / img_dir.width, h_dir_alvo / img_dir.height)
        w_dir = int(img_dir.width * prop_dir)
        h_dir = int(img_dir.height * prop_dir)
        img_dir_redim = img_dir.resize((w_dir, h_dir), Image.Resampling.LANCZOS)
        x_dir = largura - margem_x - w_dir
        y_dir = y_centro - h_dir // 2
        placa.paste(img_dir_redim, (x_dir, y_dir), img_dir_redim)

        y_titulo = topo_y + altura_topo + int(360 * fator)

    elif img_esq is not None or img_dir is not None:
        # Modo Único: Centraliza a única logo disponível
        img_unica = img_esq if img_esq is not None else img_dir
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

        if subtitulo:
            fonte_subtitulo = _obter_fonte(max(12, int(125 * fator)), negrito=False)
            desenho.text(
                (largura // 2, int(750 * fator)),
                subtitulo,
                fill=(107, 114, 128),
                font=fonte_subtitulo,
                anchor="mm",
            )
        y_titulo = int(1200 * fator)

    # Título em grande destaque do Setor ou Via (com auto-escala aumentada)
    _desenhar_titulo_com_escala(
        desenho=desenho,
        texto=titulo,
        centro_x=largura // 2,
        centro_y=y_titulo,
        largura_maxima=int(largura - 400 * fator),
        tamanho_inicial=max(36, int(420 * fator)),
    )

    # QR Code centralizado (ligeiramente reduzido para proporção harmônica)
    tamanho_qr = int(2950 * fator)
    qr_img = gerar_qrcode_com_logo(
        url=url,
        caminho_logo=caminho_logo,
        tamanho_px=tamanho_qr,
        cor_borda=cor_borda_logo,
    )
    pos_qr_x = (largura - tamanho_qr) // 2
    pos_qr_y = y_titulo + int(300 * fator)
    placa.paste(qr_img.convert("RGB"), (pos_qr_x, pos_qr_y))

    # Instrução de leitura no rodapé
    fonte_instrucao = _obter_fonte(max(12, int(105 * fator)), negrito=False)
    desenho.text(
        (largura // 2, pos_qr_y + tamanho_qr + int(240 * fator)),
        "Aponte a câmera para abrir o croqui e navegar offline no app",
        fill=(55, 65, 81),
        font=fonte_instrucao,
        anchor="mm",
    )

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
    """Gera a placa completa em formato vetorial SVG puro com logo oficial embutido."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    fator = largura / 4960.0

    matriz = qr.get_matrix()
    qtd_modulos = len(matriz)
    tamanho_qr = int(2950 * fator)
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

    # Determina o logo a ser utilizado
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
            largura_total = int(tamanho_qr * 0.25)
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

    # Resolução dos caminhos de logo do cabeçalho
    caminho_aresta_resolvido = (
        obter_logo_aresta_padrao()
        if caminho_logo_aresta is None
        else (Path(caminho_logo_aresta) if caminho_logo_aresta else None)
    )

    img_esq = carregar_imagem_topo(caminho_logo_topo, dpi=int(300 * fator))
    img_dir = carregar_imagem_topo(caminho_aresta_resolvido, dpi=int(300 * fator))

    if img_esq is not None and img_dir is not None:
        margem_x = int(420 * fator)
        topo_y = int(460 * fator)
        altura_topo = int(820 * fator)
        y_centro = topo_y + altura_topo // 2

        # Esquerda (Igarameca / parceiro)
        max_w_esq = int(1950 * fator)
        h_esq_alvo = int(780 * fator)
        prop_esq = min(max_w_esq / img_esq.width, h_esq_alvo / img_esq.height)
        w_esq = int(img_esq.width * prop_esq)
        h_esq = int(img_esq.height * prop_esq)
        img_esq_redim = img_esq.resize((w_esq, h_esq), Image.Resampling.LANCZOS)
        buf_esq = BytesIO()
        img_esq_redim.save(buf_esq, "PNG")
        b64_esq = base64.b64encode(buf_esq.getvalue()).decode("ascii")
        x_esq = margem_x
        y_esq = y_centro - h_esq // 2

        # Direita (Aresta Climb)
        max_w_dir = int(1450 * fator)
        h_dir_alvo = int(880 * fator)
        prop_dir = min(max_w_dir / img_dir.width, h_dir_alvo / img_dir.height)
        w_dir = int(img_dir.width * prop_dir)
        h_dir = int(img_dir.height * prop_dir)
        img_dir_redim = img_dir.resize((w_dir, h_dir), Image.Resampling.LANCZOS)
        buf_dir = BytesIO()
        img_dir_redim.save(buf_dir, "PNG")
        b64_dir = base64.b64encode(buf_dir.getvalue()).decode("ascii")
        x_dir = largura - margem_x - w_dir
        y_dir = y_centro - h_dir // 2

        svg_cabecalho = f"""<image href="data:image/png;base64,{b64_esq}" x="{x_esq:.2f}" y="{y_esq:.2f}" width="{w_esq}" height="{h_esq}" />
  <image href="data:image/png;base64,{b64_dir}" x="{x_dir:.2f}" y="{y_dir:.2f}" width="{w_dir}" height="{h_dir}" />"""
        y_titulo = topo_y + altura_topo + int(360 * fator)

    elif img_esq is not None or img_dir is not None:
        img_unica = img_esq if img_esq is not None else img_dir
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

    pos_qr_x = (largura - tamanho_qr) / 2
    pos_qr_y = y_titulo + int(300 * fator)
    borda_offset = max(8, int(120 * fator))
    raio_borda = max(12, int(160 * fator))
    espessura_borda = max(2, int(28 * fator))
    pos_instrucao_y = pos_qr_y + tamanho_qr + int(240 * fator)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}">
  <defs>
    <style>
      .fundo {{ fill: #ffffff; }}
      .borda {{ fill: none; stroke: #111827; stroke-width: {espessura_borda}; }}
      .marca {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: {int(150 * fator)}px; font-weight: 800; letter-spacing: 4px; fill: #d97706; text-anchor: middle; }}
      .subtitulo {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: {int(125 * fator)}px; font-weight: 500; fill: #6b7280; text-anchor: middle; }}
      .titulo {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: {int(420 * fator)}px; font-weight: 800; fill: #111827; text-anchor: middle; }}
      .instrucao {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: {int(105 * fator)}px; font-weight: 600; fill: #374151; text-anchor: middle; }}
    </style>
  </defs>

  <rect class="fundo" x="0" y="0" width="{largura}" height="{altura}" rx="{raio_borda}" ry="{raio_borda}" />
  <rect class="borda" x="{borda_offset}" y="{borda_offset}" width="{largura - 2 * borda_offset}" height="{altura - 2 * borda_offset}" rx="{raio_borda}" ry="{raio_borda}" />

  {svg_cabecalho}

  <text class="titulo" x="{largura / 2}" y="{y_titulo}">{escapar(titulo)}</text>

  <g transform="translate({pos_qr_x:.2f}, {pos_qr_y:.2f})">
    <rect width="{tamanho_qr}" height="{tamanho_qr}" fill="#ffffff" />
    <g>
      {svg_modulos}
      {svg_logo}
    </g>
  </g>

  <text class="instrucao" x="{largura / 2}" y="{pos_instrucao_y}">Aponte a câmera para abrir o croqui e navegar offline no app</text>
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
        raiz_projeto = Path(__file__).resolve().parent.parent

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
    cor_borda_logo: str = "preta",
    utm_source: str | None = "setor_igarameca",
    utm_medium: str | None = "qrcode",
    utm_campaign: str | None = None,
) -> list[dict[str, Any]]:
    """Gera e salva em disco todas as placas em formato A4 de alta resolução (PNG e opcionalmente SVG)."""
    destino = Path(diretorio_saida)
    destino.mkdir(parents=True, exist_ok=True)

    itens = extrair_itens_croqui(
        pico_id, raiz_projeto=raiz_projeto, incluir_vias=incluir_vias
    )
    if limite_itens is not None:
        itens = itens[:limite_itens]

    if caminho_logo_topo is None:
        caminho_logo_topo = obter_logo_topo_padrao(pico_id)

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

        arquivos_gerados.append(registro)

    return arquivos_gerados
