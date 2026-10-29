# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para cálculo de diff semântico (pareado por UID) e visual (mapas e imagens)
entre o estado base e o estado compilado de uma Pull Request.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from aresta_api.proto.generated import croqui_pb2


@dataclass(frozen=True)
class AlteracaoCampo:
    """Representa a mudança de valor de um campo individual de uma entidade."""

    nome_campo: str
    valor_antes: str
    valor_depois: str
    eh_markdown: bool = False


@dataclass(frozen=True)
class PontoMapaVisual:
    """Representação geométrica normalizada de um PontoDeInteresse para overlay SVG."""

    uid: str
    rotulo: str
    tipo_geometria: str
    x: int
    y: int
    raio: int = 12
    largura: int = 0
    altura: int = 0
    coordenadas_poligono: tuple[tuple[int, int], ...] = ()
    caminho_svg_linha: str = ""
    cor: str = ""


@dataclass(frozen=True)
class DiffPontoMapa:
    """Resultado da comparação de um ponto de interesse de mapa por UID."""

    uid: str
    status: str
    ponto_antes: PontoMapaVisual | None
    ponto_depois: PontoMapaVisual | None
    alteracoes_campos: list[AlteracaoCampo] = field(default_factory=list)


@dataclass(frozen=True)
class DiffMapa:
    """Resultado da comparação semântica e visual de um Mapa."""

    caminho_imagem: str
    contexto: str
    status: str
    imagem_alterada: bool
    caminho_imagem_base_relativo: str | None
    largura_antes: int
    altura_antes: int
    largura_depois: int
    altura_depois: int
    tamanho_kb_antes: float
    tamanho_kb_depois: float
    pontos: list[DiffPontoMapa] = field(default_factory=list)


@dataclass(frozen=True)
class DiffEntidade:
    """Resultado da comparação de uma entidade estrutural (Pico, Grupo, Setor, Escalada) por UID."""

    tipo_entidade: str
    uid: str
    nome_antes: str
    nome_depois: str
    contexto: str
    status: str
    subtipo_antes: str = ""
    subtipo_depois: str = ""
    resumo_curto: str = ""
    alteracoes_campos: list[AlteracaoCampo] = field(default_factory=list)


@dataclass(frozen=True)
class DiffImagem:
    """Resultado da comparação de um arquivo de imagem (mapa, capa, thumbnail ou Markdown)."""

    caminho_relativo: str
    categoria: str
    onde_usada: str
    status: str
    caminho_pr_relativo: str | None
    caminho_base_relativo: str | None
    largura_antes: int = 0
    altura_antes: int = 0
    largura_depois: int = 0
    altura_depois: int = 0
    tamanho_kb_antes: float = 0.0
    tamanho_kb_depois: float = 0.0


@dataclass
class DiffCroqui:
    """Resumo completo de alterações de um croqui individual na Pull Request."""

    id_croqui: str
    uid: str
    nome: str
    status: str
    alteracoes_metadados: list[AlteracaoCampo] = field(default_factory=list)
    entidades: list[DiffEntidade] = field(default_factory=list)
    mapas: list[DiffMapa] = field(default_factory=list)
    imagens: list[DiffImagem] = field(default_factory=list)
    arquivos_base_copiados: list[str] = field(default_factory=list)


@dataclass
class ResumoDiffPullRequest:
    """Resumo consolidado de todos os croquis analisados na Pull Request."""

    croquis: list[DiffCroqui] = field(default_factory=list)

    def _contar_entidades(self, tipo: str, status: str) -> int:
        return sum(
            1
            for croqui in self.croquis
            for entidade in croqui.entidades
            if entidade.tipo_entidade == tipo and entidade.status == status
        )

    @property
    def total_escaladas_adicionadas(self) -> int:
        return self._contar_entidades("escalada", "adicionado")

    @property
    def total_escaladas_modificadas(self) -> int:
        return self._contar_entidades("escalada", "modificado")

    @property
    def total_escaladas_removidas(self) -> int:
        return self._contar_entidades("escalada", "removido")

    @property
    def total_setores_adicionados(self) -> int:
        return self._contar_entidades("setor", "adicionado")

    @property
    def total_setores_modificados(self) -> int:
        return self._contar_entidades("setor", "modificado")

    @property
    def total_setores_removidos(self) -> int:
        return self._contar_entidades("setor", "removido")

    @property
    def total_mapas_alterados(self) -> int:
        return sum(
            1
            for croqui in self.croquis
            for mapa in croqui.mapas
            if mapa.status != "inalterado"
        )

    @property
    def total_imagens_alteradas(self) -> int:
        return sum(len(croqui.imagens) for croqui in self.croquis)


def _carregar_croqui(caminho_pb: Path) -> croqui_pb2.Croqui:
    croqui = croqui_pb2.Croqui()
    croqui.ParseFromString(caminho_pb.read_bytes())
    return croqui


def _calcular_sha256_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _obter_dimensoes_e_peso_imagem(caminho: Path) -> tuple[int, int, float]:
    if not caminho.is_file():
        return (0, 0, 0.0)
    tamanho_kb = round(caminho.stat().st_size / 1024.0, 1)
    with Image.open(caminho) as img:
        largura, altura = img.size
    return (largura, altura, tamanho_kb)


def _comparar_valores(
    alteracoes: list[AlteracaoCampo],
    nome_campo: str,
    antes: str,
    depois: str,
    *,
    eh_markdown: bool = False,
) -> None:
    if antes != depois:
        alteracoes.append(
            AlteracaoCampo(
                nome_campo=nome_campo,
                valor_antes=antes,
                valor_depois=depois,
                eh_markdown=eh_markdown,
            )
        )


def _extrair_campos_escalada(
    escalada: croqui_pb2.Escalada,
) -> tuple[str, str, str, list[ tuple[str, str, bool] ]]:
    """Retorna (subtipo, nome, resumo_curto, lista de (nome_campo, valor, eh_markdown))."""
    subtipo = escalada.WhichOneof("tipo") or "via_esportiva"
    if subtipo == "via_esportiva":
        v = escalada.via_esportiva
        grau = croqui_pb2.GrauVia.GrauVia.Name(v.dificuldade)
        resumo = f"{grau} · {v.extensao}m" if v.extensao else grau
        campos = [
            ("Nome", v.nome, False),
            ("Dificuldade", grau, False),
            ("Extensão (m)", str(v.extensao), False),
            ("Proteções Intermediárias", str(v.quantidade_protecoes_intermediarias), False),
            ("Conquistadores", ", ".join(v.conquistadores), False),
            ("Descrição", v.descricao, True),
        ]
        return (subtipo, v.nome, resumo, campos)
    if subtipo == "via_movel":
        vm = escalada.via_movel
        grau = croqui_pb2.GrauVia.GrauVia.Name(vm.dificuldade)
        resumo = f"{grau} · {vm.extensao}m" if vm.extensao else grau
        campos = [
            ("Nome", vm.nome, False),
            ("Dificuldade", grau, False),
            ("Extensão (m)", str(vm.extensao), False),
            ("Proteções Móveis", vm.protecoes_moveis, False),
            ("Conquistadores", ", ".join(vm.conquistadores), False),
            ("Descrição", vm.descricao, True),
        ]
        return (subtipo, vm.nome, resumo, campos)
    if subtipo == "boulder":
        b = escalada.boulder
        grau = croqui_pb2.GrauBoulder.GrauBoulder.Name(b.dificuldade)
        campos = [
            ("Nome", b.nome, False),
            ("Dificuldade", grau, False),
            ("Conquistadores", ", ".join(b.conquistadores), False),
            ("Descrição", b.descricao, True),
        ]
        return (subtipo, b.nome, grau, campos)
    if subtipo == "via_multiplas_enfiadas":
        vme = escalada.via_multiplas_enfiadas
        grau = croqui_pb2.GrauVia.GrauVia.Name(vme.dificuldade_maxima)
        resumo = f"{grau} · {vme.comprimento_total}m ({vme.numero_enfiadas} enf.)"
        campos = [
            ("Nome", vme.nome, False),
            ("Dificuldade Máxima", grau, False),
            ("Comprimento Total (m)", str(vme.comprimento_total), False),
            ("Número de Enfiadas", str(vme.numero_enfiadas), False),
            ("Conquistadores", ", ".join(vme.conquistadores), False),
            ("Descrição", vme.descricao, True),
        ]
        return (subtipo, vme.nome, resumo, campos)
    hl = escalada.highline
    resumo = f"{hl.distancia}m · alt {hl.altura}m"
    campos = [
        ("Nome", hl.nome, False),
        ("Distância (m)", str(hl.distancia), False),
        ("Altura (m)", str(hl.altura), False),
        ("Conquistadores", ", ".join(hl.conquistadores), False),
        ("Descrição", hl.descricao, True),
    ]
    return ("highline", hl.nome, resumo, campos)


def _converter_ponto_visual(ponto: croqui_pb2.Mapa.PontoDeInteresse) -> PontoMapaVisual:
    uid = ponto.uid or ponto.id
    rotulo = ponto.rotulo or ponto.label or ponto.texto_visivel
    tipo_area = ponto.WhichOneof("tipo_area") or "circulo"
    if tipo_area == "circulo":
        return PontoMapaVisual(
            uid=uid,
            rotulo=rotulo,
            tipo_geometria="circulo",
            x=ponto.circulo.x,
            y=ponto.circulo.y,
            raio=ponto.circulo.raio or 12,
            cor=ponto.cor,
        )
    if tipo_area == "quadrado":
        lado = ponto.quadrado.lado or 20
        return PontoMapaVisual(
            uid=uid,
            rotulo=rotulo,
            tipo_geometria="quadrado",
            x=ponto.quadrado.x,
            y=ponto.quadrado.y,
            largura=lado,
            altura=lado,
            cor=ponto.cor,
        )
    if tipo_area == "retangulo":
        return PontoMapaVisual(
            uid=uid,
            rotulo=rotulo,
            tipo_geometria="retangulo",
            x=ponto.retangulo.x,
            y=ponto.retangulo.y,
            largura=ponto.retangulo.comprimento or 30,
            altura=ponto.retangulo.largura or 20,
            cor=ponto.cor,
        )
    if tipo_area == "poligono":
        coords = list(ponto.poligono.coordenadas)
        pares = tuple((coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2))
        cx = pares[0][0] if pares else 0
        cy = pares[0][1] if pares else 0
        return PontoMapaVisual(
            uid=uid,
            rotulo=rotulo,
            tipo_geometria="poligono",
            x=cx,
            y=cy,
            coordenadas_poligono=pares,
            cor=ponto.cor,
        )
    caminho_svg = ponto.linha.compilado.caminho_svg
    return PontoMapaVisual(
        uid=uid,
        rotulo=rotulo,
        tipo_geometria="linha",
        x=0,
        y=0,
        caminho_svg_linha=caminho_svg,
        cor=ponto.cor,
    )


@dataclass
class _ColecaoExtraida:
    grupos: dict[str, tuple[str, croqui_pb2.Grupo]] = field(default_factory=dict)
    setores: dict[str, tuple[str, croqui_pb2.Setor]] = field(default_factory=dict)
    escaladas: dict[str, tuple[str, croqui_pb2.Escalada]] = field(default_factory=dict)
    mapas: dict[str, tuple[str, croqui_pb2.Mapa]] = field(default_factory=dict)
    usos_imagens: dict[str, tuple[str, str]] = field(default_factory=dict)


def _extrair_colecao_croqui(croqui: croqui_pb2.Croqui) -> _ColecaoExtraida:
    col = _ColecaoExtraida()
    if croqui.caminho_thumbnail:
        col.usos_imagens[croqui.caminho_thumbnail] = ("thumbnail", f"Thumbnail de {croqui.nome}")

    def _registrar_mapa(contexto: str, mapa: croqui_pb2.Mapa) -> None:
        if mapa.caminho_imagem_mapa:
            col.mapas[mapa.caminho_imagem_mapa] = (contexto, mapa)
            col.usos_imagens[mapa.caminho_imagem_mapa] = ("mapa", f"Mapa ({contexto})")

    def _processar_setor(contexto_pai: str, setor: croqui_pb2.Setor) -> None:
        uid_setor = setor.uid or f"setor:{setor.nome}"
        col.setores[uid_setor] = (contexto_pai, setor)
        ctx_setor = f"{contexto_pai} > {setor.nome}"
        if setor.caminho_imagem_capa:
            col.usos_imagens[setor.caminho_imagem_capa] = ("capa", f"Capa do Setor {setor.nome}")
        for m in setor.mapas:
            _registrar_mapa(ctx_setor, m)
        for esc in setor.escaladas:
            _, nome_esc, _, _ = _extrair_campos_escalada(esc)
            uid_esc = esc.uid or f"escalada:{nome_esc}"
            col.escaladas[uid_esc] = (ctx_setor, esc)
            for m_esc in esc.mapas:
                _registrar_mapa(f"{ctx_setor} > {nome_esc}", m_esc)

    for pico in croqui.picos:
        ctx_pico = pico.nome
        for m_geral in pico.mapas_gerais.conteudo.mapas:
            _registrar_mapa(ctx_pico, m_geral)
        for item in pico.setores_ou_grupos:
            if item.WhichOneof("tipo") == "grupo":
                grupo = item.grupo.conteudo
                uid_grupo = grupo.uid or f"grupo:{grupo.nome}"
                col.grupos[uid_grupo] = (ctx_pico, grupo)
                ctx_grupo = f"{ctx_pico} > {grupo.nome}"
                if grupo.caminho_imagem_capa:
                    col.usos_imagens[grupo.caminho_imagem_capa] = (
                        "capa",
                        f"Capa do Grupo {grupo.nome}",
                    )
                for m_grupo in grupo.mapas:
                    _registrar_mapa(ctx_grupo, m_grupo)
                for arq_setor in grupo.setores:
                    _processar_setor(ctx_grupo, arq_setor.conteudo)
            else:
                _processar_setor(ctx_pico, item.setor.conteudo)

    return col


def _comparar_pontos_mapa(
    mapa_base: croqui_pb2.Mapa | None,
    mapa_pr: croqui_pb2.Mapa | None,
) -> list[DiffPontoMapa]:
    pontos_base = {
        (p.uid or p.id): _converter_ponto_visual(p)
        for p in (mapa_base.pontos_de_interesse if mapa_base else [])
    }
    pontos_pr = {
        (p.uid or p.id): _converter_ponto_visual(p)
        for p in (mapa_pr.pontos_de_interesse if mapa_pr else [])
    }
    todos_uids = list(dict.fromkeys(list(pontos_base.keys()) + list(pontos_pr.keys())))
    resultado: list[DiffPontoMapa] = []

    for uid in todos_uids:
        antes = pontos_base.get(uid)
        depois = pontos_pr.get(uid)
        if antes is None:
            resultado.append(
                DiffPontoMapa(uid=uid, status="adicionado", ponto_antes=None, ponto_depois=depois)
            )
        elif depois is None:
            resultado.append(
                DiffPontoMapa(uid=uid, status="removido", ponto_antes=antes, ponto_depois=None)
            )
        elif antes != depois:
            alteracoes: list[AlteracaoCampo] = []
            _comparar_valores(alteracoes, "Rótulo", antes.rotulo, depois.rotulo)
            _comparar_valores(
                alteracoes,
                "Posição",
                f"({antes.x}, {antes.y})",
                f"({depois.x}, {depois.y})",
            )
            _comparar_valores(
                alteracoes,
                "Traçado SVG",
                antes.caminho_svg_linha,
                depois.caminho_svg_linha,
            )
            resultado.append(
                DiffPontoMapa(
                    uid=uid,
                    status="modificado",
                    ponto_antes=antes,
                    ponto_depois=depois,
                    alteracoes_campos=alteracoes,
                )
            )
        else:
            resultado.append(
                DiffPontoMapa(uid=uid, status="inalterado", ponto_antes=antes, ponto_depois=depois)
            )
    return resultado


def _copiar_para_base(origem: Path, dir_pr: Path, rel_destino_base: str, copiados: list[str]) -> str:
    destino = dir_pr / rel_destino_base
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, destino)
    copiados.append(rel_destino_base)
    return rel_destino_base


def _processar_diff_croqui(
    id_croqui: str,
    dir_base: Path,
    dir_pr: Path,
) -> DiffCroqui:
    caminho_pb_pr = dir_pr / id_croqui / "compilado.binarypb"
    croqui_pr = _carregar_croqui(caminho_pb_pr)
    caminho_pb_base = dir_base / id_croqui / "compilado.binarypb"
    eh_novo = not caminho_pb_base.is_file()
    croqui_base = croqui_pb2.Croqui() if eh_novo else _carregar_croqui(caminho_pb_base)

    col_base = _extrair_colecao_croqui(croqui_base)
    col_pr = _extrair_colecao_croqui(croqui_pr)
    copiados_base: list[str] = []

    alteracoes_meta: list[AlteracaoCampo] = []
    if not eh_novo:
        _comparar_valores(alteracoes_meta, "Nome do Croqui", croqui_base.nome, croqui_pr.nome)
        _comparar_valores(
            alteracoes_meta,
            "Descrição do Croqui",
            croqui_base.descricao,
            croqui_pr.descricao,
            eh_markdown=True,
        )

    entidades: list[DiffEntidade] = []

    # 1. Grupos
    uids_grupos = list(dict.fromkeys(list(col_base.grupos.keys()) + list(col_pr.grupos.keys())))
    for uid in uids_grupos:
        item_b = col_base.grupos.get(uid)
        item_p = col_pr.grupos.get(uid)
        if item_b is None and item_p is not None:
            ctx, g_p = item_p
            entidades.append(
                DiffEntidade(
                    tipo_entidade="grupo",
                    uid=uid,
                    nome_antes="",
                    nome_depois=g_p.nome,
                    contexto=ctx,
                    status="adicionado",
                )
            )
        elif item_p is None and item_b is not None:
            ctx, g_b = item_b
            entidades.append(
                DiffEntidade(
                    tipo_entidade="grupo",
                    uid=uid,
                    nome_antes=g_b.nome,
                    nome_depois="",
                    contexto=ctx,
                    status="removido",
                )
            )
        elif item_b is not None and item_p is not None:
            ctx, g_p = item_p
            _, g_b = item_b
            alt_g: list[AlteracaoCampo] = []
            _comparar_valores(alt_g, "Nome", g_b.nome, g_p.nome)
            _comparar_valores(alt_g, "Descrição", g_b.descricao, g_p.descricao, eh_markdown=True)
            if alt_g:
                entidades.append(
                    DiffEntidade(
                        tipo_entidade="grupo",
                        uid=uid,
                        nome_antes=g_b.nome,
                        nome_depois=g_p.nome,
                        contexto=ctx,
                        status="modificado",
                        alteracoes_campos=alt_g,
                    )
                )

    # 2. Setores
    uids_setores = list(dict.fromkeys(list(col_base.setores.keys()) + list(col_pr.setores.keys())))
    for uid in uids_setores:
        setor_b = col_base.setores.get(uid)
        setor_p = col_pr.setores.get(uid)
        if setor_b is None and setor_p is not None:
            ctx, s_p = setor_p
            entidades.append(
                DiffEntidade(
                    tipo_entidade="setor",
                    uid=uid,
                    nome_antes="",
                    nome_depois=s_p.nome,
                    contexto=ctx,
                    status="adicionado",
                )
            )
        elif setor_p is None and setor_b is not None:
            ctx, s_b = setor_b
            entidades.append(
                DiffEntidade(
                    tipo_entidade="setor",
                    uid=uid,
                    nome_antes=s_b.nome,
                    nome_depois="",
                    contexto=ctx,
                    status="removido",
                )
            )
        elif setor_b is not None and setor_p is not None:
            ctx, s_p = setor_p
            _, s_b = setor_b
            alt_s: list[AlteracaoCampo] = []
            _comparar_valores(alt_s, "Nome", s_b.nome, s_p.nome)
            _comparar_valores(alt_s, "Descrição", s_b.descricao, s_p.descricao, eh_markdown=True)
            _comparar_valores(
                alt_s,
                "Foto de Capa",
                s_b.caminho_imagem_capa,
                s_p.caminho_imagem_capa,
            )
            if alt_s:
                entidades.append(
                    DiffEntidade(
                        tipo_entidade="setor",
                        uid=uid,
                        nome_antes=s_b.nome,
                        nome_depois=s_p.nome,
                        contexto=ctx,
                        status="modificado",
                        alteracoes_campos=alt_s,
                    )
                )

    # 3. Escaladas
    uids_escaladas = list(
        dict.fromkeys(list(col_base.escaladas.keys()) + list(col_pr.escaladas.keys()))
    )
    for uid in uids_escaladas:
        esc_b = col_base.escaladas.get(uid)
        esc_p = col_pr.escaladas.get(uid)
        if esc_b is None and esc_p is not None:
            ctx, e_p = esc_p
            sub_p, nome_p, resumo_p, campos_p = _extrair_campos_escalada(e_p)
            entidades.append(
                DiffEntidade(
                    tipo_entidade="escalada",
                    uid=uid,
                    nome_antes="",
                    nome_depois=nome_p,
                    contexto=ctx,
                    status="adicionado",
                    subtipo_depois=sub_p,
                    resumo_curto=resumo_p,
                    alteracoes_campos=[
                        AlteracaoCampo(nome_campo=c, valor_antes="", valor_depois=v, eh_markdown=md)
                        for c, v, md in campos_p
                        if v and v != "0" and v != "INDEFINIDO"
                    ],
                )
            )
        elif esc_p is None and esc_b is not None:
            ctx, e_b = esc_b
            sub_b, nome_b, resumo_b, _ = _extrair_campos_escalada(e_b)
            entidades.append(
                DiffEntidade(
                    tipo_entidade="escalada",
                    uid=uid,
                    nome_antes=nome_b,
                    nome_depois="",
                    contexto=ctx,
                    status="removido",
                    subtipo_antes=sub_b,
                    resumo_curto=resumo_b,
                )
            )
        elif esc_b is not None and esc_p is not None:
            ctx, e_p = esc_p
            _, e_b = esc_b
            sub_b, nome_b, _, campos_b = _extrair_campos_escalada(e_b)
            sub_p, nome_p, resumo_p, campos_p = _extrair_campos_escalada(e_p)
            alt_e: list[AlteracaoCampo] = []
            _comparar_valores(alt_e, "Modalidade", sub_b, sub_p)
            mapa_b = {c: (v, md) for c, v, md in campos_b}
            for nome_c, val_p, md in campos_p:
                val_b, _ = mapa_b.get(nome_c, ("", md))
                _comparar_valores(alt_e, nome_c, val_b, val_p, eh_markdown=md)
            if alt_e:
                entidades.append(
                    DiffEntidade(
                        tipo_entidade="escalada",
                        uid=uid,
                        nome_antes=nome_b,
                        nome_depois=nome_p,
                        contexto=ctx,
                        status="modificado",
                        subtipo_antes=sub_b,
                        subtipo_depois=sub_p,
                        resumo_curto=resumo_p,
                        alteracoes_campos=alt_e,
                    )
                )

    # 4. Imagens e arquivos externos (incluindo cópia seletiva para _base/)
    checksums_base = {a.caminho: a.checksum_sha256 for a in croqui_base.arquivos_externos}
    checksums_pr = {a.caminho: a.checksum_sha256 for a in croqui_pr.arquivos_externos}
    todos_caminhos_arq = list(
        dict.fromkeys(list(checksums_base.keys()) + list(checksums_pr.keys()))
    )
    diffs_imagens: list[DiffImagem] = []
    imagens_alteradas_set: set[str] = set()
    caminhos_base_por_img: dict[str, str] = {}

    for caminho_rel in todos_caminhos_arq:
        sha_b = checksums_base.get(caminho_rel)
        sha_p = checksums_pr.get(caminho_rel)
        cat, onde = col_pr.usos_imagens.get(
            caminho_rel,
            col_base.usos_imagens.get(caminho_rel, ("markdown", f"Imagem em {caminho_rel}")),
        )
        arq_b = dir_base / id_croqui / caminho_rel
        arq_p = dir_pr / id_croqui / caminho_rel
        larg_b, alt_b, kb_b = _obter_dimensoes_e_peso_imagem(arq_b)
        larg_p, alt_p, kb_p = _obter_dimensoes_e_peso_imagem(arq_p)

        if sha_b is None:
            diffs_imagens.append(
                DiffImagem(
                    caminho_relativo=caminho_rel,
                    categoria=cat,
                    onde_usada=onde,
                    status="adicionado",
                    caminho_pr_relativo=f"{id_croqui}/{caminho_rel}",
                    caminho_base_relativo=None,
                    largura_depois=larg_p,
                    altura_depois=alt_p,
                    tamanho_kb_depois=kb_p,
                )
            )
            imagens_alteradas_set.add(caminho_rel)
        elif sha_p is None:
            rel_base = f"_base/{id_croqui}/{caminho_rel}"
            if arq_b.is_file():
                _copiar_para_base(arq_b, dir_pr, rel_base, copiados_base)
            caminhos_base_por_img[caminho_rel] = rel_base
            diffs_imagens.append(
                DiffImagem(
                    caminho_relativo=caminho_rel,
                    categoria=cat,
                    onde_usada=onde,
                    status="removido",
                    caminho_pr_relativo=None,
                    caminho_base_relativo=rel_base,
                    largura_antes=larg_b,
                    altura_antes=alt_b,
                    tamanho_kb_antes=kb_b,
                )
            )
            imagens_alteradas_set.add(caminho_rel)
        elif sha_b != sha_p:
            rel_base = f"_base/{id_croqui}/{caminho_rel}"
            if arq_b.is_file():
                _copiar_para_base(arq_b, dir_pr, rel_base, copiados_base)
            caminhos_base_por_img[caminho_rel] = rel_base
            diffs_imagens.append(
                DiffImagem(
                    caminho_relativo=caminho_rel,
                    categoria=cat,
                    onde_usada=onde,
                    status="modificado",
                    caminho_pr_relativo=f"{id_croqui}/{caminho_rel}",
                    caminho_base_relativo=rel_base,
                    largura_antes=larg_b,
                    altura_antes=alt_b,
                    largura_depois=larg_p,
                    altura_depois=alt_p,
                    tamanho_kb_antes=kb_b,
                    tamanho_kb_depois=kb_p,
                )
            )
            imagens_alteradas_set.add(caminho_rel)

    # Verifica thumbnail gerada em thumbnails/<id>.webp
    thumb_rel = f"thumbnails/{id_croqui}.webp"
    thumb_b = dir_base / thumb_rel
    thumb_p = dir_pr / thumb_rel
    if thumb_b.is_file() and thumb_p.is_file():
        if _calcular_sha256_arquivo(thumb_b) != _calcular_sha256_arquivo(thumb_p):
            rel_base_thumb = f"_base/{id_croqui}/{thumb_rel}"
            _copiar_para_base(thumb_b, dir_pr, rel_base_thumb, copiados_base)
            larg_b, alt_b, kb_b = _obter_dimensoes_e_peso_imagem(thumb_b)
            larg_p, alt_p, kb_p = _obter_dimensoes_e_peso_imagem(thumb_p)
            diffs_imagens.append(
                DiffImagem(
                    caminho_relativo=thumb_rel,
                    categoria="thumbnail",
                    onde_usada=f"Thumbnail global ({id_croqui})",
                    status="modificado",
                    caminho_pr_relativo=thumb_rel,
                    caminho_base_relativo=rel_base_thumb,
                    largura_antes=larg_b,
                    altura_antes=alt_b,
                    largura_depois=larg_p,
                    altura_depois=alt_p,
                    tamanho_kb_antes=kb_b,
                    tamanho_kb_depois=kb_p,
                )
            )

    # 5. Mapas
    caminhos_mapas = list(dict.fromkeys(list(col_base.mapas.keys()) + list(col_pr.mapas.keys())))
    diffs_mapas: list[DiffMapa] = []
    for caminho_m in caminhos_mapas:
        m_b_tupla = col_base.mapas.get(caminho_m)
        m_p_tupla = col_pr.mapas.get(caminho_m)
        m_b = m_b_tupla[1] if m_b_tupla else None
        m_p = m_p_tupla[1] if m_p_tupla else None
        ctx_m = m_p_tupla[0] if m_p_tupla else (m_b_tupla[0] if m_b_tupla else id_croqui)
        pontos_diff = _comparar_pontos_mapa(m_b, m_p)
        img_alterada = (
            caminho_m in imagens_alteradas_set
            and m_b is not None
            and m_p is not None
        )
        tem_ponto_alterado = any(p.status != "inalterado" for p in pontos_diff)

        if m_b is None:
            status_mapa = "adicionado"
        elif m_p is None:
            status_mapa = "removido"
        elif img_alterada or tem_ponto_alterado:
            status_mapa = "modificado"
        else:
            status_mapa = "inalterado"

        arq_mb = dir_base / id_croqui / caminho_m
        arq_mp = dir_pr / id_croqui / caminho_m
        _, _, kb_mb = _obter_dimensoes_e_peso_imagem(arq_mb)
        _, _, kb_mp = _obter_dimensoes_e_peso_imagem(arq_mp)

        diffs_mapas.append(
            DiffMapa(
                caminho_imagem=caminho_m,
                contexto=ctx_m,
                status=status_mapa,
                imagem_alterada=img_alterada,
                caminho_imagem_base_relativo=caminhos_base_por_img.get(caminho_m),
                largura_antes=m_b.largura_mapa if m_b else 0,
                altura_antes=m_b.altura_mapa if m_b else 0,
                largura_depois=m_p.largura_mapa if m_p else 0,
                altura_depois=m_p.altura_mapa if m_p else 0,
                tamanho_kb_antes=kb_mb,
                tamanho_kb_depois=kb_mp,
                pontos=pontos_diff,
            )
        )

    tem_mudanca = bool(
        eh_novo
        or alteracoes_meta
        or entidades
        or diffs_imagens
        or any(m.status != "inalterado" for m in diffs_mapas)
    )
    status_croqui = "novo" if eh_novo else ("modificado" if tem_mudanca else "inalterado")

    return DiffCroqui(
        id_croqui=id_croqui,
        uid=croqui_pr.uid,
        nome=croqui_pr.nome,
        status=status_croqui,
        alteracoes_metadados=alteracoes_meta,
        entidades=entidades,
        mapas=diffs_mapas,
        imagens=diffs_imagens,
        arquivos_base_copiados=copiados_base,
    )


def calcular_diff_pull_request(
    dir_base: Path,
    dir_pr: Path,
    ids_croquis: list[str] | None = None,
) -> ResumoDiffPullRequest:
    """
    Calcula o diff semântico e visual entre os artefatos compilados na base e na Pull Request.
    Também copia seletivamente para `dir_pr/_base/<id>/` as imagens da base que foram
    modificadas ou removidas na PR.
    """
    if ids_croquis is None:
        ids_descobertos = sorted(
            p.name
            for p in dir_pr.iterdir()
            if p.is_dir()
            and not p.name.startswith("_")
            and (p / "compilado.binarypb").is_file()
        )
    else:
        ids_descobertos = [
            cid for cid in ids_croquis if (dir_pr / cid / "compilado.binarypb").is_file()
        ]

    resumo = ResumoDiffPullRequest()
    for cid in ids_descobertos:
        resumo.croquis.append(_processar_diff_croqui(cid, dir_base, dir_pr))
    return resumo
