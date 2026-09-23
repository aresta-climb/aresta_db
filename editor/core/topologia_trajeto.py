# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca de cálculos topológicos, geométricos e semânticos para traçados de mapas.

Princípio II de AGENTS.md: Library-First.
Este módulo é independente de frameworks visuais e implementa a lógica pura de:
- Projeção de pontos e detecção de snap magnético (vértices e segmentos).
- Fatiamento de traçados com inserção de nós e preservação de curvatura.
- Resolução semântica padrão Ouroboulder (inícios '1, 2', topos 'A, B, C', desambiguação).
- Escopo unificado de setor e garantia de IDs mutuamente disjuntos.
"""

import math
import re
import copy
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Any, Sequence, Set, Union, Dict

from aresta_api.proto.generated import croqui_pb2
from editor.core.spline_catmull_rom import Ponto2D as Ponto2D


class TipoSnap(Enum):
    """Representa a natureza do ponto capturado pelo snap magnético."""
    LIVRE = "livre"
    NO = "no"
    CURVA = "curva"


@dataclass(frozen=True)
class ResultadoSnap:
    """Resultado detalhado do cálculo de snap magnético."""
    tipo: TipoSnap
    coordenada: Ponto2D
    id_linha: Optional[str] = None
    indice_no: Optional[int] = None
    indice_segmento: Optional[int] = None
    fator_t: Optional[float] = None
    rotulo: Optional[str] = None


def projetar_ponto_em_segmento(
    p: Ponto2D,
    a: Ponto2D,
    b: Ponto2D
) -> Tuple[Ponto2D, float, float]:
    """
    Projeta o ponto 'p' ortogonalmente sobre o segmento de reta 'ab'.
    Retorna uma tupla contendo:
    - Ponto2D projetado (limitado aos extremos do segmento).
    - Fator paramétrico 't' normalizado no intervalo [0.0, 1.0].
    - Distância euclidiana entre 'p' e a projeção.
    """
    dx = b.x - a.x
    dy = b.y - a.y
    comp_quadrada = dx * dx + dy * dy

    if comp_quadrada <= 1e-9:
        dist = p.distancia_ate(a)
        return a, 0.0, dist

    t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / comp_quadrada
    t_clamped = max(0.0, min(1.0, t))

    proj_x = a.x + t_clamped * dx
    proj_y = a.y + t_clamped * dy
    p_proj = Ponto2D(proj_x, proj_y)
    dist = p.distancia_ate(p_proj)

    return p_proj, t_clamped, dist


def detectar_snap_nos(
    ponto: Ponto2D,
    linhas: Sequence[Any],
    raio_snap: float = 15.0
) -> Optional[ResultadoSnap]:
    """
    Localiza o nó (vértice) mais próximo de 'ponto' entre todas as linhas informadas,
    caso a distância esteja dentro do raio de tolerância.
    """
    melhor_dist = float("inf")
    melhor_snap: Optional[ResultadoSnap] = None

    for linha in linhas:
        if not hasattr(linha, "linha") or not linha.HasField("linha"):
            continue
        nos = linha.linha.conteudo.nos
        id_linha = str(linha.id)
        for idx, no in enumerate(nos):
            p_no = Ponto2D(float(no.x), float(no.y))
            dist = ponto.distancia_ate(p_no)
            if dist <= raio_snap and dist < melhor_dist:
                melhor_dist = dist
                melhor_snap = ResultadoSnap(
                    tipo=TipoSnap.NO,
                    coordenada=p_no,
                    id_linha=id_linha,
                    indice_no=idx,
                    rotulo=str(no.rotulo) if no.rotulo else None
                )

    return melhor_snap


def detectar_snap_curva(
    ponto: Ponto2D,
    linhas: Sequence[Any],
    raio_snap: float = 15.0
) -> Optional[ResultadoSnap]:
    """
    Localiza a projeção mais próxima de 'ponto' sobre os segmentos contíguos das linhas,
    caso esteja dentro do raio de tolerância.
    """
    melhor_dist = float("inf")
    melhor_snap: Optional[ResultadoSnap] = None

    for linha in linhas:
        if not hasattr(linha, "linha") or not linha.HasField("linha"):
            continue
        nos = linha.linha.conteudo.nos
        if len(nos) < 2:
            continue
        id_linha = str(linha.id)
        for i in range(len(nos) - 1):
            p_a = Ponto2D(float(nos[i].x), float(nos[i].y))
            p_b = Ponto2D(float(nos[i + 1].x), float(nos[i + 1].y))
            p_proj, t, dist = projetar_ponto_em_segmento(ponto, p_a, p_b)
            if dist <= raio_snap and dist < melhor_dist:
                melhor_dist = dist
                melhor_snap = ResultadoSnap(
                    tipo=TipoSnap.CURVA,
                    coordenada=p_proj,
                    id_linha=id_linha,
                    indice_segmento=i,
                    fator_t=t
                )

    return melhor_snap


def calcular_snap(
    ponto: Ponto2D,
    linhas: Sequence[Any],
    raio_snap: float = 15.0
) -> ResultadoSnap:
    """
    Calcula o snap magnético para uma coordenada dada:
    1. Prioriza nós (vértices existentes).
    2. Em seguida, busca projeções sobre o corpo dos segmentos/curvas.
    3. Se nenhum ponto estiver no raio, retorna TipoSnap.LIVRE com a coordenada original.
    """
    snap_no = detectar_snap_nos(ponto, linhas, raio_snap)
    if snap_no:
        return snap_no

    snap_curva = detectar_snap_curva(ponto, linhas, raio_snap)
    if snap_curva:
        return snap_curva

    return ResultadoSnap(tipo=TipoSnap.LIVRE, coordenada=ponto)


def _copiar_poi_linha_base(linha_proto: Any, novo_id: str) -> Any:
    """Cria uma cópia limpa do POI do tipo linha com novo ID."""
    poi = croqui_pb2.Mapa.PontoDeInteresse(id=novo_id)
    if hasattr(linha_proto, "cor") and linha_proto.cor:
        poi.cor = str(linha_proto.cor)
    if hasattr(linha_proto, "label") and linha_proto.label:
        poi.label = str(linha_proto.label)
    if hasattr(linha_proto, "linha"):
        if hasattr(linha_proto.linha, "estilo"):
            poi.linha.estilo = linha_proto.linha.estilo
        if hasattr(linha_proto.linha, "espessura"):
            poi.linha.espessura = int(linha_proto.linha.espessura)
    return poi


def _adicionar_no_copia(linha_dst: Any, no_src: Any, tipo_sobrescrever: Optional[Any] = None, rotulo_sobrescrever: Optional[str] = None) -> Any:
    """Adiciona um nó copiado para o destino suportando mensagens Protobuf ou ReadOnlyProxy."""
    no = linha_dst.linha.conteudo.nos.add()
    no.x = int(round(float(no_src.x)))
    no.y = int(round(float(no_src.y)))
    no.tipo = tipo_sobrescrever if tipo_sobrescrever is not None else no_src.tipo
    no.rotulo = rotulo_sobrescrever if rotulo_sobrescrever is not None else str(no_src.rotulo or "")
    return no


def fatiar_linha_em_no(
    linha_proto: Any,
    indice_no: int,
    id_sub1: str,
    id_sub2: str,
    preservar_tipo_no_corte: bool = False
) -> Tuple[Any, Any]:
    """
    Divide uma linha existente em duas sublinhas no nó de índice especificado.
    - Sublinha 1 conterá os nós de 0 até indice_no.
    - Sublinha 2 conterá os nós de indice_no até o final.
    O nó de junção terá tipo PASSAGEM e rótulo vazio a menos que preservar_tipo_no_corte seja True.
    """
    nos = linha_proto.linha.conteudo.nos
    total_nos = len(nos)
    if indice_no <= 0 or indice_no >= total_nos - 1:
        raise ValueError(
            f"O índice do nó para fatiamento ({indice_no}) deve ser intermediário "
            f"(entre 1 e {total_nos - 2})."
        )

    tipo_juncao = nos[indice_no].tipo if preservar_tipo_no_corte else croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
    rotulo_juncao = str(nos[indice_no].rotulo or "") if preservar_tipo_no_corte else ""

    sub1 = _copiar_poi_linha_base(linha_proto, id_sub1)
    for i in range(indice_no):
        _adicionar_no_copia(sub1, nos[i])
    # Ponto de junção em sub1
    _adicionar_no_copia(sub1, nos[indice_no], tipo_sobrescrever=tipo_juncao, rotulo_sobrescrever=rotulo_juncao)

    sub2 = _copiar_poi_linha_base(linha_proto, id_sub2)
    # Ponto de junção em sub2
    _adicionar_no_copia(sub2, nos[indice_no], tipo_sobrescrever=tipo_juncao, rotulo_sobrescrever=rotulo_juncao)
    for i in range(indice_no + 1, total_nos):
        _adicionar_no_copia(sub2, nos[i])

    return sub1, sub2


def fatiar_linha_em_ponto_curva(
    linha_proto: Any,
    ponto_corte: Ponto2D,
    indice_segmento: int,
    id_sub1: str,
    id_sub2: str
) -> Tuple[Any, Any]:
    """
    Insere um novo nó de corte no segmento indicado e fatia a linha em duas partes.
    """
    linha_intermediaria = _copiar_poi_linha_base(linha_proto, "temp_intermediaria")
    nos = list(linha_proto.linha.conteudo.nos)
    
    no_novo = croqui_pb2.NoTrajeto(
        x=int(round(ponto_corte.x)),
        y=int(round(ponto_corte.y)),
        tipo=croqui_pb2.NoTrajeto.TipoNo.PASSAGEM,
        rotulo=""
    )
    indice_insercao = indice_segmento + 1
    
    for i in range(indice_insercao):
        _adicionar_no_copia(linha_intermediaria, nos[i])
    _adicionar_no_copia(linha_intermediaria, no_novo)
    for i in range(indice_insercao, len(nos)):
        _adicionar_no_copia(linha_intermediaria, nos[i])

    return fatiar_linha_em_no(linha_intermediaria, indice_insercao, id_sub1, id_sub2)


def fatiar_linha_triplo(
    linha_proto: Any,
    indice_entrada: int,
    indice_saida: int,
    id_sub1: str,
    id_sub2: str,
    id_sub3: str
) -> Tuple[Any, Any, Any]:
    """
    Divide uma linha em 3 partes contíguas para acomodar uma rota de travessia:
    - Início: 0 .. indice_entrada
    - Meio compartilhado: indice_entrada .. indice_saida
    - Fim: indice_saida .. N-1
    """
    nos = linha_proto.linha.conteudo.nos
    total_nos = len(nos)

    if not (0 < indice_entrada < indice_saida < total_nos - 1):
        raise ValueError("Índices de entrada e saída inválidos para fatiamento triplo.")

    sub1 = _copiar_poi_linha_base(linha_proto, id_sub1)
    for i in range(indice_entrada):
        _adicionar_no_copia(sub1, nos[i])
    _adicionar_no_copia(sub1, nos[indice_entrada], tipo_sobrescrever=croqui_pb2.NoTrajeto.TipoNo.PASSAGEM, rotulo_sobrescrever="")

    sub2 = _copiar_poi_linha_base(linha_proto, id_sub2)
    _adicionar_no_copia(sub2, nos[indice_entrada], tipo_sobrescrever=croqui_pb2.NoTrajeto.TipoNo.PASSAGEM, rotulo_sobrescrever="")
    for i in range(indice_entrada + 1, indice_saida):
        _adicionar_no_copia(sub2, nos[i])
    _adicionar_no_copia(sub2, nos[indice_saida], tipo_sobrescrever=croqui_pb2.NoTrajeto.TipoNo.PASSAGEM, rotulo_sobrescrever="")

    sub3 = _copiar_poi_linha_base(linha_proto, id_sub3)
    _adicionar_no_copia(sub3, nos[indice_saida], tipo_sobrescrever=croqui_pb2.NoTrajeto.TipoNo.PASSAGEM, rotulo_sobrescrever="")
    for i in range(indice_saida + 1, total_nos):
        _adicionar_no_copia(sub3, nos[i])

    return sub1, sub2, sub3


def atualizar_referencias_apos_fatiamento(
    referencias: Sequence[Any],
    id_linha_antiga: str,
    novos_ids_ordenados: List[str]
) -> None:
    """
    Substitui o id_linha_antiga pela sequência ordenada de novos_ids_ordenados
    em todas as referências do mapa que apontavam para a linha fatiada.
    """
    for ref in referencias:
        if id_linha_antiga in ref.ids:
            lista_ids = list(ref.ids)
            idx = lista_ids.index(id_linha_antiga)
            nova_lista = lista_ids[:idx] + novos_ids_ordenados + lista_ids[idx + 1:]
            ref.ClearField("ids")
            for nid in nova_lista:
                ref.ids.append(nid)


def formatar_rotulo_inicio(numeros: Sequence[Union[int, str]]) -> str:
    """
    Converte uma lista de números/strings em rótulo padrão Ouroboulder (ex: '1, 2, 3').
    """
    numeros_int: Set[int] = set()
    for n in numeros:
        try:
            numeros_int.add(int(n))
        except (ValueError, TypeError):
            continue
    return ", ".join(str(n) for n in sorted(numeros_int))


def adicionar_numero_inicio(rotulo_atual: str, novo_numero: int) -> str:
    """
    Adiciona um novo número a um rótulo de início sem duplicar e mantendo ordenação.
    """
    numeros = [int(x.strip()) for x in rotulo_atual.split(",") if x.strip().isdigit()]
    if novo_numero not in numeros:
        numeros.append(novo_numero)
    return formatar_rotulo_inicio(numeros)


def remover_numero_inicio(rotulo_atual: str, numero_a_remover: int) -> str:
    """
    Remove um número de um rótulo de início composto mantendo a ordenação.
    """
    numeros = [int(x.strip()) for x in rotulo_atual.split(",") if x.strip().isdigit()]
    numeros_restantes = [n for n in numeros if n != numero_a_remover]
    return formatar_rotulo_inicio(numeros_restantes)


def obter_proxima_letra_top(letras_em_uso: Sequence[str]) -> str:
    """
    Determina a próxima letra disponível para topo ('A', 'B', 'C', ...).
    """
    letras_set = {letra.strip().upper() for letra in letras_em_uso if letra.strip()}
    for codigo in range(ord("A"), ord("Z") + 1):
        c = chr(codigo)
        if c not in letras_set:
            return c
    return "Z"


def desambiguar_topos(
    linhas: Sequence[Any],
    referencias: Sequence[Any]
) -> None:
    """
    Aplica a regra de desambiguação sob demanda para topos:
    - Rotas isoladas permanecem com nó de término tipo PASSAGEM e rótulo vazio.
    - Rotas que compartilham traçados e se bifurcam recebem letras sequenciais ('A', 'B'...).
    - Rotas que convergem no mesmo topo compartilham o mesmo rótulo de topo.
    """
    linhas_por_id = {str(linha.id): linha for linha in linhas if hasattr(linha, "id")}
    
    # Identifica o último nó de cada referência
    topos_por_ref: Dict[str, Tuple[int, int]] = {}
    ultimo_no_por_ref: Dict[str, Any] = {}

    for ref in referencias:
        nome_escalada = getattr(ref, "escalada", "")
        if not ref.ids:
            continue
        ultimo_id = str(ref.ids[-1])
        if ultimo_id in linhas_por_id:
            linha = linhas_por_id[ultimo_id]
            nos = linha.linha.conteudo.nos
            if nos:
                ultimo_no = nos[-1]
                coord = (int(ultimo_no.x), int(ultimo_no.y))
                topos_por_ref[nome_escalada] = coord
                ultimo_no_por_ref[nome_escalada] = ultimo_no

    # Verifica se há bifurcação ou convergência
    rotas = list(referencias)
    if len(rotas) <= 1:
        # Rota isolada: garante que o término seja PASSAGEM sem rótulo
        for ultimo_no in ultimo_no_por_ref.values():
            ultimo_no.tipo = croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
            ultimo_no.rotulo = ""
        return

    # Mapeia coordenadas únicas de topo para letras
    coords_unicas: List[Tuple[int, int]] = []
    for coord in topos_por_ref.values():
        if coord not in coords_unicas:
            coords_unicas.append(coord)

    letras_atribuidas: Dict[Tuple[int, int], str] = {}
    letras_em_uso: List[str] = []

    for coord in coords_unicas:
        proxima_letra = obter_proxima_letra_top(letras_em_uso)
        letras_atribuidas[coord] = proxima_letra
        letras_em_uso.append(proxima_letra)

    # Aplica as letras e tipos aos nós de topo
    for nome_escalada, coord in topos_por_ref.items():
        no_topo = ultimo_no_por_ref[nome_escalada]
        no_topo.tipo = croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
        no_topo.rotulo = letras_atribuidas[coord]


def obter_rotulo_escalada_no_setor(setor_msg: Any, nome_escalada: str) -> Optional[str]:
    """
    Verifica se a escalada já possui traçado em outro mapa do mesmo setor e
    retorna o rótulo numérico do seu ponto inicial, mantendo a coerência.
    """
    for mapa in setor_msg.mapas:
        linhas_mapa = {str(p.id): p for p in mapa.pontos_de_interesse if p.HasField("linha")}
        for ref in mapa.referencias:
            if getattr(ref, "escalada", "") == nome_escalada and ref.ids:
                primeiro_id = str(ref.ids[0])
                if primeiro_id in linhas_mapa:
                    linha = linhas_mapa[primeiro_id]
                    nos = linha.linha.conteudo.nos
                    if nos and nos[0].rotulo:
                        return str(nos[0].rotulo)
    return None


def calcular_proximo_numero_inicio_setor(setor_msg: Any) -> int:
    """
    Analisa todos os mapas do setor para encontrar o maior número de início em uso
    e retorna o próximo número inteiro sequencial disponível.
    """
    numeros_encontrados: Set[int] = set()

    for mapa in setor_msg.mapas:
        for p in mapa.pontos_de_interesse:
            if p.HasField("linha"):
                nos = p.linha.conteudo.nos
                if nos:
                    rotulo = str(nos[0].rotulo)
                    for pedaco in re.split(r"[^\d]+", rotulo):
                        if pedaco.isdigit():
                            numeros_encontrados.add(int(pedaco))

    return max(numeros_encontrados) + 1 if numeros_encontrados else 1


def gerar_id_poi_disjunto_setor(
    setor_msg: Any,
    prefixo: str = "linha",
    ids_reservados: Optional[Set[str]] = None
) -> str:
    """
    Gera um novo identificador de POI garantindo que seja estritamente disjunto
    em relação a todos os IDs de todos os mapas pertencentes ao setor e ao conjunto de IDs reservados.
    """
    ids_existentes: Set[str] = set(ids_reservados or [])
    if setor_msg and hasattr(setor_msg, "mapas"):
        for mapa in setor_msg.mapas:
            for p in mapa.pontos_de_interesse:
                if p.id:
                    ids_existentes.add(str(p.id))

    indice = 1
    while f"{prefixo}_{indice}" in ids_existentes:
        indice += 1

    return f"{prefixo}_{indice}"
