# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Utilitário para extração e resolução de rótulos identificadores de referências de mapa."""

from typing import Any, List, Optional
from aresta_api.proto.generated import croqui_pb2

# Identificadores válidos de nós de trajeto que representam círculos identificadores
_TIPOS_NOS_IDENTIFICADORES = {
    croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR,
    croqui_pb2.NoTrajeto.TipoNo.INICIO_AGACHADO,
    croqui_pb2.NoTrajeto.TipoNo.FIM_TOP,
    "1",
    "CIRCULO_IDENTIFICADOR",
    "TIPO_NO_CIRCULO_IDENTIFICADOR",
    "2",
    "INICIO_AGACHADO",
    "TIPO_NO_INICIO_AGACHADO",
    "11",
    "FIM_TOP",
    "TIPO_NO_FIM_TOP",
}


def _eh_no_identificador(tipo: Any) -> bool:
    """Verifica se o tipo de nó é um círculo identificador com rótulo."""
    if tipo in _TIPOS_NOS_IDENTIFICADORES:
        return True
    if isinstance(tipo, str) and tipo.upper() in _TIPOS_NOS_IDENTIFICADORES:
        return True
    return False


def extrair_rotulo_referencia(mapa: Optional[Any], referencia: Optional[Any]) -> str:
    """
    Extrai e formata o rótulo identificador (codenome) de uma referência visual de mapa.

    Itera sobre `ref.ids` e seus nós na ordem sequencial exata, coletando:
    - Rótulos de nós de traçados vetoriais do tipo `CIRCULO_IDENTIFICADOR`,
      `INICIO_AGACHADO` ou `FIM_TOP` que possuam `rotulo` preenchido.
    - O campo `label` de pontos de interesse convencionais (não-linhas) que esteja preenchido.

    Deduplica rótulos idênticos consecutivos (ex: nós compartilhados entre segmentos)
    e une os identificadores com traço (ex: "5-C", "SS-1-TOP").

    Se nenhum rótulo válido for encontrado, retorna uma string vazia `""`
    (nunca realiza fallback para IDs técnicos internos como "linha_XX").
    """
    if not mapa or not referencia:
        return ""

    ref_ids = (
        referencia.get("ids", [])
        if isinstance(referencia, dict)
        else getattr(referencia, "ids", [])
    )
    if not ref_ids:
        return ""

    pois = (
        mapa.get("pontos_de_interesse", [])
        if isinstance(mapa, dict)
        else getattr(mapa, "pontos_de_interesse", [])
    )

    pois_map = {}
    for p in pois:
        pid = p.get("id") if isinstance(p, dict) else getattr(p, "id", None)
        if pid is not None:
            pois_map[str(pid)] = p

    rotulos: List[str] = []

    for id_ref in ref_ids:
        p = pois_map.get(str(id_ref))
        if not p:
            continue

        eh_dict = isinstance(p, dict)
        tem_linha = "linha" in p if eh_dict else (hasattr(p, "HasField") and p.HasField("linha"))

        if tem_linha:
            linha = p.get("linha", {}) if eh_dict else p.linha
            linha_dict = isinstance(linha, dict)

            # Inspeciona marcadores compilados ou nós de conteúdo
            marcadores = (
                linha.get("compilado", {}).get("marcadores", [])
                if linha_dict
                else (
                    getattr(linha.compilado, "marcadores", [])
                    if hasattr(linha, "HasField") and linha.HasField("compilado")
                    else []
                )
            )

            nos = (
                linha.get("conteudo", {}).get("nos", [])
                if linha_dict
                else (
                    getattr(linha.conteudo, "nos", [])
                    if hasattr(linha, "HasField") and linha.HasField("conteudo")
                    else []
                )
            )

            lista_nos = marcadores if marcadores else nos

            for no in lista_nos:
                no_dict = isinstance(no, dict)
                tipo = no.get("tipo") if no_dict else getattr(no, "tipo", None)
                if _eh_no_identificador(tipo):
                    rot = str(
                        (no.get("rotulo") if no_dict else getattr(no, "rotulo", "")) or ""
                    ).strip()
                    if rot:
                        rotulos.append(rot)
        else:
            rot = str(
                (p.get("label") if eh_dict else getattr(p, "label", "")) or ""
            ).strip()
            if rot:
                rotulos.append(rot)

    if not rotulos:
        return ""

    # Deduplica rótulos consecutivos idênticos
    rotulos_deduplicados: List[str] = []
    for rotulo in rotulos:
        if not rotulos_deduplicados or rotulos_deduplicados[-1] != rotulo:
            rotulos_deduplicados.append(rotulo)

    return "-".join(rotulos_deduplicados)
