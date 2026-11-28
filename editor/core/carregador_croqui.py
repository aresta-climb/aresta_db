# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca pura (sem QObject/QWidget) para pré-aquecimento de módulos e carregamento
completo da árvore Protobuf de um croqui em thread de segundo plano.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google.protobuf import json_format

from aresta_api.proto.generated.croqui_pb2 import (
    ArquivoCuradoriaBetas,
    ArquivoGrupo,
    ArquivoMalhaEstrada,
    ArquivoMapas,
    ArquivoMarkdown,
    ArquivoSetor,
    Croqui,
)
from editor.core.avaliador_nota_qualidade import (
    ResultadoNotaQualidade,
    avaliar_nota_qualidade_croqui,
)
from editor.core.serializacao_util import carregar_yaml
from scripts.deploy_generated import registrar_snapshot_disco_arquivo
from scripts.migrador import aplicar_migracoes

_PADRAO_FRONTMATTER = re.compile(
    r"^---([ \t]*\r?\n(?:.*?\r?\n)?)---([ \t]*(?:\r?\n.*)?)$",
    re.DOTALL,
)


@dataclass(frozen=True)
class PacoteCroquiCarregado:
    """Agrega os artefatos puros hidratados fora da thread de interface gráfica."""

    caminho_db: Path
    croqui_data: dict[str, Any]
    croqui_msg: Croqui
    cache_json_original: dict[str, dict[str, Any]]
    houve_migracao: bool
    commit_base_sha: str
    resultado_qualidade_inicial: ResultadoNotaQualidade


def _remover_quebra_inicial(texto: str) -> str:
    return texto[1:] if texto.startswith("\n") else texto


def _ler_objeto_com_frontmatter(
    caminho_arquivo: Path,
    message_ref: Any,
    ext_descriptor: Any,
    cache_json_original_out: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    conteudo = caminho_arquivo.read_text(encoding="utf-8")
    match_fm = _PADRAO_FRONTMATTER.match(conteudo)
    if match_fm:
        frontmatter_str = match_fm.group(1)
        body_str = _remover_quebra_inicial(match_fm.group(2))
        try:
            carregado_fm = carregar_yaml(frontmatter_str) or {}
        except Exception:
            carregado_fm = {}
        dados = dict(carregado_fm) if isinstance(carregado_fm, dict) else {}

        if not message_ref.HasExtension(ext_descriptor):
            message_ref.Extensions[ext_descriptor].caminho_original = ""

        json_str = json.dumps(dados, ensure_ascii=False)
        message_ref.Extensions[ext_descriptor].dados_json_originais = json_str
        cache_json_original_out[json_str] = copy.deepcopy(dados)
        registrar_snapshot_disco_arquivo(caminho_arquivo, dados, body_str)

        if body_str:
            dados["descricao"] = body_str
        return dados

    try:
        carregado = carregar_yaml(conteudo) or {}
    except Exception:
        return {}
    return dict(carregado) if isinstance(carregado, dict) else {}


def _limpar_extensao_se_presente(bloco: Any, ext_descriptor: Any) -> None:
    if bloco.HasExtension(ext_descriptor):
        bloco.ClearExtension(ext_descriptor)


def _sanitizar_dados_curadoria_betas(dados_cur: dict[str, Any]) -> None:
    dados_cur.pop("uid", None)
    dados_cur.pop("id", None)
    escaladas = dados_cur.get("escaladas")
    if isinstance(escaladas, list):
        for item_esc in escaladas:
            if isinstance(item_esc, dict):
                item_esc.pop("uid", None)
                item_esc.pop("id", None)


def hidratar_arquivos_externos_protobuf(
    croqui_msg: Any,
    caminho_db: Path,
    cache_json_original_out: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Carrega e mescla na mensagem Protobuf `Croqui` todos os arquivos externos (`.md` e `.yaml`)
    sem instanciar objetos `QObject`, permitindo execução segura em worker threads.
    """
    cache_json: dict[str, dict[str, Any]] = (
        cache_json_original_out if cache_json_original_out is not None else {}
    )
    if not caminho_db.exists():
        return cache_json

    def _hidratar_bloco(
        bloco: Any,
        ext_descriptor: Any,
        *,
        caminho_novo_fixo: str | None = None,
        aceitar_fallback_yaml: bool = False,
        preparar_dados: Callable[[dict[str, Any]], None] | None = None,
        pos_hidratar: Callable[[Any], None] | None = None,
    ) -> None:
        if bloco.WhichOneof("arquivo") != "caminho" or not bloco.caminho:
            return
        nome_relativo = str(bloco.caminho)
        caminho_arquivo = caminho_db / nome_relativo
        if aceitar_fallback_yaml and not caminho_arquivo.exists() and nome_relativo.endswith(".md"):
            alt_yaml = f"{nome_relativo[:-3]}.yaml"
            if (caminho_db / alt_yaml).exists():
                nome_relativo = alt_yaml
                caminho_arquivo = caminho_db / alt_yaml
        if not caminho_arquivo.exists():
            return

        try:
            dados = _ler_objeto_com_frontmatter(caminho_arquivo, bloco, ext_descriptor, cache_json)
            if not dados:
                _limpar_extensao_se_presente(bloco, ext_descriptor)
                return
            if preparar_dados is not None:
                preparar_dados(dados)
            json_format.ParseDict(dados, bloco.conteudo, ignore_unknown_fields=True)
            bloco.Extensions[ext_descriptor].caminho_original = nome_relativo
            bloco.Extensions[ext_descriptor].caminho_novo = caminho_novo_fixo or nome_relativo
            bloco.ClearField("caminho")
            if pos_hidratar is not None:
                pos_hidratar(bloco)
        except Exception:
            _limpar_extensao_se_presente(bloco, ext_descriptor)

    def _hidratar_setor(arq_setor: Any) -> None:
        _hidratar_bloco(arq_setor, ArquivoSetor.ext_metadados_arquivo)

    def _hidratar_subsetores_grupo(arq_grupo: Any) -> None:
        for subsetor in arq_grupo.conteudo.setores:
            _hidratar_setor(subsetor)

    # 1. Botões textuais (Markdown)
    for botao in croqui_msg.botoes:
        if botao.HasField("destino") and botao.destino.WhichOneof("destino") == "secao_textual":
            md = botao.destino.secao_textual
            if md.WhichOneof("arquivo") == "caminho" and md.caminho:
                nome_relativo = str(md.caminho)
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        conteudo_md = caminho_arquivo.read_text(encoding="utf-8")
                        frontmatter_bloco = ""
                        corpo_md = conteudo_md
                        match_md = _PADRAO_FRONTMATTER.match(conteudo_md)
                        if match_md:
                            frontmatter_bloco = f"---{match_md.group(1)}---\n"
                            corpo_md = _remover_quebra_inicial(match_md.group(2))
                        md.conteudo = corpo_md
                        md.Extensions[
                            ArquivoMarkdown.ext_metadados_arquivo
                        ].caminho_original = nome_relativo
                        md.Extensions[
                            ArquivoMarkdown.ext_metadados_arquivo
                        ].caminho_novo = nome_relativo
                        if frontmatter_bloco:
                            md.Extensions[
                                ArquivoMarkdown.ext_metadados_arquivo
                            ].dados_json_originais = frontmatter_bloco
                        md.ClearField("caminho")
                    except Exception:
                        _limpar_extensao_se_presente(md, ArquivoMarkdown.ext_metadados_arquivo)

    # 2. Picos, mapas gerais, malha de estrada, setores e grupos
    for pico in croqui_msg.picos:
        if pico.HasField("mapas_gerais"):
            _hidratar_bloco(pico.mapas_gerais, ArquivoMapas.ext_metadados_arquivo)
        if pico.HasField("malha_estrada"):
            _hidratar_bloco(pico.malha_estrada, ArquivoMalhaEstrada.ext_metadados_arquivo)
        for sg in pico.setores_ou_grupos:
            if sg.HasField("setor"):
                _hidratar_setor(sg.setor)
            elif sg.HasField("grupo"):
                _hidratar_bloco(
                    sg.grupo,
                    ArquivoGrupo.ext_metadados_arquivo,
                    pos_hidratar=_hidratar_subsetores_grupo,
                )

    # 3. Curadoria de betas (`curadoria_betas.yaml` ou `.md` legado)
    if croqui_msg.HasField("curadoria_betas"):
        _hidratar_bloco(
            croqui_msg.curadoria_betas,
            ArquivoCuradoriaBetas.ext_metadados_arquivo,
            caminho_novo_fixo="curadoria_betas.yaml",
            aceitar_fallback_yaml=True,
            preparar_dados=_sanitizar_dados_curadoria_betas,
        )

    return cache_json


def carregar_pacote_croqui(
    caminho_db: Path | str,
    *,
    obter_commit_sha: Callable[[], str] | None = None,
    executar_migracoes: bool = True,
) -> PacoteCroquiCarregado | None:
    """
    Executa migrações, leitura de `croqui.yaml`, hidratação completa de arquivos externos,
    avaliação inicial da `nota_qualidade` e obtenção de `commit_base_sha` fora da UI thread.
    """
    caminho_db_path = Path(caminho_db)
    if not caminho_db_path.is_dir():
        return None

    houve_migracao = aplicar_migracoes(caminho_db_path) if executar_migracoes else False
    yaml_path = caminho_db_path / "croqui.yaml"
    if not yaml_path.is_file():
        return None

    carregado_raiz = carregar_yaml(yaml_path.read_text(encoding="utf-8")) or {}
    croqui_data: dict[str, Any] = dict(carregado_raiz) if isinstance(carregado_raiz, dict) else {}

    croqui_msg = json_format.ParseDict(croqui_data, Croqui(), ignore_unknown_fields=True)
    croqui_msg.Extensions[Croqui.ext_metadados_arquivo].dados_json_originais = json.dumps(
        croqui_data, ensure_ascii=False
    )
    registrar_snapshot_disco_arquivo(yaml_path, croqui_data, None)

    cache_json: dict[str, dict[str, Any]] = {}
    hidratar_arquivos_externos_protobuf(croqui_msg, caminho_db_path, cache_json)
    resultado_qualidade = avaliar_nota_qualidade_croqui(croqui_msg)
    commit_sha = obter_commit_sha() if callable(obter_commit_sha) else ""

    return PacoteCroquiCarregado(
        caminho_db=caminho_db_path,
        croqui_data=croqui_data,
        croqui_msg=croqui_msg,
        cache_json_original=cache_json,
        houve_migracao=houve_migracao,
        commit_base_sha=commit_sha,
        resultado_qualidade_inicial=resultado_qualidade,
    )


def pre_aquecer_modulos_editor() -> None:
    """
    Pré-importa módulos pesados da janela principal em thread de segundo plano durante a
    `TelaDeAbertura`, evitando bloqueio de ~1-2s na transição entre janelas.
    """
    import editor.core.workspace
    import editor.legacy_views.area_principal
    import editor.mcp.registro_ferramentas
    import editor.mcp.servidor
    import editor.views.widget_editor_dados

    _ = (
        editor.core.workspace,
        editor.legacy_views.area_principal,
        editor.mcp.registro_ferramentas,
        editor.mcp.servidor,
        editor.views.widget_editor_dados,
    )
