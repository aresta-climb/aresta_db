# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from aresta_api.proto.generated import croqui_pb2
from editor.core.nomes_arquivos import (
    deduplicar_prefixo,
    gerar_nome_mapa_sugerido,
    gerar_nome_arquivo_entidade,
)


class TestNomesArquivos:
    def test_deduplicar_prefixo_quando_nome_ja_tem_prefixo(self):
        assert deduplicar_prefixo("Setor Fugitivos I", "setor") == "setor_fugitivos_i"
        assert deduplicar_prefixo("setor_fugitivos_i", "setor") == "setor_fugitivos_i"
        assert deduplicar_prefixo("Grupo Principal", "grupo") == "grupo_principal"
        assert deduplicar_prefixo("grupo_principal", "grupo") == "grupo_principal"

    def test_deduplicar_prefixo_quando_nome_nao_tem_prefixo(self):
        assert deduplicar_prefixo("Fugitivos I", "setor") == "setor_fugitivos_i"
        assert deduplicar_prefixo("Sherpa", "grupo") == "grupo_sherpa"

    def test_deduplicar_prefixo_quando_nome_e_exatamente_o_prefixo(self):
        assert deduplicar_prefixo("Setor", "setor") == "setor"
        assert deduplicar_prefixo("Grupo", "grupo") == "grupo"

    def test_deduplicar_prefixo_vazio(self):
        assert deduplicar_prefixo("", "setor") == "setor"
        assert deduplicar_prefixo(None, "setor") == "setor"

    def test_gerar_nome_mapa_sugerido_setor_com_prefixo(self):
        setor = croqui_pb2.Setor(nome="Setor Fugitivos I")
        assert gerar_nome_mapa_sugerido(setor, 0) == "setor_fugitivos_i_p0.webp"
        assert gerar_nome_mapa_sugerido(setor, 2) == "setor_fugitivos_i_p2.webp"

    def test_gerar_nome_mapa_sugerido_setor_sem_prefixo(self):
        setor = croqui_pb2.Setor(nome="Pedra do Sino")
        assert gerar_nome_mapa_sugerido(setor, 0) == "setor_pedra_do_sino_p0.webp"

    def test_gerar_nome_mapa_sugerido_grupo(self):
        grupo = croqui_pb2.Grupo(nome="Grupo dos Blocos")
        assert gerar_nome_mapa_sugerido(grupo, 0) == "grupo_dos_blocos_p0.webp"

        grupo_sem_prefixo = croqui_pb2.Grupo(nome="Sherpa")
        assert gerar_nome_mapa_sugerido(grupo_sem_prefixo, 1) == "grupo_sherpa_p1.webp"

    def test_gerar_nome_mapa_sugerido_colecao_mapas_gerais(self):
        colecao = croqui_pb2.ColecaoDeMapas()
        assert gerar_nome_mapa_sugerido(colecao, 0) == "mapas_gerais_p0.webp"
        assert gerar_nome_mapa_sugerido(colecao, 3) == "mapas_gerais_p3.webp"

    def test_gerar_nome_mapa_sugerido_entidade_sem_nome(self):
        setor = croqui_pb2.Setor()
        assert gerar_nome_mapa_sugerido(setor, 0) == "setor_p0.webp"

    def test_deduplicar_prefixo_quando_nome_e_bloco_de_setor(self):
        assert deduplicar_prefixo("Bloco Fugitivos I", "setor") == "bloco_fugitivos_i"
        assert deduplicar_prefixo("bloco_fugitivos_i", "setor") == "bloco_fugitivos_i"
        assert deduplicar_prefixo("Bloco", "setor") == "bloco"
        assert deduplicar_prefixo("Blocos da Entrada", "setor") == "blocos_da_entrada"
        assert deduplicar_prefixo("Blocos", "setor") == "blocos"

    def test_gerar_nome_mapa_sugerido_setor_com_nome_bloco(self):
        setor = croqui_pb2.Setor(nome="Bloco Fugitivos I")
        assert gerar_nome_mapa_sugerido(setor, 0) == "bloco_fugitivos_i_p0.webp"
        assert gerar_nome_mapa_sugerido(setor, 1) == "bloco_fugitivos_i_p1.webp"

        setor_bloco_puro = croqui_pb2.Setor(nome="Bloco")
        assert gerar_nome_mapa_sugerido(setor_bloco_puro, 0) == "bloco_p0.webp"

    def test_gerar_nome_arquivo_entidade(self):
        assert gerar_nome_arquivo_entidade("Setor do Meio", "setor") == "setor_do_meio.md"
        assert gerar_nome_arquivo_entidade("Falésia", "setor") == "setor_falesia.md"
        assert gerar_nome_arquivo_entidade("Bloco Tremembé", "setor") == "bloco_tremembe.md"
        assert gerar_nome_arquivo_entidade("Blocos da Entrada", "setor") == "blocos_da_entrada.md"
        assert gerar_nome_arquivo_entidade("Bloco", "setor") == "bloco.md"
        assert gerar_nome_arquivo_entidade("Grupo Principal", "grupo") == "grupo_principal.md"
        assert gerar_nome_arquivo_entidade("Setor", "setor") == "setor.md"
        assert gerar_nome_arquivo_entidade("", "setor") == "setor.md"

