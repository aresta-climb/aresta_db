# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, List, Tuple, Any
from aresta_api.proto.generated import croqui_pb2


def _desembrulhar_proxy(obj: Any) -> Any:
    """Desembrulha ReadOnlyProxy se o objeto estiver envolvido."""
    from editor.models.readonly_proxy import ReadOnlyProxy
    if isinstance(obj, ReadOnlyProxy):
        return object.__getattribute__(obj, "_obj")
    return obj


def extrair_nome_escalada(msg: Any) -> str:
    """Extrai o nome da escalada de qualquer mensagem de via ou boulder."""
    msg = _desembrulhar_proxy(msg)
    if hasattr(msg, "nome"):
        return str(msg.nome)
    if hasattr(msg, "WhichOneof"):
        tipo = msg.WhichOneof("tipo")
        if tipo:
            sub = getattr(msg, tipo)
            if hasattr(sub, "nome"):
                return str(sub.nome)
    return ""


def referencia_aponta_para_escalada(
    ref: croqui_pb2.Mapa.Referencia,
    mapa_setor_nome: Optional[str],
    mapa_grupo_nome: Optional[str],
    alvo_escalada_nome: str,
    alvo_setor_nome: str,
    alvo_grupo_nome: Optional[str] = None,
) -> bool:
    """
    Verifica se uma mensagem de referência em mapa aponta para a escalada alvo especificada,
    resolvendo simetricamente o setor efetivo e o grupo efetivo.
    """
    ref = _desembrulhar_proxy(ref)
    if not ref.escalada or ref.escalada != alvo_escalada_nome:
        return False

    # 1. Resolução do setor efetivo (explícito na ref ou implícito pelo mapa)
    setor_efetivo = ref.setor if ref.setor else mapa_setor_nome
    if setor_efetivo is not None and setor_efetivo != alvo_setor_nome:
        return False

    # 2. Resolução do grupo efetivo
    grupo_efetivo = ref.grupo if ref.grupo else mapa_grupo_nome
    if alvo_grupo_nome is not None and grupo_efetivo is not None:
        if grupo_efetivo != alvo_grupo_nome:
            return False
    elif alvo_grupo_nome is None and grupo_efetivo is not None:
        # Se o alvo é de um setor isolado (sem grupo), referências restritas a grupo não batem
        return False

    return True


def obter_contexto_escalada(
    root_croqui: Any,
    msg_escalada: Any,
) -> Tuple[Optional[Any], Optional[Any], Optional[Any], str]:
    """
    Localiza a escalada na árvore do croqui e retorna:
    (pico, grupo, setor, nome_escalada).
    Retorna (None, None, None, nome) se a escalada for órfã ou não encontrada.
    """
    root_croqui = _desembrulhar_proxy(root_croqui)
    msg_escalada = _desembrulhar_proxy(msg_escalada)

    nome_escalada = extrair_nome_escalada(msg_escalada)
    if not hasattr(root_croqui, "picos"):
        return None, None, None, nome_escalada

    for pico in root_croqui.picos:
        for sg in pico.setores_ou_grupos:
            if sg.HasField("grupo"):
                grupo = sg.grupo.conteudo
                for setor_item in grupo.setores:
                    setor = setor_item.conteudo
                    for esc in setor.escaladas:
                        tipo_esc = esc.WhichOneof("tipo")
                        sub_esc = getattr(esc, tipo_esc) if tipo_esc else None
                        if sub_esc is msg_escalada or esc is msg_escalada:
                            return pico, grupo, setor, nome_escalada
                        if tipo_esc == "via_multiplas_enfiadas" and sub_esc is not None:
                            for enf in sub_esc.enfiadas:
                                tipo_enf = enf.WhichOneof("tipo")
                                sub_enf = getattr(enf, tipo_enf) if tipo_enf else None
                                if sub_enf is msg_escalada or enf is msg_escalada:
                                    return pico, grupo, setor, nome_escalada

            elif sg.HasField("setor"):
                setor = sg.setor.conteudo
                for esc in setor.escaladas:
                    tipo_esc = esc.WhichOneof("tipo")
                    sub_esc = getattr(esc, tipo_esc) if tipo_esc else None
                    if sub_esc is msg_escalada or esc is msg_escalada:
                        return pico, None, setor, nome_escalada
                    if tipo_esc == "via_multiplas_enfiadas" and sub_esc is not None:
                        for enf in sub_esc.enfiadas:
                            tipo_enf = enf.WhichOneof("tipo")
                            sub_enf = getattr(enf, tipo_enf) if tipo_enf else None
                            if sub_enf is msg_escalada or enf is msg_escalada:
                                return pico, None, setor, nome_escalada

    return None, None, None, nome_escalada


def buscar_referencias_para_escalada(
    root_croqui: Any,
    msg_escalada: Any,
) -> List[Any]:
    """
    Varre todos os mapas do Pico onde a escalada reside e retorna uma lista
    com todas as referências que apontam para ela.
    """
    root_croqui = _desembrulhar_proxy(root_croqui)
    msg_escalada = _desembrulhar_proxy(msg_escalada)

    pico, grupo, setor, nome_escalada = obter_contexto_escalada(root_croqui, msg_escalada)
    if pico is None or setor is None or not nome_escalada:
        return []

    nome_setor = str(setor.nome)
    nome_grupo = str(grupo.nome) if grupo is not None else None

    referencias_encontradas: List[Any] = []

    def _verificar_mapa(mapa: Any, mapa_setor: Optional[str], mapa_grupo: Optional[str]) -> None:
        for ref in mapa.referencias:
            if referencia_aponta_para_escalada(
                ref=ref,
                mapa_setor_nome=mapa_setor,
                mapa_grupo_nome=mapa_grupo,
                alvo_escalada_nome=nome_escalada,
                alvo_setor_nome=nome_setor,
                alvo_grupo_nome=nome_grupo,
            ):
                referencias_encontradas.append(ref)

    # 1. Mapas no nível do Pico (mapas_gerais ou mapas diretos)
    if hasattr(pico, "mapas_gerais") and pico.mapas_gerais.HasField("conteudo"):
        for mapa in pico.mapas_gerais.conteudo.mapas:
            _verificar_mapa(mapa, None, None)
    elif hasattr(pico, "mapas"):
        for mapa in pico.mapas:
            _verificar_mapa(mapa, None, None)

    # 2. Mapas em Grupos e Setores
    for sg in pico.setores_ou_grupos:
        if sg.HasField("grupo"):
            g = sg.grupo.conteudo
            for mapa in g.mapas:
                _verificar_mapa(mapa, None, str(g.nome))

            for setor_item in g.setores:
                s = setor_item.conteudo
                for mapa in s.mapas:
                    _verificar_mapa(mapa, str(s.nome), str(g.nome))

                for esc in s.escaladas:
                    if esc.WhichOneof("tipo") == "via_multiplas_enfiadas":
                        for mapa in esc.via_multiplas_enfiadas.mapas:
                            _verificar_mapa(mapa, str(s.nome), str(g.nome))

        elif sg.HasField("setor"):
            s = sg.setor.conteudo
            for mapa in s.mapas:
                _verificar_mapa(mapa, str(s.nome), None)

            for esc in s.escaladas:
                if esc.WhichOneof("tipo") == "via_multiplas_enfiadas":
                    for mapa in esc.via_multiplas_enfiadas.mapas:
                        _verificar_mapa(mapa, str(s.nome), None)

    return referencias_encontradas
