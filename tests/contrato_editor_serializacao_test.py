# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de contrato para as rotinas de serialização do Editor Desktop.

Garante que o editor, ao salvar croquis novos ou editados:
1. Sempre gera UIDs válidos de 14 caracteres Base62 para todas as entidades.
2. Preserva imutavelmente os UIDs já existentes em entidades persistidas.
3. Serializa exclusivamente 'rotulo' em pontos de interesse, nunca gravando o campo depreciado 'label'.
4. Serializa exclusivamente 'alvo_uid' e 'pontos_uids' em referências de mapas, nunca gravando
   campos depreciados ('escalada', 'setor', 'grupo').
"""

from pathlib import Path
import pytest
import yaml

from aresta_api.proto.generated.croqui_pb2 import Croqui, ArquivoSetor, ArquivoGrupo
from editor.models.croqui_model import CroquiModel
from scripts.gerenciar_uids_lib import validar_uid, gerar_uid
from scripts.preparar_submissao_lib import parse_md_com_frontmatter


def test_contrato_editor_serializacao_croqui_novo_gera_uids_e_sem_legados(qapp, tmp_path: Path):
    """Garante que um novo croqui serializado pelo editor cumpre o contrato Pure NanoID e rótulos."""
    croqui = Croqui(nome="Croqui Novo Contrato")
    pico = croqui.picos.add(nome="Pico 1")

    # Adiciona um setor via ArquivoSetor
    setor_ou_grupo = pico.setores_ou_grupos.add()
    setor_arq = setor_ou_grupo.setor
    setor_arq.caminho = "setor_novo.md"
    setor_arq.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_novo.md"

    conteudo_setor = setor_arq.conteudo
    conteudo_setor.nome = "Setor Novo Contrato"

    # Adiciona escalada sem UID
    esc = conteudo_setor.escaladas.add()
    esc.via_esportiva.nome = "Via Nova Contrato"

    # Adiciona mapa com POI e referência
    mapa = conteudo_setor.mapas.add(caminho_imagem_mapa="imagens/mapa.webp")
    poi = mapa.pontos_de_interesse.add(id="poi1", rotulo="1")
    poi.circulo.x = 100
    poi.circulo.y = 200
    poi.circulo.raio = 15

    # Referência conectando via e poi
    ref = mapa.referencias.add(escalada="Via Nova Contrato", ids=["poi1"])

    # Adiciona botão textual sem UID
    btn = croqui.botoes.add(texto="Avisos")
    btn.destino.secao_textual.conteudo = "# Avisos importantes"

    model = CroquiModel(croqui)
    pasta_destino = tmp_path / "novo_croqui"
    pasta_destino.mkdir()

    # Executa a serialização
    dados_yaml = model.extrair_arquivos_e_serializar(pasta_destino)

    # 1. Valida croqui.yaml
    assert "uid" in dados_yaml
    assert validar_uid(dados_yaml["uid"]) is True
    assert "botoes" in dados_yaml
    assert len(dados_yaml["botoes"]) == 1
    assert "uid" in dados_yaml["botoes"][0]
    assert validar_uid(dados_yaml["botoes"][0]["uid"]) is True

    # 2. Valida arquivo .md do setor gerado no disco
    arquivo_md = pasta_destino / "setor_novo.md"
    assert arquivo_md.exists()

    frontmatter, _ = parse_md_com_frontmatter(arquivo_md)
    assert frontmatter is not None

    # UID do setor
    assert "uid" in frontmatter
    assert validar_uid(frontmatter["uid"]) is True

    # UID da escalada
    escaladas = frontmatter.get("escaladas", [])
    assert len(escaladas) == 1
    assert "uid" in escaladas[0]
    assert validar_uid(escaladas[0]["uid"]) is True
    uid_escalada = escaladas[0]["uid"]

    # POI: uid presente, rotulo presente, label e id ausentes
    mapas = frontmatter.get("mapas", [])
    assert len(mapas) == 1
    pois = mapas[0].get("pontos_de_interesse", [])
    assert len(pois) == 1
    assert "uid" in pois[0]
    assert validar_uid(pois[0]["uid"]) is True
    assert pois[0].get("rotulo") == "1"
    assert "label" not in pois[0], "O campo 'label' não pode ser emitido pelo editor."
    assert "id" not in pois[0], "O campo depreciado 'id' não pode ser emitido pelo editor."
    uid_poi = pois[0]["uid"]

    # Referência: alvo_uid e pontos_uids presentes, escalada/setor/grupo/ids/indice_mapa_alvo ausentes
    refs = mapas[0].get("referencias", [])
    assert len(refs) == 1
    assert refs[0].get("alvo_uid") == uid_escalada
    assert refs[0].get("pontos_uids") == [uid_poi]
    assert "escalada" not in refs[0], "O campo depreciado 'escalada' não pode ser emitido pelo editor."
    assert "setor" not in refs[0]
    assert "grupo" not in refs[0]
    assert "ids" not in refs[0], "O campo depreciado 'ids' não pode ser emitido pelo editor."
    assert "indice_mapa_alvo" not in refs[0], "O campo depreciado 'indice_mapa_alvo' não pode ser emitido pelo editor."


def test_contrato_editor_serializacao_preserva_uids_existentes(qapp, tmp_path: Path):
    """Garante que salvar um croqui existente preserva estritamente os UIDs já alocados."""
    uid_croqui_original = gerar_uid()
    uid_setor_original = gerar_uid()
    uid_esc_original = gerar_uid()
    uid_poi_original = gerar_uid()

    croqui = Croqui(nome="Croqui Existente", uid=uid_croqui_original)
    pico = croqui.picos.add(nome="Pico 1")

    setor_ou_grupo = pico.setores_ou_grupos.add()
    setor_arq = setor_ou_grupo.setor
    setor_arq.caminho = "setor_existente.md"
    setor_arq.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_existente.md"

    conteudo_setor = setor_arq.conteudo
    conteudo_setor.uid = uid_setor_original
    conteudo_setor.nome = "Setor Existente"

    esc = conteudo_setor.escaladas.add(uid=uid_esc_original)
    esc.via_esportiva.nome = "Via Existente"

    mapa = conteudo_setor.mapas.add(caminho_imagem_mapa="imagens/mapa.webp")
    poi = mapa.pontos_de_interesse.add(id="poi1", uid=uid_poi_original, rotulo="10")
    poi.circulo.x = 50
    poi.circulo.y = 60
    poi.circulo.raio = 10

    ref = mapa.referencias.add(alvo_uid=uid_esc_original, pontos_uids=[uid_poi_original], ids=["poi1"])

    model = CroquiModel(croqui)
    pasta_destino = tmp_path / "croqui_existente"
    pasta_destino.mkdir()

    # Modifica o nome da via antes de salvar
    model._set_primitivo(esc.via_esportiva, "nome", "Via Renomeada")

    uid_botao_original = gerar_uid()
    btn = croqui.botoes.add(texto="Regras", uid=uid_botao_original)
    btn.destino.secao_textual.conteudo = "# Regras"

    dados_yaml = model.extrair_arquivos_e_serializar(pasta_destino)

    # UIDs devem ser idênticos aos originais
    assert dados_yaml["uid"] == uid_croqui_original
    assert dados_yaml["botoes"][0]["uid"] == uid_botao_original

    arquivo_md = pasta_destino / "setor_existente.md"
    frontmatter, _ = parse_md_com_frontmatter(arquivo_md)

    assert frontmatter["uid"] == uid_setor_original
    assert frontmatter["escaladas"][0]["uid"] == uid_esc_original
    assert frontmatter["escaladas"][0]["via_esportiva"]["nome"] == "Via Renomeada"

    poi_salvo = frontmatter["mapas"][0]["pontos_de_interesse"][0]
    assert poi_salvo["uid"] == uid_poi_original
    assert poi_salvo["rotulo"] == "10"
    assert "label" not in poi_salvo
    assert "id" not in poi_salvo, "O campo depreciado 'id' não deve ser gravado."

    ref_salva = frontmatter["mapas"][0]["referencias"][0]
    assert ref_salva["alvo_uid"] == uid_esc_original
    assert ref_salva["pontos_uids"] == [uid_poi_original]
    assert "escalada" not in ref_salva
    assert "ids" not in ref_salva, "O campo depreciado 'ids' não deve ser gravado."
    assert "indice_mapa_alvo" not in ref_salva, "O campo depreciado 'indice_mapa_alvo' não deve ser gravado."
