# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from aresta_api.proto.generated import croqui_pb2
from editor.models.readonly_proxy import ReadOnlyProxy
from editor.core.imagens_croqui import (
    extrair_caminhos_imagens,
    obter_imagens_orfas_ao_remover,
)


class TestImagensCroqui:
    def test_extrair_caminhos_imagens_objeto_nulo_ou_vazio(self):
        assert extrair_caminhos_imagens(None) == []
        mapa_vazio = croqui_pb2.Mapa()
        assert extrair_caminhos_imagens(mapa_vazio) == []

    def test_extrair_caminhos_imagens_mapa_simples(self):
        mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/mapa1.webp")
        assert extrair_caminhos_imagens(mapa) == ["imagens/mapa1.webp"]

    def test_extrair_caminhos_imagens_normalizacao_barras(self):
        mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens\\subpasta\\mapa1.webp")
        assert extrair_caminhos_imagens(mapa) == ["imagens/subpasta/mapa1.webp"]

    def test_extrair_caminhos_imagens_com_proxy(self):
        mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/proxy.webp")
        proxy = ReadOnlyProxy(mapa)
        assert extrair_caminhos_imagens(proxy) == ["imagens/proxy.webp"]

    def test_extrair_caminhos_imagens_setor_e_grupo(self):
        setor = croqui_pb2.Setor(nome="Setor A")
        setor.mapas.add(caminho_imagem_mapa="imagens/mapa_setor_1.webp")
        setor.mapas.add(caminho_imagem_mapa="imagens/mapa_setor_2.webp")

        caminhos_setor = extrair_caminhos_imagens(setor)
        assert caminhos_setor == ["imagens/mapa_setor_1.webp", "imagens/mapa_setor_2.webp"]

        grupo = croqui_pb2.Grupo(nome="Grupo Principal")
        grupo.mapas.add(caminho_imagem_mapa="imagens/mapa_grupo.webp")
        setor_filho = grupo.setores.add().conteudo
        setor_filho.mapas.add(caminho_imagem_mapa="imagens/mapa_filho.webp")

        caminhos_grupo = extrair_caminhos_imagens(grupo)
        assert caminhos_grupo == ["imagens/mapa_grupo.webp", "imagens/mapa_filho.webp"]

    def test_extrair_caminhos_imagens_croqui_completo_com_thumbnail(self):
        croqui = croqui_pb2.Croqui(nome="Croqui", caminho_thumbnail="imagens/thumb.webp")
        pico = croqui.picos.add(nome="Pico")
        pico.mapas_gerais.conteudo.mapas.add(caminho_imagem_mapa="imagens/mapas_gerais.webp")

        caminhos = extrair_caminhos_imagens(croqui)
        assert "imagens/thumb.webp" in caminhos
        assert "imagens/mapas_gerais.webp" in caminhos

    def test_obter_imagens_orfas_ao_remover_sem_imagens_em_ram(self):
        mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/mapa1.webp")
        croqui = croqui_pb2.Croqui()
        orfas = obter_imagens_orfas_ao_remover(croqui, mapa, imagens_em_ram={})
        assert orfas == {}

    def test_obter_imagens_orfas_ao_remover_imagem_exclusiva(self):
        croqui = croqui_pb2.Croqui()
        pico = croqui.picos.add()
        sg = pico.setores_ou_grupos.add()
        setor = sg.setor.conteudo
        setor.mapas.add(caminho_imagem_mapa="imagens/mapa_exclusivo.webp")

        mapa_removido = setor.mapas[0]
        imagens_ram = {"imagens/mapa_exclusivo.webp": b"dados_imagem_bytes"}

        orfas = obter_imagens_orfas_ao_remover(croqui, mapa_removido, imagens_ram)
        assert orfas == {"imagens/mapa_exclusivo.webp": b"dados_imagem_bytes"}

    def test_obter_imagens_orfas_ao_remover_imagem_compartilhada(self):
        croqui = croqui_pb2.Croqui()
        pico = croqui.picos.add()
        sg1 = pico.setores_ou_grupos.add()
        setor1 = sg1.setor.conteudo
        setor1.mapas.add(caminho_imagem_mapa="imagens/mapa_compartilhado.webp")

        sg2 = pico.setores_ou_grupos.add()
        setor2 = sg2.setor.conteudo
        setor2.mapas.add(caminho_imagem_mapa="imagens/mapa_compartilhado.webp")

        mapa_removido = setor1.mapas[0]
        imagens_ram = {"imagens/mapa_compartilhado.webp": b"dados_imagem"}

        # Como setor2 ainda usa imagens/mapa_compartilhado.webp, ela NÃO deve ser órfã
        orfas = obter_imagens_orfas_ao_remover(croqui, mapa_removido, imagens_ram)
        assert orfas == {}

    def test_obter_imagens_orfas_ao_remover_item_sem_caminhos_imagem(self):
        croqui = croqui_pb2.Croqui()
        pico_sem_mapas = croqui_pb2.Pico(nome="Pico sem mapas")
        orfas = obter_imagens_orfas_ao_remover(croqui, pico_sem_mapas, {"imagens/teste.webp": b"123"})
        assert orfas == {}

    def test_obter_imagens_orfas_ao_remover_caminhos_nao_presentes_na_ram(self):
        croqui = croqui_pb2.Croqui()
        mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/outro.webp")
        orfas = obter_imagens_orfas_ao_remover(croqui, mapa, {"imagens/diferente.webp": b"123"})
        assert orfas == {}

    def test_obter_imagens_orfas_ao_remover_croqui_nulo(self):
        mapa = croqui_pb2.Mapa(caminho_imagem_mapa="imagens/teste.webp")
        orfas = obter_imagens_orfas_ao_remover(None, mapa, {"imagens/teste.webp": b"123"})
        assert orfas == {}

    def test_obter_imagens_orfas_ao_remover_item_nulo(self):
        croqui = croqui_pb2.Croqui()
        orfas = obter_imagens_orfas_ao_remover(croqui, None, {"imagens/teste.webp": b"123"})
        assert orfas == {}
