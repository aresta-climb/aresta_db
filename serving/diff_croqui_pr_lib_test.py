# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes comportamentais para a biblioteca de diff semântico e visual de croquis em Pull Requests."""

from pathlib import Path

from PIL import Image

from aresta_api.proto.generated import croqui_pb2
from serving.diff_croqui_pr_lib import calcular_diff_pull_request


def _criar_imagem_webp(caminho: Path, largura: int, altura: int, cor: tuple[int, int, int]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    imagem = Image.new("RGB", (largura, altura), color=cor)
    imagem.save(caminho, format="WEBP")


def _salvar_croqui_compilado(diretorio_raiz: Path, croqui: croqui_pb2.Croqui) -> Path:
    pasta_croqui = diretorio_raiz / croqui.id
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    caminho_pb = pasta_croqui / "compilado.binarypb"
    caminho_pb.write_bytes(croqui.SerializeToString())
    return pasta_croqui


def test_classifica_croqui_ausente_na_base_como_novo_e_contabiliza_entidades(
    tmp_path: Path,
) -> None:
    """Dado um croqui que não existe na branch base, deve classificá-lo como novo e listar suas entidades."""
    dir_base = tmp_path / "base"
    dir_pr = tmp_path / "pr"
    dir_base.mkdir()
    dir_pr.mkdir()

    croqui = croqui_pb2.Croqui(
        id="serra_cipo",
        uid="uid_croqui_cipo",
        nome="Serra do Cipó",
        caminho_thumbnail="imagens/thumb.webp",
    )
    _criar_imagem_webp(dir_pr / "serra_cipo" / "imagens" / "thumb.webp", 200, 150, (20, 40, 60))
    _criar_imagem_webp(dir_pr / "serra_cipo" / "imagens" / "mapa_setor.webp", 800, 600, (90, 90, 90))
    croqui.arquivos_externos.add(caminho="imagens/thumb.webp", checksum_sha256="sha_thumb_novo")
    croqui.arquivos_externos.add(caminho="imagens/mapa_setor.webp", checksum_sha256="sha_mapa_novo")

    pico = croqui.picos.add(nome="Serra do Cipó", cidade="Santana do Riacho", estado="MG")
    grupo = pico.setores_ou_grupos.add().grupo.conteudo
    grupo.uid = "uid_grupo_1"
    grupo.nome = "Grupo Grande"

    setor = grupo.setores.add().conteudo
    setor.uid = "uid_setor_1"
    setor.nome = "Setor Fenda"

    mapa = setor.mapas.add(
        caminho_imagem_mapa="imagens/mapa_setor.webp",
        largura_mapa=800,
        altura_mapa=600,
    )
    ponto = mapa.pontos_de_interesse.add(uid="uid_ponto_1", rotulo="1")
    ponto.circulo.x = 120
    ponto.circulo.y = 240
    ponto.circulo.raio = 14

    via = setor.escaladas.add(uid="uid_via_1")
    via.via_esportiva.nome = "Fenda Central"
    via.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP
    via.via_esportiva.extensao = 25

    _salvar_croqui_compilado(dir_pr, croqui)

    resumo = calcular_diff_pull_request(dir_base=dir_base, dir_pr=dir_pr)

    assert len(resumo.croquis) == 1
    diff_croqui = resumo.croquis[0]
    assert diff_croqui.id_croqui == "serra_cipo"
    assert diff_croqui.status == "novo"
    assert resumo.total_setores_adicionados == 1
    assert resumo.total_escaladas_adicionadas == 1
    assert resumo.total_mapas_alterados == 1
    assert len(diff_croqui.imagens) == 2
    assert all(img.status == "adicionado" for img in diff_croqui.imagens)
    assert diff_croqui.arquivos_base_copiados == []


def test_pareia_entidades_por_uid_detectando_renomeacoes_e_edicoes_de_campos(
    tmp_path: Path,
) -> None:
    """Dado um croqui modificado mantendo o mesmo UID nas entidades, deve pareá-las como modificadas."""
    dir_base = tmp_path / "base"
    dir_pr = tmp_path / "pr"
    dir_base.mkdir()
    dir_pr.mkdir()

    # Estado Base
    croqui_base = croqui_pb2.Croqui(
        id="ouro_preto",
        uid="uid_op",
        nome="Ouro Preto",
        descricao="Texto antigo do croqui.",
    )
    pico_base = croqui_base.picos.add(nome="Parque das Andorinhas", cidade="Ouro Preto", estado="MG")
    grupo_base_rem = pico_base.setores_ou_grupos.add().grupo.conteudo
    grupo_base_rem.uid = "uid_grupo_rem"
    grupo_base_rem.nome = "Grupo Removido"
    setor_rem = grupo_base_rem.setores.add().conteudo
    setor_rem.uid = "uid_setor_rem"
    setor_rem.nome = "Setor Removido"

    grupo_base_mod = pico_base.setores_ou_grupos.add().grupo.conteudo
    grupo_base_mod.uid = "uid_grupo_mod"
    grupo_base_mod.nome = "Grupo Antigo"
    grupo_base_mod.caminho_imagem_capa = "imagens/capa_grupo.webp"
    grupo_base_mod.mapas.add(caminho_imagem_mapa="imagens/mapa_grupo_rem.webp", largura_mapa=400, altura_mapa=300)

    setor_base = pico_base.setores_ou_grupos.add().setor.conteudo
    setor_base.uid = "uid_setor_andorinhas"
    setor_base.nome = "Parede Antiga"
    setor_base.descricao = "Acesso pela trilha velha."
    setor_base.mapas.add(
        caminho_imagem_mapa="imagens/mapa_estatico.webp", largura_mapa=600, altura_mapa=400
    )

    via_esportiva_base = setor_base.escaladas.add(uid="uid_esc_1")
    via_esportiva_base.via_esportiva.nome = "Via do Sol"
    via_esportiva_base.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6
    via_esportiva_base.via_esportiva.extensao = 20
    via_esportiva_base.via_esportiva.quantidade_protecoes_intermediarias = 6
    via_esportiva_base.via_esportiva.conquistadores.extend(["João"])
    via_esportiva_base.via_esportiva.descricao = "Beta antigo."

    boulder_base = setor_base.escaladas.add(uid="uid_boulder_mod")
    boulder_base.boulder.nome = "Bloco Antigo"
    boulder_base.boulder.dificuldade = croqui_pb2.GrauBoulder.V3

    boulder_removido = setor_base.escaladas.add(uid="uid_boulder_rem")
    boulder_removido.boulder.nome = "Bloco Perdido"
    boulder_removido.boulder.dificuldade = croqui_pb2.GrauBoulder.V2

    via_movel_base = setor_base.escaladas.add(uid="uid_movel_1")
    via_movel_base.via_movel.nome = "Diedro Clássico"
    via_movel_base.via_movel.dificuldade = croqui_pb2.GrauVia.BR_5SUP
    via_movel_base.via_movel.protecoes_moveis = "1 jogo de Camalot"

    _salvar_croqui_compilado(dir_base, croqui_base)

    # Estado PR
    croqui_pr = croqui_pb2.Croqui(
        id="ouro_preto",
        uid="uid_op",
        nome="Ouro Preto Revisado",
        descricao="Texto atualizado do croqui.",
    )
    pico_pr = croqui_pr.picos.add(nome="Parque Municipal das Andorinhas", cidade="Ouro Preto", estado="MG")
    pico_pr.mapas_gerais.conteudo.mapas.add(
        caminho_imagem_mapa="imagens/mapa_geral.webp", largura_mapa=500, altura_mapa=400
    )

    grupo_pr_mod = pico_pr.setores_ou_grupos.add().grupo.conteudo
    grupo_pr_mod.uid = "uid_grupo_mod"
    grupo_pr_mod.nome = "Grupo Renomeado"
    grupo_pr_mod.caminho_imagem_capa = "imagens/capa_grupo.webp"

    setor_pr = pico_pr.setores_ou_grupos.add().setor.conteudo
    setor_pr.uid = "uid_setor_andorinhas"
    setor_pr.nome = "Parede Principal"
    setor_pr.descricao = "Acesso pela trilha nova sinalizada."
    setor_pr.mapas.add(
        caminho_imagem_mapa="imagens/mapa_estatico.webp", largura_mapa=600, altura_mapa=400
    )

    via_esportiva_pr = setor_pr.escaladas.add(uid="uid_esc_1")
    via_esportiva_pr.via_esportiva.nome = "Via do Sol Nascente"
    via_esportiva_pr.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP
    via_esportiva_pr.via_esportiva.extensao = 24
    via_esportiva_pr.via_esportiva.quantidade_protecoes_intermediarias = 8
    via_esportiva_pr.via_esportiva.conquistadores.extend(["João", "Maria"])
    via_esportiva_pr.via_esportiva.descricao = "Beta revisado com crux no teto."
    via_esportiva_pr.mapas.add(
        caminho_imagem_mapa="imagens/mapa_detalhe_via.webp", largura_mapa=300, altura_mapa=300
    )

    boulder_pr = setor_pr.escaladas.add(uid="uid_boulder_mod")
    boulder_pr.boulder.nome = "Bloco Novo"
    boulder_pr.boulder.dificuldade = croqui_pb2.GrauBoulder.V4

    via_movel_pr = setor_pr.escaladas.add(uid="uid_movel_1")
    via_movel_pr.via_movel.nome = "Diedro Clássico"
    via_movel_pr.via_movel.dificuldade = croqui_pb2.GrauVia.BR_5SUP
    via_movel_pr.via_movel.protecoes_moveis = "1 jogo de Camalot #0.5 a #3"

    via_mult_nova = setor_pr.escaladas.add(uid="uid_mult_nova")
    via_mult_nova.via_multiplas_enfiadas.nome = "Parede Infinita"
    via_mult_nova.via_multiplas_enfiadas.dificuldade_maxima = croqui_pb2.GrauVia.BR_7A
    via_mult_nova.via_multiplas_enfiadas.comprimento_total = 120
    via_mult_nova.via_multiplas_enfiadas.numero_enfiadas = 4

    highline_novo = setor_pr.escaladas.add(uid="uid_high_novo")
    highline_novo.highline.nome = "Travessia dos Ventos"
    highline_novo.highline.distancia = 85
    highline_novo.highline.altura = 50

    _salvar_croqui_compilado(dir_pr, croqui_pr)

    resumo = calcular_diff_pull_request(
        dir_base=dir_base,
        dir_pr=dir_pr,
        ids_croquis=["ouro_preto"],
    )

    assert len(resumo.croquis) == 1
    diff_croqui = resumo.croquis[0]
    assert diff_croqui.status == "modificado"
    assert resumo.total_setores_modificados == 1
    assert resumo.total_setores_adicionados == 0
    assert resumo.total_setores_removidos == 1
    assert resumo.total_escaladas_modificadas == 3
    assert resumo.total_escaladas_adicionadas == 2
    assert resumo.total_escaladas_removidas == 1
    assert resumo.total_imagens_alteradas == 0

    entidades_por_uid = {e.uid: e for e in diff_croqui.entidades}
    diff_setor = entidades_por_uid["uid_setor_andorinhas"]
    assert diff_setor.status == "modificado"
    assert diff_setor.nome_antes == "Parede Antiga"
    assert diff_setor.nome_depois == "Parede Principal"

    diff_via = entidades_por_uid["uid_esc_1"]
    assert diff_via.status == "modificado"
    assert diff_via.nome_antes == "Via do Sol"
    assert diff_via.nome_depois == "Via do Sol Nascente"
    nomes_campos_via = {c.nome_campo: c for c in diff_via.alteracoes_campos}
    assert nomes_campos_via["Nome"].valor_antes == "Via do Sol"
    assert nomes_campos_via["Nome"].valor_depois == "Via do Sol Nascente"
    assert nomes_campos_via["Dificuldade"].valor_antes == "BR_6"
    assert nomes_campos_via["Dificuldade"].valor_depois == "BR_6SUP"
    assert nomes_campos_via["Extensão (m)"].valor_antes == "20"
    assert nomes_campos_via["Extensão (m)"].valor_depois == "24"
    assert nomes_campos_via["Descrição"].eh_markdown is True


def test_compara_mapas_pontos_de_interesse_e_copia_imagens_modificadas_para_pasta_base(
    tmp_path: Path,
) -> None:
    """Dado um croqui com mapas e imagens alteradas, deve calcular o diff geométrico e copiar imagens base modificadas/removidas."""
    dir_base = tmp_path / "base"
    dir_pr = tmp_path / "pr"
    dir_base.mkdir()
    dir_pr.mkdir()

    # Imagens na base
    _criar_imagem_webp(dir_base / "cipo" / "imagens" / "mapa_inalterado.webp", 1000, 800, (50, 50, 50))
    _criar_imagem_webp(dir_base / "cipo" / "imagens" / "mapa_cortado.webp", 1000, 800, (100, 40, 40))
    _criar_imagem_webp(dir_base / "cipo" / "imagens" / "capa_setor.webp", 600, 400, (30, 80, 30))
    _criar_imagem_webp(dir_base / "cipo" / "imagens" / "foto_removida.webp", 400, 300, (80, 80, 10))
    _criar_imagem_webp(dir_base / "thumbnails" / "cipo.webp", 300, 200, (10, 20, 30))

    # Imagens na PR (mapa_inalterado é idêntico; mapa_cortado e capa_setor e thumbnail mudaram; foto_md_nova adicionada)
    _criar_imagem_webp(dir_pr / "cipo" / "imagens" / "mapa_inalterado.webp", 1000, 800, (50, 50, 50))
    _criar_imagem_webp(dir_pr / "cipo" / "imagens" / "mapa_cortado.webp", 900, 700, (120, 60, 60))
    _criar_imagem_webp(dir_pr / "cipo" / "imagens" / "capa_setor.webp", 600, 400, (40, 120, 40))
    _criar_imagem_webp(dir_pr / "cipo" / "imagens" / "foto_md_nova.webp", 500, 350, (90, 20, 90))
    _criar_imagem_webp(dir_pr / "thumbnails" / "cipo.webp", 300, 200, (99, 88, 77))

    # Croqui Base
    croqui_base = croqui_pb2.Croqui(id="cipo", uid="uid_cipo", nome="Cipó")
    croqui_base.arquivos_externos.add(caminho="imagens/mapa_inalterado.webp", checksum_sha256="sha_m1_igual")
    croqui_base.arquivos_externos.add(caminho="imagens/mapa_cortado.webp", checksum_sha256="sha_m2_antigo")
    croqui_base.arquivos_externos.add(caminho="imagens/capa_setor.webp", checksum_sha256="sha_capa_antiga")
    croqui_base.arquivos_externos.add(caminho="imagens/foto_removida.webp", checksum_sha256="sha_foto_rem")

    pico_b = croqui_base.picos.add(nome="Serra")
    setor_b = pico_b.setores_ou_grupos.add().setor.conteudo
    setor_b.uid = "uid_s1"
    setor_b.nome = "Setor 1"
    setor_b.caminho_imagem_capa = "imagens/capa_setor.webp"
    setor_b.descricao = "Veja ![Foto](imagens/foto_removida.webp)"

    mapa1_b = setor_b.mapas.add(
        caminho_imagem_mapa="imagens/mapa_inalterado.webp",
        largura_mapa=1000,
        altura_mapa=800,
    )
    p_movido_b = mapa1_b.pontos_de_interesse.add(uid="p_movido", rotulo="1")
    p_movido_b.circulo.x = 100
    p_movido_b.circulo.y = 200
    p_movido_b.circulo.raio = 12

    p_removido_b = mapa1_b.pontos_de_interesse.add(uid="p_rem", rotulo="2")
    p_removido_b.quadrado.x = 300
    p_removido_b.quadrado.y = 400
    p_removido_b.quadrado.lado = 20

    p_linha_b = mapa1_b.pontos_de_interesse.add(uid="p_linha", rotulo="L1")
    p_linha_b.linha.espessura = 3
    p_linha_b.linha.compilado.caminho_svg = "M 10 10 L 50 50"

    mapa2_b = setor_b.mapas.add(
        caminho_imagem_mapa="imagens/mapa_cortado.webp",
        largura_mapa=1000,
        altura_mapa=800,
    )
    p_pol_b = mapa2_b.pontos_de_interesse.add(uid="p_pol", rotulo="P")
    p_pol_b.poligono.coordenadas.extend([10, 20, 30, 40, 50, 60])

    _salvar_croqui_compilado(dir_base, croqui_base)

    # Croqui PR
    croqui_pr = croqui_pb2.Croqui(id="cipo", uid="uid_cipo", nome="Cipó")
    croqui_pr.arquivos_externos.add(caminho="imagens/mapa_inalterado.webp", checksum_sha256="sha_m1_igual")
    croqui_pr.arquivos_externos.add(caminho="imagens/mapa_cortado.webp", checksum_sha256="sha_m2_novo")
    croqui_pr.arquivos_externos.add(caminho="imagens/capa_setor.webp", checksum_sha256="sha_capa_nova")
    croqui_pr.arquivos_externos.add(caminho="imagens/foto_md_nova.webp", checksum_sha256="sha_foto_nova")

    pico_p = croqui_pr.picos.add(nome="Serra")
    setor_p = pico_p.setores_ou_grupos.add().setor.conteudo
    setor_p.uid = "uid_s1"
    setor_p.nome = "Setor 1"
    setor_p.caminho_imagem_capa = "imagens/capa_setor.webp"
    setor_p.descricao = "Veja ![Foto Nova](imagens/foto_md_nova.webp)"

    mapa1_p = setor_p.mapas.add(
        caminho_imagem_mapa="imagens/mapa_inalterado.webp",
        largura_mapa=1000,
        altura_mapa=800,
    )
    p_movido_p = mapa1_p.pontos_de_interesse.add(uid="p_movido", rotulo="1")
    p_movido_p.circulo.x = 150
    p_movido_p.circulo.y = 260
    p_movido_p.circulo.raio = 12

    p_adicionado_p = mapa1_p.pontos_de_interesse.add(uid="p_add", rotulo="3")
    p_adicionado_p.retangulo.x = 500
    p_adicionado_p.retangulo.y = 600
    p_adicionado_p.retangulo.comprimento = 40
    p_adicionado_p.retangulo.largura = 30

    p_linha_p = mapa1_p.pontos_de_interesse.add(uid="p_linha", rotulo="L1")
    p_linha_p.linha.espessura = 3
    p_linha_p.linha.compilado.caminho_svg = "M 10 10 L 80 90"

    mapa2_p = setor_p.mapas.add(
        caminho_imagem_mapa="imagens/mapa_cortado.webp",
        largura_mapa=900,
        altura_mapa=700,
    )
    p_pol_p = mapa2_p.pontos_de_interesse.add(uid="p_pol", rotulo="P")
    p_pol_p.poligono.coordenadas.extend([10, 20, 30, 40, 50, 60])

    _salvar_croqui_compilado(dir_pr, croqui_pr)

    resumo = calcular_diff_pull_request(dir_base=dir_base, dir_pr=dir_pr)
    diff_croqui = resumo.croquis[0]

    mapas_por_caminho = {m.caminho_imagem: m for m in diff_croqui.mapas}
    m1 = mapas_por_caminho["imagens/mapa_inalterado.webp"]
    assert m1.imagem_alterada is False
    assert m1.status == "modificado"
    pontos_m1 = {p.uid: p for p in m1.pontos}
    assert pontos_m1["p_movido"].status == "modificado"
    assert pontos_m1["p_movido"].ponto_antes is not None
    assert pontos_m1["p_movido"].ponto_depois is not None
    assert (pontos_m1["p_movido"].ponto_antes.x, pontos_m1["p_movido"].ponto_antes.y) == (100, 200)
    assert (pontos_m1["p_movido"].ponto_depois.x, pontos_m1["p_movido"].ponto_depois.y) == (150, 260)
    assert pontos_m1["p_rem"].status == "removido"
    assert pontos_m1["p_add"].status == "adicionado"
    assert pontos_m1["p_linha"].status == "modificado"

    m2 = mapas_por_caminho["imagens/mapa_cortado.webp"]
    assert m2.imagem_alterada is True
    assert m2.largura_antes == 1000
    assert m2.largura_depois == 900
    assert m2.caminho_imagem_base_relativo == "_base/cipo/imagens/mapa_cortado.webp"

    # Verifica cópia seletiva para _base/
    assert (dir_pr / "_base" / "cipo" / "imagens" / "mapa_cortado.webp").is_file()
    assert (dir_pr / "_base" / "cipo" / "imagens" / "capa_setor.webp").is_file()
    assert (dir_pr / "_base" / "cipo" / "imagens" / "foto_removida.webp").is_file()
    assert (dir_pr / "_base" / "cipo" / "thumbnails" / "cipo.webp").is_file()
    assert not (dir_pr / "_base" / "cipo" / "imagens" / "mapa_inalterado.webp").exists()
