# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import yaml
from pathlib import Path

def migrar(caminho_croqui: Path) -> None:
    """
    Migra a estrutura legada de seções textuais ou arquivos markdown do croqui
    para a nova estrutura de botões contendo o destino apropriado.
    """
    caminho_yaml = caminho_croqui / "croqui.yaml"
    if not caminho_yaml.exists():
        return
        
    with open(caminho_yaml, "r", encoding="utf-8") as f:
        dados_croqui = yaml.safe_load(f) or {}
        
    if dados_croqui.get("ultima_migracao", 0) >= 1:
        return

    # Identifica as seções nos formatos antigo (secoes_textuais) e antiquado (arquivos_markdown)
    secoes_antigas = dados_croqui.get("secoes_textuais") or dados_croqui.get("arquivos_markdown")
    if not secoes_antigas:
        return
        
    botoes = []
    for item in secoes_antigas:
        if not isinstance(item, dict):
            continue
            
        titulo = item.get("titulo", "Informações")
        caminho = item.get("caminho")
        
        if caminho:
            # Cria a estrutura aninhada exigida pelo novo schema do Botao e DestinoBotao (oneof)
            botoes.append({
                "texto": titulo,
                "destino": {
                    "secao_textual": {
                        "caminho": caminho
                    }
                }
            })
            
    # Aplica o novo formato e remove os legados
    dados_croqui["botoes"] = botoes
    dados_croqui.pop("secoes_textuais", None)
    dados_croqui.pop("arquivos_markdown", None)
    
    with open(caminho_yaml, "w", encoding="utf-8") as f:
        yaml.dump(dados_croqui, f, allow_unicode=True, sort_keys=False)
