# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Aresta Contributors

import os
import yaml
from pathlib import Path
from typing import Dict, List
from aresta_api.proto.generated import beta_pb2

def _midia_beta_para_dict(midia: beta_pb2.MidiaBeta) -> dict:
    """Converte um objeto protobuf MidiaBeta para um dicionário serializável em YAML."""
    fonte_str = "YOUTUBE" if midia.fonte == beta_pb2.FonteMidia.YOUTUBE else "INSTAGRAM"
    d = {
        "url": midia.url,
        "titulo": midia.titulo,
        "fonte": fonte_str,
    }
    if midia.thumbnail_url:
        d["thumbnail_url"] = midia.thumbnail_url
    if midia.match_multiplas_fontes:
        d["match_multiplas_fontes"] = True
    if midia.match_nome_no_snippet:
        d["match_nome_no_snippet"] = True

    if midia.HasField("meta"):
        d["meta"] = {
            "resumo_do_movimento": midia.meta.resumo_do_movimento,
            "llm_confidence_score": midia.meta.llm_confidence_score,
            "llm_reasoning": midia.meta.llm_reasoning
        }
    return d


def injetar_betas_no_markdown(
    caminho_md: Path | str,
    betas_por_escalada: Dict[str, List[beta_pb2.MidiaBeta]]
) -> bool:
    """
    Lê um arquivo Markdown com frontmatter YAML, localiza as escaladas correspondentes
    e injeta a lista de betas no frontmatter, preservando o layout do documento.
    """
    path = Path(caminho_md)
    if not path.exists():
        return False

    conteudo = path.read_text(encoding="utf-8")
    if not conteudo.startswith("---"):
        return False

    partes = conteudo.split("---", 2)
    if len(partes) < 3:
        return False

    header_raw = partes[1]
    body_raw = partes[2]

    # Extrai comentários de cabeçalho (como licença SPDX)
    linhas = header_raw.splitlines()
    comentarios = []
    linhas_yaml = []
    for l in linhas:
        if l.strip().startswith("#"):
            comentarios.append(l)
        else:
            linhas_yaml.append(l)

    try:
        frontmatter = yaml.safe_load("\n".join(linhas_yaml)) or {}
    except Exception:
        return False

    alterado = False
    for lista_key in ["escaladas", "vias"]:
        if lista_key in frontmatter and isinstance(frontmatter[lista_key], list):
            for esc in frontmatter[lista_key]:
                # Descobre o nome da escalada dentro de via_esportiva, via_movel, boulder, etc.
                nome_esc = ""
                for tipo_esc in ["via_esportiva", "via_movel", "boulder", "via_multiplas_enfiadas", "highline"]:
                    if tipo_esc in esc and isinstance(esc[tipo_esc], dict):
                        nome_esc = esc[tipo_esc].get("nome", "")
                        break
                if not nome_esc and "nome" in esc:
                    nome_esc = esc["nome"]

                if nome_esc and nome_esc in betas_por_escalada:
                    novos_betas = [_midia_beta_para_dict(m) for m in betas_por_escalada[nome_esc]]
                    if "betas" not in esc:
                        esc["betas"] = []
                    
                    # Evita duplicar URLs já existentes
                    urls_existentes = {b.get("url") for b in esc["betas"] if isinstance(b, dict)}
                    for nb in novos_betas:
                        if nb["url"] not in urls_existentes:
                            esc["betas"].append(nb)
                            alterado = True

    if alterado:
        # Serializa YAML e reconstrói o arquivo Markdown
        yaml_dumped = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)
        cabecalho_final = ""
        if comentarios:
            cabecalho_final = "\n".join(comentarios) + "\n"
        cabecalho_final += yaml_dumped

        novo_conteudo = f"---{cabecalho_final}---{body_raw}"
        path.write_text(novo_conteudo, encoding="utf-8")

    return alterado


def persistir_aprovacoes(
    caminho_croqui_db: Path | str,
    aprovados_por_escalada: Dict[str, List[beta_pb2.MidiaBeta]],
    limpar_staging: bool = True
) -> int:
    """
    Percorre todos os arquivos .md do croqui e injeta as mídias aprovadas nas vias correspondentes.
    Opcionalmente remove o arquivo temporário betas_pendentes.binarypb.
    """
    db_path = Path(caminho_croqui_db)
    if not db_path.exists() or not db_path.is_dir():
        return 0

    total_injetado = 0
    for arquivo_md in db_path.glob("*.md"):
        if injetar_betas_no_markdown(arquivo_md, aprovados_por_escalada):
            total_injetado += 1

    if limpar_staging:
        staging_file = db_path / "betas_pendentes.binarypb"
        if staging_file.exists():
            try:
                staging_file.unlink()
            except Exception:
                pass

    return total_injetado
