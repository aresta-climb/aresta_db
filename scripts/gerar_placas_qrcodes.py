# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Script de linha de comando (CLI) para geração de placas físicas e QR Codes do Aresta Climb.

Permite gerar placas individuais para um pico, setor ou via específica, ou gerar em lote
todas as placas para um pico a partir do compilado Protobuf ou do banco YAML.
"""

import argparse
from pathlib import Path
import sys

_RAIZ = str(Path(__file__).resolve().parent.parent)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)  # pragma: no cover

from scripts.gerar_placas_qrcodes_lib import (
    exportar_placas_pico,
    gerar_placa_png,
    gerar_placa_svg,
    montar_url_deep_link,
    obter_logo_aresta_padrao,
    obter_logo_topo_padrao,
    slugify,
)



def criar_analisador_argumentos() -> argparse.ArgumentParser:
    """Cria e configura o analisador de argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        prog="gerar_placas_qrcodes",
        description="Geração de placas físicas e QR Codes para sinalização do Aresta Climb.",
    )

    # Modo Lote
    grupo_lote = parser.add_argument_group("Modo Lote (Pico Inteiro)")
    grupo_lote.add_argument(
        "--lote-pico",
        dest="lote_pico",
        type=str,
        help="ID do pico para gerar placas em lote (ex: br_mg_igarape_pedra_grande).",
    )
    grupo_lote.add_argument(
        "--incluir-vias",
        dest="incluir_vias",
        action="store_true",
        help="Inclui placas individuais para cada via do setor além dos setores.",
    )
    grupo_lote.add_argument(
        "--limite",
        dest="limite",
        type=int,
        default=None,
        help="Número máximo de placas a gerar em lote.",
    )

    # Modo Individual
    grupo_indiv = parser.add_argument_group("Modo Individual (Placa Única)")
    grupo_indiv.add_argument(
        "--pico",
        dest="pico",
        type=str,
        help="ID do pico (ex: br_mg_igarape_pedra_grande).",
    )
    grupo_indiv.add_argument(
        "--grupo",
        dest="grupo",
        type=str,
        default=None,
        help="Slug ou nome do grupo de setores (ex: grupo_estacionamento).",
    )
    grupo_indiv.add_argument(
        "--setor",
        dest="setor",
        type=str,
        default=None,
        help="Slug ou nome do setor (ex: savassinha).",
    )
    grupo_indiv.add_argument(
        "--via",
        dest="via",
        type=str,
        default=None,
        help="Slug ou nome da via (ex: teto_da_aresta).",
    )
    grupo_indiv.add_argument(
        "--titulo",
        dest="titulo",
        type=str,
        default=None,
        help="Título da placa (padrão: nome derivado do setor ou via).",
    )
    grupo_indiv.add_argument(
        "--subtitulo",
        dest="subtitulo",
        type=str,
        default=None,
        help="Subtítulo da placa (padrão: nome do pico/setor).",
    )

    # Configurações Comuns
    parser.add_argument(
        "--saida",
        "-o",
        dest="saida",
        type=str,
        default="output/placas",
        help="Diretório de saída para salvar os arquivos gerados (padrão: output/placas).",
    )
    parser.add_argument(
        "--dpi",
        dest="dpi",
        type=int,
        default=600,
        help="Resolução em DPI da placa PNG A4 (padrão: 600 DPI).",
    )
    parser.add_argument(
        "--svg",
        dest="svg",
        action="store_true",
        help="Gera também arquivos vetoriais SVG (por padrão gera apenas PNG A4 600 DPI).",
    )
    parser.add_argument(
        "--pdf",
        dest="pdf",
        action="store_true",
        help="Gera também arquivos em formato PDF A4 em alta resolução (600 DPI).",
    )
    parser.add_argument(
        "--apenas-svg",
        dest="apenas_svg",
        action="store_true",
        help="Gera exclusivamente arquivos vetoriais SVG.",
    )
    parser.add_argument(
        "--largura",
        dest="largura",
        type=int,
        default=4960,
        help="Largura da placa em pixels (padrão A4 a 600 DPI: 4960).",
    )
    parser.add_argument(
        "--altura",
        dest="altura",
        type=int,
        default=7016,
        help="Altura da placa em pixels (padrão A4 a 600 DPI: 7016).",
    )
    parser.add_argument(
        "--logo",
        dest="logo",
        type=str,
        default=None,
        help="Caminho alternativo para a imagem de logo central no QR Code.",
    )
    parser.add_argument(
        "--logo-topo",
        dest="logo_topo",
        type=str,
        default=None,
        help="Caminho para imagem ou PDF do logo institucional a ser inserido no topo da placa (ex: logo_igarameca.pdf).",
    )
    parser.add_argument(
        "--logo-aresta",
        dest="logo_aresta",
        type=str,
        default=None,
        help="Caminho para imagem da logo do Aresta Climb no cabeçalho (padrão: logo_splash.png).",
    )
    parser.add_argument(
        "--cor-borda-logo",
        dest="cor_borda_logo",
        type=str,
        default="preta",
        help="Cor da borda ao redor do badge da logo central no QR Code (padrão: preta).",
    )
    parser.add_argument(
        "--host",
        dest="host",
        type=str,
        default="app.arestaclimb.com",
        help="Domínio oficial do deep link (padrão: app.arestaclimb.com).",
    )
    parser.add_argument(
        "--utm-source",
        dest="utm_source",
        type=str,
        default="setor_igarameca",
        help="Parâmetro utm_source para rastreamento no QR Code (padrão: setor_igarameca).",
    )
    parser.add_argument(
        "--utm-medium",
        dest="utm_medium",
        type=str,
        default="qrcode",
        help="Parâmetro utm_medium para rastreamento no QR Code (padrão: qrcode).",
    )
    parser.add_argument(
        "--utm-campaign",
        dest="utm_campaign",
        type=str,
        default=None,
        help="Parâmetro utm_campaign opcional para rastreamento no QR Code.",
    )
    parser.add_argument(
        "--raiz-projeto",
        dest="raiz_projeto",
        type=str,
        default=None,
        help="Caminho alternativo para a raiz do projeto (contendo generated/ ou database/).",
    )

    return parser


def main(argumentos: list[str] | None = None) -> int:
    """Ponto de entrada principal do utilitário CLI."""
    analisador = criar_analisador_argumentos()
    args = analisador.parse_args(argumentos)

    if not args.lote_pico and not args.pico:
        sys.stderr.write(
            "Erro: você deve informar ao menos --pico (para placa única) ou --lote-pico (para lote).\n"
        )
        return 1

    diretorio_saida = Path(args.saida)
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    raiz_projeto = Path(args.raiz_projeto) if args.raiz_projeto else None

    caminho_logo = Path(args.logo) if args.logo else None
    caminho_logo_topo = (
        Path(args.logo_topo)
        if args.logo_topo
        else obter_logo_topo_padrao(args.lote_pico or args.pico, raiz_projeto=raiz_projeto)
    )
    caminho_logo_aresta = (
        Path(args.logo_aresta)
        if args.logo_aresta
        else obter_logo_aresta_padrao(raiz_projeto=raiz_projeto)
    )
    gerar_svg = bool(args.svg or args.apenas_svg)

    # Modo Lote
    if args.lote_pico:
        print(f"Iniciando geração em lote para o pico '{args.lote_pico}'...")
        arquivos = exportar_placas_pico(
            pico_id=args.lote_pico,
            diretorio_saida=diretorio_saida,
            raiz_projeto=raiz_projeto,
            incluir_vias=args.incluir_vias,
            caminho_logo=caminho_logo,
            caminho_logo_topo=caminho_logo_topo,
            caminho_logo_aresta=caminho_logo_aresta,
            limite_itens=args.limite,
            largura=args.largura,
            altura=args.altura,
            dpi=args.dpi,
            gerar_svg=gerar_svg,
            gerar_pdf=bool(args.pdf),
            cor_borda_logo=args.cor_borda_logo,
            utm_source=args.utm_source,
            utm_medium=args.utm_medium,
            utm_campaign=args.utm_campaign,
        )
        print(
            f"Exportação em lote concluída: {len(arquivos)} placas geradas em {diretorio_saida}."
        )
        return 0

    # Modo Individual
    url = montar_url_deep_link(
        pico=args.pico,
        grupo=args.grupo,
        setor=args.setor,
        via=args.via,
        host=args.host,
        utm_source=args.utm_source,
        utm_medium=args.utm_medium,
        utm_campaign=args.utm_campaign,
    )

    # Constrói título e subtítulo amigáveis se não fornecidos
    titulo = args.titulo
    if not titulo:
        if args.via:
            titulo = args.via.replace("_", " ").title()
        elif args.setor:
            titulo = f"Setor {args.setor.replace('_', ' ').title()}"
        elif args.grupo:
            titulo = args.grupo.replace("_", " ").title()
        else:
            titulo = args.pico.replace("_", " ").title()

    subtitulo = args.subtitulo
    if not subtitulo:
        if args.via:
            subtitulo = f"{args.setor or args.pico} · Aresta Climb"
        elif args.setor:
            subtitulo = f"{args.pico.replace('_', ' ').title()} · Setor"
        else:
            subtitulo = "Croqui Oficial · Aresta Climb"

    slug_base = (
        slugify(args.via)
        if args.via
        else slugify(args.setor)
        if args.setor
        else slugify(args.grupo)
        if args.grupo
        else slugify(args.pico)
    )
    nome_base = f"placa_{slug_base}"

    img = None
    if not args.apenas_svg:
        caminho_png = diretorio_saida / f"{nome_base}.png"
        img = gerar_placa_png(
            url=url,
            titulo=titulo,
            subtitulo=subtitulo,
            caminho_logo=caminho_logo,
            caminho_logo_topo=caminho_logo_topo,
            caminho_logo_aresta=caminho_logo_aresta,
            largura=args.largura,
            altura=args.altura,
            cor_borda_logo=args.cor_borda_logo,
        )
        img.save(caminho_png, "PNG", dpi=(args.dpi, args.dpi))
        print(f"PNG gerado (A4 {args.dpi} DPI): {caminho_png}")

        if args.pdf:
            caminho_pdf = diretorio_saida / f"{nome_base}.pdf"
            img.convert("RGB").save(caminho_pdf, "PDF", resolution=float(args.dpi))
            print(f"PDF gerado (A4 {args.dpi} DPI): {caminho_pdf}")

    if gerar_svg:
        caminho_svg = diretorio_saida / f"{nome_base}.svg"
        conteudo_svg = gerar_placa_svg(
            url=url,
            titulo=titulo,
            subtitulo=subtitulo,
            caminho_logo=caminho_logo,
            caminho_logo_topo=caminho_logo_topo,
            caminho_logo_aresta=caminho_logo_aresta,
            largura=args.largura,
            altura=args.altura,
            cor_borda_logo=args.cor_borda_logo,
        )
        caminho_svg.write_text(conteudo_svg, encoding="utf-8")
        print(f"SVG gerado: {caminho_svg}")

    print(f"Placa individual gerada com sucesso para '{url}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover

