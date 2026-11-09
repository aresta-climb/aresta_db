# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from aresta_api.proto.generated import croqui_pb2
from editor.core.nomes_arquivos import (
    LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD,
    deduplicar_prefixo,
    garantir_nome_arquivo_md_seguro,
    gerar_nome_arquivo_entidade,
    gerar_nome_mapa_sugerido,
    normalizar_entrada_nome_arquivo_md,
    validar_nome_arquivo_md,
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

    def test_gerar_nome_mapa_sugerido_escalada_boulder(self):
        escalada = croqui_pb2.Escalada()
        escalada.boulder.nome = "La Bamba"
        assert gerar_nome_mapa_sugerido(escalada, 0) == "boulder_la_bamba_p0.webp"
        assert gerar_nome_mapa_sugerido(escalada, 1) == "boulder_la_bamba_p1.webp"

        escalada_com_prefixo = croqui_pb2.Escalada()
        escalada_com_prefixo.boulder.nome = "Boulder do Meio"
        assert gerar_nome_mapa_sugerido(escalada_com_prefixo, 0) == "boulder_do_meio_p0.webp"

        boulder_direto = croqui_pb2.Boulder(nome="Super Teto")
        assert gerar_nome_mapa_sugerido(boulder_direto, 0) == "boulder_super_teto_p0.webp"

    def test_gerar_nome_mapa_sugerido_escalada_vias(self):
        # Via Esportiva
        escalada_esp = croqui_pb2.Escalada()
        escalada_esp.via_esportiva.nome = "Fenda da Ilusão"
        assert gerar_nome_mapa_sugerido(escalada_esp, 0) == "via_fenda_da_ilusao_p0.webp"

        # Via Móvel
        escalada_movel = croqui_pb2.Escalada()
        escalada_movel.via_movel.nome = "Via Fissura"
        assert gerar_nome_mapa_sugerido(escalada_movel, 0) == "via_fissura_p0.webp"

        # Via Múltiplas Enfiadas
        escalada_multi = croqui_pb2.Escalada()
        escalada_multi.via_multiplas_enfiadas.nome = "Paredão Central"
        assert gerar_nome_mapa_sugerido(escalada_multi, 0) == "via_paredao_central_p0.webp"

        # Objeto direto ViaEsportiva
        via_direta = croqui_pb2.ViaEsportiva(nome="Sol Nascente")
        assert gerar_nome_mapa_sugerido(via_direta, 0) == "via_sol_nascente_p0.webp"

        # Highline em Escalada e direto
        escalada_high = croqui_pb2.Escalada()
        escalada_high.highline.nome = "Travessia do Vale"
        assert gerar_nome_mapa_sugerido(escalada_high, 0) == "highline_travessia_do_vale_p0.webp"

        highline_direto = croqui_pb2.Highline(nome=" Fita Azul ")
        assert gerar_nome_mapa_sugerido(highline_direto, 0) == "highline_fita_azul_p0.webp"

        # Escalada sem oneof preenchido
        escalada_vazia = croqui_pb2.Escalada()
        assert gerar_nome_mapa_sugerido(escalada_vazia, 0) == "escalada_p0.webp"

    def test_normalizar_entrada_nome_arquivo_md_converte_espacos_e_adiciona_extensao(self):
        assert normalizar_entrada_nome_arquivo_md("setor fornos") == "setor_fornos.md"
        assert normalizar_entrada_nome_arquivo_md("  setor   do   meio.md  ") == "setor_do_meio.md"
        assert normalizar_entrada_nome_arquivo_md("") == ""
        assert normalizar_entrada_nome_arquivo_md("   ") == ""

    def test_validar_nome_arquivo_md_aceita_snake_case_valido_ate_limite(self):
        valido, normalizado, erro = validar_nome_arquivo_md("setor fornos 2")
        assert valido is True
        assert normalizado == "setor_fornos_2.md"
        assert erro == ""

        nome_no_limite = "a" * (LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD - 3) + ".md"
        valido_lim, norm_lim, erro_lim = validar_nome_arquivo_md(nome_no_limite)
        assert len(norm_lim) == LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD
        assert valido_lim is True
        assert erro_lim == ""

    def test_validar_nome_arquivo_md_recusa_vazio_ou_apenas_extensao(self):
        for entrada in ("", "   ", ".md"):
            valido, _, erro = validar_nome_arquivo_md(entrada)
            assert valido is False
            assert erro != ""

    def test_validar_nome_arquivo_md_recusa_acima_do_limite_de_100_caracteres(self):
        nome_longo = "a" * (LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD - 2) + ".md"
        assert len(nome_longo) == 101
        valido, _, erro = validar_nome_arquivo_md(nome_longo)
        assert valido is False
        assert "100" in erro

    def test_validar_nome_arquivo_md_recusa_caracteres_invalidos_acentos_e_maiusculas(self):
        entradas_invalidas = [
            "YAML: 'aspas' \"duplas\".md",
            "<script>alert('caos')</script>.md",
            "subpasta/setor.md",
            "subpasta\\setor.md",
            "setor_forno_da_onça.md",
            "Setor_Fornos.md",
            "_setor_fornos.md",
            "setor_fornos_.md",
            "setor__fornos.md",
            "setor-fornos.md",
        ]
        for entrada in entradas_invalidas:
            valido, _, erro = validar_nome_arquivo_md(entrada)
            assert valido is False, f"Deveria recusar: {entrada}"
            assert erro != ""

    def test_validar_nome_arquivo_md_verifica_duplicidade_exceto_arquivo_atual(self):
        existentes = ["setor_norte.md", "setor_sul.md"]
        valido_dup, _, erro_dup = validar_nome_arquivo_md("setor norte", existentes)
        assert valido_dup is False
        assert "já existe" in erro_dup.lower() or "uso" in erro_dup.lower()

        valido_atual, norm_atual, erro_atual = validar_nome_arquivo_md(
            "setor_norte.md",
            existentes,
            arquivo_atual="setor_norte.md",
        )
        assert valido_atual is True
        assert norm_atual == "setor_norte.md"
        assert erro_atual == ""

    def test_garantir_nome_arquivo_md_seguro_preserva_nome_valido_ou_original_legado(self):
        assert (
            garantir_nome_arquivo_md_seguro("setor_custom.md", "Setor X", "setor")
            == "setor_custom.md"
        )
        # Arquivo legado com acento mas sem caracteres ilegais de sistema operacional
        assert (
            garantir_nome_arquivo_md_seguro(
                "setor_forno_da_onça.md",
                "Forno da Onça",
                "setor",
                caminho_original="setor_forno_da_onça.md",
            )
            == "setor_forno_da_onça.md"
        )
        assert (
            garantir_nome_arquivo_md_seguro(
                "",
                "Forno da Onça",
                "setor",
                caminho_original="setor_forno_da_onça.md",
            )
            == "setor_forno_da_onça.md"
        )

    def test_garantir_nome_arquivo_md_seguro_higieniza_strings_toxicas_e_nomes_longos(self):
        # Issue #86: dois-pontos, aspas, pipes, etc.
        assert (
            garantir_nome_arquivo_md_seguro(
                "YAML: 'aspas' \"duplas\" : # --- | > @ `.md",
                "Setor Principal",
                "setor",
            )
            == "setor_principal.md"
        )
        # Issue #87: barras e tags HTML, com nome da entidade também tóxico
        assert (
            garantir_nome_arquivo_md_seguro(
                "<script>alert('caos')</script> & <b>bold</b>",
                "???: *** ///",
                "setor",
            )
            == "setor.md"
        )
        # Nome da entidade muito longo truncado <= 100 caracteres
        nome_gigante = "Setor " + ("muito_longo_" * 20)
        gerado = garantir_nome_arquivo_md_seguro("invalido:?.md", nome_gigante, "setor")
        assert len(gerado) <= LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD
        assert gerado.endswith(".md")
        valido, _, _ = validar_nome_arquivo_md(gerado)
        assert valido is True
