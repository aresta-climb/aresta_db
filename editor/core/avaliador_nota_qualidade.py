# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Motor determinístico de avaliação da nota_qualidade e diagnóstico de tarefas de melhoria de croquis.

Opera em escala aberta aditiva estruturada em três etapas por ordens de grandeza:
- Etapa 1 (Essenciais para Publicação): 1000 pontos por tarefa (8 tarefas = 8000 pontos).
- Etapa 2 (Qualidade, Navegação Offline e Segurança): 100 pontos por tarefa (7 tarefas = 700 pontos).
- Etapa 3 (Lapidação, História e Comunidade): 10 pontos por tarefa (7 tarefas = 70 pontos).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message


@dataclass(frozen=True)
class AcaoTarefaQualidade:
    """Representa um atalho de navegação direta para resolver uma pendência no editor."""

    rotulo: str
    uri_contexto: str


@dataclass(frozen=True)
class TarefaQualidade:
    """Representa o diagnóstico de um critério individual de qualidade do croqui."""

    id_tarefa: str
    titulo: str
    descricao: str
    etapa: int
    pontos_obtidos: int
    pontos_maximos: int
    concluida: bool
    progresso_atual: int
    progresso_total: int
    acoes: tuple[AcaoTarefaQualidade, ...] = ()

    @property
    def ganho_potencial(self) -> int:
        """Retorna quantos pontos o croqui ganhará ao concluir integralmente esta tarefa."""
        return max(0, self.pontos_maximos - self.pontos_obtidos)


@dataclass(frozen=True)
class ResumoEtapaQualidade:
    """Agrega o resultado e as tarefas de uma etapa hierárquica de qualidade."""

    numero_etapa: int
    titulo: str
    pontos_obtidos: int
    pontos_maximos: int
    tarefas_concluidas: int
    total_tarefas: int
    concluida: bool
    tarefas: tuple[TarefaQualidade, ...]


@dataclass(frozen=True)
class ResultadoNotaQualidade:
    """Resultado consolidado da avaliação de qualidade e completude de um croqui."""

    nota_qualidade: int
    nota_maxima: int
    pronto_para_publicar: bool
    publicado: bool
    etapas: tuple[ResumoEtapaQualidade, ...]


@dataclass(frozen=True)
class _InfoSetor:
    uid: str
    nome: str
    dados: dict[str, Any]
    dados_grupo_pai: dict[str, Any] | None
    uri_dados: str
    uri_mapa: str


@dataclass(frozen=True)
class _InfoEscalada:
    uid: str
    nome: str
    modalidade: str
    dados_modalidade: dict[str, Any]
    dados_escalada: dict[str, Any]
    setor_info: _InfoSetor
    uri_dados: str


def _converter_para_dicionario(croqui: Any) -> dict[str, Any]:
    """Converte CroquiModel, ReadOnlyProxy, mensagem Protobuf Croqui ou dict em dicionário."""
    alvo = croqui
    if hasattr(alvo, "obter_croqui_readonly"):
        alvo = alvo.obter_croqui_readonly()
    if hasattr(alvo, "_obj"):
        alvo = object.__getattribute__(alvo, "_obj")
    if isinstance(alvo, Message):
        return MessageToDict(alvo, preserving_proto_field_name=True)
    if isinstance(alvo, Mapping):
        return dict(alvo)
    return {}


def _resolver_arquivo_md(
    bloco: Any,
    croqui_path: Path | None,
    cache_md: Mapping[str, tuple[dict[str, Any] | None, str]] | None,
) -> dict[str, Any]:
    """Resolve um bloco ONEOF_CONTEUDO (inline em `conteudo` ou externo via `caminho`)."""
    if isinstance(bloco, str):
        caminho = bloco.strip()
    elif isinstance(bloco, Mapping):
        conteudo = bloco.get("conteudo")
        if isinstance(conteudo, Mapping):
            return dict(conteudo)
        caminho = str(bloco.get("caminho") or "").strip()
    else:
        return {}

    if not caminho:
        return {}

    if cache_md is not None and caminho in cache_md:
        fm, corpo = cache_md[caminho]
        res = dict(fm) if isinstance(fm, Mapping) else {}
        if corpo and not res.get("descricao"):
            res["descricao"] = corpo
        return res

    if croqui_path is not None:
        arquivo_md = croqui_path / caminho
        if arquivo_md.is_file():
            if caminho.endswith((".yaml", ".yml")):
                from editor.core.serializacao_util import carregar_yaml

                carregado = carregar_yaml(arquivo_md.read_text(encoding="utf-8"))
                return dict(carregado) if isinstance(carregado, Mapping) else {}
            from scripts.markdown_frontmatter_lib import parse_md_com_frontmatter

            fm, corpo = parse_md_com_frontmatter(arquivo_md)
            res = dict(fm) if isinstance(fm, Mapping) else {}
            if corpo and not res.get("descricao"):
                res["descricao"] = corpo
            return res

    return {}


def _avaliar_estado_malha_estrada_pico(
    pico: Mapping[str, Any],
    croqui_path: Path | None,
    cache_md: Mapping[str, tuple[dict[str, Any] | None, str]] | None,
) -> str:
    """Classifica a malha_estrada do pico em 'atualizada' (v>=2), 'versao_antiga' (v<2) ou 'ausente'."""
    if not _coordenada_valida(pico.get("localizacao")):
        return "ausente"
    loc = pico["localizacao"]
    lat_loc = int(loc.get("latitude") or 0)
    lon_loc = int(loc.get("longitude") or 0)
    malha_conteudo = _resolver_arquivo_md(pico.get("malha_estrada"), croqui_path, cache_md)
    nos = malha_conteudo.get("nos")
    if not isinstance(nos, list) or len(nos) == 0:
        return "ausente"
    lat_ref = int(malha_conteudo.get("latitude_referencia_e7") or 0)
    lon_ref = int(malha_conteudo.get("longitude_referencia_e7") or 0)
    sincronizada = (
        lat_ref == lat_loc
        and lon_ref == lon_loc
        and all(
            isinstance(n, Mapping)
            and (int(n.get("distancia_metros") or 0) <= 0 or int(n.get("duracao_minutos") or 0) > 0)
            for n in nos
        )
    )
    if not sincronizada:
        return "ausente"
    from scripts.gerar_malha_estrada_lib import VERSAO_ATUAL_MALHA_ESTRADA

    versao = int(malha_conteudo.get("versao") or 0)
    return "atualizada" if versao >= VERSAO_ATUAL_MALHA_ESTRADA else "versao_antiga"


def _coordenada_valida(coord: Any) -> bool:
    """Verifica se um dicionário de Coordenada possui latitude e longitude não nulas."""
    if not isinstance(coord, Mapping):
        return False
    lat = coord.get("latitude")
    lon = coord.get("longitude")
    return bool(lat is not None and lon is not None and lat != 0 and lon != 0)


def _valor_enum_preenchido(valor: Any) -> bool:
    """Verifica se um campo enum em dict Protobuf/YAML está preenchido e não é INDEFINIDO."""
    if valor is None:
        return False
    texto = str(valor).strip()
    return bool(texto and texto not in ("INDEFINIDO", "0"))


def _pontuar_cobertura(
    atuais: int,
    total: int,
    peso: int,
    *,
    meta: float = 0.90,
    dispensar_quando_vazio: bool = False,
    possui_estrutura_base: bool = True,
) -> tuple[int, bool]:
    """Calcula os pontos proporcionais até a meta e se a tarefa está concluída."""
    if not possui_estrutura_base:
        return 0, False
    if total == 0:
        return (peso, True) if dispensar_quando_vazio else (0, False)
    proporcao = atuais / total
    if proporcao >= meta - 1e-9:
        return peso, True
    pontos = min(peso, int(round(peso * (proporcao / meta))))
    return pontos, False


def _coletar_referencias_com_pontos(
    mapas: list[dict[str, Any]],
) -> tuple[set[str], set[str], set[str], set[str]]:
    """
    Percorre uma lista de mapas e retorna:
    - alvos_uids: conjunto de `alvo_uid` referenciados com pelo menos 1 ponto.
    - nomes_setores_grupos: nomes legados de setor/grupo referenciados.
    - nomes_escaladas: nomes legados de escalada referenciados.
    - alvos_com_linha: `alvo_uid` ou nome de escalada cujo ponto referenciado é `LinhaTrajeto`.
    """
    alvos_uids: set[str] = set()
    nomes_sg: set[str] = set()
    nomes_esc: set[str] = set()
    alvos_com_linha: set[str] = set()

    for mapa in mapas:
        pontos_por_id: dict[str, dict[str, Any]] = {}
        for pt in mapa.get("pontos_de_interesse") or []:
            chave_pt = str(pt.get("uid") or pt.get("id") or "").strip()
            if chave_pt:
                pontos_por_id[chave_pt] = dict(pt)

        for ref in mapa.get("referencias") or []:
            pts_ref = list(ref.get("pontos_uids") or ref.get("ids") or [])
            if not pts_ref:
                continue
            alvo_uid = str(ref.get("alvo_uid") or "").strip()
            nome_setor = str(ref.get("setor") or "").strip()
            nome_grupo = str(ref.get("grupo") or "").strip()
            nome_escalada = str(ref.get("escalada") or "").strip()

            if alvo_uid:
                alvos_uids.add(alvo_uid)
            if nome_setor:
                nomes_sg.add(nome_setor)
            if nome_grupo:
                nomes_sg.add(nome_grupo)
            if nome_escalada:
                nomes_esc.add(nome_escalada)

            tem_linha = any("linha" in pontos_por_id.get(str(pid), {}) for pid in pts_ref)
            if tem_linha:
                if alvo_uid:
                    alvos_com_linha.add(alvo_uid)
                if nome_escalada:
                    alvos_com_linha.add(nome_escalada)

    return alvos_uids, nomes_sg, nomes_esc, alvos_com_linha


def _extrair_modalidade_escalada(esc_dict: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Retorna (nome_campo_oneof, dict_dados_modalidade) de uma Escalada."""
    for mod in (
        "via_esportiva",
        "via_movel",
        "boulder",
        "via_multiplas_enfiadas",
        "highline",
    ):
        bloco = esc_dict.get(mod)
        if isinstance(bloco, Mapping):
            return mod, dict(bloco)
    return "", {}


def _escalada_possui_grau(modalidade: str, dados_mod: dict[str, Any]) -> bool:
    """Verifica se uma escalada possui grau de dificuldade preenchido (incluindo PROJETO)."""
    if modalidade in ("via_esportiva", "via_movel", "boulder"):
        return _valor_enum_preenchido(dados_mod.get("dificuldade")) or _valor_enum_preenchido(
            dados_mod.get("dificuldade_artificial")
        )
    if modalidade == "via_multiplas_enfiadas":
        return (
            _valor_enum_preenchido(dados_mod.get("dificuldade_media"))
            or _valor_enum_preenchido(dados_mod.get("dificuldade_maxima"))
            or _valor_enum_preenchido(dados_mod.get("dificuldade_artificial"))
        )
    return int(dados_mod.get("distancia") or 0) > 0


def _diagnosticar_extensao_e_protecoes_via(
    modalidade: str, dados_mod: dict[str, Any]
) -> tuple[bool, bool, str, str]:
    """Retorna (tem_extensao, tem_protecoes, campo_extensao, campo_protecoes) de uma via encordada."""
    if modalidade in ("via_esportiva", "via_movel"):
        tem_ext = int(dados_mod.get("extensao") or 0) > 0
        tem_prot = (
            bool(str(dados_mod.get("protecoes_moveis") or "").strip())
            or int(dados_mod.get("quantidade_protecoes_intermediarias") or 0) > 0
            or int(dados_mod.get("quantidade_protecoes_parada") or 0) > 0
        )
        campo_prot = (
            "protecoes_moveis"
            if modalidade == "via_movel"
            else "quantidade_protecoes_intermediarias"
        )
        return tem_ext, tem_prot, "extensao", campo_prot
    # via_multiplas_enfiadas
    tem_ext = (
        int(dados_mod.get("comprimento_total") or 0) > 0
        or int(dados_mod.get("numero_enfiadas") or 0) > 0
    )
    tem_prot = (
        bool(str(dados_mod.get("equipamento_recomendado") or "").strip())
        or int(dados_mod.get("quantidade_costuras_intermediarias") or 0) > 0
        or int(dados_mod.get("quantidade_equipamentos_parada") or 0) > 0
        or _valor_enum_preenchido(dados_mod.get("tipo_via_multiplas_enfiadas"))
    )
    return tem_ext, tem_prot, "comprimento_total", "tipo_via_multiplas_enfiadas"


def avaliar_nota_qualidade_croqui(
    croqui: Any,
    *,
    croqui_path: Path | None = None,
    cache_md: Mapping[str, tuple[dict[str, Any] | None, str]] | None = None,
) -> ResultadoNotaQualidade:
    """
    Avalia um croqui (instância Protobuf `Croqui`, `CroquiModel` ou `dict` YAML/compilado)
    e retorna o `ResultadoNotaQualidade` com a pontuação total e o diagnóstico das 3 etapas.
    """
    dados = _converter_para_dicionario(croqui)
    if not dados and croqui_path is not None and (croqui_path / "croqui.yaml").is_file():
        from editor.core.serializacao_util import carregar_yaml

        carregado = carregar_yaml((croqui_path / "croqui.yaml").read_text(encoding="utf-8"))
        if isinstance(carregado, Mapping):
            dados = dict(carregado)

    picos_raw = [dict(p) for p in (dados.get("picos") or []) if isinstance(p, Mapping)]
    setores_info: list[_InfoSetor] = []
    grupos_info: list[tuple[str, str, dict[str, Any], str]] = []
    itens_topo_por_pico: list[tuple[int, list[tuple[str, str]]]] = []
    todos_mapas: list[dict[str, Any]] = []
    mapas_gerais_por_pico: list[list[dict[str, Any]]] = []

    for p_idx, pico in enumerate(picos_raw):
        mg_conteudo = _resolver_arquivo_md(pico.get("mapas_gerais"), croqui_path, cache_md)
        mapas_mg = [dict(m) for m in (mg_conteudo.get("mapas") or []) if isinstance(m, Mapping)]
        mapas_gerais_por_pico.append(mapas_mg)
        todos_mapas.extend(mapas_mg)

        itens_topo: list[tuple[str, str]] = []
        for sg_idx, sg in enumerate(pico.get("setores_ou_grupos") or []):
            if not isinstance(sg, Mapping):
                continue
            uri_sg_dados = (
                f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}"
                f"/expando:setores_ou_grupos/item:{sg_idx}"
            )
            if "setor" in sg:
                setor_dict = _resolver_arquivo_md(sg.get("setor"), croqui_path, cache_md)
                uid_s = str(setor_dict.get("uid") or "").strip()
                nome_s = str(setor_dict.get("nome") or f"Setor {sg_idx + 1}").strip()
                itens_topo.append((uid_s, nome_s))
                mapas_s = [
                    dict(m) for m in (setor_dict.get("mapas") or []) if isinstance(m, Mapping)
                ]
                todos_mapas.extend(mapas_s)
                uri_s_mapa = (
                    f"page:mapas/node:root/node:Croqui/expando:picos/item:{p_idx}"
                    f"/expando:setores_ou_grupos/item:{sg_idx}/expando:mapas/item:0"
                    if mapas_s
                    else uri_sg_dados
                )
                setores_info.append(
                    _InfoSetor(
                        uid=uid_s,
                        nome=nome_s,
                        dados=setor_dict,
                        dados_grupo_pai=None,
                        uri_dados=uri_sg_dados,
                        uri_mapa=uri_s_mapa,
                    )
                )
            elif "grupo" in sg:
                grupo_dict = _resolver_arquivo_md(sg.get("grupo"), croqui_path, cache_md)
                uid_g = str(grupo_dict.get("uid") or "").strip()
                nome_g = str(grupo_dict.get("nome") or f"Grupo {sg_idx + 1}").strip()
                itens_topo.append((uid_g, nome_g))
                grupos_info.append((uid_g, nome_g, grupo_dict, uri_sg_dados))
                mapas_g = [
                    dict(m) for m in (grupo_dict.get("mapas") or []) if isinstance(m, Mapping)
                ]
                todos_mapas.extend(mapas_g)

                sub_lista = grupo_dict.get("setores") or grupo_dict.get("sub_setores") or []
                for s_idx, sub_item in enumerate(sub_lista):
                    bloco_sub = (
                        sub_item.get("setor")
                        if isinstance(sub_item, Mapping) and "setor" in sub_item
                        else sub_item
                    )
                    sub_dict = _resolver_arquivo_md(bloco_sub, croqui_path, cache_md)
                    uid_sub = str(sub_dict.get("uid") or "").strip()
                    nome_sub = str(sub_dict.get("nome") or f"Setor {s_idx + 1}").strip()
                    mapas_sub = [
                        dict(m) for m in (sub_dict.get("mapas") or []) if isinstance(m, Mapping)
                    ]
                    todos_mapas.extend(mapas_sub)
                    uri_sub_dados = f"{uri_sg_dados}/expando:setores/item:{s_idx}"
                    uri_sub_mapa = (
                        f"page:mapas/node:root/node:Croqui/expando:picos/item:{p_idx}"
                        f"/expando:setores_ou_grupos/item:{sg_idx}/expando:setores/item:{s_idx}"
                        f"/expando:mapas/item:0"
                        if mapas_sub
                        else uri_sub_dados
                    )
                    setores_info.append(
                        _InfoSetor(
                            uid=uid_sub,
                            nome=nome_sub,
                            dados=sub_dict,
                            dados_grupo_pai=grupo_dict,
                            uri_dados=uri_sub_dados,
                            uri_mapa=uri_sub_mapa,
                        )
                    )
        itens_topo_por_pico.append((p_idx, itens_topo))

    escaladas_info: list[_InfoEscalada] = []
    for s_info in setores_info:
        for e_idx, esc_raw in enumerate(s_info.dados.get("escaladas") or []):
            esc_dict = dict(esc_raw)
            for m_esc in esc_dict.get("mapas") or []:
                todos_mapas.append(dict(m_esc))
            mod, dados_mod = _extrair_modalidade_escalada(esc_dict)
            nome_esc = str(dados_mod.get("nome") or f"Escalada {e_idx + 1}").strip()
            uid_esc = str(esc_dict.get("uid") or "").strip()
            uri_esc = f"{s_info.uri_dados}/expando:escaladas/item:{e_idx}"
            escaladas_info.append(
                _InfoEscalada(
                    uid=uid_esc,
                    nome=nome_esc,
                    modalidade=mod,
                    dados_modalidade=dados_mod,
                    dados_escalada=esc_dict,
                    setor_info=s_info,
                    uri_dados=uri_esc,
                )
            )

    tem_picos = len(picos_raw) > 0
    tem_setores = len(setores_info) > 0
    tem_escaladas = len(escaladas_info) > 0

    alvos_uids_todos, _, nomes_esc_todos, alvos_com_linha = _coletar_referencias_com_pontos(
        todos_mapas
    )

    # =========================================================================
    # ETAPA 1: Essenciais para Publicação (1000 pontos cada)
    # =========================================================================
    multiplos_picos = len(picos_raw) > 1

    # 1.1 Identidade e capa do croqui
    tem_nome_croqui = bool(str(dados.get("nome") or "").strip())
    tem_desc_croqui = bool(str(dados.get("descricao") or "").strip())
    tem_thumb_croqui = bool(str(dados.get("caminho_thumbnail") or "").strip())
    itens_identidade = sum([tem_nome_croqui, tem_desc_croqui, tem_thumb_croqui])
    pts_id, conc_id = _pontuar_cobertura(itens_identidade, 3, 1000, meta=1.0)
    lista_acoes_id: list[AcaoTarefaQualidade] = []
    if not tem_nome_croqui:
        lista_acoes_id.append(
            AcaoTarefaQualidade(
                "Definir nome do croqui", "page:dados/node:root/node:Croqui/campo:nome"
            )
        )
    if not tem_desc_croqui:
        lista_acoes_id.append(
            AcaoTarefaQualidade(
                "Adicionar descrição do croqui",
                "page:dados/node:root/node:Croqui/campo:descricao",
            )
        )
    if not tem_thumb_croqui:
        lista_acoes_id.append(
            AcaoTarefaQualidade(
                "Adicionar imagem de capa",
                "page:dados/node:root/node:Croqui/campo:caminho_thumbnail",
            )
        )
    t1_identidade = TarefaQualidade(
        id_tarefa="etapa1_identidade_capa",
        titulo="Identidade e capa do croqui",
        descricao="Preencher nome, descrição curta e imagem de capa (thumbnail) do croqui.",
        etapa=1,
        pontos_obtidos=pts_id,
        pontos_maximos=1000,
        concluida=conc_id,
        progresso_atual=itens_identidade,
        progresso_total=3,
        acoes=() if conc_id else tuple(lista_acoes_id),
    )

    # 1.2 Localização e Google Maps dos picos
    picos_com_loc = 0
    acoes_loc: list[AcaoTarefaQualidade] = []
    for p_idx, pico in enumerate(picos_raw):
        tem_coord = _coordenada_valida(pico.get("localizacao"))
        tem_url = bool(str(pico.get("url_google_maps") or "").strip())
        if tem_coord and tem_url:
            picos_com_loc += 1
        else:
            nome_p = str(pico.get("nome") or f"Pico {p_idx + 1}").strip()
            sufixo_p = f" ({nome_p})" if multiplos_picos else ""
            uri_pico = f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}"
            if not tem_coord:
                acoes_loc.append(
                    AcaoTarefaQualidade(
                        f"Adicionar localização{sufixo_p}",
                        f"{uri_pico}/campo:localizacao",
                    )
                )
            if not tem_url:
                acoes_loc.append(
                    AcaoTarefaQualidade(
                        f"Adicionar link Google Maps{sufixo_p}",
                        f"{uri_pico}/campo:url_google_maps",
                    )
                )
    if not tem_picos:
        acoes_loc.append(
            AcaoTarefaQualidade("Adicionar pico", "page:dados/node:root/node:Croqui/campo:picos")
        )
    pts_loc, conc_loc = _pontuar_cobertura(
        picos_com_loc, len(picos_raw), 1000, meta=1.0, possui_estrutura_base=tem_picos
    )
    t1_localizacao = TarefaQualidade(
        id_tarefa="etapa1_localizacao_picos",
        titulo="Localização e Google Maps dos picos",
        descricao="Informar coordenadas geográficas (latitude/longitude) e link do Google Maps nos picos.",
        etapa=1,
        pontos_obtidos=pts_loc,
        pontos_maximos=1000,
        concluida=conc_loc,
        progresso_atual=picos_com_loc,
        progresso_total=max(1, len(picos_raw)),
        acoes=() if conc_loc else tuple(acoes_loc[:3]),
    )

    # 1.3 Instruções de chegada e acesso
    tem_botao_texto = any(
        isinstance(b, Mapping)
        and isinstance(b.get("destino"), Mapping)
        and bool(
            str(
                _resolver_arquivo_md(b["destino"].get("secao_textual"), croqui_path, cache_md).get(
                    "descricao"
                )
                or (
                    b["destino"].get("secao_textual", {}).get("conteudo")
                    if isinstance(b["destino"].get("secao_textual"), Mapping)
                    else ""
                )
                or ""
            ).strip()
        )
        for b in (dados.get("botoes") or [])
    )
    picos_com_acesso = 0
    acoes_acesso: list[AcaoTarefaQualidade] = []
    for p_idx, pico in enumerate(picos_raw):
        if bool(str(pico.get("descricao") or "").strip()) or tem_botao_texto:
            picos_com_acesso += 1
        else:
            nome_p = str(pico.get("nome") or f"Pico {p_idx + 1}").strip()
            sufixo_p = f" ({nome_p})" if multiplos_picos else ""
            acoes_acesso.append(
                AcaoTarefaQualidade(
                    f"Adicionar instruções de acesso{sufixo_p}",
                    f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}/campo:descricao",
                )
            )
    if not tem_picos:
        acoes_acesso.append(
            AcaoTarefaQualidade("Adicionar pico", "page:dados/node:root/node:Croqui/campo:picos")
        )
    pts_acesso, conc_acesso = _pontuar_cobertura(
        picos_com_acesso, len(picos_raw), 1000, meta=1.0, possui_estrutura_base=tem_picos
    )
    t1_acesso = TarefaQualidade(
        id_tarefa="etapa1_instrucoes_acesso",
        titulo="Instruções de chegada e acesso",
        descricao="Detalhar como chegar e acessar o pico na descrição do pico ou em botão informativo.",
        etapa=1,
        pontos_obtidos=pts_acesso,
        pontos_maximos=1000,
        concluida=conc_acesso,
        progresso_atual=picos_com_acesso,
        progresso_total=max(1, len(picos_raw)),
        acoes=() if conc_acesso else tuple(acoes_acesso[:3]),
    )

    # 1.4 Mapa Geral referenciando >= 90% dos setores/grupos (dispensado se <= 1 setor)
    total_entidades_mg = sum(len(itens) for _, itens in itens_topo_por_pico)
    dispensa_mapa_geral = tem_setores and len(setores_info) <= 1 and total_entidades_mg <= 1
    if dispensa_mapa_geral:
        pts_mg, conc_mg = 1000, True
        prog_mg_atual, prog_mg_total = 1, 1
        acoes_mg: tuple[AcaoTarefaQualidade, ...] = ()
    else:
        mapeados_mg = 0
        lista_acoes_mg: list[AcaoTarefaQualidade] = []
        for p_idx, itens in itens_topo_por_pico:
            mapas_mg_pico = mapas_gerais_por_pico[p_idx]
            uids_mg, nomes_mg, _, _ = _coletar_referencias_com_pontos(mapas_mg_pico)
            faltou_no_pico = False
            for uid_item, nome_item in itens:
                if (uid_item and uid_item in uids_mg) or (nome_item and nome_item in nomes_mg):
                    mapeados_mg += 1
                else:
                    faltou_no_pico = True
            if faltou_no_pico:
                nome_p = str(picos_raw[p_idx].get("nome") or f"Pico {p_idx + 1}").strip()
                sufixo_p = f" ({nome_p})" if multiplos_picos else ""
                uri_mg = (
                    f"page:mapas/node:root/node:Croqui/expando:picos/item:{p_idx}"
                    f"/node:mapas_gerais/expando:mapas/item:0"
                    if mapas_mg_pico
                    else f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}/campo:mapas_gerais"
                )
                rotulo_mg = (
                    f"Mapear setores no Mapa Geral{sufixo_p}"
                    if mapas_mg_pico
                    else f"Adicionar Mapa Geral{sufixo_p}"
                )
                lista_acoes_mg.append(AcaoTarefaQualidade(rotulo_mg, uri_mg))
        pts_mg, conc_mg = _pontuar_cobertura(
            mapeados_mg,
            total_entidades_mg,
            1000,
            meta=0.90,
            possui_estrutura_base=tem_setores,
        )
        prog_mg_atual = mapeados_mg
        prog_mg_total = max(1, total_entidades_mg)
        acoes_mg = () if conc_mg else tuple(lista_acoes_mg[:3])

    t1_mapa_geral = TarefaQualidade(
        id_tarefa="etapa1_mapa_geral",
        titulo="Mapa Geral com setores e grupos",
        descricao="Mapear ao menos 90% dos setores ou grupos no Mapa Geral do pico (automático para setor único).",
        etapa=1,
        pontos_obtidos=pts_mg,
        pontos_maximos=1000,
        concluida=conc_mg,
        progresso_atual=prog_mg_atual,
        progresso_total=prog_mg_total,
        acoes=acoes_mg,
    )

    # 1.5 >= 90% dos setores com mapa
    setores_com_mapa = 0
    acoes_setores_mapa: list[AcaoTarefaQualidade] = []
    for s_info in setores_info:
        mapas_s = s_info.dados.get("mapas") or []
        escs_s = [e for e in (s_info.dados.get("escaladas") or []) if isinstance(e, Mapping)]
        todas_escs_tem_mapa = bool(escs_s) and all(bool(e.get("mapas")) for e in escs_s)
        if len(mapas_s) > 0 or todas_escs_tem_mapa:
            setores_com_mapa += 1
        else:
            acoes_setores_mapa.append(
                AcaoTarefaQualidade(
                    f"Adicionar mapa em {s_info.nome}", f"{s_info.uri_dados}/campo:mapas"
                )
            )
    pts_sm, conc_sm = _pontuar_cobertura(
        setores_com_mapa, len(setores_info), 1000, meta=0.90, possui_estrutura_base=tem_setores
    )
    t1_setores_mapa = TarefaQualidade(
        id_tarefa="etapa1_setores_com_mapa",
        titulo="Mapas nos setores",
        descricao="Cadastrar ao menos um mapa fotográfico ou desenhado em pelo menos 90% dos setores.",
        etapa=1,
        pontos_obtidos=pts_sm,
        pontos_maximos=1000,
        concluida=conc_sm,
        progresso_atual=setores_com_mapa,
        progresso_total=max(1, len(setores_info)),
        acoes=() if conc_sm else tuple(acoes_setores_mapa[:3]),
    )

    # 1.6 >= 90% das escaladas referenciadas em mapas
    escaladas_mapeadas = 0
    acoes_esc_mapa: list[AcaoTarefaQualidade] = []
    setores_ja_acionados_mapa: set[str] = set()
    for esc_info in escaladas_info:
        tem_ref = (esc_info.uid and esc_info.uid in alvos_uids_todos) or (
            esc_info.nome and esc_info.nome in nomes_esc_todos
        )
        tem_mapa_proprio = any(
            bool(m.get("pontos_de_interesse")) for m in (esc_info.dados_escalada.get("mapas") or [])
        )
        if tem_ref or tem_mapa_proprio:
            escaladas_mapeadas += 1
        elif esc_info.setor_info.uri_dados not in setores_ja_acionados_mapa:
            setores_ja_acionados_mapa.add(esc_info.setor_info.uri_dados)
            setor_tem_mapa = bool(esc_info.setor_info.dados.get("mapas"))
            acoes_esc_mapa.append(
                AcaoTarefaQualidade(
                    f"Mapear escaladas em {esc_info.setor_info.nome}"
                    if setor_tem_mapa
                    else f"Adicionar mapa em {esc_info.setor_info.nome}",
                    esc_info.setor_info.uri_mapa
                    if setor_tem_mapa
                    else f"{esc_info.setor_info.uri_dados}/campo:mapas",
                )
            )
    pts_em, conc_em = _pontuar_cobertura(
        escaladas_mapeadas,
        len(escaladas_info),
        1000,
        meta=0.90,
        possui_estrutura_base=tem_escaladas,
    )
    t1_escaladas_mapa = TarefaQualidade(
        id_tarefa="etapa1_escaladas_no_mapa",
        titulo="Escaladas localizadas nos mapas",
        descricao="Vincular ao menos 90% das escaladas a pontos de interesse ou linhas em um mapa.",
        etapa=1,
        pontos_obtidos=pts_em,
        pontos_maximos=1000,
        concluida=conc_em,
        progresso_atual=escaladas_mapeadas,
        progresso_total=max(1, len(escaladas_info)),
        acoes=() if conc_em else tuple(acoes_esc_mapa[:3]),
    )

    # 1.7 >= 90% das escaladas com grau de dificuldade (incluindo PROJETO)
    escaladas_com_grau = 0
    acoes_grau: list[AcaoTarefaQualidade] = []
    for esc_info in escaladas_info:
        if _escalada_possui_grau(esc_info.modalidade, esc_info.dados_modalidade):
            escaladas_com_grau += 1
        else:
            campo_grau = (
                "dificuldade_media"
                if esc_info.modalidade == "via_multiplas_enfiadas"
                else ("distancia" if esc_info.modalidade == "highline" else "dificuldade")
            )
            acoes_grau.append(
                AcaoTarefaQualidade(
                    f"Definir grau de {esc_info.nome}",
                    f"{esc_info.uri_dados}/campo:{campo_grau}",
                )
            )
    pts_grau, conc_grau = _pontuar_cobertura(
        escaladas_com_grau,
        len(escaladas_info),
        1000,
        meta=0.90,
        possui_estrutura_base=tem_escaladas,
    )
    t1_grau = TarefaQualidade(
        id_tarefa="etapa1_grau_dificuldade",
        titulo="Grau de dificuldade nas escaladas",
        descricao="Informar o grau de dificuldade (incluindo Projeto) em pelo menos 90% das escaladas.",
        etapa=1,
        pontos_obtidos=pts_grau,
        pontos_maximos=1000,
        concluida=conc_grau,
        progresso_atual=escaladas_com_grau,
        progresso_total=max(1, len(escaladas_info)),
        acoes=() if conc_grau else tuple(acoes_grau[:3]),
    )

    # 1.8 Mapa de pontos de estrada dos picos (100% dos picos com malha_estrada atualizada na versão atual)
    picos_com_malha = 0
    unidades_malha = 0.0
    acoes_malha: list[AcaoTarefaQualidade] = []
    for p_idx, pico in enumerate(picos_raw):
        estado_malha = _avaliar_estado_malha_estrada_pico(pico, croqui_path, cache_md)
        if estado_malha == "atualizada":
            picos_com_malha += 1
            unidades_malha += 1.0
        elif estado_malha == "versao_antiga":
            unidades_malha += 0.7
            nome_p = str(pico.get("nome") or f"Pico {p_idx + 1}").strip()
            sufixo_p = f" ({nome_p})" if multiplos_picos else ""
            acoes_malha.append(
                AcaoTarefaQualidade(
                    f"Atualizar mapa de pontos{sufixo_p}",
                    f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}/campo:localizacao",
                )
            )
        else:
            nome_p = str(pico.get("nome") or f"Pico {p_idx + 1}").strip()
            sufixo_p = f" ({nome_p})" if multiplos_picos else ""
            rotulo_malha = (
                f"Gerar mapa de pontos{sufixo_p}"
                if _coordenada_valida(pico.get("localizacao"))
                else f"Adicionar localização{sufixo_p}"
            )
            acoes_malha.append(
                AcaoTarefaQualidade(
                    rotulo_malha,
                    f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}/campo:localizacao",
                )
            )
    if not tem_picos:
        acoes_malha.append(
            AcaoTarefaQualidade("Adicionar pico", "page:dados/node:root/node:Croqui/campo:picos")
        )
        pts_malha, conc_malha = 0, False
    elif picos_com_malha == len(picos_raw):
        pts_malha, conc_malha = 1000, True
    else:
        pts_malha = int(round(1000 * (unidades_malha / len(picos_raw))))
        conc_malha = False
    t1_malha_estrada = TarefaQualidade(
        id_tarefa="etapa1_malha_estrada_picos",
        titulo="Mapa de pontos de estrada dos picos",
        descricao="Gerar a malha rodoviária de pontos (Overpass/OSM) sincronizada com a localização de cada pico.",
        etapa=1,
        pontos_obtidos=pts_malha,
        pontos_maximos=1000,
        concluida=conc_malha,
        progresso_atual=picos_com_malha,
        progresso_total=max(1, len(picos_raw)),
        acoes=() if conc_malha else tuple(acoes_malha[:3]),
    )

    tarefas_etapa1 = (
        t1_identidade,
        t1_localizacao,
        t1_acesso,
        t1_mapa_geral,
        t1_setores_mapa,
        t1_escaladas_mapa,
        t1_grau,
        t1_malha_estrada,
    )

    # =========================================================================
    # ETAPA 2: Qualidade, Navegação Offline e Segurança (100 pontos cada)
    # =========================================================================

    # 2.1 Coordenadas de estacionamento e escalada nos setores/grupos (>= 90%)
    setores_com_coord = 0
    acoes_coord_setor: list[AcaoTarefaQualidade] = []
    for s_info in setores_info:
        est_ok = _coordenada_valida(s_info.dados.get("localizacao_estacionamento")) or (
            s_info.dados_grupo_pai is not None
            and _coordenada_valida(s_info.dados_grupo_pai.get("localizacao_estacionamento"))
        )
        esc_ok = _coordenada_valida(s_info.dados.get("localizacao_escalada")) or (
            s_info.dados_grupo_pai is not None
            and _coordenada_valida(s_info.dados_grupo_pai.get("localizacao_escalada"))
        )
        if est_ok and esc_ok:
            setores_com_coord += 1
        else:
            if not est_ok:
                acoes_coord_setor.append(
                    AcaoTarefaQualidade(
                        f"Adicionar estacionamento ({s_info.nome})",
                        f"{s_info.uri_dados}/campo:localizacao_estacionamento",
                    )
                )
            if not esc_ok:
                acoes_coord_setor.append(
                    AcaoTarefaQualidade(
                        f"Adicionar localização da parede ({s_info.nome})",
                        f"{s_info.uri_dados}/campo:localizacao_escalada",
                    )
                )
    pts_cs, conc_cs = _pontuar_cobertura(
        setores_com_coord, len(setores_info), 100, meta=0.90, possui_estrutura_base=tem_setores
    )
    t2_coord_setores = TarefaQualidade(
        id_tarefa="etapa2_coordenadas_setores",
        titulo="Coordenadas de estacionamento e escalada nos setores",
        descricao="Preencher coordenadas de estacionamento e da parede em pelo menos 90% dos setores.",
        etapa=2,
        pontos_obtidos=pts_cs,
        pontos_maximos=100,
        concluida=conc_cs,
        progresso_atual=setores_com_coord,
        progresso_total=max(1, len(setores_info)),
        acoes=() if conc_cs else tuple(acoes_coord_setor[:3]),
    )

    # 2.2 Trilhas de aproximação nos setores (>= 90%)
    setores_com_trilha = 0
    acoes_trilhas: list[AcaoTarefaQualidade] = []
    for s_info in setores_info:
        trilhas = [t for t in (s_info.dados.get("trilhas") or []) if isinstance(t, Mapping)]
        tem_trilha_valida = any(
            bool(str(t.get("nome") or "").strip())
            or bool(str(t.get("descricao") or "").strip())
            or bool(str(t.get("tempo_aproximacao") or "").strip())
            or bool(t.get("pontos"))
            for t in trilhas
        )
        if tem_trilha_valida:
            setores_com_trilha += 1
        else:
            acoes_trilhas.append(
                AcaoTarefaQualidade(
                    f"Adicionar trilha em {s_info.nome}", f"{s_info.uri_dados}/campo:trilhas"
                )
            )
    pts_tr, conc_tr = _pontuar_cobertura(
        setores_com_trilha, len(setores_info), 100, meta=0.90, possui_estrutura_base=tem_setores
    )
    t2_trilhas = TarefaQualidade(
        id_tarefa="etapa2_trilhas_aproximacao",
        titulo="Trilhas de aproximação nos setores",
        descricao="Cadastrar trilha de aproximação (tempo de caminhada, descrição ou pontos) nos setores.",
        etapa=2,
        pontos_obtidos=pts_tr,
        pontos_maximos=100,
        concluida=conc_tr,
        progresso_atual=setores_com_trilha,
        progresso_total=max(1, len(setores_info)),
        acoes=() if conc_tr else tuple(acoes_trilhas[:3]),
    )

    # 2.3 Extensão e proteções nas vias encordadas (>= 90%; dispensado para croqui 100% Boulder/Highline)
    vias_encordadas = [
        e
        for e in escaladas_info
        if e.modalidade in ("via_esportiva", "via_movel", "via_multiplas_enfiadas")
    ]
    vias_completas = 0
    acoes_vias: list[AcaoTarefaQualidade] = []
    for via_info in vias_encordadas:
        tem_ext, tem_prot, campo_ext, campo_prot = _diagnosticar_extensao_e_protecoes_via(
            via_info.modalidade, via_info.dados_modalidade
        )
        if tem_ext and tem_prot:
            vias_completas += 1
        else:
            if not tem_ext:
                acoes_vias.append(
                    AcaoTarefaQualidade(
                        f"Adicionar extensão ({via_info.nome})",
                        f"{via_info.uri_dados}/campo:{campo_ext}",
                    )
                )
            if not tem_prot:
                acoes_vias.append(
                    AcaoTarefaQualidade(
                        f"Adicionar proteções ({via_info.nome})",
                        f"{via_info.uri_dados}/campo:{campo_prot}",
                    )
                )
    pts_ext, conc_ext = _pontuar_cobertura(
        vias_completas,
        len(vias_encordadas),
        100,
        meta=0.90,
        dispensar_quando_vazio=True,
        possui_estrutura_base=tem_escaladas,
    )
    t2_extensao_protecoes = TarefaQualidade(
        id_tarefa="etapa2_extensao_protecoes_vias",
        titulo="Extensão e proteções nas vias encordadas",
        descricao="Informar extensão (metros) e proteções necessárias em pelo menos 90% das vias encordadas.",
        etapa=2,
        pontos_obtidos=pts_ext,
        pontos_maximos=100,
        concluida=conc_ext,
        progresso_atual=1 if (tem_escaladas and not vias_encordadas) else vias_completas,
        progresso_total=1 if not vias_encordadas else len(vias_encordadas),
        acoes=() if conc_ext else tuple(acoes_vias[:3]),
    )

    # 2.4 Traçados vetoriais (LinhaTrajeto) ou status_desenho_extraivel concluído
    status_desenho = dados.get("status_desenho_extraivel")
    desenho_extraido_ok = status_desenho in (
        "DESENHO_EXTRAIDO",
        "NAO_TEM_DESENHO",
        1,
        3,
    )
    escaladas_com_linha = 0
    acoes_linhas: list[AcaoTarefaQualidade] = []
    setores_ja_acionados_linha: set[str] = set()
    for e in escaladas_info:
        if (e.uid and e.uid in alvos_com_linha) or (e.nome and e.nome in alvos_com_linha):
            escaladas_com_linha += 1
        elif e.setor_info.uri_dados not in setores_ja_acionados_linha:
            setores_ja_acionados_linha.add(e.setor_info.uri_dados)
            uri_lin_setor = (
                e.setor_info.uri_mapa
                if bool(e.setor_info.dados.get("mapas"))
                else f"{e.setor_info.uri_dados}/campo:mapas"
            )
            acoes_linhas.append(
                AcaoTarefaQualidade(f"Desenhar linhas em {e.setor_info.nome}", uri_lin_setor)
            )
    if tem_escaladas and desenho_extraido_ok and escaladas_mapeadas > 0:
        pts_lin, conc_lin = 100, True
        prog_lin_atual = len(escaladas_info)
    else:
        pts_lin, conc_lin = _pontuar_cobertura(
            escaladas_com_linha,
            len(escaladas_info),
            100,
            meta=0.90,
            possui_estrutura_base=tem_escaladas,
        )
        prog_lin_atual = escaladas_com_linha
    if not acoes_linhas and not conc_lin:
        acoes_linhas.append(
            AcaoTarefaQualidade(
                f"Desenhar linhas em {setores_info[0].nome}",
                setores_info[0].uri_mapa
                if bool(setores_info[0].dados.get("mapas"))
                else f"{setores_info[0].uri_dados}/campo:mapas",
            )
            if setores_info
            else AcaoTarefaQualidade(
                "Desenhar linhas no mapa", "page:dados/node:root/node:Croqui/campo:picos"
            )
        )
    t2_tracados = TarefaQualidade(
        id_tarefa="etapa2_tracados_vetoriais",
        titulo="Traçados vetoriais nas linhas de escalada",
        descricao="Desenhar linhas de trajeto vetoriais nos mapas ou concluir a extração de desenho do croqui.",
        etapa=2,
        pontos_obtidos=pts_lin,
        pontos_maximos=100,
        concluida=conc_lin,
        progresso_atual=prog_lin_atual,
        progresso_total=max(1, len(escaladas_info)),
        acoes=() if conc_lin else tuple(acoes_linhas[:3]),
    )

    # 2.5 Escaladas de destaque nos setores (>= 90%)
    setores_com_escaladas = [s for s in setores_info if bool(s.dados.get("escaladas"))]
    setores_com_destaque = 0
    acoes_destaque: list[AcaoTarefaQualidade] = []
    for s_info in setores_com_escaladas:
        tem_dest = any(
            bool(_extrair_modalidade_escalada(dict(e))[1].get("destaque"))
            for e in (s_info.dados.get("escaladas") or [])
        )
        if tem_dest:
            setores_com_destaque += 1
        else:
            acoes_destaque.append(
                AcaoTarefaQualidade(
                    f"Escolher destaque em {s_info.nome}",
                    f"{s_info.uri_dados}/expando:escaladas/item:0/campo:destaque",
                )
            )
    pts_dest, conc_dest = _pontuar_cobertura(
        setores_com_destaque,
        len(setores_com_escaladas),
        100,
        meta=0.90,
        possui_estrutura_base=len(setores_com_escaladas) > 0,
    )
    t2_destaques = TarefaQualidade(
        id_tarefa="etapa2_destaques_setores",
        titulo="Escaladas de destaque nos setores",
        descricao="Marcar ao menos uma escalada clássica/imperdível como destaque em pelo menos 90% dos setores.",
        etapa=2,
        pontos_obtidos=pts_dest,
        pontos_maximos=100,
        concluida=conc_dest,
        progresso_atual=setores_com_destaque,
        progresso_total=max(1, len(setores_com_escaladas)),
        acoes=() if conc_dest else tuple(acoes_destaque[:3]),
    )

    # 2.6 Descrições/betas textuais nas escaladas (>= 50%)
    escaladas_com_desc = 0
    acoes_desc_esc: list[AcaoTarefaQualidade] = []
    for esc_info in escaladas_info:
        if bool(str(esc_info.dados_modalidade.get("descricao") or "").strip()):
            escaladas_com_desc += 1
        else:
            acoes_desc_esc.append(
                AcaoTarefaQualidade(
                    f"Adicionar descrição ({esc_info.nome})",
                    f"{esc_info.uri_dados}/campo:descricao",
                )
            )
    pts_de, conc_de = _pontuar_cobertura(
        escaladas_com_desc,
        len(escaladas_info),
        100,
        meta=0.50,
        possui_estrutura_base=tem_escaladas,
    )
    t2_descricoes = TarefaQualidade(
        id_tarefa="etapa2_descricoes_escaladas",
        titulo="Descrição e beta textual nas escaladas",
        descricao="Adicionar descrição, dicas de movimentação ou segurança em pelo menos 50% das escaladas.",
        etapa=2,
        pontos_obtidos=pts_de,
        pontos_maximos=100,
        concluida=conc_de,
        progresso_atual=escaladas_com_desc,
        progresso_total=max(1, len(escaladas_info)),
        acoes=() if conc_de else tuple(acoes_desc_esc[:3]),
    )

    # 2.7 Fotos de capa nos setores e grupos (>= 90%)
    entidades_capa: list[tuple[str, dict[str, Any], str]] = [
        (s.nome, s.dados, s.uri_dados) for s in setores_info
    ] + [(nome_g, dados_g, uri_g) for _, nome_g, dados_g, uri_g in grupos_info]
    com_capa = 0
    acoes_capa: list[AcaoTarefaQualidade] = []
    for nome_ent, dados_ent, uri_ent in entidades_capa:
        if bool(str(dados_ent.get("caminho_imagem_capa") or "").strip()):
            com_capa += 1
        else:
            acoes_capa.append(
                AcaoTarefaQualidade(
                    f"Adicionar foto de capa ({nome_ent})",
                    f"{uri_ent}/campo:caminho_imagem_capa",
                )
            )
    pts_capa, conc_capa = _pontuar_cobertura(
        com_capa, len(entidades_capa), 100, meta=0.90, possui_estrutura_base=len(entidades_capa) > 0
    )
    t2_fotos_capa = TarefaQualidade(
        id_tarefa="etapa2_fotos_capa_setores",
        titulo="Foto de capa nos setores e grupos",
        descricao="Definir uma foto de capa em pelo menos 90% dos setores e grupos.",
        etapa=2,
        pontos_obtidos=pts_capa,
        pontos_maximos=100,
        concluida=conc_capa,
        progresso_atual=com_capa,
        progresso_total=max(1, len(entidades_capa)),
        acoes=() if conc_capa else tuple(acoes_capa[:3]),
    )

    tarefas_etapa2 = (
        t2_coord_setores,
        t2_trilhas,
        t2_extensao_protecoes,
        t2_tracados,
        t2_destaques,
        t2_descricoes,
        t2_fotos_capa,
    )

    # =========================================================================
    # ETAPA 3: Lapidação, História e Comunidade (10 pontos cada)
    # =========================================================================

    # 3.1 Créditos aos autores
    tem_creditos = any(bool(str(c).strip()) for c in (dados.get("creditos") or []))
    t3_creditos = TarefaQualidade(
        id_tarefa="etapa3_creditos",
        titulo="Créditos aos autores do croqui",
        descricao="Registrar os nomes dos autores e colaboradores na lista de créditos do croqui.",
        etapa=3,
        pontos_obtidos=10 if tem_creditos else 0,
        pontos_maximos=10,
        concluida=tem_creditos,
        progresso_atual=1 if tem_creditos else 0,
        progresso_total=1,
        acoes=(
            ()
            if tem_creditos
            else (
                AcaoTarefaQualidade(
                    "Adicionar créditos", "page:dados/node:root/node:Croqui/campo:creditos"
                ),
            )
        ),
    )

    # 3.2 Conquistadores e data de abertura (>= 90%)
    esc_com_hist = 0
    acoes_hist: list[AcaoTarefaQualidade] = []
    for esc_info in escaladas_info:
        conqs = [
            c for c in (esc_info.dados_modalidade.get("conquistadores") or []) if str(c).strip()
        ]
        data_ab = str(esc_info.dados_modalidade.get("data_abertura") or "").strip()
        if conqs or data_ab:
            esc_com_hist += 1
        else:
            acoes_hist.append(
                AcaoTarefaQualidade(
                    f"Adicionar conquistadores ({esc_info.nome})",
                    f"{esc_info.uri_dados}/campo:conquistadores",
                )
            )
    pts_hist, conc_hist = _pontuar_cobertura(
        esc_com_hist, len(escaladas_info), 10, meta=0.90, possui_estrutura_base=tem_escaladas
    )
    t3_conquistadores = TarefaQualidade(
        id_tarefa="etapa3_conquistadores_datas",
        titulo="Conquistadores e data de abertura",
        descricao="Documentar conquistadores ou data de abertura em pelo menos 90% das escaladas.",
        etapa=3,
        pontos_obtidos=pts_hist,
        pontos_maximos=10,
        concluida=conc_hist,
        progresso_atual=esc_com_hist,
        progresso_total=max(1, len(escaladas_info)),
        acoes=() if conc_hist else tuple(acoes_hist[:3]),
    )

    # 3.3 Tipo de parede e exposição (>= 90%)
    esc_com_parede = 0
    acoes_parede: list[AcaoTarefaQualidade] = []
    for esc_info in escaladas_info:
        tem_tp = _valor_enum_preenchido(esc_info.dados_modalidade.get("tipo_parede"))
        tem_exp = _valor_enum_preenchido(esc_info.dados_modalidade.get("exposicao"))
        if tem_tp or tem_exp:
            esc_com_parede += 1
        else:
            campo_par = (
                "exposicao"
                if esc_info.modalidade in ("via_multiplas_enfiadas", "highline")
                else "tipo_parede"
            )
            acoes_parede.append(
                AcaoTarefaQualidade(
                    f"Definir tipo de parede ({esc_info.nome})",
                    f"{esc_info.uri_dados}/campo:{campo_par}",
                )
            )
    pts_par, conc_par = _pontuar_cobertura(
        esc_com_parede, len(escaladas_info), 10, meta=0.90, possui_estrutura_base=tem_escaladas
    )
    t3_parede = TarefaQualidade(
        id_tarefa="etapa3_tipo_parede_exposicao",
        titulo="Tipo de parede e grau de exposição",
        descricao="Informar inclinação da parede ou grau de exposição em pelo menos 90% das escaladas.",
        etapa=3,
        pontos_obtidos=pts_par,
        pontos_maximos=10,
        concluida=conc_par,
        progresso_atual=esc_com_parede,
        progresso_total=max(1, len(escaladas_info)),
        acoes=() if conc_par else tuple(acoes_parede[:3]),
    )

    # 3.4 Indicadores de família e sinal de celular nos setores (>= 90%)
    setores_com_ind = 0
    acoes_ind: list[AcaoTarefaQualidade] = []
    for s_info in setores_info:
        tem_ind = any(
            k in s_info.dados
            for k in ("sinal_de_celular", "amigavel_a_criancas", "amigavel_a_bebes")
        )
        if tem_ind:
            setores_com_ind += 1
        else:
            acoes_ind.append(
                AcaoTarefaQualidade(
                    f"Preencher indicadores ({s_info.nome})",
                    f"{s_info.uri_dados}/campo:sinal_de_celular",
                )
            )
    pts_ind, conc_ind = _pontuar_cobertura(
        setores_com_ind, len(setores_info), 10, meta=0.90, possui_estrutura_base=tem_setores
    )
    t3_indicadores = TarefaQualidade(
        id_tarefa="etapa3_indicadores_familia_celular",
        titulo="Sinal de celular e acesso para crianças/bebês",
        descricao="Informar nos setores se há sinal de celular e se a base é amigável a crianças ou bebês.",
        etapa=3,
        pontos_obtidos=pts_ind,
        pontos_maximos=10,
        concluida=conc_ind,
        progresso_atual=setores_com_ind,
        progresso_total=max(1, len(setores_info)),
        acoes=() if conc_ind else tuple(acoes_ind[:3]),
    )

    # 3.5 Vídeos de beta e ausência de betas pendentes
    tem_midia_beta = any(
        bool(e.dados_escalada.get("betas"))
        or bool(str(e.dados_modalidade.get("url_video_beta") or "").strip())
        for e in escaladas_info
    )
    tem_beta_pendente = bool(
        croqui_path is not None and (croqui_path / "betas_pendentes.binarypb").is_file()
    )
    betas_ok = tem_escaladas and tem_midia_beta and not tem_beta_pendente
    rotulo_acao_betas = (
        "Revisar betas pendentes" if tem_beta_pendente else "Adicionar vídeo de beta"
    )
    t3_betas = TarefaQualidade(
        id_tarefa="etapa3_videos_betas",
        titulo="Vídeos de beta e curadoria em dia",
        descricao="Ter vídeos/mídias de beta vinculados às escaladas e nenhum beta pendente de curadoria.",
        etapa=3,
        pontos_obtidos=10 if betas_ok else 0,
        pontos_maximos=10,
        concluida=betas_ok,
        progresso_atual=1 if betas_ok else 0,
        progresso_total=1,
        acoes=() if betas_ok else (AcaoTarefaQualidade(rotulo_acao_betas, "page:betas"),),
    )

    # 3.6 Associação local ou chave Pix de manutenção
    picos_com_assoc = 0
    acoes_assoc: list[AcaoTarefaQualidade] = []
    tem_pix_escalada = any(
        bool(str(e.dados_modalidade.get("chave_pix_manutencao") or "").strip())
        for e in escaladas_info
    )
    for p_idx, pico in enumerate(picos_raw):
        tem_assoc = (
            bool(str(pico.get("nome_associacao") or "").strip())
            or bool(str(pico.get("url_filiacao_associacao") or "").strip())
            or bool(str(pico.get("chave_pix_manutencao") or "").strip())
            or bool(pico.get("patrocinadores"))
            or tem_pix_escalada
        )
        if tem_assoc:
            picos_com_assoc += 1
        else:
            nome_p = str(pico.get("nome") or f"Pico {p_idx + 1}").strip()
            sufixo_p = f" ({nome_p})" if multiplos_picos else ""
            uri_pico = f"page:dados/node:root/node:Croqui/expando:picos/item:{p_idx}"
            acoes_assoc.append(
                AcaoTarefaQualidade(
                    f"Adicionar associação{sufixo_p}", f"{uri_pico}/campo:nome_associacao"
                )
            )
            acoes_assoc.append(
                AcaoTarefaQualidade(
                    f"Adicionar chave Pix{sufixo_p}",
                    f"{uri_pico}/campo:chave_pix_manutencao",
                )
            )
    pts_assoc, conc_assoc = _pontuar_cobertura(
        picos_com_assoc, len(picos_raw), 10, meta=0.90, possui_estrutura_base=tem_picos
    )
    t3_associacao = TarefaQualidade(
        id_tarefa="etapa3_associacao_pix",
        titulo="Associação local ou chave Pix de manutenção",
        descricao="Informar associação responsável, link de filiação ou chave Pix para manutenção nos picos.",
        etapa=3,
        pontos_obtidos=pts_assoc,
        pontos_maximos=10,
        concluida=conc_assoc,
        progresso_atual=picos_com_assoc,
        progresso_total=max(1, len(picos_raw)),
        acoes=() if conc_assoc else tuple(acoes_assoc[:3]),
    )

    # 3.7 Flags de revisão manual e bounding circle
    tem_rev_manual = bool(dados.get("revisado_manualmente") is True)
    tem_rev_bc = bool(dados.get("revisado_bounding_circle") is True)
    itens_revisao = sum([tem_rev_manual, tem_rev_bc])
    pts_rev, conc_rev = _pontuar_cobertura(itens_revisao, 2, 10, meta=1.0)
    acoes_rev: list[AcaoTarefaQualidade] = []
    if not tem_rev_manual:
        acoes_rev.append(
            AcaoTarefaQualidade(
                "Marcar revisão manual",
                "page:dados/node:root/node:Croqui/campo:revisado_manualmente",
            )
        )
    if not tem_rev_bc:
        acoes_rev.append(
            AcaoTarefaQualidade(
                "Marcar revisão de bounding circle",
                "page:dados/node:root/node:Croqui/campo:revisado_bounding_circle",
            )
        )
    t3_revisao = TarefaQualidade(
        id_tarefa="etapa3_revisao_final",
        titulo="Revisão manual e de enquadramento concluída",
        descricao="Marcar as confirmações de Revisado Manualmente e Revisado Bounding Circle no croqui.",
        etapa=3,
        pontos_obtidos=pts_rev,
        pontos_maximos=10,
        concluida=conc_rev,
        progresso_atual=itens_revisao,
        progresso_total=2,
        acoes=() if conc_rev else tuple(acoes_rev),
    )

    tarefas_etapa3 = (
        t3_creditos,
        t3_conquistadores,
        t3_parede,
        t3_indicadores,
        t3_betas,
        t3_associacao,
        t3_revisao,
    )

    def _montar_resumo(
        num: int, titulo: str, tarefas: tuple[TarefaQualidade, ...]
    ) -> ResumoEtapaQualidade:
        pts_obt = sum(t.pontos_obtidos for t in tarefas)
        pts_max = sum(t.pontos_maximos for t in tarefas)
        concluidas = sum(1 for t in tarefas if t.concluida)
        total_t = len(tarefas)
        return ResumoEtapaQualidade(
            numero_etapa=num,
            titulo=titulo,
            pontos_obtidos=pts_obt,
            pontos_maximos=pts_max,
            tarefas_concluidas=concluidas,
            total_tarefas=total_t,
            concluida=(concluidas == total_t),
            tarefas=tarefas,
        )

    resumo_e1 = _montar_resumo(1, "Etapa 1: Essenciais para Publicação", tarefas_etapa1)
    resumo_e2 = _montar_resumo(
        2, "Etapa 2: Qualidade, Navegação Offline e Segurança", tarefas_etapa2
    )
    resumo_e3 = _montar_resumo(3, "Etapa 3: Lapidação, História e Comunidade", tarefas_etapa3)

    etapas = (resumo_e1, resumo_e2, resumo_e3)
    nota_total = sum(e.pontos_obtidos for e in etapas)
    nota_max = sum(e.pontos_maximos for e in etapas)

    return ResultadoNotaQualidade(
        nota_qualidade=nota_total,
        nota_maxima=nota_max,
        pronto_para_publicar=resumo_e1.concluida,
        publicado=bool(dados.get("publicar_croqui") is True),
        etapas=etapas,
    )
