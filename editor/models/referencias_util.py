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
    alvo_uid: str,
) -> bool:
    """
    Verifica se uma mensagem de referência em mapa aponta para o UID da entidade alvo.
    """
    ref = _desembrulhar_proxy(ref)
    if not ref or not alvo_uid:
        return False
    return bool(getattr(ref, "alvo_uid", "") == alvo_uid)


def obter_contexto_por_uid(root_croqui: Any, uid: str) -> Optional[Tuple[str, str]]:
    """
    Localiza uma entidade (Grupo, Setor ou Escalada) na árvore do croqui pelo seu UID
    e retorna uma tupla (tipo_entidade, caminho_completo_formatado).
    Retorna None se o UID não for encontrado.
    """
    if not root_croqui or not uid:
        return None

    root_croqui = _desembrulhar_proxy(root_croqui)
    if not hasattr(root_croqui, "picos"):
        return None

    for pico in root_croqui.picos:
        for sg in pico.setores_ou_grupos:
            if sg.HasField("grupo"):
                grupo = sg.grupo.conteudo if sg.grupo.HasField("conteudo") else sg.grupo
                if getattr(grupo, "uid", "") == uid:
                    return ("Grupo", str(grupo.nome))

                for setor_item in grupo.setores:
                    setor = setor_item.conteudo if setor_item.HasField("conteudo") else setor_item
                    if getattr(setor, "uid", "") == uid:
                        return ("Setor", f"{grupo.nome} > {setor.nome}")

                    for esc in setor.escaladas:
                        if getattr(esc, "uid", "") == uid:
                            nome_via = extrair_nome_escalada(esc)
                            return ("Escalada", f"{grupo.nome} > {setor.nome} > {nome_via}")
                        if esc.WhichOneof("tipo") == "via_multiplas_enfiadas":
                            sub = esc.via_multiplas_enfiadas
                            for idx_enf, enf in enumerate(sub.enfiadas, 1):
                                if getattr(enf, "uid", "") == uid:
                                    nome_via = extrair_nome_escalada(esc)
                                    return ("Escalada", f"{grupo.nome} > {setor.nome} > {nome_via} ({idx_enf}ª Enfiada)")

            elif sg.HasField("setor"):
                setor = sg.setor.conteudo if sg.setor.HasField("conteudo") else sg.setor
                if getattr(setor, "uid", "") == uid:
                    return ("Setor", str(setor.nome))

                for esc in setor.escaladas:
                    if getattr(esc, "uid", "") == uid:
                        nome_via = extrair_nome_escalada(esc)
                        return ("Escalada", f"{setor.nome} > {nome_via}")
                    if esc.WhichOneof("tipo") == "via_multiplas_enfiadas":
                        sub = esc.via_multiplas_enfiadas
                        for idx_enf, enf in enumerate(sub.enfiadas, 1):
                            if getattr(enf, "uid", "") == uid:
                                nome_via = extrair_nome_escalada(esc)
                                return ("Escalada", f"{setor.nome} > {nome_via} ({idx_enf}ª Enfiada)")

    return None


def resolver_caminho_referencia(root_croqui: Any, ref: Any) -> str:
    """
    Resolve o título legível de uma referência visual de mapa a partir do alvo_uid.
    Suporta resolução O(1) quando root_croqui for IndiceUidsModel ou CroquiModel,
    mantendo fallback para objeto Protobuf Croqui.
    """
    ref = _desembrulhar_proxy(ref)
    alvo_uid = getattr(ref, "alvo_uid", "")
    if not alvo_uid or not root_croqui:
        return "Referência Inválida"

    # 1. IndiceUidsModel direto
    if hasattr(root_croqui, "obter_caminho"):
        caminho = root_croqui.obter_caminho(alvo_uid)
        return caminho if caminho is not None else "Referência Inválida"

    # 2. CroquiModel com indice_uids
    indice = getattr(root_croqui, "indice_uids", None)
    if indice and hasattr(indice, "obter_caminho"):
        caminho = indice.obter_caminho(alvo_uid)
        return caminho if caminho is not None else "Referência Inválida"

    # 3. Fallback: objeto Protobuf Croqui
    ctx = obter_contexto_por_uid(root_croqui, alvo_uid)
    if ctx:
        return ctx[1]
    return "Referência Inválida"


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
                grupo = sg.grupo.conteudo if sg.grupo.HasField("conteudo") else sg.grupo
                for setor_item in grupo.setores:
                    setor = setor_item.conteudo if setor_item.HasField("conteudo") else setor_item
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
                setor = sg.setor.conteudo if sg.setor.HasField("conteudo") else sg.setor
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


def extrair_uid_escalada(root_croqui: Any, msg_escalada: Any) -> str:
    """Extrai o UID da escalada, seja ela a mensagem Escalada ou a mensagem interna de seu tipo."""
    msg = _desembrulhar_proxy(msg_escalada)
    if not msg:
        return ""
    uid = getattr(msg, "uid", "")
    if uid:
        return str(uid)
    root = _desembrulhar_proxy(root_croqui)
    if not hasattr(root, "picos"):
        return ""
    for pico in root.picos:
        for sg in pico.setores_ou_grupos:
            setores: List[Any] = []
            if sg.HasField("grupo"):
                g = sg.grupo.conteudo if sg.grupo.HasField("conteudo") else sg.grupo
                setores.extend(s.conteudo if s.HasField("conteudo") else s for s in g.setores)
            elif sg.HasField("setor"):
                setores.append(sg.setor.conteudo if sg.setor.HasField("conteudo") else sg.setor)
            for s in setores:
                for esc in s.escaladas:
                    tipo = esc.WhichOneof("tipo")
                    sub = getattr(esc, tipo) if tipo else None
                    if sub is msg or esc is msg:
                        return str(getattr(esc, "uid", ""))
                    if tipo == "via_multiplas_enfiadas" and sub is not None:
                        for enf in getattr(sub, "enfiadas", []):
                            tipo_enf = enf.WhichOneof("tipo") if hasattr(enf, "WhichOneof") else None
                            sub_enf = getattr(enf, tipo_enf) if tipo_enf else None
                            if sub_enf is msg or enf is msg:
                                return str(getattr(enf, "uid", ""))
    return ""


def buscar_referencias_para_escalada(
    root_croqui: Any,
    msg_escalada: Any,
    contexto: Optional[Tuple[Any, Any, Any, str]] = None,
) -> List[Any]:
    """
    Varre todos os mapas do Pico onde a escalada reside e retorna uma lista
    com todas as referências que apontam para o seu UID.
    """
    root_croqui = _desembrulhar_proxy(root_croqui)
    msg_escalada = _desembrulhar_proxy(msg_escalada)

    esc_uid = getattr(msg_escalada, "uid", "") or extrair_uid_escalada(root_croqui, msg_escalada)
    if not esc_uid:
        return []

    if contexto is not None:
        pico, grupo, setor, _ = contexto
    else:
        pico, grupo, setor, _ = obter_contexto_escalada(root_croqui, msg_escalada)
    if pico is None:
        return []

    referencias_encontradas: List[Any] = []

    def _verificar_mapa(mapa: Any) -> None:
        for ref in mapa.referencias:
            if referencia_aponta_para_escalada(ref, esc_uid):
                referencias_encontradas.append(ref)

    # 1. Mapas no nível do Pico (mapas_gerais ou mapas diretos)
    if hasattr(pico, "mapas_gerais") and pico.mapas_gerais.HasField("conteudo"):
        for mapa in pico.mapas_gerais.conteudo.mapas:
            _verificar_mapa(mapa)
    elif hasattr(pico, "mapas"):
        for mapa in pico.mapas:
            _verificar_mapa(mapa)

    # 2. Mapas em Grupos e Setores
    for sg in pico.setores_ou_grupos:
        if sg.HasField("grupo"):
            g = sg.grupo.conteudo if sg.grupo.HasField("conteudo") else sg.grupo
            for mapa in g.mapas:
                _verificar_mapa(mapa)

            for setor_item in g.setores:
                s = setor_item.conteudo if setor_item.HasField("conteudo") else setor_item
                for mapa in s.mapas:
                    _verificar_mapa(mapa)

                for esc in s.escaladas:
                    for mapa in esc.mapas:
                        _verificar_mapa(mapa)

        elif sg.HasField("setor"):
            s = sg.setor.conteudo if sg.setor.HasField("conteudo") else sg.setor
            for mapa in s.mapas:
                _verificar_mapa(mapa)

            for esc in s.escaladas:
                for mapa in esc.mapas:
                    _verificar_mapa(mapa)

    return referencias_encontradas
