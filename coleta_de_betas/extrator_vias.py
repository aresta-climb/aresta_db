# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import sys
import argparse
from pathlib import Path
from typing import List, Union
import yaml
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.io_yaml import salvar_vias_extraidas_yaml


def _ler_frontmatter_md(caminho_md: Path) -> dict:
    """Lê o frontmatter YAML de um arquivo markdown."""
    try:
        texto = caminho_md.read_text(encoding="utf-8")
    except Exception:
        return {}

    partes = texto.split("---")
    if len(partes) >= 3:
        try:
            return yaml.safe_load(partes[1]) or {}
        except Exception:
            return {}
    return {}


def extrair_vias_de_croqui(caminho_croqui_dir: Union[Path, str]) -> beta_pb2.ViasExtraidasCroqui:
    """
    Percorre a hierarquia de picos, grupos e setores do croqui e retorna
    um objeto ViasExtraidasCroqui estaticamente tipado.
    """
    diretorio = Path(caminho_croqui_dir)
    arquivo_croqui_yaml = diretorio / "croqui.yaml"

    dados_croqui = {}
    if arquivo_croqui_yaml.exists():
        with open(arquivo_croqui_yaml, "r", encoding="utf-8") as f:
            dados_croqui = yaml.safe_load(f) or {}

    vias_croqui = beta_pb2.ViasExtraidasCroqui()
    vias_croqui.id_croqui = diretorio.name
    vias_croqui.nome_croqui = dados_croqui.get("nome", diretorio.name)
    vias_croqui.cidade = dados_croqui.get("cidade", "")
    vias_croqui.estado = dados_croqui.get("estado", "")
    vias_croqui.pais = dados_croqui.get("pais", "Brasil")

    picos = dados_croqui.get("picos", [])
    contador_id = 1

    for pico in picos:
        nome_pico = pico.get("nome", "")
        setores_ou_grupos = pico.get("setores_ou_grupos", [])

        for item in setores_ou_grupos:
            # Caso 1: Item é um Grupo contendo setores
            if "grupo" in item:
                grupo_dict = item["grupo"]
                nome_grupo = grupo_dict.get("nome", "")
                setores = grupo_dict.get("setores", [])

                for setor_ref in setores:
                    caminho_rel = setor_ref.get("caminho", "")
                    if not caminho_rel:
                        continue
                    arquivo_md = diretorio / caminho_rel
                    _processar_arquivo_setor(
                        arquivo_md=arquivo_md,
                        caminho_rel=caminho_rel,
                        nome_grupo=nome_grupo,
                        nome_pico=nome_pico,
                        cidade_croqui=vias_croqui.cidade,
                        estado_croqui=vias_croqui.estado,
                        vias_croqui=vias_croqui,
                        contador_id=contador_id
                    )
                    contador_id = len(vias_croqui.escaladas) + 1

            # Caso 2: Item é um Setor direto (sem grupo)
            elif "setor" in item:
                setor_dict = item["setor"]
                caminho_rel = setor_dict.get("caminho", "")
                if not caminho_rel:
                    continue
                arquivo_md = diretorio / caminho_rel
                _processar_arquivo_setor(
                    arquivo_md=arquivo_md,
                    caminho_rel=caminho_rel,
                    nome_grupo="",
                    nome_pico=nome_pico,
                    cidade_croqui=vias_croqui.cidade,
                    estado_croqui=vias_croqui.estado,
                    vias_croqui=vias_croqui,
                    contador_id=contador_id
                )
                contador_id = len(vias_croqui.escaladas) + 1

    return vias_croqui


def _processar_arquivo_setor(
    arquivo_md: Path,
    caminho_rel: str,
    nome_grupo: str,
    nome_pico: str,
    cidade_croqui: str,
    estado_croqui: str,
    vias_croqui: beta_pb2.ViasExtraidasCroqui,
    contador_id: int
) -> None:
    """Extrai vias de um arquivo Markdown e as adiciona na mensagem ViasExtraidasCroqui."""
    if not arquivo_md.exists():
        return

    frontmatter = _ler_frontmatter_md(arquivo_md)
    nome_setor = frontmatter.get("nome", arquivo_md.stem)
    escaladas = frontmatter.get("escaladas", [])

    for esc_dict in escaladas:
        if not isinstance(esc_dict, dict):
            continue

        for tipo_chave, dados_via in esc_dict.items():
            if not isinstance(dados_via, dict):
                continue

            nome_via = dados_via.get("nome", "").strip()
            if not nome_via:
                continue

            grau_via = dados_via.get("grau", "").strip()

            alvo = vias_croqui.escaladas.add()
            alvo.id_escalada = str(contador_id)
            alvo.nome = nome_via
            alvo.grau = grau_via
            alvo.tipo = tipo_chave
            alvo.nome_setor = nome_setor
            alvo.nome_grupo = nome_grupo
            alvo.nome_pico = nome_pico
            alvo.cidade = cidade_croqui
            alvo.estado = estado_croqui
            alvo.arquivo_origem = caminho_rel

            contador_id += 1


def executar_cli_extrair_vias(argv: List[str] = None) -> int:
    """Ponto de entrada CLI para extração de vias."""
    parser = argparse.ArgumentParser(
        description="Extrai todas as vias e boulders de um croqui para um arquivo vias_extraidas.yaml tipado."
    )
    parser.add_argument(
        "croqui_dir",
        type=str,
        help="Caminho para o diretório do croqui (ex: database/br_mg_ouro_preto_ouroboulder)"
    )
    parser.add_argument(
        "-o", "--saida",
        type=str,
        default="",
        help="Caminho opcional do arquivo de saída (padrão: <croqui_dir>/vias_extraidas.yaml)"
    )

    args = parser.parse_args(argv)
    pico_dir = Path(args.croqui_dir)
    if not pico_dir.exists() or not pico_dir.is_dir():
        print(f"Erro: Diretório de croqui inválido ou não encontrado: {args.croqui_dir}", file=sys.stderr)
        return 1

    vias = extrair_vias_de_croqui(pico_dir)

    caminho_saida = Path(args.saida) if args.saida else pico_dir / "vias_extraidas.yaml"
    salvar_vias_extraidas_yaml(vias, caminho_saida)
    print(f"Sucesso: {len(vias.escaladas)} vias extraídas salvas em {caminho_saida}")
    return 0
