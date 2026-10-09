# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de contrato de integridade do acervo do banco de dados (database/).

Valida estritamente que todos os croquis e arquivos em database/:
1. Possuem UIDs de 14 caracteres Base62 contínuo em todas as entidades (Croqui, Grupo, Setor, Escalada, POI).
2. Não utilizam o campo legado 'label' em pontos de interesse (exclusivamente 'rotulo').
3. Não utilizam campos textuais legados em referências de mapa ('escalada', 'setor', 'grupo').
4. Possuem 'alvo_uid' e 'pontos_uids' em todas as referências de mapa.
5. Não possuem arquivos residuais de mapeamento de IDs ('ids_*.yaml').
"""

from pathlib import Path
from typing import List, Dict, Any
import pytest
import yaml

from scripts.gerenciar_uids_lib import validar_uid
from scripts.preparar_submissao_lib import parse_md_com_frontmatter

PASTA_RAIZ: Path = Path(__file__).resolve().parent.parent
PASTA_DATABASE: Path = PASTA_RAIZ / "database"


def test_ausencia_arquivos_mapeamento_ids_yaml():
    """Garante que não existem tabelas intermediárias de mapeamento (ids_globais.yaml, ids_entidades.yaml, etc.) no repositório."""
    tabelas_proibidas = {"ids_globais.yaml", "ids_entidades.yaml", "ids_pontos.yaml", "ids_mapeamento.yaml"}
    arquivos_db = list(PASTA_DATABASE.rglob("*.yaml")) if PASTA_DATABASE.is_dir() else []
    arquivos_residuais: List[Path] = [
        f for f in arquivos_db + list(PASTA_RAIZ.glob("*.yaml"))
        if f.name in tabelas_proibidas
    ]
    assert not arquivos_residuais, (
        f"Foram encontradas tabelas intermediárias de mapeamento de IDs que violam o modelo Pure NanoID: {arquivos_residuais}"
    )


def test_contrato_database_todas_entidades_possuem_uid_14c_base62():
    """Valida que toda entidade no database/ possui um UID válido de 14 caracteres Base62."""
    if not PASTA_DATABASE.is_dir():
        pytest.skip("Diretório database/ não presente no ambiente (ex: sparse-checkout do build do Editor).")

    pastas_croqui = [d for d in PASTA_DATABASE.iterdir() if d.is_dir() and (d / "croqui.yaml").exists()]
    assert pastas_croqui, "Nenhum croqui encontrado em database/."

    erros: List[str] = []

    for pasta_croqui in pastas_croqui:
        croqui_yaml_path = pasta_croqui / "croqui.yaml"
        with open(croqui_yaml_path, "r", encoding="utf-8") as f:
            croqui_data = yaml.safe_load(f) or {}

        # 1. Valida UID do Croqui raiz e sua posição como primeira chave
        croqui_uid = croqui_data.get("uid")
        if not validar_uid(croqui_uid):
            erros.append(f"Croqui '{pasta_croqui.name}/croqui.yaml' sem UID 14c válido: '{croqui_uid}'")
        elif list(croqui_data.keys())[0] != "uid":
            erros.append(f"Croqui '{pasta_croqui.name}/croqui.yaml': 'uid' deve ser o primeiro campo (atual: '{list(croqui_data.keys())[0]}')")

        # 1.1 Valida UIDs em todos os botões do croqui
        for botao in croqui_data.get("botoes", []):
            if isinstance(botao, dict):
                b_uid = botao.get("uid")
                if not validar_uid(b_uid):
                    erros.append(f"Botão '{botao.get('texto')}' em '{pasta_croqui.name}/croqui.yaml' sem UID 14c válido: '{b_uid}'")
                elif list(botao.keys())[0] != "uid":
                    erros.append(f"Botão '{botao.get('texto')}' em '{pasta_croqui.name}/croqui.yaml': 'uid' deve ser o primeiro campo")

        # 2. Valida UIDs em todos os arquivos Markdown do croqui
        for md_path in pasta_croqui.glob("*.md"):
            frontmatter, _ = parse_md_com_frontmatter(md_path)
            if not frontmatter or not isinstance(frontmatter, dict):
                continue

            eh_setor = md_path.name.startswith("setor") or "escaladas" in frontmatter or str(frontmatter.get("nome", "")).lower().startswith("setor")
            eh_grupo = md_path.name.startswith("grupo") or "setores" in frontmatter or "sub_setores" in frontmatter or str(frontmatter.get("nome", "")).lower().startswith("grupo")
            eh_mapa = md_path.name.startswith("mapas") or "mapas" in frontmatter

            if eh_setor or eh_grupo:
                # UID do Setor ou Grupo
                ent_uid = frontmatter.get("uid")
                if not validar_uid(ent_uid):
                    erros.append(f"Entidade '{frontmatter.get('nome')}' em {pasta_croqui.name}/{md_path.name} com UID inválido: '{ent_uid}'")
                elif list(frontmatter.keys())[0] != "uid":
                    erros.append(f"Entidade '{frontmatter.get('nome')}' em {pasta_croqui.name}/{md_path.name}: 'uid' deve ser o primeiro campo")

                # UIDs das escaladas
                for esc in frontmatter.get("escaladas", []):
                    if isinstance(esc, dict):
                        esc_uid = esc.get("uid")
                        if not validar_uid(esc_uid):
                            erros.append(f"Escalada em {pasta_croqui.name}/{md_path.name} com UID inválido: '{esc_uid}'")
                        elif list(esc.keys())[0] != "uid":
                            erros.append(f"Escalada em {pasta_croqui.name}/{md_path.name}: 'uid' deve ser o primeiro campo")
            elif not eh_mapa:
                # Arquivo auxiliar (ex: capa.md, avisos.md): não deve conter UID nem ID
                if "uid" in frontmatter:
                    erros.append(f"Arquivo auxiliar '{pasta_croqui.name}/{md_path.name}' não deve conter UID no frontmatter: '{frontmatter['uid']}'")
                if "id" in frontmatter:
                    erros.append(f"Arquivo auxiliar '{pasta_croqui.name}/{md_path.name}' não deve conter ID no frontmatter: '{frontmatter['id']}'")

            # UIDs dos POIs nos mapas e referências
            for mapa in frontmatter.get("mapas", []):
                if isinstance(mapa, dict):
                    for poi in mapa.get("pontos_de_interesse", []):
                        if isinstance(poi, dict):
                            poi_uid = poi.get("uid")
                            if not validar_uid(poi_uid):
                                erros.append(f"POI '{poi.get('id')}' em {pasta_croqui.name}/{md_path.name} com UID inválido: '{poi_uid}'")
                            elif list(poi.keys())[0] != "uid":
                                erros.append(f"POI em {pasta_croqui.name}/{md_path.name}: 'uid' deve ser o primeiro campo")
                            if len(poi.keys()) > 1 and list(poi.keys())[1] != "rotulo" and "rotulo" in poi:
                                erros.append(f"POI em {pasta_croqui.name}/{md_path.name}: 'rotulo' deve vir logo após 'uid'")

                    for ref in mapa.get("referencias", []):
                        if isinstance(ref, dict):
                            chaves_ref = list(ref.keys())
                            if "alvo_uid" in ref and chaves_ref[0] != "alvo_uid":
                                erros.append(f"Referência em {pasta_croqui.name}/{md_path.name}: 'alvo_uid' deve ser o primeiro campo")
                            if "pontos_uids" in ref and len(chaves_ref) > 1 and chaves_ref[1] != "pontos_uids":
                                erros.append(f"Referência em {pasta_croqui.name}/{md_path.name}: 'pontos_uids' deve vir logo após 'alvo_uid'")

    assert not erros, f"Inconsistências de UID encontradas no database/:\n" + "\n".join(erros[:20])


def test_contrato_database_mapas_sem_campos_legados_e_sem_label():
    """Valida que referências de mapa não contêm 'escalada', 'setor', 'grupo' e POIs não contêm 'label'."""
    if not PASTA_DATABASE.is_dir():
        pytest.skip("Diretório database/ não presente no ambiente (ex: sparse-checkout do build do Editor).")

    pastas_croqui = [d for d in PASTA_DATABASE.iterdir() if d.is_dir() and (d / "croqui.yaml").exists()]

    erros: List[str] = []

    for pasta_croqui in pastas_croqui:
        for md_path in pasta_croqui.glob("*.md"):
            frontmatter, _ = parse_md_com_frontmatter(md_path)
            if not frontmatter or not isinstance(frontmatter, dict):
                continue

            for mapa in frontmatter.get("mapas", []):
                if not isinstance(mapa, dict):
                    continue

                # 1. POIs não podem conter os campos depreciados 'label' nem 'id'
                for poi in mapa.get("pontos_de_interesse", []):
                    if isinstance(poi, dict):
                        if "label" in poi:
                            erros.append(f"POI '{poi.get('uid')}' em {pasta_croqui.name}/{md_path.name} possui campo depreciado 'label:'")
                        if "id" in poi:
                            erros.append(f"POI '{poi.get('uid')}' em {pasta_croqui.name}/{md_path.name} possui campo depreciado 'id: {poi['id']}'")

                # 2. Referências não podem conter 'escalada', 'setor', 'grupo', 'ids', 'indice_mapa_alvo'
                for ref in mapa.get("referencias", []):
                    if not isinstance(ref, dict):
                        continue

                    for campo_legado in ("escalada", "setor", "grupo", "ids", "indice_mapa_alvo"):
                        if campo_legado in ref:
                            erros.append(
                                f"Referência em {pasta_croqui.name}/{md_path.name} possui campo depreciado '{campo_legado}: {ref[campo_legado]}'"
                            )

                    alvo_uid = ref.get("alvo_uid")
                    if alvo_uid is not None and not validar_uid(alvo_uid):
                        erros.append(f"Referência em {pasta_croqui.name}/{md_path.name} com 'alvo_uid' inválido: '{alvo_uid}'")

                    if "pontos_uids" not in ref:
                        erros.append(f"Referência em {pasta_croqui.name}/{md_path.name} sem campo 'pontos_uids'")

    assert not erros, f"Inconsistências contratuais de mapa encontradas no database/:\n" + "\n".join(erros[:20])


def test_contrato_compilado_retrocompatibilidade_preenche_id_e_ids():
    """Valida que o compilador preenche 'id' em POIs e 'ids' em referências nos artefatos gerados para retrocompatibilidade."""
    pasta_generated = PASTA_RAIZ / "generated"
    if not pasta_generated.is_dir():
        pytest.skip("Pasta generated/ não encontrada.")

    pastas_compilados = [d for d in pasta_generated.iterdir() if d.is_dir() and (d / "compilado.yaml").exists()]
    if not pastas_compilados:
        pytest.skip("Nenhum croqui compilado encontrado em generated/.")

    erros: List[str] = []

    def _validar_mapas_compilados(obj: Any, contexto: str) -> None:
        if isinstance(obj, list):
            for item in obj:
                _validar_mapas_compilados(item, contexto)
        elif isinstance(obj, dict):
            if "mapas" in obj and isinstance(obj["mapas"], list):
                for idx_m, mapa in enumerate(obj["mapas"]):
                    if not isinstance(mapa, dict):
                        continue
                    # Valida POIs: id deve estar preenchido com uid
                    for poi in mapa.get("pontos_de_interesse", []):
                        if isinstance(poi, dict):
                            p_uid = poi.get("uid")
                            p_id = poi.get("id")
                            if p_uid and p_id != p_uid:
                                erros.append(f"Compilado {contexto} (Mapa {idx_m+1}): POI com uid '{p_uid}' tem id '{p_id}' diferente")
                            p_rotulo = poi.get("rotulo")
                            p_label = poi.get("label")
                            if p_rotulo and p_label != p_rotulo:
                                erros.append(f"Compilado {contexto} (Mapa {idx_m+1}): POI com rotulo '{p_rotulo}' tem label '{p_label}' diferente")

                    # Valida Referências: ids deve estar preenchido com pontos_uids
                    for ref in mapa.get("referencias", []):
                        if isinstance(ref, dict):
                            pontos_uids = ref.get("pontos_uids", [])
                            ids = ref.get("ids", [])
                            if pontos_uids and ids != pontos_uids:
                                erros.append(f"Compilado {contexto} (Mapa {idx_m+1}): Referência com pontos_uids {pontos_uids} tem ids {ids} diferente")

            for v in obj.values():
                if isinstance(v, (dict, list)):
                    _validar_mapas_compilados(v, contexto)

    for pasta in pastas_compilados:
        yaml_comp = pasta / "compilado.yaml"
        with open(yaml_comp, "r", encoding="utf-8") as f:
            dados = yaml.safe_load(f) or {}
        _validar_mapas_compilados(dados, pasta.name)
        for b in dados.get("botoes", []):
            if isinstance(b, dict):
                b_uid = b.get("uid")
                if not validar_uid(b_uid):
                    erros.append(f"Compilado {pasta.name}: Botão '{b.get('texto')}' sem UID 14c válido: '{b_uid}'")

    assert not erros, f"Inconsistências de retrocompatibilidade no compilado:\n" + "\n".join(erros[:20])
