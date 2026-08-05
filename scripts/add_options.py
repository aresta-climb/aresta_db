# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import re

with open("kmon_api/proto/croqui.proto", "r", encoding="utf-8") as f:
    content = f.read()

# ui_label
content = re.sub(r'(\s+)string id_no_mapa =', r'\1string id_no_mapa =', content) # wait, better to just replace specific lines
# Let's replace manually by doing multiple re.sub
replacements = [
    (r'string id_no_mapa =', r'string id_no_mapa =', '[(acecmg.ui_label) = "ID no Mapa"]'),
    (r'string id_no_mapa_meio =', r'string id_no_mapa_meio =', '[(acecmg.ui_label) = "ID no Mapa (Meio)"]'),
    (r'string id_no_mapa_fim =', r'string id_no_mapa_fim =', '[(acecmg.ui_label) = "ID no Mapa (Fim)"]'),
    (r'string url_video_beta =', r'string url_video_beta =', '[(acecmg.ui_label) = "URL do Vídeo do Beta", (acecmg.conteudo) = CONTEUDO_CAMINHO, (acecmg.mime_type) = "video/mp4"]'),
    (r'string chave_pix_manutencao =', r'string chave_pix_manutencao =', '[(acecmg.ui_label) = "Chave Pix para Manutenção"]'),
    (r'string url_google_maps =', r'string url_google_maps =', '[(acecmg.ui_label) = "URL Google Maps"]'),
    (r'string url_filiacao_associacao =', r'string url_filiacao_associacao =', '[(acecmg.ui_label) = "URL de Filiação"]'),
    (r'string url_logo =', r'string url_logo =', '[(acecmg.ui_label) = "URL da Logo"]'),
    (r'string url_link =', r'string url_link =', '[(acecmg.ui_label) = "URL do Link"]'),
    
    # conteudo_markdown
    (r'string descricao =', r'string descricao =', '[(acecmg.conteudo_markdown) = true]'),
    
    # conteudo_caminho
    (r'string caminho_imagem_mapa =', r'string caminho_imagem_mapa =', '[(acecmg.conteudo) = CONTEUDO_CAMINHO, (acecmg.mime_type) = "image/webp"]'),
    (r'string caminho_thumbnail =', r'string caminho_thumbnail =', '[(acecmg.conteudo) = CONTEUDO_CAMINHO, (acecmg.mime_type) = "image/webp"]'),
]

for old, new, option in replacements:
    content = re.sub(r'(\s+)' + old + r' (\d+);', r'\1' + new + r' \2 ' + option + r';', content)

# special cases for "caminho" in oneofs
content = re.sub(r'(\s+)string caminho = (\d+);(.*?)// ArquivoMarkdown', r'\1string caminho = \2 [(acecmg.conteudo) = CONTEUDO_CAMINHO, (acecmg.mime_type) = "text/markdown-yaml"];\3// ArquivoMarkdown', content, flags=re.DOTALL)

with open("kmon_api/proto/croqui.proto", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
