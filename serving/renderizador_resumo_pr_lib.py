# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para renderização do relatório interativo `resumo.html` e do comentário
Markdown enxuto para Pull Requests que modificam croquis.
"""

from __future__ import annotations

import difflib
import html

import qrcode

from editor.core.codigo_sessao import (
    gerar_codigo_pull_request,
    obter_url_previa,
    obter_url_resumo_previa,
)
from serving.diff_croqui_pr_lib import (
    AlteracaoCampo,
    DiffCroqui,
    DiffEntidade,
    DiffImagem,
    DiffMapa,
    DiffPontoMapa,
    PontoMapaVisual,
    ResumoDiffPullRequest,
)

ASSINATURA_COMENTARIO_PR = "<!-- aresta-pr-validator -->"


def _gerar_qr_code_svg(url: str) -> str:
    """Gera um elemento `<svg>` vetorial compacto representando o QR Code da URL."""
    qr = qrcode.QRCode(border=1, box_size=4)
    qr.add_data(url)
    qr.make(fit=True)
    matriz = qr.get_matrix()
    tamanho = len(matriz)
    retangulos: list[str] = []
    for y, linha in enumerate(matriz):
        for x, ativo in enumerate(linha):
            if ativo:
                retangulos.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="#0d1117"/>')
    corpo = "".join(retangulos)
    return (
        f'<svg class="qr-svg" viewBox="0 0 {tamanho} {tamanho}" '
        f'width="136" height="136" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="100%" height="100%" fill="#ffffff" rx="1.5"/>'
        f"{corpo}</svg>"
    )


def _renderizar_geometria_svg(ponto: PontoMapaVisual, cor: str, classe_camada: str) -> str:
    rotulo_esc = html.escape(ponto.rotulo)
    if ponto.tipo_geometria == "linha":
        d_esc = html.escape(ponto.caminho_svg_linha)
        return (
            f'<g class="{classe_camada}">'
            f'<path d="{d_esc}" fill="none" stroke="{cor}" stroke-width="4" '
            f'stroke-dasharray="8,5" stroke-linecap="round"/>'
            f"</g>"
        )
    if ponto.tipo_geometria == "poligono":
        pts = " ".join(f"{x},{y}" for x, y in ponto.coordenadas_poligono)
        return (
            f'<g class="{classe_camada}">'
            f'<polygon points="{pts}" fill="{cor}33" stroke="{cor}" stroke-width="3"/>'
            f'<text x="{ponto.x}" y="{ponto.y}" fill="#ffffff" font-size="14" '
            f'font-weight="bold" text-anchor="middle">{rotulo_esc}</text>'
            f"</g>"
        )
    if ponto.tipo_geometria in ("quadrado", "retangulo"):
        x0 = ponto.x - ponto.largura // 2
        y0 = ponto.y - ponto.altura // 2
        return (
            f'<g class="{classe_camada}">'
            f'<rect x="{x0}" y="{y0}" width="{ponto.largura}" height="{ponto.altura}" '
            f'fill="{cor}33" stroke="{cor}" stroke-width="3" rx="3"/>'
            f'<text x="{ponto.x}" y="{ponto.y + 5}" fill="#ffffff" font-size="13" '
            f'font-weight="bold" text-anchor="middle">{rotulo_esc}</text>'
            f"</g>"
        )
    return (
        f'<g class="{classe_camada}">'
        f'<circle cx="{ponto.x}" cy="{ponto.y}" r="{ponto.raio}" '
        f'fill="{cor}44" stroke="{cor}" stroke-width="3"/>'
        f'<text x="{ponto.x}" y="{ponto.y + 4}" fill="#ffffff" font-size="12" '
        f'font-weight="bold" text-anchor="middle">{rotulo_esc}</text>'
        f"</g>"
    )


def _renderizar_svg_pontos_mapa(
    pontos: list[DiffPontoMapa],
    largura: int,
    altura: int,
) -> str:
    larg = largura or 1000
    alt = altura or 800
    elementos: list[str] = []

    for dp in pontos:
        if dp.status == "adicionado" and dp.ponto_depois is not None:
            elementos.append(
                _renderizar_geometria_svg(dp.ponto_depois, "#2ea043", "camada-depois camada-diff")
            )
        elif dp.status == "removido" and dp.ponto_antes is not None:
            elementos.append(
                _renderizar_geometria_svg(dp.ponto_antes, "#f85149", "camada-antes camada-diff")
            )
        elif (
            dp.status == "modificado" and dp.ponto_antes is not None and dp.ponto_depois is not None
        ):
            elementos.append(
                _renderizar_geometria_svg(dp.ponto_antes, "#f85149", "camada-antes camada-diff")
            )
            elementos.append(
                f'<g class="camada-diff">'
                f'<line x1="{dp.ponto_antes.x}" y1="{dp.ponto_antes.y}" '
                f'x2="{dp.ponto_depois.x}" y2="{dp.ponto_depois.y}" '
                f'stroke="#d29922" stroke-width="3" stroke-dasharray="6,4"/>'
                f"</g>"
            )
            elementos.append(
                _renderizar_geometria_svg(dp.ponto_depois, "#d29922", "camada-depois camada-diff")
            )
        elif dp.ponto_depois is not None:
            elementos.append(
                _renderizar_geometria_svg(
                    dp.ponto_depois, "#58a6ff", "camada-antes camada-depois camada-diff"
                )
            )

    corpo_svg = "".join(elementos)
    return (
        f'<svg class="mapa-svg-overlay" viewBox="0 0 {larg} {alt}" '
        f'xmlns="http://www.w3.org/2000/svg">{corpo_svg}</svg>'
    )


def _renderizar_secao_mapa(
    id_croqui: str,
    indice_mapa: int,
    mapa: DiffMapa,
    numero_pr: int,
    url_base_serving: str,
) -> str:
    id_dom = f"mapa-{html.escape(id_croqui)}-{indice_mapa}"
    url_depois = f"{url_base_serving}/pr/{numero_pr}/{id_croqui}/{mapa.caminho_imagem}"
    ctx_esc = html.escape(mapa.contexto)
    caminho_esc = html.escape(mapa.caminho_imagem)
    svg_overlay = _renderizar_svg_pontos_mapa(
        mapa.pontos,
        mapa.largura_depois or mapa.largura_antes,
        mapa.altura_depois or mapa.altura_antes,
    )

    if mapa.imagem_alterada and mapa.caminho_imagem_base_relativo:
        url_antes = f"{url_base_serving}/pr/{numero_pr}/{mapa.caminho_imagem_base_relativo}"
        res_info = (
            f"{mapa.largura_antes}x{mapa.altura_antes} ({mapa.tamanho_kb_antes} KB) → "
            f"{mapa.largura_depois}x{mapa.altura_depois} ({mapa.tamanho_kb_depois} KB)"
        )
        return f"""
        <div class="cartao-item item-filtravel" data-categoria="mapa" data-status="{mapa.status}" id="{id_dom}">
          <div class="cabecalho-cartao">
            <div>
              <span class="badge badge-modificado">IMAGEM DO MAPA ALTERADA</span>
              <strong>{ctx_esc}</strong>
              <span class="subtexto">({caminho_esc} · {res_info})</span>
            </div>
            <div class="grupo-botoes-modo">
              <button type="button" class="btn-modo ativo" onclick="alternarVisualizacaoMapaImagem('{id_dom}', 'lado-a-lado', this)">Lado a Lado</button>
              <button type="button" class="btn-modo" onclick="alternarVisualizacaoMapaImagem('{id_dom}', 'cortina', this)">Slider Cortina</button>
            </div>
          </div>
          <div class="comparador-mapa-imagem modo-lado-a-lado">
            <div class="painel-antes">
              <div class="rotulo-painel">Antes ({mapa.largura_antes}x{mapa.altura_antes})</div>
              <div class="container-mapa mode-antes">
                <img src="{html.escape(url_antes)}" alt="Mapa Antes" loading="lazy"/>
                {svg_overlay}
              </div>
            </div>
            <div class="painel-depois">
              <div class="rotulo-painel">Depois ({mapa.largura_depois}x{mapa.altura_depois})</div>
              <div class="container-mapa mode-depois">
                <img src="{html.escape(url_depois)}" alt="Mapa Depois" loading="lazy"/>
                {svg_overlay}
              </div>
            </div>
            <input type="range" min="0" max="100" value="50" class="slider-cortina" oninput="atualizarCortina('{id_dom}', this.value)"/>
          </div>
        </div>
        """

    return f"""
    <div class="cartao-item item-filtravel" data-categoria="mapa" data-status="{mapa.status}" id="{id_dom}">
      <div class="cabecalho-cartao">
        <div>
          <span class="badge badge-{mapa.status}">MAPA {mapa.status.upper()}</span>
          <strong>{ctx_esc}</strong>
          <span class="subtexto">({caminho_esc} · {mapa.largura_depois}x{mapa.altura_depois})</span>
        </div>
        <div class="grupo-botoes-modo">
          <button type="button" class="btn-modo ativo" onclick="definirModoSvg('{id_dom}', 'mode-diff', this)">Diff</button>
          <button type="button" class="btn-modo" onclick="definirModoSvg('{id_dom}', 'mode-antes', this)">Antes</button>
          <button type="button" class="btn-modo" onclick="definirModoSvg('{id_dom}', 'mode-depois', this)">Depois</button>
          <button type="button" class="btn-modo" onclick="definirModoSvg('{id_dom}', 'mode-ocultar', this)">Ocultar</button>
        </div>
      </div>
      <div class="container-mapa mode-diff">
        <img src="{html.escape(url_depois)}" alt="Mapa {ctx_esc}" loading="lazy"/>
        {svg_overlay}
      </div>
    </div>
    """


def _renderizar_diff_markdown(antes: str, depois: str) -> str:
    linhas_diff = list(difflib.ndiff(antes.splitlines(), depois.splitlines()))
    partes: list[str] = ['<pre class="diff-markdown">']
    for linha in linhas_diff:
        esc = html.escape(linha)
        if linha.startswith("+ "):
            partes.append(f'<span class="linha-add">{esc}</span>')
        elif linha.startswith("- "):
            partes.append(f'<span class="linha-rem">{esc}</span>')
        elif not linha.startswith("? "):
            partes.append(f"<span>{esc}</span>")
    partes.append("</pre>")
    return "\n".join(partes)


def _renderizar_alteracoes_campos(alteracoes: list[AlteracaoCampo]) -> str:
    linhas: list[str] = ['<div class="lista-campos">']
    for alt in alteracoes:
        nome_esc = html.escape(alt.nome_campo)
        if alt.eh_markdown:
            corpo = _renderizar_diff_markdown(alt.valor_antes, alt.valor_depois)
            linhas.append(f'<div class="item-campo"><strong>{nome_esc}:</strong>{corpo}</div>')
        else:
            antes_esc = html.escape(alt.valor_antes) or "<em>(vazio)</em>"
            depois_esc = html.escape(alt.valor_depois) or "<em>(vazio)</em>"
            linhas.append(
                f'<div class="item-campo"><strong>{nome_esc}:</strong> '
                f'<span class="val-antes">{antes_esc}</span> → '
                f'<span class="val-depois">{depois_esc}</span></div>'
            )
    linhas.append("</div>")
    return "".join(linhas)


def _renderizar_cartao_entidade(ent: DiffEntidade) -> str:
    titulo = ent.nome_depois or ent.nome_antes
    renomeado = (
        f' <span class="subtexto">(antes: {html.escape(ent.nome_antes)})</span>'
        if ent.nome_antes and ent.nome_depois and ent.nome_antes != ent.nome_depois
        else ""
    )
    resumo_badge = (
        f' <span class="badge-neutro">{html.escape(ent.resumo_curto)}</span>'
        if ent.resumo_curto
        else ""
    )
    campos_html = (
        _renderizar_alteracoes_campos(ent.alteracoes_campos) if ent.alteracoes_campos else ""
    )
    return f"""
    <div class="cartao-item item-filtravel" data-categoria="entidade" data-status="{ent.status}">
      <div class="cabecalho-cartao">
        <div>
          <span class="badge badge-{ent.status}">{ent.tipo_entidade.upper()} · {ent.status.upper()}</span>
          <strong>{html.escape(titulo)}</strong>{renomeado}{resumo_badge}
          <span class="subtexto">({html.escape(ent.contexto)} · UID: <code>{html.escape(ent.uid)}</code>)</span>
        </div>
      </div>
      {campos_html}
    </div>
    """


def _renderizar_cartao_imagem(
    img: DiffImagem,
    numero_pr: int,
    url_base_serving: str,
) -> str:
    url_antes = (
        f"{url_base_serving}/pr/{numero_pr}/{img.caminho_base_relativo}"
        if img.caminho_base_relativo
        else ""
    )
    url_depois = (
        f"{url_base_serving}/pr/{numero_pr}/{img.caminho_pr_relativo}"
        if img.caminho_pr_relativo
        else ""
    )
    if img.status == "modificado":
        corpo_midia = f"""
        <div class="galeria-antes-depois">
          <div class="coluna-img">
            <div class="rotulo-painel">Antes ({img.largura_antes}x{img.altura_antes} · {img.tamanho_kb_antes} KB)</div>
            <img src="{html.escape(url_antes)}" alt="Antes" loading="lazy"/>
          </div>
          <div class="coluna-img">
            <div class="rotulo-painel">Depois ({img.largura_depois}x{img.altura_depois} · {img.tamanho_kb_depois} KB)</div>
            <img src="{html.escape(url_depois)}" alt="Depois" loading="lazy"/>
          </div>
        </div>
        """
    elif img.status == "adicionado":
        corpo_midia = f"""
        <div class="galeria-unica">
          <div class="rotulo-painel">Adicionada ({img.largura_depois}x{img.altura_depois} · {img.tamanho_kb_depois} KB)</div>
          <img src="{html.escape(url_depois)}" alt="Nova imagem" loading="lazy"/>
        </div>
        """
    else:
        corpo_midia = f"""
        <div class="galeria-unica">
          <div class="rotulo-painel">Removida ({img.largura_antes}x{img.altura_antes} · {img.tamanho_kb_antes} KB)</div>
          <img src="{html.escape(url_antes)}" alt="Imagem removida" loading="lazy"/>
        </div>
        """

    return f"""
    <div class="cartao-item item-filtravel" data-categoria="imagem" data-status="{img.status}">
      <div class="cabecalho-cartao">
        <div>
          <span class="badge badge-{img.status}">IMAGEM {img.status.upper()}</span>
          <strong>{html.escape(img.onde_usada)}</strong>
          <span class="subtexto">({html.escape(img.caminho_relativo)})</span>
        </div>
      </div>
      {corpo_midia}
    </div>
    """


def _renderizar_bloco_croqui(
    croqui: DiffCroqui,
    numero_pr: int,
    url_base_serving: str,
) -> str:
    meta_html = (
        _renderizar_alteracoes_campos(croqui.alteracoes_metadados)
        if croqui.alteracoes_metadados
        else ""
    )
    mapas_html = "".join(
        _renderizar_secao_mapa(croqui.id_croqui, idx, m, numero_pr, url_base_serving)
        for idx, m in enumerate(croqui.mapas)
        if m.status != "inalterado"
    )
    imagens_html = "".join(
        _renderizar_cartao_imagem(img, numero_pr, url_base_serving) for img in croqui.imagens
    )
    entidades_html = "".join(_renderizar_cartao_entidade(e) for e in croqui.entidades)

    return f"""
    <section class="secao-croqui">
      <div class="cabecalho-croqui">
        <h2>{html.escape(croqui.nome)} <code>({html.escape(croqui.id_croqui)})</code></h2>
        <span class="badge badge-{croqui.status}">CROQUI {croqui.status.upper()}</span>
      </div>
      {meta_html}
      {mapas_html}
      {imagens_html}
      {entidades_html}
    </section>
    """


def renderizar_resumo_html(
    resumo: ResumoDiffPullRequest,
    numero_pr: int,
    url_base_serving: str = "https://serving.arestaclimb.com",
    url_base_previa: str = "https://previa.arestaclimb.com",
    commit_sha: str = "",
) -> str:
    """
    Gera a página HTML5 autocontida (`resumo.html`) com diffs estruturais,
    overlays SVG de mapas, comparadores visuais de imagens e acesso rápido ao aplicativo.
    """
    codigo_formatado = gerar_codigo_pull_request(numero_pr)
    url_app = obter_url_previa(codigo_formatado, base_url=url_base_previa)
    qr_svg = _gerar_qr_code_svg(url_app)
    commit_curto = commit_sha[:7] if commit_sha else "HEAD"

    blocos_croquis = "".join(
        _renderizar_bloco_croqui(c, numero_pr, url_base_serving.rstrip("/")) for c in resumo.croquis
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Resumo da PR #{numero_pr} ({codigo_formatado}) - Aresta Climb</title>
  <style>
    :root {{
      --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3;
      --muted: #8b949e; --green: #2ea043; --yellow: #d29922; --red: #f85149; --blue: #58a6ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; padding: 20px; }}
    .container {{ max-width: 1180px; margin: 0 auto; }}
    .hero {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 20px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
    .codigo-box {{ display: inline-flex; align-items: center; gap: 10px; background: #090d13; border: 1px solid var(--border); padding: 8px 14px; border-radius: 8px; font-family: monospace; font-size: 1.25rem; font-weight: bold; color: var(--blue); }}
    .btn-acao {{ display: inline-block; background: var(--green); color: #fff; text-decoration: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; border: none; cursor: pointer; }}
    .btn-secundario {{ background: #21262d; color: var(--text); border: 1px solid var(--border); padding: 6px 12px; border-radius: 6px; cursor: pointer; }}
    .filtros {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
    .btn-modo {{ background: #21262d; color: var(--text); border: 1px solid var(--border); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }}
    .btn-modo.ativo {{ background: var(--blue); color: #0d1117; font-weight: 700; border-color: var(--blue); }}
    .secao-croqui {{ margin-bottom: 32px; }}
    .cabecalho-croqui {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 16px; }}
    .cartao-item {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 14px; }}
    .cabecalho-cartao {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 700; margin-right: 6px; }}
    .badge-adicionado, .badge-novo {{ background: rgba(46,160,67,0.2); color: #3fb950; border: 1px solid #2ea043; }}
    .badge-modificado {{ background: rgba(210,153,34,0.2); color: #e3b341; border: 1px solid #d29922; }}
    .badge-removido {{ background: rgba(248,81,73,0.2); color: #ff7b72; border: 1px solid #f85149; }}
    .badge-neutro {{ background: #21262d; color: var(--muted); padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; margin-left: 6px; }}
    .subtexto {{ color: var(--muted); font-size: 0.85rem; margin-left: 6px; }}
    .container-mapa {{ position: relative; display: inline-block; width: 100%; max-width: 900px; overflow: hidden; border-radius: 8px; border: 1px solid var(--border); }}
    .container-mapa img {{ display: block; width: 100%; height: auto; }}
    .mapa-svg-overlay {{ position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }}
    .container-mapa.mode-antes .camada-depois {{ display: none; }}
    .container-mapa.mode-depois .camada-antes {{ display: none; }}
    .container-mapa.mode-ocultar .mapa-svg-overlay {{ display: none; }}
    .comparador-mapa-imagem.modo-lado-a-lado {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .comparador-mapa-imagem.modo-lado-a-lado .slider-cortina {{ display: none; }}
    .comparador-mapa-imagem.modo-cortina {{ position: relative; max-width: 900px; }}
    .comparador-mapa-imagem.modo-cortina .painel-depois {{ position: absolute; inset: 0; clip-path: inset(0 0 0 50%); }}
    .galeria-antes-depois {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .galeria-antes-depois img, .galeria-unica img {{ max-width: 100%; border-radius: 6px; border: 1px solid var(--border); }}
    .val-antes {{ color: #ff7b72; text-decoration: line-through; }}
    .val-depois {{ color: #3fb950; font-weight: 600; }}
    .diff-markdown {{ background: #090d13; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 0.85rem; }}
    .linha-add {{ display: block; color: #3fb950; background: rgba(46,160,67,0.12); }}
    .linha-rem {{ display: block; color: #ff7b72; background: rgba(248,81,73,0.12); }}
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <div>
        <h1>Prévia da Pull Request #{numero_pr}</h1>
        <p class="subtexto">Commit: <code>{html.escape(commit_curto)}</code> · Escaladas: +{resumo.total_escaladas_adicionadas} / ~{resumo.total_escaladas_modificadas} / -{resumo.total_escaladas_removidas} · Mapas: {resumo.total_mapas_alterados} · Imagens: {resumo.total_imagens_alteradas}</p>
        <div style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
          <span class="codigo-box" id="codigo-pr">{codigo_formatado}</span>
          <button type="button" class="btn-secundario" onclick="navigator.clipboard.writeText('{codigo_formatado}')">Copiar Código</button>
          <a class="btn-acao" href="{html.escape(url_app)}">Abrir no Aplicativo Aresta Climb</a>
        </div>
      </div>
      <div style="text-align: center;">
        {qr_svg}
        <div class="subtexto" style="margin-top: 4px;">Escaneie no celular</div>
      </div>
    </header>

    <nav class="filtros">
      <button type="button" class="btn-modo ativo" onclick="filtrarItens('todos', this)">Todas</button>
      <button type="button" class="btn-modo" onclick="filtrarItens('adicionado', this)">Adicionadas (+{resumo.total_escaladas_adicionadas})</button>
      <button type="button" class="btn-modo" onclick="filtrarItens('modificado', this)">Modificadas (~{resumo.total_escaladas_modificadas})</button>
      <button type="button" class="btn-modo" onclick="filtrarItens('removido', this)">Removidas (-{resumo.total_escaladas_removidas})</button>
      <button type="button" class="btn-modo" onclick="filtrarCategoria('mapa', this)">Mapas ({resumo.total_mapas_alterados})</button>
      <button type="button" class="btn-modo" onclick="filtrarCategoria('imagem', this)">Imagens ({resumo.total_imagens_alteradas})</button>
    </nav>

    {blocos_croquis}
  </div>
  <script>
    function definirModoSvg(idDom, classeModo, btn) {{
      const card = document.getElementById(idDom);
      const container = card.querySelector('.container-mapa');
      container.className = 'container-mapa ' + classeModo;
      card.querySelectorAll('.btn-modo').forEach(b => b.classList.remove('ativo'));
      btn.classList.add('ativo');
    }}
    function alternarVisualizacaoMapaImagem(idDom, modo, btn) {{
      const card = document.getElementById(idDom);
      const comp = card.querySelector('.comparador-mapa-imagem');
      comp.className = 'comparador-mapa-imagem modo-' + modo;
      card.querySelectorAll('.btn-modo').forEach(b => b.classList.remove('ativo'));
      btn.classList.add('ativo');
    }}
    function atualizarCortina(idDom, valor) {{
      const card = document.getElementById(idDom);
      const depois = card.querySelector('.painel-depois');
      depois.style.clipPath = 'inset(0 0 0 ' + valor + '%)';
    }}
    function filtrarItens(status, btn) {{
      document.querySelectorAll('.filtros .btn-modo').forEach(b => b.classList.remove('ativo'));
      btn.classList.add('ativo');
      document.querySelectorAll('.item-filtravel').forEach(el => {{
        el.style.display = (status === 'todos' || el.dataset.status === status) ? '' : 'none';
      }});
    }}
    function filtrarCategoria(cat, btn) {{
      document.querySelectorAll('.filtros .btn-modo').forEach(b => b.classList.remove('ativo'));
      btn.classList.add('ativo');
      document.querySelectorAll('.item-filtravel').forEach(el => {{
        el.style.display = (el.dataset.categoria === cat) ? '' : 'none';
      }});
    }}
  </script>
</body>
</html>"""


def renderizar_comentario_pr_markdown(
    resumo: ResumoDiffPullRequest,
    numero_pr: int,
    url_base_previa: str = "https://previa.arestaclimb.com",
    publicado_no_r2: bool = True,
) -> str:
    """
    Gera o comentário Markdown enxuto da Pull Request contendo a assinatura invisível
    `<!-- aresta-pr-validator -->`, resumo das alterações e links diretos.
    """
    codigo_formatado = gerar_codigo_pull_request(numero_pr)
    link_app = obter_url_previa(codigo_formatado, base_url=url_base_previa)
    link_resumo = obter_url_resumo_previa(codigo_formatado, base_url=url_base_previa)

    nomes_croquis = ", ".join(f"**{c.nome}** (`{c.id_croqui}`)" for c in resumo.croquis)
    linhas = [
        ASSINATURA_COMENTARIO_PR,
        "### ✅ Validação Concluída e Prévia da Pull Request Disponível",
        "",
        f"Croquis analisados: {nomes_croquis}",
        "",
        "| Métrica | Adicionadas | Modificadas | Removidas |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Escaladas** | +{resumo.total_escaladas_adicionadas} | ~{resumo.total_escaladas_modificadas} | -{resumo.total_escaladas_removidas} |",
        f"| **Setores** | +{resumo.total_setores_adicionados} | ~{resumo.total_setores_modificados} | -{resumo.total_setores_removidos} |",
        "",
        f"- 🗺️ **Mapas alterados:** {resumo.total_mapas_alterados} · 🖼️ **Imagens alteradas:** {resumo.total_imagens_alteradas}",
        f"- 🔑 **Código de pareamento no App:** `{codigo_formatado}`",
        f"- 📱 **Abrir direto no App Aresta Climb:** [{link_app}]({link_app})",
        f"- 🔍 **Ver Resumo Visual e Diff Interativo:** [{link_resumo}]({link_resumo})",
    ]
    if not publicado_no_r2:
        linhas.extend(
            [
                "",
                "> ⚠️ **Aviso:** Credenciais do R2 ausentes no ambiente (ex: PR originada de fork externo). A validação estrutural passou, mas os artefatos da prévia não foram enviados ao bucket.",
            ]
        )
    return "\n".join(linhas) + "\n"


def renderizar_comentario_falha_pr_markdown(erros: list[str]) -> str:
    """
    Gera o comentário Markdown de falha na validação da Pull Request mantendo
    a assinatura invisível `<!-- aresta-pr-validator -->`.
    """
    bloco_erros = "\n".join(erros)
    return "\n".join(
        [
            ASSINATURA_COMENTARIO_PR,
            "### ❌ Falha na Validação da Pull Request",
            "",
            "```text",
            bloco_erros,
            "```",
            "",
        ]
    )
