# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Gera o relatório STATUS_CROQUIS.md como dump direto do Painel de Qualidade."""

import argparse
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

# Adiciona o diretório raiz do projeto ao sys.path para importar a lib utilitária
sys.path.append(str(Path(__file__).resolve().parent.parent))
from editor.core.avaliador_nota_qualidade import (
    ResumoEtapaQualidade,
    TarefaQualidade,
    avaliar_nota_qualidade_croqui,
)
from editor.core.serializacao_util import carregar_yaml

CacheMd = dict[str, tuple[dict[str, Any] | None, str]]

COLUNAS_TAREFAS_PAINEL: tuple[tuple[str, str], ...] = (
    ("etapa1_identidade_capa", "1.1 Identidade e Capa"),
    ("etapa1_localizacao_picos", "1.2 Localização e Maps"),
    ("etapa1_instrucoes_acesso", "1.3 Instruções Acesso"),
    ("etapa1_mapa_geral", "1.4 Mapa Geral"),
    ("etapa1_setores_com_mapa", "1.5 Mapas Setores"),
    ("etapa1_escaladas_no_mapa", "1.6 Escaladas no Mapa"),
    ("etapa1_grau_dificuldade", "1.7 Grau Dificuldade"),
    ("etapa1_malha_estrada_picos", "1.8 Malha Estrada"),
    ("etapa2_coordenadas_setores", "2.1 Coords Setores"),
    ("etapa2_trilhas_aproximacao", "2.2 Trilhas"),
    ("etapa2_extensao_protecoes_vias", "2.3 Extensão/Proteções"),
    ("etapa2_tracados_vetoriais", "2.4 Traçados Vetoriais"),
    ("etapa2_destaques_setores", "2.5 Destaques"),
    ("etapa2_descricoes_escaladas", "2.6 Descrições Vias"),
    ("etapa2_fotos_capa_setores", "2.7 Fotos Capa Setores"),
    ("etapa2_videos_betas", "2.8 Vídeos Beta"),
    ("etapa3_creditos", "3.1 Créditos"),
    ("etapa3_conquistadores_datas", "3.2 Conquistadores/Datas"),
    ("etapa3_tipo_parede_exposicao", "3.3 Parede/Exposição"),
    ("etapa3_indicadores_familia_celular", "3.4 Sinal/Família"),
    ("etapa3_associacao_pix", "3.5 Associação/Pix"),
    ("etapa3_revisao_final", "3.6 Revisão Final"),
)

CHAVES_COLUNAS_RELATORIO: tuple[str, ...] = (
    "Nome",
    "Publicado",
    "Pronto Publicar",
    "Nota Qualidade",
    "Etapa 1",
    "Etapa 2",
    "Etapa 3",
    *(nome_coluna for _, nome_coluna in COLUNAS_TAREFAS_PAINEL),
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


def _formatar_etapa(etapa: ResumoEtapaQualidade) -> str:
    icone = "✅" if etapa.concluida else ("⚠️" if etapa.pontos_obtidos > 0 else "❌")
    return (
        f"{icone} {etapa.pontos_obtidos}/{etapa.pontos_maximos} "
        f"({etapa.tarefas_concluidas}/{etapa.total_tarefas})"
    )


def _formatar_tarefa(tarefa: TarefaQualidade) -> str:
    icone = "✅" if tarefa.concluida else ("⚠️" if tarefa.pontos_obtidos > 0 else "❌")
    return f"{icone} ({tarefa.progresso_atual}/{tarefa.progresso_total})"


def avaliar_saude_croqui(
    croqui_path: Path,
    dados_yaml: dict[str, Any] | None = None,
    cache_md: CacheMd | None = None,
) -> dict[str, Any]:
    """
    Avalia a saúde de um croqui espelhando diretamente o Painel de Qualidade
    (`avaliar_nota_qualidade_croqui`), realizando no máximo 1 parse de `croqui.yaml`
    e 1 parse por arquivo `.md` (ou zero quando `dados_yaml` e `cache_md` já estão em memória).
    """
    nome = croqui_path.name
    existe_yaml, dados_carregados, erro_yaml = _carregar_dados_yaml(croqui_path, dados_yaml)
    cache_local: CacheMd = cache_md if cache_md is not None else {}

    if not existe_yaml or erro_yaml or dados_carregados is None:
        publicado = "❌"
        avaliacao = avaliar_nota_qualidade_croqui({}, croqui_path=None, cache_md={})
    else:
        publicado = "✅" if dados_carregados.get("publicar_croqui") is True else "❌"
        avaliacao = avaliar_nota_qualidade_croqui(
            dados_carregados,
            croqui_path=croqui_path,
            cache_md=cache_local,
        )

    mapa_tarefas: dict[str, TarefaQualidade] = {
        t.id_tarefa: t for etapa in avaliacao.etapas for t in etapa.tarefas
    }

    linha: dict[str, Any] = {
        "Nome": nome,
        "Publicado": publicado,
        "Pronto Publicar": "✅" if avaliacao.pronto_para_publicar else "❌",
        "Nota Qualidade": str(avaliacao.nota_qualidade),
        "Etapa 1": _formatar_etapa(avaliacao.etapas[0]),
        "Etapa 2": _formatar_etapa(avaliacao.etapas[1]),
        "Etapa 3": _formatar_etapa(avaliacao.etapas[2]),
    }

    for id_tarefa, nome_coluna in COLUNAS_TAREFAS_PAINEL:
        linha[nome_coluna] = _formatar_tarefa(mapa_tarefas[id_tarefa])

    return linha


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
    """Gera a tabela Markdown a partir dos dados do relatório do Painel de Qualidade."""
    total_croquis = len(report_data)
    if total_croquis == 0:
        return ""

    a_publicados = sum(1 for d in report_data if d["Publicado"] == "✅")
    a_prontos = sum(1 for d in report_data if d.get("Pronto Publicar") == "✅")
    a_etapa1 = sum(1 for d in report_data if str(d.get("Etapa 1", "")).startswith("✅"))
    a_etapa2 = sum(1 for d in report_data if str(d.get("Etapa 2", "")).startswith("✅"))
    a_etapa3 = sum(1 for d in report_data if str(d.get("Etapa 3", "")).startswith("✅"))

    headers = [
        "Croqui",
        f"Publicado ({a_publicados}/{total_croquis})",
        f"Pronto Publicar ({a_prontos}/{total_croquis})",
        "Nota Qualidade (máx 8860)",
        f"Etapa 1 ({a_etapa1}/{total_croquis})",
        f"Etapa 2 ({a_etapa2}/{total_croquis})",
        f"Etapa 3 ({a_etapa3}/{total_croquis})",
    ]

    for _, nome_coluna in COLUNAS_TAREFAS_PAINEL:
        concluidas = sum(1 for d in report_data if str(d.get(nome_coluna, "")).startswith("✅"))
        headers.append(f"{nome_coluna} ({concluidas}/{total_croquis})")

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    for data in report_data:
        row = [str(data.get(chave, "")) for chave in CHAVES_COLUNAS_RELATORIO]
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
