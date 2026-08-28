# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import os
import argparse
from pathlib import Path
from typing import List, Union, Optional
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.io_yaml import carregar_vias_extraidas_yaml, salvar_candidatos_brutos_yaml
from coleta_de_betas.extratores.deduplicador import deduplicar_midias
from coleta_de_betas.extratores.youtube import ExtratorYouTube
from coleta_de_betas.extratores.vertex import ExtratorVertexSearch
from coleta_de_betas.extratores.duckduckgo import ExtratorDuckDuckGo


def instanciar_extratores_padrao() -> List[object]:
    """Instancia os extratores padrão disponíveis com base nas credenciais e ambiente."""
    extratores = []

    # DuckDuckGo funciona sem autenticação
    extratores.append(ExtratorDuckDuckGo())

    # YouTube (se chave estiver presente)
    chave_yt = os.environ.get("YOUTUBE_API_KEY", "")
    if chave_yt:
        extratores.append(ExtratorYouTube(chave_api=chave_yt))

    # Vertex (se configurado no ambiente)
    projeto_vertex = os.environ.get("VERTEX_PROJECT_ID", "")
    datastore_vertex = os.environ.get("VERTEX_DATA_STORE_ID", "")
    if projeto_vertex and datastore_vertex:
        extratores.append(ExtratorVertexSearch(
            project_id=projeto_vertex,
            data_store_id=datastore_vertex,
            location=os.environ.get("VERTEX_LOCATION", "global"),
            api_key=os.environ.get("VERTEX_API_KEY", "")
        ))

    return extratores


def buscar_candidatos_para_croqui(
    vias: beta_pb2.ViasExtraidasCroqui,
    extratores: Optional[List[object]] = None
) -> beta_pb2.BetasPendentes:
    """
    Executa a busca de mídias para cada escalada informada usando os extratores fornecidos,
    deduplicando resultados e populando uma mensagem BetasPendentes.
    """
    if extratores is None:
        extratores = instanciar_extratores_padrao()

    pendentes = beta_pb2.BetasPendentes()
    pendentes.id_croqui = vias.id_croqui

    for via in vias.escaladas:
        listas_de_resultados = []

        for ext in extratores:
            try:
                # Tenta chamar buscar com argumentos enriquecidos se suportado
                res = ext.buscar(
                    nome_escalada=via.nome,
                    nome_setor=via.nome_setor,
                    nome_pico=via.nome_pico or vias.nome_croqui
                )
                listas_de_resultados.append(res)
            except Exception as e:
                # Registra erro no extrator específico sem interromper o fluxo total
                print(f"Aviso: Erro no extrator {ext.__class__.__name__} para '{via.nome}': {e}", file=sys.stderr)

        midias_deduplicadas = deduplicar_midias(listas_de_resultados)

        cand_esc = pendentes.candidatos_por_escalada.add()
        cand_esc.nome_escalada = via.nome
        cand_esc.grau = via.grau
        cand_esc.nome_setor = via.nome_setor
        cand_esc.nome_grupo = via.nome_grupo
        cand_esc.nome_pico = via.nome_pico
        cand_esc.cidade = via.cidade or vias.cidade
        cand_esc.estado = via.estado or vias.estado
        cand_esc.candidatos.extend(midias_deduplicadas)

    return pendentes


def executar_cli_buscar(argv: List[str] = None, extratores: Optional[List[object]] = None) -> int:
    """Ponto de entrada CLI para busca de candidatos."""
    parser = argparse.ArgumentParser(
        description="Executa a busca tripla de betas para as vias de um croqui a partir de vias_extraidas.yaml."
    )
    parser.add_argument(
        "croqui_dir",
        type=str,
        help="Caminho para o diretório do croqui (ex: database/br_mg_ouro_preto_ouroboulder)"
    )
    parser.add_argument(
        "-i", "--entrada",
        type=str,
        default="",
        help="Caminho opcional do vias_extraidas.yaml (padrão: <croqui_dir>/vias_extraidas.yaml)"
    )
    parser.add_argument(
        "-o", "--saida",
        type=str,
        default="",
        help="Caminho opcional do candidatos_brutos.yaml (padrão: <croqui_dir>/candidatos_brutos.yaml)"
    )

    args = parser.parse_args(argv)
    pico_dir = Path(args.croqui_dir)
    if not pico_dir.exists() or not pico_dir.is_dir():
        print(f"Erro: Diretório de croqui inválido ou não encontrado: {args.croqui_dir}", file=sys.stderr)
        return 1

    caminho_entrada = Path(args.entrada) if args.entrada else pico_dir / "vias_extraidas.yaml"
    if not caminho_entrada.exists():
        print(f"Erro: Arquivo de vias de entrada não encontrado: {caminho_entrada}", file=sys.stderr)
        return 1

    vias = carregar_vias_extraidas_yaml(caminho_entrada)
    pendentes = buscar_candidatos_para_croqui(vias, extratores=extratores)

    caminho_saida = Path(args.saida) if args.saida else pico_dir / "candidatos_brutos.yaml"
    salvar_candidatos_brutos_yaml(pendentes, caminho_saida)
    total_cand = sum(len(c.candidatos) for c in pendentes.candidatos_por_escalada)
    print(f"Sucesso: {total_cand} candidatos coletados salvos em {caminho_saida}")
    return 0
