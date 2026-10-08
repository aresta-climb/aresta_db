# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Migração 0005: Migração para UIDs universais (Pure NanoID 14c) e rótulos.

Esta migração atribui identificadores NanoID de 14 caracteres Base62 contínuo
a todas as entidades (Croqui, Grupo, Setor, Escalada e PontoDeInteresse),
substitui o campo 'label' por 'rotulo' e converte as referências de mapa
para apontarem exclusivamente para 'alvo_uid' e 'pontos_uids', removendo
os campos legados 'escalada', 'setor' e 'grupo' dos arquivos Markdown.
"""

from typing import Dict, Any, Tuple, Optional, List
import io
import re
from pathlib import Path
from ruamel.yaml import YAML
from scripts.gerenciar_uids_lib import gerar_uid, validar_uid

# Migração com escopo restrito aos arquivos de dados internos (database/ e croquis).
# Não incrementa a versão pública de serving consumida pelo aplicativo móvel (mantém v4).
AFETA_VERSAO_SERVING: bool = False
MIGRATION_ID: int = 5


def _inserir_ou_mover_para_posicao(mapa: Any, chave: str, valor: Any = None, pos: int = 0) -> None:
    """Insere ou move uma chave para uma posição específica (padrão 0 = início) preservando ruamel.yaml CommentedMap."""
    if hasattr(mapa, "insert"):
        if chave in mapa:
            val = mapa.pop(chave)
            mapa.insert(pos, chave, valor if valor is not None else val)
        elif valor is not None:
            mapa.insert(pos, chave, valor)
    elif isinstance(mapa, dict):
        if chave in mapa:
            val = mapa.pop(chave)
            novo_val = valor if valor is not None else val
        elif valor is not None:
            novo_val = valor
        else:
            return
        itens = list(mapa.items())
        itens.insert(pos, (chave, novo_val))
        mapa.clear()
        for k, v in itens:
            mapa[k] = v


def _obter_yaml() -> YAML:
    """Configura instância do ruamel.yaml com preservação estrita de comentários e formatação."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 120
    y.representer.ignore_aliases = lambda *data: True
    return y


def _carregar_md_ruamel(caminho: Path) -> Tuple[Optional[Any], str, Optional[YAML]]:
    """Lê um arquivo Markdown e faz o parse do Frontmatter preservando formatação e comentários."""
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except Exception:
        return None, "", None

    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n(.*))?$", conteudo, re.DOTALL)
    if not match:
        return None, conteudo, None

    y = _obter_yaml()
    try:
        dados = y.load(match.group(1)) or {}
    except Exception:
        return None, conteudo, None

    corpo = match.group(2) or ""
    return dados, corpo, y


def _salvar_md_ruamel(caminho: Path, dados: Any, corpo: str, y: YAML) -> None:
    """Salva o Frontmatter e o corpo preservando comentários originais."""
    stream = io.StringIO()
    y.dump(dados, stream)
    texto_yaml = stream.getvalue().strip()
    texto_corpo = corpo.strip()
    if texto_corpo:
        caminho.write_text(f"---\n{texto_yaml}\n---\n\n{texto_corpo}\n", encoding="utf-8")
    else:
        caminho.write_text(f"---\n{texto_yaml}\n---\n", encoding="utf-8")


def _extrair_nome_escalada(escalada: Dict[str, Any]) -> str:
    """Extrai o nome de uma escalada suportando modelo plano ou polimórfico."""
    if not isinstance(escalada, dict):
        return ""
    if "nome" in escalada and isinstance(escalada["nome"], str):
        return escalada["nome"].strip()
    for subtipo in (
        "via_esportiva",
        "via_movel",
        "via_tradicional",
        "boulder",
        "via_psicobloc",
        "via_artificial",
        "highline",
        "via_multiplas_enfiadas",
    ):
        conteudo_sub = escalada.get(subtipo)
        if isinstance(conteudo_sub, dict) and "nome" in conteudo_sub:
            return str(conteudo_sub.get("nome", "")).strip()
    return ""


def migrar(pico_path: Path) -> None:
    """Ponto de entrada da migração 0005 invocado pelo motor de migrações."""
    # 1. Migra croqui.yaml
    caminho_yaml = pico_path / "croqui.yaml"
    if caminho_yaml.exists():
        y = _obter_yaml()
        try:
            dados_croqui = y.load(caminho_yaml.read_text(encoding="utf-8")) or {}
        except Exception:
            dados_croqui = {}

        if dados_croqui:
            croqui_uid = dados_croqui.get("uid")
            if not validar_uid(str(croqui_uid or "")):
                croqui_uid = gerar_uid()
            _inserir_ou_mover_para_posicao(dados_croqui, "uid", croqui_uid, 0)

            for botao in dados_croqui.get("botoes", []):
                if isinstance(botao, dict):
                    botao_uid = botao.get("uid")
                    if not validar_uid(str(botao_uid or "")):
                        botao_uid = gerar_uid()
                    _inserir_ou_mover_para_posicao(botao, "uid", botao_uid, 0)

            stream = io.StringIO()
            y.dump(dados_croqui, stream)
            caminho_yaml.write_text(stream.getvalue(), encoding="utf-8")

    # 2. Primeira passagem pelos arquivos .md: atribui UIDs a setores, grupos e escaladas,
    # e constrói o índice de resolução de nomes para referências
    arquivos_md: List[Path] = [p for p in pico_path.glob("*.md") if p.is_file()]
    dados_md_carregados: Dict[Path, Tuple[Any, str, YAML]] = {}

    mapa_escaladas_com_setor: Dict[Tuple[str, str], str] = {}
    mapa_escaladas_simples: Dict[str, str] = {}
    mapa_setores: Dict[str, str] = {}
    mapa_grupos: Dict[str, str] = {}

    for md_path in arquivos_md:
        dados, corpo, inst_y = _carregar_md_ruamel(md_path)
        if dados is None or not isinstance(dados, dict) or inst_y is None:
            continue

        nome_lower = str(dados.get("nome", "")).lower()
        eh_setor = md_path.name.startswith("setor") or "escaladas" in dados or nome_lower.startswith("setor")
        eh_grupo = md_path.name.startswith("grupo") or "setores" in dados or "sub_setores" in dados or nome_lower.startswith("grupo")
        eh_mapa = md_path.name.startswith("mapas") or "mapas" in dados

        if not (eh_setor or eh_grupo or eh_mapa):
            # Arquivo auxiliar de texto (ex: capa.md, avisos.md):
            # Preserva comentários de licença e outros campos, mas garante que não possui UID nem ID no frontmatter
            if "uid" in dados or "id" in dados:
                dados.pop("uid", None)
                dados.pop("id", None)
                _salvar_md_ruamel(md_path, dados, corpo, inst_y)
            continue

        dados_md_carregados[md_path] = (dados, corpo, inst_y)

        if eh_setor or eh_grupo:
            # Garante UID da entidade raiz (Setor ou Grupo) na primeira posição
            setor_ou_grupo_uid = dados.get("uid")
            if not validar_uid(str(setor_ou_grupo_uid or "")):
                setor_ou_grupo_uid = gerar_uid()
            _inserir_ou_mover_para_posicao(dados, "uid", setor_ou_grupo_uid, 0)

            nome_entidade = str(dados.get("nome", "")).strip()
            if eh_setor:
                if nome_entidade:
                    mapa_setores[nome_entidade] = dados["uid"]
                    if nome_entidade.lower().startswith("setor "):
                        mapa_setores[nome_entidade[6:].strip()] = dados["uid"]
                    else:
                        mapa_setores[f"Setor {nome_entidade}"] = dados["uid"]
            else:
                if nome_entidade:
                    mapa_grupos[nome_entidade] = dados["uid"]
                    if nome_entidade.lower().startswith("grupo "):
                        mapa_grupos[nome_entidade[6:].strip()] = dados["uid"]
                    else:
                        mapa_grupos[f"Grupo {nome_entidade}"] = dados["uid"]

            # Garante UIDs de todas as escaladas na primeira posição
            for escalada in dados.get("escaladas", []):
                if isinstance(escalada, dict):
                    esc_uid = escalada.get("uid")
                    if not validar_uid(str(esc_uid or "")):
                        esc_uid = gerar_uid()
                    _inserir_ou_mover_para_posicao(escalada, "uid", esc_uid, 0)

                    nome_via = _extrair_nome_escalada(escalada)
                    if nome_via:
                        if nome_entidade:
                            mapa_escaladas_com_setor[(nome_entidade, nome_via)] = escalada["uid"]
                        mapa_escaladas_simples[nome_via] = escalada["uid"]

    # 3. Segunda passagem pelos arquivos .md: migra mapas (POIs e referências)
    for md_path, (dados, corpo, y) in dados_md_carregados.items():
        nome_setor_atual = str(dados.get("nome", "")).strip()
        mapas = dados.get("mapas", [])
        if isinstance(mapas, list):
            for mapa in mapas:
                if not isinstance(mapa, dict):
                    continue

                # 3.1 Migra pontos de interesse: label -> rotulo e atribui UIDs, posicionando uid e rotulo no início
                poi_id_para_uid: Dict[str, str] = {}
                for poi in mapa.get("pontos_de_interesse", []):
                    if not isinstance(poi, dict):
                        continue

                    # Extrai / remove label legado
                    label_legado = poi.pop("label", None)
                    rotulo = poi.pop("rotulo", None) or label_legado

                    # Atribui / extrai UID
                    poi_uid = poi.pop("uid", None)
                    if not validar_uid(str(poi_uid or "")):
                        poi_uid = gerar_uid()

                    if "id" in poi:
                        poi_id_para_uid[str(poi["id"])] = poi_uid
                        del poi["id"]

                    # Ordem: 1º rotulo na pos 0, depois uid na pos 0 -> resultado: uid (pos 0), rotulo (pos 1)
                    if rotulo is not None:
                        _inserir_ou_mover_para_posicao(poi, "rotulo", rotulo, 0)
                    _inserir_ou_mover_para_posicao(poi, "uid", poi_uid, 0)

                # 3.2 Migra referências: alvo_uid, pontos_uids e remove strings legadas
                for ref in mapa.get("referencias", []):
                    if not isinstance(ref, dict):
                        continue

                    # Converte alvo_uid se ausente
                    alvo_uid = ref.pop("alvo_uid", None)
                    if not validar_uid(str(alvo_uid or "")):
                        alvo_uid_encontrado: Optional[str] = None
                        if "escalada" in ref:
                            nome_via = str(ref.get("escalada", "")).strip()
                            nome_setor = str(ref.get("setor", "")).strip() or nome_setor_atual
                            alvo_uid_encontrado = mapa_escaladas_com_setor.get((nome_setor, nome_via)) or mapa_escaladas_simples.get(nome_via)
                        elif "setor" in ref:
                            nome_setor = str(ref.get("setor", "")).strip()
                            alvo_uid_encontrado = mapa_setores.get(nome_setor) or mapa_grupos.get(nome_setor)
                        elif "grupo" in ref:
                            nome_grupo = str(ref.get("grupo", "")).strip()
                            alvo_uid_encontrado = mapa_grupos.get(nome_grupo) or mapa_setores.get(nome_grupo)

                        if alvo_uid_encontrado:
                            alvo_uid = alvo_uid_encontrado

                    # Converte pontos_uids se ausente
                    pontos_uids = ref.pop("pontos_uids", None)
                    if pontos_uids is None:
                        ids_locais = ref.get("ids", [])
                        if isinstance(ids_locais, list):
                            pontos_uids = [
                                poi_id_para_uid.get(str(pid), pid) for pid in ids_locais
                            ]

                    # Remove campos legados ids e indice_mapa_alvo
                    ref.pop("ids", None)
                    ref.pop("indice_mapa_alvo", None)

                    # Remove obrigatoriamente campos textuais legados se alvo_uid foi resolvido
                    if validar_uid(str(alvo_uid or "")):
                        ref.pop("escalada", None)
                        ref.pop("setor", None)
                        ref.pop("grupo", None)

                    # Ordem: 1º pontos_uids na pos 0, depois alvo_uid na pos 0 -> resultado: alvo_uid (pos 0), pontos_uids (pos 1)
                    if pontos_uids is not None:
                        _inserir_ou_mover_para_posicao(ref, "pontos_uids", pontos_uids, 0)
                    if alvo_uid is not None:
                        _inserir_ou_mover_para_posicao(ref, "alvo_uid", alvo_uid, 0)

        # Salva o arquivo modificado
        _salvar_md_ruamel(md_path, dados, corpo, y)
