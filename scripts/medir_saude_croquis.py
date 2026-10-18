# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

# Adiciona o diretório raiz do projeto ao sys.path para importar a lib utilitária
sys.path.append(str(Path(__file__).resolve().parent.parent))
from editor.core.serializacao_util import carregar_yaml
from scripts.markdown_frontmatter_lib import parse_md_com_frontmatter

CacheMd = dict[str, tuple[dict[str, Any] | None, str]]

CHAVES_COLUNAS_RELATORIO: tuple[str, ...] = (
    "Nome",
    "Publicado",
    "Revisado Manual",
    "Revisado Circ",
    "Status Desenho",
    "Pontos de Interesse",
    "Thumbnail",
    "Coordenadas Picos",
    "URL Google Maps",
    "Mapas Gerais",
    "Betas Pendentes",
    "croqui.yaml",
    "Conteúdo PDF",
    "partes.json",
    "PDF Original",
)


def _carregar_dados_yaml(
    croqui_path: Path, dados_yaml: dict[str, Any] | None = None
) -> tuple[bool, dict[str, Any] | None, bool]:
    """
    Retorna (existe_arquivo, dados_dict, erro_leitura).
    Se dados_yaml já for fornecido em memória, evita qualquer leitura do disco.
    """
    if dados_yaml is not None:
        return True, dados_yaml, False

    yaml_path = croqui_path / "croqui.yaml"
    if not yaml_path.exists():
        return False, None, False

    try:
        conteudo = yaml_path.read_text(encoding="utf-8")
        data = carregar_yaml(conteudo)
        return True, (data if isinstance(data, dict) else {}), False
    except Exception:
        return True, None, True


def _obter_frontmatter_md(
    md_path: Path,
    croqui_path: Path,
    cache_md: CacheMd | None = None,
) -> dict[str, Any] | None:
    """Obtém o frontmatter de um arquivo Markdown usando cache em memória quando disponível."""
    chave = (
        md_path.relative_to(croqui_path).as_posix()
        if md_path.is_relative_to(croqui_path)
        else md_path.as_posix()
    )
    if cache_md is not None and chave in cache_md:
        return cache_md[chave][0]

    if not md_path.exists():
        return None

    fm, corpo = parse_md_com_frontmatter(md_path)
    if cache_md is not None and fm is not None:
        cache_md[chave] = (fm, corpo)
    return fm


def check_partes_json(croqui_path: Path) -> bool:
    """Verifica se partes.json existe e é um JSON válido."""
    partes_path = croqui_path / "partes.json"
    if not partes_path.exists():
        return False
    try:
        with open(partes_path, encoding="utf-8") as f:
            data = json.load(f)
            return bool(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False


def check_raw_original_pdf(croqui_path: Path) -> bool:
    """Verifica se raw_original_pdf existe e não está vazia."""
    pdf_path = croqui_path / "raw_original_pdf"
    return pdf_path.exists() and pdf_path.is_dir() and any(pdf_path.iterdir())


def check_raw_pdf_contents(croqui_path: Path) -> bool:
    """Verifica se raw_pdf_contents existe e não está vazia."""
    contents_path = croqui_path / "raw_pdf_contents"
    return contents_path.exists() and contents_path.is_dir() and any(contents_path.iterdir())


def check_croqui_yaml(croqui_path: Path) -> bool:
    """Verifica se croqui.yaml existe."""
    return (croqui_path / "croqui.yaml").exists()


def check_caminho_thumbnail(croqui_path: Path, dados_yaml: dict[str, Any] | None = None) -> bool:
    """Verifica se croqui.yaml possui caminho_thumbnail preenchido."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe or erro or not data:
        return False
    return bool(data.get("caminho_thumbnail"))


def check_mapas_gerais_exists(croqui_path: Path, cache_md: CacheMd | None = None) -> bool:
    """Verifica se mapas_gerais.md existe."""
    if cache_md is not None and "mapas_gerais.md" in cache_md:
        return True
    return (croqui_path / "mapas_gerais.md").exists()


def check_publicar_croqui(croqui_path: Path, dados_yaml: dict[str, Any] | None = None) -> bool:
    """Verifica se croqui.yaml possui publicar_croqui: true."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe or erro or not data:
        return False
    return data.get("publicar_croqui") is True


def check_revisado_manualmente(croqui_path: Path, dados_yaml: dict[str, Any] | None = None) -> bool:
    """Verifica se croqui.yaml possui revisado_manualmente: true."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe or erro or not data:
        return False
    return data.get("revisado_manualmente") is True


def check_revisado_bounding_circle(
    croqui_path: Path, dados_yaml: dict[str, Any] | None = None
) -> bool:
    """Verifica se croqui.yaml possui revisado_bounding_circle: true."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe or erro or not data:
        return False
    return data.get("revisado_bounding_circle") is True


def check_status_desenho_extraivel(
    croqui_path: Path, dados_yaml: dict[str, Any] | None = None
) -> str:
    """Verifica o status de desenhos extraíveis no croqui.yaml."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe or erro or not data:
        return "❌"
    status = data.get("status_desenho_extraivel")
    if status == "NAO_TEM_DESENHO":
        return "✅ (não)"
    if status == "TEM_DESENHO_MAS_NAO_EXTRAIDO":
        return "⚠️"
    if status == "DESENHO_EXTRAIDO":
        return "✅"
    return "❌"


def check_pico_coordinates(croqui_path: Path, dados_yaml: dict[str, Any] | None = None) -> str:
    """Verifica se os picos possuem coordenadas geográficas (latitude/longitude)."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe:
        return "N/A"
    if erro or data is None:
        return "❌ (Erro)"
    picos = data.get("picos", [])
    if not picos or not isinstance(picos, list):
        return "N/A"

    passaram = 0
    total = len(picos)
    for pico in picos:
        loc = pico.get("localizacao") if isinstance(pico, dict) else None
        if (
            loc
            and isinstance(loc, dict)
            and loc.get("latitude") is not None
            and loc.get("longitude") is not None
        ):
            passaram += 1

    if passaram == total:
        return f"✅ ({passaram}/{total})"
    if passaram > 0:
        return f"⚠️ ({passaram}/{total})"
    return f"❌ (0/{total})"


def checar_url_google_maps(croqui_path: Path, dados_yaml: dict[str, Any] | None = None) -> str:
    """Verifica se os picos possuem link para o Google Maps preenchido."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe:
        return "N/A"
    if erro or data is None:
        return "❌ (Erro)"
    picos = data.get("picos", [])
    if not picos or not isinstance(picos, list):
        return "N/A"

    passaram = 0
    total = len(picos)
    for pico in picos:
        if isinstance(pico, dict):
            url = pico.get("url_google_maps")
            if url and isinstance(url, str) and url.strip():
                passaram += 1

    if passaram == total:
        return f"✅ ({passaram}/{total})"
    if passaram > 0:
        return f"⚠️ ({passaram}/{total})"
    return f"❌ (0/{total})"


# Alias em inglês para compatibilidade
check_url_google_maps = checar_url_google_maps


def find_all_sectors(
    croqui_path: Path,
    dados_yaml: dict[str, Any] | None = None,
    cache_md: CacheMd | None = None,
) -> list[Path]:
    """Encontra recursivamente todos os caminhos de setores definidos no croqui.yaml."""
    existe, data, erro = _carregar_dados_yaml(croqui_path, dados_yaml)
    if not existe or erro or not data:
        return sorted(croqui_path.glob("setor_*.md"))

    sector_paths: list[Path] = []

    def collect_recursively(elements: list[Any]) -> None:
        for e in elements:
            if not e or not isinstance(e, dict):
                continue
            tipo = "setor" if "setor" in e else "grupo"
            obj = e.get(tipo)
            if not obj:
                continue

            if isinstance(obj, str):
                p = croqui_path / obj
                if p.suffix == ".md" and p not in sector_paths:
                    sector_paths.append(p)
                continue

            if not isinstance(obj, dict):
                continue

            if "caminho" in obj:
                p = croqui_path / obj["caminho"]
                if p.suffix == ".md" and p not in sector_paths:
                    sector_paths.append(p)

                if tipo == "grupo":
                    fm = _obter_frontmatter_md(p, croqui_path, cache_md)
                    if fm:
                        filhos = fm.get("setores") or fm.get("sub_setores")
                        if filhos:
                            collect_recursively(
                                [{"setor": s} if isinstance(s, (str, dict)) else s for s in filhos]
                            )

            conteudo = obj.get("conteudo")
            if conteudo and isinstance(conteudo, dict):
                sub = conteudo.get("setores") or conteudo.get("sub_setores")
                if sub:
                    collect_recursively(
                        [{"setor": s} if isinstance(s, (str, dict)) else s for s in sub if s]
                    )

    picos = data.get("picos", [])
    if isinstance(picos, list):
        for pico in picos:
            if isinstance(pico, dict) and "setores_ou_grupos" in pico:
                collect_recursively(pico["setores_ou_grupos"])

    if not sector_paths:
        return sorted(croqui_path.glob("setor_*.md"))

    return sorted(sector_paths)


def check_pontos_de_interesse(
    croqui_path: Path,
    dados_yaml: dict[str, Any] | None = None,
    cache_md: CacheMd | None = None,
) -> str:
    """Verifica pontos de interesse nos arquivos de setor encontrados recursivamente."""
    cache_local = cache_md if cache_md is not None else {}
    setores = find_all_sectors(croqui_path, dados_yaml=dados_yaml, cache_md=cache_local)
    if not setores:
        return "N/A"

    passaram = 0
    total = len(setores)

    for setor_path in setores:
        frontmatter = _obter_frontmatter_md(setor_path, croqui_path, cache_local)
        if frontmatter and "mapas" in frontmatter:
            tem_ponto = any(
                isinstance(mapa, dict)
                and isinstance(mapa.get("pontos_de_interesse"), list)
                and len(mapa["pontos_de_interesse"]) > 0
                for mapa in frontmatter["mapas"]
            )
            if tem_ponto:
                passaram += 1

    if passaram == total and total > 0:
        return f"✅ ({passaram}/{total})"
    if passaram > 0:
        return f"⚠️ ({passaram}/{total})"
    return f"❌ (0/{total})"


def check_betas_pendentes(croqui_path: Path) -> str:
    """
    Verifica se o croqui possui betas pendentes de curadoria (betas_pendentes.binarypb).
    Ter pendências é considerado não saudável (⚠️).
    """
    staging_file = croqui_path / "betas_pendentes.binarypb"
    if not staging_file.exists():
        return "✅"

    try:
        from coleta_de_betas.inteligencia.avaliador import carregar_betas_pendentes

        pendentes = carregar_betas_pendentes(staging_file)
        total = sum(len(e.candidatos) for e in pendentes.candidatos_por_escalada)
        if total > 0:
            return f"⚠️ ({total})"
    except Exception:
        pass
    return "⚠️"


def avaliar_saude_croqui(
    croqui_path: Path,
    dados_yaml: dict[str, Any] | None = None,
    cache_md: CacheMd | None = None,
) -> dict[str, Any]:
    """
    Avalia todas as métricas de saúde de um croqui realizando no máximo 1 parse
    de croqui.yaml e 1 parse por arquivo .md (ou zero se dados_yaml e cache_md
    já forem fornecidos em memória).
    """
    nome = croqui_path.name
    existe_yaml, dados_carregados, erro_yaml = _carregar_dados_yaml(croqui_path, dados_yaml)
    cache_local: CacheMd = cache_md if cache_md is not None else {}

    if not existe_yaml:
        publicado = "❌"
        revisado = "❌"
        revisado_circ = "❌"
        yaml_present = "❌"
        thumbnail = "❌"
        coord_picos = "N/A"
        url_maps = "N/A"
        status_desenho = "❌"
        pontos = check_pontos_de_interesse(croqui_path, dados_yaml=None, cache_md=cache_local)
    elif erro_yaml or dados_carregados is None:
        publicado = "❌"
        revisado = "❌"
        revisado_circ = "❌"
        yaml_present = "✅"
        thumbnail = "❌"
        coord_picos = "❌ (Erro)"
        url_maps = "❌ (Erro)"
        status_desenho = "❌"
        pontos = check_pontos_de_interesse(croqui_path, dados_yaml=None, cache_md=cache_local)
    else:
        publicado = "✅" if check_publicar_croqui(croqui_path, dados_carregados) else "❌"
        revisado = "✅" if check_revisado_manualmente(croqui_path, dados_carregados) else "❌"
        revisado_circ = (
            "✅" if check_revisado_bounding_circle(croqui_path, dados_carregados) else "❌"
        )
        yaml_present = "✅"
        thumbnail = "✅" if check_caminho_thumbnail(croqui_path, dados_carregados) else "❌"
        coord_picos = check_pico_coordinates(croqui_path, dados_carregados)
        url_maps = checar_url_google_maps(croqui_path, dados_carregados)
        status_desenho = check_status_desenho_extraivel(croqui_path, dados_carregados)
        pontos = check_pontos_de_interesse(
            croqui_path, dados_yaml=dados_carregados, cache_md=cache_local
        )

    partes = "✅" if check_partes_json(croqui_path) else "❌"
    raw_pdf = "✅" if check_raw_original_pdf(croqui_path) else "❌"
    raw_contents = "✅" if check_raw_pdf_contents(croqui_path) else "❌"
    mapas_gerais = "✅" if check_mapas_gerais_exists(croqui_path, cache_md=cache_local) else "❌"
    betas_status = check_betas_pendentes(croqui_path)

    return {
        "Nome": nome,
        "Publicado": publicado,
        "Revisado Manual": revisado,
        "Revisado Circ": revisado_circ,
        "Status Desenho": status_desenho,
        "Pontos de Interesse": pontos,
        "Thumbnail": thumbnail,
        "Coordenadas Picos": coord_picos,
        "URL Google Maps": url_maps,
        "Mapas Gerais": mapas_gerais,
        "Betas Pendentes": betas_status,
        "croqui.yaml": yaml_present,
        "Conteúdo PDF": raw_contents,
        "partes.json": partes,
        "PDF Original": raw_pdf,
    }


def extrair_dados_tabela_markdown(texto_markdown: str) -> list[dict[str, Any]]:
    """
    Extrai os dicionários de linhas a partir de uma tabela Markdown gerada anteriormente
    em STATUS_CROQUIS.md, permitindo atualização incremental em memória.
    """
    linhas_dados: list[dict[str, Any]] = []
    for linha in texto_markdown.replace("\r\n", "\n").splitlines():
        linha_limpa = linha.strip()
        if not linha_limpa.startswith("|") or not linha_limpa.endswith("|"):
            continue
        colunas = [c.strip() for c in linha_limpa.strip("|").split("|")]
        if len(colunas) != len(CHAVES_COLUNAS_RELATORIO):
            continue
        if colunas[0] == "Croqui" or set(colunas[0]) <= {"-"}:
            continue
        linhas_dados.append(dict(zip(CHAVES_COLUNAS_RELATORIO, colunas, strict=True)))
    return linhas_dados


def generate_report_table(report_data: list[dict[str, Any]]) -> str:
    """Gera a tabela Markdown a partir dos dados do relatório."""
    total_croquis = len(report_data)
    if total_croquis == 0:
        return ""

    a_publicados = sum(1 for d in report_data if d["Publicado"] == "✅")
    a_revisados = sum(1 for d in report_data if d["Revisado Manual"] == "✅")
    a_revisados_circ = sum(1 for d in report_data if d["Revisado Circ"] == "✅")
    a_pontos = sum(1 for d in report_data if "✅" in d["Pontos de Interesse"])
    a_thumbnail = sum(1 for d in report_data if d["Thumbnail"] == "✅")
    a_coord_picos = sum(1 for d in report_data if "✅" in d["Coordenadas Picos"])
    a_url_google_maps = sum(1 for d in report_data if "✅" in d.get("URL Google Maps", ""))
    a_mapas_gerais = sum(1 for d in report_data if d["Mapas Gerais"] == "✅")
    a_croqui_yaml = sum(1 for d in report_data if d["croqui.yaml"] == "✅")
    a_raw_pdf_contents = sum(1 for d in report_data if d["Conteúdo PDF"] == "✅")
    a_partes_json = sum(1 for d in report_data if d["partes.json"] == "✅")
    a_raw_original_pdf = sum(1 for d in report_data if d["PDF Original"] == "✅")
    a_betas_pendentes = sum(1 for d in report_data if d.get("Betas Pendentes") == "✅")

    c_nao_tem = sum(1 for d in report_data if d["Status Desenho"] == "✅ (não)")
    c_sim_extraido = sum(1 for d in report_data if d["Status Desenho"] == "✅")
    c_sim_mas_nao = sum(1 for d in report_data if d["Status Desenho"] == "⚠️")
    c_unknown = sum(1 for d in report_data if d["Status Desenho"] == "❌")
    a_status_desenho = c_nao_tem + c_sim_extraido

    headers = [
        "Croqui",
        f"Publicado ({a_publicados}/{total_croquis})",
        f"Revisado Manual ({a_revisados}/{total_croquis})",
        f"Revisado Circ ({a_revisados_circ}/{total_croquis})",
        f"Desenho Extraível ({a_status_desenho}/{c_sim_mas_nao}/{c_unknown})",
        f"Pontos de Interesse ({a_pontos}/{total_croquis})",
        f"Thumbnail ({a_thumbnail}/{total_croquis})",
        f"Coordenadas Picos ({a_coord_picos}/{total_croquis})",
        f"URL Google Maps ({a_url_google_maps}/{total_croquis})",
        f"Mapas Gerais ({a_mapas_gerais}/{total_croquis})",
        f"Betas Pendentes ({a_betas_pendentes}/{total_croquis})",
        f"croqui.yaml ({a_croqui_yaml}/{total_croquis})",
        f"Conteúdo PDF ({a_raw_pdf_contents}/{total_croquis})",
        f"partes.json ({a_partes_json}/{total_croquis})",
        f"PDF Original ({a_raw_original_pdf}/{total_croquis})",
    ]

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for data in report_data:
        row = [
            data["Nome"],
            data["Publicado"],
            data["Revisado Manual"],
            data["Revisado Circ"],
            data["Status Desenho"],
            data["Pontos de Interesse"],
            data["Thumbnail"],
            data["Coordenadas Picos"],
            data.get("URL Google Maps", "N/A"),
            data["Mapas Gerais"],
            data["Betas Pendentes"],
            data["croqui.yaml"],
            data["Conteúdo PDF"],
            data["partes.json"],
            data["PDF Original"],
        ]
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def salvar_relatorio_saude_se_modificado(
    caminho_saida: Path,
    tabela_markdown: str,
    agora: datetime | None = None,
) -> bool:
    """
    Salva o relatório STATUS_CROQUIS.md em LF apenas se a tabela gerada diferir
    da tabela já existente no arquivo, evitando alterações espúrias de timestamp.
    """
    tabela_lf = tabela_markdown.replace("\r\n", "\n").strip()

    if caminho_saida.exists():
        bytes_atuais = caminho_saida.read_bytes()
        texto_atual = bytes_atuais.decode("utf-8", errors="ignore").replace("\r\n", "\n")
        idx_tabela = texto_atual.find("\n| ")
        if idx_tabela != -1:
            tabela_atual = texto_atual[idx_tabela + 1 :].strip()
            if tabela_atual == tabela_lf and b"\r\n" not in bytes_atuais:
                return False

    instante = agora or datetime.now()
    conteudo_novo = (
        "# Estado de Saúde dos Croquis\n\n"
        f"Relatório gerado em: {instante.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        f"{tabela_lf}"
    )
    with open(caminho_saida, "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo_novo)
    return True


def _desempacotar_dados_memoria(
    nome: str,
    dados_em_memoria: Mapping[str, tuple[dict[str, Any], CacheMd | None] | dict[str, Any]] | None,
) -> tuple[dict[str, Any] | None, CacheMd | None]:
    if not dados_em_memoria or nome not in dados_em_memoria:
        return None, None
    item = dados_em_memoria[nome]
    if isinstance(item, tuple):
        return item[0], item[1]
    return item, None


def atualizar_relatorio_saude_croquis(
    base_path: Path | None = None,
    output_path: Path | None = None,
    alvos: Sequence[str | Path] | None = None,
    dados_em_memoria: (
        Mapping[str, tuple[dict[str, Any], CacheMd | None] | dict[str, Any]] | None
    ) = None,
    agora: datetime | None = None,
) -> bool:
    """
    Avalia a saúde dos croquis e atualiza STATUS_CROQUIS.md em memória.
    Quando `alvos` é informado e `output_path` já existe, atualiza apenas as linhas
    dos croquis alvo e recalcula os totais do cabeçalho sem reler os demais croquis.
    """
    root_path = Path(__file__).resolve().parent.parent
    pasta_base = base_path or (root_path / "database")
    caminho_saida = output_path or (root_path / "STATUS_CROQUIS.md")

    linhas_existentes: list[dict[str, Any]] = []
    if alvos and caminho_saida.is_file():
        linhas_existentes = extrair_dados_tabela_markdown(
            caminho_saida.read_text(encoding="utf-8", errors="ignore")
        )

    if alvos and linhas_existentes:
        mapa_linhas = {linha["Nome"]: linha for linha in linhas_existentes}
        for alvo in alvos:
            alvo_path = Path(alvo)
            nome_alvo = alvo_path.name
            dir_croqui = alvo_path if alvo_path.is_dir() else (pasta_base / nome_alvo)
            dyaml, cmd = _desempacotar_dados_memoria(nome_alvo, dados_em_memoria)
            if dir_croqui.is_dir() or dyaml is not None:
                mapa_linhas[nome_alvo] = avaliar_saude_croqui(
                    dir_croqui, dados_yaml=dyaml, cache_md=cmd
                )
            else:
                mapa_linhas.pop(nome_alvo, None)
        report_data = [mapa_linhas[k] for k in sorted(mapa_linhas)]
    else:
        if not pasta_base.exists():
            print(f"Erro: Pasta database não encontrada em {pasta_base}")
            return False
        croquis = sorted([d for d in pasta_base.iterdir() if d.is_dir()])
        report_data = []
        for croqui in croquis:
            dyaml, cmd = _desempacotar_dados_memoria(croqui.name, dados_em_memoria)
            report_data.append(avaliar_saude_croqui(croqui, dados_yaml=dyaml, cache_md=cmd))

    markdown_output = generate_report_table(report_data)
    modificado = salvar_relatorio_saude_se_modificado(caminho_saida, markdown_output, agora=agora)
    if modificado:
        print(f"Relatório gerado com sucesso em: {caminho_saida}")
    else:
        print(f"Relatório sem alterações em: {caminho_saida}")
    return modificado


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Mede a saúde dos croquis na base de dados.")
    parser.add_argument(
        "--output",
        "-o",
        default="STATUS_CROQUIS.md",
        help="Arquivo de saída do relatório Markdown.",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Diretório base dos croquis (padrão: database/).",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        default=None,
        help="Croquis específicos para atualização incremental.",
    )
    args = parser.parse_args(argv)

    root_path = Path(__file__).resolve().parent.parent
    output_path = Path(args.output)
    base_path = Path(args.base_dir) if args.base_dir else (root_path / "database")

    atualizar_relatorio_saude_croquis(
        base_path=base_path,
        output_path=output_path,
        alvos=args.target,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
