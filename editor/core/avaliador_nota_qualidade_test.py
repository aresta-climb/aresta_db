# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from editor.core.avaliador_nota_qualidade import (
    avaliar_nota_qualidade_croqui,
)
from editor.models.croqui_model import CroquiModel


def _criar_croqui_etapa1_completa_setor_unico() -> croqui_pb2.Croqui:
    """Cria um croqui Protobuf que cumpre todas as 8 tarefas da Etapa 1 com setor único."""
    croqui = croqui_pb2.Croqui(
        id="br_mg_teste_qualidade",
        uid="uid_croqui_0001",
        nome="Serra da Qualidade",
        descricao="Croqui completo de teste para validação da nota de qualidade.",
        caminho_thumbnail="imagens/thumbnail.webp",
    )
    pico = croqui.picos.add(
        nome="Pico Principal",
        descricao="Acesso pela rodovia MG-010, estacionamento ao lado da portaria.",
        url_google_maps="https://maps.google.com/?q=-19.5,-43.5",
    )
    pico.localizacao.latitude = -195000000
    pico.localizacao.longitude = -435000000
    pico.malha_estrada.conteudo.latitude_referencia_e7 = -195000000
    pico.malha_estrada.conteudo.longitude_referencia_e7 = -435000000
    pico.malha_estrada.conteudo.versao = 2
    no_malha = pico.malha_estrada.conteudo.nos.add()
    no_malha.no_osm_id = 1001
    no_malha.latitude_e7 = -195000000
    no_malha.longitude_e7 = -435000000
    no_malha.distancia_metros = 0
    no_malha.duracao_minutos = 0

    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.uid = "uid_setor_00001"
    setor.nome = "Setor Principal"

    mapa = setor.mapas.add(
        caminho_imagem_mapa="imagens/mapa_setor.webp",
        largura_mapa=1000,
        altura_mapa=800,
    )
    ponto = mapa.pontos_de_interesse.add(uid="uid_ponto_00001", rotulo="1")
    ponto.circulo.x = 100
    ponto.circulo.y = 200
    ponto.circulo.raio = 20

    esc = setor.escaladas.add(uid="uid_esc_0000001")
    esc.via_esportiva.nome = "Via Clássica"
    esc.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP

    ref = mapa.referencias.add(alvo_uid="uid_esc_0000001")
    ref.pontos_uids.append("uid_ponto_00001")

    return croqui


def test_croqui_vazio_retorna_nota_zero_e_nao_pronto_para_publicar() -> None:
    """Dado um croqui recém-criado sem dados, quando avaliado, então nota_qualidade é 0 e não está pronto."""
    croqui = croqui_pb2.Croqui()

    resultado = avaliar_nota_qualidade_croqui(croqui)

    assert resultado.nota_qualidade == 0
    assert resultado.nota_maxima == 8770
    assert resultado.pronto_para_publicar is False
    assert resultado.publicado is False
    assert len(resultado.etapas) == 3
    assert resultado.etapas[0].numero_etapa == 1
    assert resultado.etapas[0].pontos_obtidos == 0
    assert resultado.etapas[0].pontos_maximos == 8000
    assert resultado.etapas[0].concluida is False
    assert resultado.etapas[0].tarefas[0].ganho_potencial == 1000
    ids_etapa1 = [t.id_tarefa for t in resultado.etapas[0].tarefas]
    assert "etapa1_malha_estrada_picos" in ids_etapa1


def test_calculo_aditivo_entre_as_tres_etapas_por_ordens_de_grandeza() -> None:
    """
    Dado um croqui que cumpre 6 tarefas de 1000 pts na Etapa 1,
    3 tarefas de 100 pts na Etapa 2 e 4 tarefas de 10 pts na Etapa 3,
    quando avaliado, então a nota_qualidade total deve ser exatamente 6340.
    """
    croqui = _criar_croqui_etapa1_completa_setor_unico()
    # Deixa 2 tarefas da Etapa 1 pendentes (remove url_google_maps e coordenadas do pico -> invalida localizacao e malha_estrada -> 6 de 8 completas = 6000)
    croqui.picos[0].ClearField("localizacao")
    croqui.picos[0].url_google_maps = ""

    # Etapa 2: cumpre exatamente 3 tarefas de 100 pts (300 pts):
    # 1) coordenadas_setores, 2) destaques_setores, 3) fotos_capa_setores
    setor = croqui.picos[0].setores_ou_grupos[0].setor.conteudo
    setor.localizacao_estacionamento.latitude = -195000000
    setor.localizacao_estacionamento.longitude = -435000000
    setor.localizacao_escalada.latitude = -195001000
    setor.localizacao_escalada.longitude = -435001000
    setor.caminho_imagem_capa = "imagens/capa_setor.webp"
    setor.escaladas[0].via_esportiva.destaque = True

    # Etapa 3: cumpre exatamente 4 tarefas de 10 pts (40 pts):
    # 1) creditos, 2) conquistadores_datas, 3) tipo_parede_exposicao, 4) revisao_final
    croqui.creditos.append("Autor Teste")
    croqui.revisado_manualmente = True
    croqui.revisado_bounding_circle = True
    setor.escaladas[0].via_esportiva.conquistadores.append("Conquistador A")
    setor.escaladas[0].via_esportiva.tipo_parede = croqui_pb2.TipoParede.VERTICAL

    resultado = avaliar_nota_qualidade_croqui(croqui)

    assert resultado.etapas[0].pontos_obtidos == 6000
    assert resultado.etapas[1].pontos_obtidos == 300
    assert resultado.etapas[2].pontos_obtidos == 40
    assert resultado.nota_qualidade == 6340
    assert resultado.pronto_para_publicar is False


def test_pontuacao_parcial_proporcional_com_meta_de_90_porcento() -> None:
    """
    Dado um croqui com 20 escaladas onde 9 (45%) possuem grau de dificuldade,
    quando avaliado na tarefa de grau (meta 90%, peso 1000),
    então concede 500 pontos parciais; e ao atingir 19/20 (95%), concede 1000 pontos e conclui.
    """
    croqui = _criar_croqui_etapa1_completa_setor_unico()
    setor = croqui.picos[0].setores_ou_grupos[0].setor.conteudo
    setor.ClearField("escaladas")

    for i in range(20):
        esc = setor.escaladas.add(uid=f"uid_esc_{i:07d}")
        esc.via_esportiva.nome = f"Via {i + 1}"
        if i < 9:
            esc.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_5

    resultado_parcial = avaliar_nota_qualidade_croqui(croqui)
    tarefas_e1 = {t.id_tarefa: t for t in resultado_parcial.etapas[0].tarefas}
    tarefa_grau = tarefas_e1["etapa1_grau_dificuldade"]

    assert tarefa_grau.pontos_obtidos == 500
    assert tarefa_grau.pontos_maximos == 1000
    assert tarefa_grau.ganho_potencial == 500
    assert tarefa_grau.concluida is False
    assert tarefa_grau.progresso_atual == 9
    assert tarefa_grau.progresso_total == 20
    assert len(tarefa_grau.acoes) > 0

    # Agora preenche até 19 de 20 (95% >= 90%)
    for i in range(9, 19):
        setor.escaladas[i].via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6

    resultado_completo = avaliar_nota_qualidade_croqui(croqui)
    tarefa_grau_completa = {t.id_tarefa: t for t in resultado_completo.etapas[0].tarefas}[
        "etapa1_grau_dificuldade"
    ]

    assert tarefa_grau_completa.pontos_obtidos == 1000
    assert tarefa_grau_completa.ganho_potencial == 0
    assert tarefa_grau_completa.concluida is True


def test_aplicabilidade_automatica_mapa_geral_setor_unico_e_multiplos_setores() -> None:
    """
    Dado um croqui com apenas 1 setor e sem Mapa Geral,
    então a tarefa de Mapa Geral concede 1000 pontos automaticamente.
    Quando um 2º setor é adicionado sem Mapa Geral, a tarefa passa a exigir o Mapa Geral (0 pontos).
    """
    croqui = _criar_croqui_etapa1_completa_setor_unico()
    resultado_1_setor = avaliar_nota_qualidade_croqui(croqui)
    tarefas_1 = {t.id_tarefa: t for t in resultado_1_setor.etapas[0].tarefas}

    assert tarefas_1["etapa1_mapa_geral"].pontos_obtidos == 1000
    assert tarefas_1["etapa1_mapa_geral"].concluida is True
    assert resultado_1_setor.pronto_para_publicar is True

    # Adiciona 2º setor sem Mapa Geral no pico
    sg2 = croqui.picos[0].setores_ou_grupos.add()
    sg2.setor.conteudo.uid = "uid_setor_00002"
    sg2.setor.conteudo.nome = "Setor Secundário"

    resultado_2_setores = avaliar_nota_qualidade_croqui(croqui)
    tarefas_2 = {t.id_tarefa: t for t in resultado_2_setores.etapas[0].tarefas}
    assert tarefas_2["etapa1_mapa_geral"].pontos_obtidos == 0
    assert tarefas_2["etapa1_mapa_geral"].concluida is False

    # Referencia ambos os setores no Mapa Geral do pico
    mg = croqui.picos[0].mapas_gerais.conteudo.mapas.add(
        caminho_imagem_mapa="imagens/mapa_geral.webp",
        largura_mapa=1200,
        altura_mapa=900,
    )
    p1 = mg.pontos_de_interesse.add(uid="p_mg_1")
    p1.circulo.x, p1.circulo.y, p1.circulo.raio = 100, 100, 30
    p2 = mg.pontos_de_interesse.add(uid="p_mg_2")
    p2.circulo.x, p2.circulo.y, p2.circulo.raio = 300, 300, 30

    r1 = mg.referencias.add(alvo_uid="uid_setor_00001")
    r1.pontos_uids.append("p_mg_1")
    r2 = mg.referencias.add(alvo_uid="uid_setor_00002")
    r2.pontos_uids.append("p_mg_2")

    resultado_mg_ok = avaliar_nota_qualidade_croqui(croqui)
    tarefas_mg_ok = {t.id_tarefa: t for t in resultado_mg_ok.etapas[0].tarefas}
    assert tarefas_mg_ok["etapa1_mapa_geral"].pontos_obtidos == 1000
    assert tarefas_mg_ok["etapa1_mapa_geral"].concluida is True


def test_aplicabilidade_automatica_boulder_dispensa_extensao_protecoes_e_aceita_grau_projeto() -> (
    None
):
    """
    Dado um croqui exclusivo de Boulders classificados como PROJETO,
    quando avaliado, então GrauBoulder.PROJETO conta como grau válido na Etapa 1
    e a tarefa de extensão/proteções de vias na Etapa 2 concede 100 pontos automaticamente.
    """
    croqui = _criar_croqui_etapa1_completa_setor_unico()
    setor = croqui.picos[0].setores_ou_grupos[0].setor.conteudo
    setor.ClearField("escaladas")

    esc_boulder = setor.escaladas.add(uid="uid_esc_0000001")
    esc_boulder.boulder.nome = "Bloco do Projeto"
    esc_boulder.boulder.dificuldade = croqui_pb2.GrauBoulder.PROJETO

    resultado = avaliar_nota_qualidade_croqui(CroquiModel(croqui))

    tarefas_e1 = {t.id_tarefa: t for t in resultado.etapas[0].tarefas}
    assert tarefas_e1["etapa1_grau_dificuldade"].pontos_obtidos == 1000
    assert tarefas_e1["etapa1_grau_dificuldade"].concluida is True

    tarefas_e2 = {t.id_tarefa: t for t in resultado.etapas[1].tarefas}
    assert tarefas_e2["etapa2_extensao_protecoes_vias"].pontos_obtidos == 100
    assert tarefas_e2["etapa2_extensao_protecoes_vias"].concluida is True


def test_avaliacao_completa_todas_etapas_e_suporte_a_dicionario_e_disco(tmp_path: Path) -> None:
    """
    Dado um croqui que cumpre todos os critérios das Etapas 1, 2 e 3 (tanto via Protobuf
    quanto via dicionário YAML + arquivos .md no disco), então atinge a nota máxima 7770.
    """
    croqui = _criar_croqui_etapa1_completa_setor_unico()
    croqui.publicar_croqui = True
    croqui.revisado_manualmente = True
    croqui.revisado_bounding_circle = True
    croqui.status_desenho_extraivel = croqui_pb2.Croqui.StatusDesenhoExtraivel.DESENHO_EXTRAIDO
    croqui.creditos.append("Equipe Aresta")

    pico = croqui.picos[0]
    pico.nome_associacao = "Associação Mineira de Escalada"
    pico.url_filiacao_associacao = "https://associacao.org.br"
    pico.chave_pix_manutencao = "manutencao@associacao.org.br"

    setor = pico.setores_ou_grupos[0].setor.conteudo
    setor.caminho_imagem_capa = "imagens/capa.webp"
    setor.localizacao_estacionamento.latitude = -195000000
    setor.localizacao_estacionamento.longitude = -435000000
    setor.localizacao_escalada.latitude = -195001000
    setor.localizacao_escalada.longitude = -435001000
    setor.sinal_de_celular = True
    setor.amigavel_a_criancas = True
    setor.amigavel_a_bebes = False
    trilha = setor.trilhas.add(
        nome="Trilha Principal",
        descricao="Caminhada leve por 5 minutos.",
        tempo_aproximacao="5 min",
    )
    pt_trilha = trilha.pontos.add(nome="Início")
    pt_trilha.localizacao.latitude = -195000000
    pt_trilha.localizacao.longitude = -435000000

    # Ponto com LinhaTrajeto no mapa do setor
    ponto_mapa = setor.mapas[0].pontos_de_interesse[0]
    ponto_mapa.ClearField("circulo")
    no1 = ponto_mapa.linha.conteudo.nos.add(
        x=100, y=500, tipo=croqui_pb2.NoTrajeto.CIRCULO_IDENTIFICADOR
    )
    no1.rotulo = "1"
    ponto_mapa.linha.conteudo.nos.add(x=100, y=100, tipo=croqui_pb2.NoTrajeto.TOP_PARADA)

    via = setor.escaladas[0].via_esportiva
    via.destaque = True
    via.extensao = 22
    via.quantidade_protecoes_intermediarias = 9
    via.quantidade_protecoes_parada = 2
    via.conquistadores.append("Conquistador Histórico")
    via.data_abertura = "2010-05"
    via.tipo_parede = croqui_pb2.TipoParede.NEGATIVO
    via.descricao = "Saída atlética em agarras boas seguida de crux técnico."
    beta = setor.escaladas[0].betas.add()
    beta.fonte = beta_pb2.FonteMidia.YOUTUBE
    beta.url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    resultado_proto = avaliar_nota_qualidade_croqui(croqui)
    assert resultado_proto.nota_qualidade == 8770
    assert resultado_proto.nota_maxima == 8770
    assert resultado_proto.pronto_para_publicar is True
    assert resultado_proto.publicado is True
    assert all(etapa.concluida for etapa in resultado_proto.etapas)

    # Também valida leitura descompilada via dicionário + arquivo malha_estrada.yaml no disco + cache_md
    (tmp_path / "malha_estrada.yaml").write_text(
        """latitude_referencia_e7: -195000000
longitude_referencia_e7: -435000000
versao: 2
nos:
  - no_osm_id: 1001
    latitude_e7: -195000000
    longitude_e7: -435000000
    distancia_metros: 0
    duracao_minutos: 0
""",
        encoding="utf-8",
    )
    dados_yaml = {
        "id": "br_mg_teste_disco",
        "nome": "Serra da Qualidade",
        "descricao": "Descrição curta.",
        "caminho_thumbnail": "imagens/thumbnail.webp",
        "publicar_croqui": True,
        "revisado_manualmente": True,
        "revisado_bounding_circle": True,
        "status_desenho_extraivel": "DESENHO_EXTRAIDO",
        "creditos": ["Equipe Aresta"],
        "picos": [
            {
                "nome": "Pico Principal",
                "descricao": "Acesso fácil.",
                "url_google_maps": "https://maps.google.com/?q=-19.5,-43.5",
                "localizacao": {"latitude": -195000000, "longitude": -435000000},
                "malha_estrada": {"caminho": "malha_estrada.yaml"},
                "chave_pix_manutencao": "pix@aresta.org",
                "setores_ou_grupos": [
                    {
                        "grupo": {
                            "caminho": "grupo_vale.md",
                        }
                    }
                ],
            }
        ],
    }
    cache_md = {
        "grupo_vale.md": (
            {
                "uid": "uid_grupo_01",
                "nome": "Vale Principal",
                "caminho_imagem_capa": "imagens/grupo.webp",
                "localizacao_estacionamento": {"latitude": -195000000, "longitude": -435000000},
                "localizacao_escalada": {"latitude": -195001000, "longitude": -435001000},
                "setores": ["setor_unico.md"],
            },
            "Descrição do grupo.",
        ),
        "setor_unico.md": (
            {
                "uid": "uid_setor_01",
                "nome": "Setor Único",
                "caminho_imagem_capa": "imagens/setor.webp",
                "sinal_de_celular": True,
                "trilhas": [{"nome": "Trilha", "tempo_aproximacao": "10 min"}],
                "mapas": [
                    {
                        "caminho_imagem_mapa": "imagens/mapa.webp",
                        "pontos_de_interesse": [
                            {
                                "uid": "pt1",
                                "linha": {
                                    "conteudo": {
                                        "nos": [{"x": 10, "y": 20}, {"x": 10, "y": 50}],
                                    }
                                },
                            }
                        ],
                        "referencias": [
                            {
                                "alvo_uid": "esc1",
                                "setor": "Setor Único",
                                "grupo": "Vale Principal",
                                "escalada": "Fenda Clássica",
                                "pontos_uids": ["pt1"],
                            }
                        ],
                    }
                ],
                "escaladas": [
                    {
                        "uid": "esc1",
                        "betas": [{"url": "https://youtube.com/watch?v=1"}],
                        "via_movel": {
                            "nome": "Fenda Clássica",
                            "destaque": True,
                            "dificuldade": "PROJETO",
                            "extensao": 30,
                            "protecoes_moveis": "Jogo de Camalots #0.5 a #3",
                            "conquistadores": ["Fulano"],
                            "exposicao": "E2",
                            "descricao": "Fenda perfeita.",
                        },
                    }
                ],
            },
            "Descrição do setor.",
        ),
    }

    resultado_dict = avaliar_nota_qualidade_croqui(
        dados_yaml, croqui_path=tmp_path, cache_md=cache_md
    )
    assert resultado_dict.nota_qualidade == 8770
    assert resultado_dict.pronto_para_publicar is True

    # Se malha_estrada.yaml tiver nó com distancia_metros > 0 sem duracao_minutos > 0, considera desatualizada
    (tmp_path / "malha_estrada.yaml").write_text(
        """latitude_referencia_e7: -195000000
longitude_referencia_e7: -435000000
nos:
  - no_osm_id: 1001
    latitude_e7: -195000000
    longitude_e7: -435000000
    distancia_metros: 0
    duracao_minutos: 0
  - no_osm_id: 1002
    latitude_e7: -195300000
    longitude_e7: -435000000
    distancia_metros: 3500
    duracao_minutos: 0
""",
        encoding="utf-8",
    )
    resultado_sem_minutos = avaliar_nota_qualidade_croqui(
        dados_yaml, croqui_path=tmp_path, cache_md=cache_md
    )
    tarefas_sem_min = {t.id_tarefa: t for t in resultado_sem_minutos.etapas[0].tarefas}
    assert tarefas_sem_min["etapa1_malha_estrada_picos"].concluida is False
    assert resultado_sem_minutos.pronto_para_publicar is False


def test_modalidades_multiplas_enfiadas_highline_e_leitura_direta_do_disco(
    tmp_path: Path,
) -> None:
    """
    Dado um croqui em disco (croqui.yaml e .md sem cache_md prévio) contendo
    ViaMultiplasEnfiadas e Highline e pendências em setores/escaladas,
    quando avaliado passando apenas croqui_path, então lê do disco e diagnostica as ações.
    """
    (tmp_path / "croqui.yaml").write_text(
        """
id: br_rj_teste
nome: Pão de Açúcar
picos:
  - nome: Morro da Urca
    localizacao:
      latitude: -229500000
      longitude: -431600000
    setores_ou_grupos:
      - setor:
          caminho: setor_urca.md
      - setor:
          caminho: setor_inexistente.md
      - setor: {}
      - null
""",
        encoding="utf-8",
    )
    (tmp_path / "setor_urca.md").write_text(
        """---
uid: s_urca
nome: Face Leste
escaladas:
  - uid: e_multi
    mapas:
      - caminho_imagem_mapa: imagens/m.webp
        pontos_de_interesse:
          - uid: p1
            circulo: {x: 1, y: 2, raio: 3}
        referencias:
          - alvo_uid: e_multi
    via_multiplas_enfiadas:
      nome: Italianos
      dificuldade_media: BR_5SUP
      comprimento_total: 260
      equipamento_recomendado: Costuras e Camalots
  - uid: e_multi_incompleta
    via_multiplas_enfiadas:
      nome: Via Sem Dados
  - uid: e_high
    highline:
      nome: Linha das Nuvens
      distancia: 80
  - uid: e_sem_mod
---
Corpo do setor na Urca.
""",
        encoding="utf-8",
    )

    resultado = avaliar_nota_qualidade_croqui(None, croqui_path=tmp_path)

    tarefas_e1 = {t.id_tarefa: t for t in resultado.etapas[0].tarefas}
    # 2 de 4 escaladas possuem grau (Italianos e Linha das Nuvens)
    assert tarefas_e1["etapa1_grau_dificuldade"].progresso_atual == 2
    assert tarefas_e1["etapa1_grau_dificuldade"].progresso_total == 4
    assert tarefas_e1["etapa1_malha_estrada_picos"].pontos_obtidos == 0
    assert tarefas_e1["etapa1_malha_estrada_picos"].acoes[0].rotulo == "Gerar mapa de pontos"
    assert (
        tarefas_e1["etapa1_malha_estrada_picos"].acoes[0].uri_contexto
        == "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:localizacao"
    )

    tarefas_e2 = {t.id_tarefa: t for t in resultado.etapas[1].tarefas}
    # 1 de 2 vias encordadas completa (Italianos completa, Via Sem Dados incompleta)
    assert tarefas_e2["etapa2_extensao_protecoes_vias"].progresso_atual == 1
    assert tarefas_e2["etapa2_extensao_protecoes_vias"].progresso_total == 2
    assert [
        (a.rotulo, a.uri_contexto) for a in tarefas_e2["etapa2_extensao_protecoes_vias"].acoes
    ] == [
        (
            "Adicionar extensão (Via Sem Dados)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:1/campo:comprimento_total",
        ),
        (
            "Adicionar proteções (Via Sem Dados)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:1/campo:tipo_via_multiplas_enfiadas",
        ),
    ]


def test_acoes_diretas_desmembradas_por_campo_e_omissao_nome_pico_unico(
    tmp_path: Path,
) -> None:
    """
    Valida que as 22 tarefas geram rótulos imperativos diretos e URIs com /campo:<nome_campo>,
    omitindo o nome do pico quando há apenas 1 pico e incluindo-o quando há 2 ou mais picos.
    """
    croqui = croqui_pb2.Croqui(id="teste_acoes_diretas")
    pico = croqui.picos.add(nome="Gruta da Lapinha")
    setor = pico.setores_ou_grupos.add().setor.conteudo
    setor.uid = "uid_setor_1"
    setor.nome = "Setor Museu"
    esc = setor.escaladas.add(uid="uid_esc_1")
    esc.via_esportiva.nome = "Via 1"

    setor2 = pico.setores_ou_grupos.add().setor.conteudo
    setor2.uid = "uid_setor_2"
    setor2.nome = "Setor Lagoa"

    (tmp_path / "betas_pendentes.binarypb").write_bytes(b"pendente")

    res = avaliar_nota_qualidade_croqui(croqui, croqui_path=tmp_path)
    t_e1 = {t.id_tarefa: t for t in res.etapas[0].tarefas}
    t_e2 = {t.id_tarefa: t for t in res.etapas[1].tarefas}
    t_e3 = {t.id_tarefa: t for t in res.etapas[2].tarefas}

    # 1.1 Identidade: 3 ações desmembradas
    assert [(a.rotulo, a.uri_contexto) for a in t_e1["etapa1_identidade_capa"].acoes] == [
        ("Definir nome do croqui", "page:dados/node:root/node:Croqui/campo:nome"),
        ("Adicionar descrição do croqui", "page:dados/node:root/node:Croqui/campo:descricao"),
        ("Adicionar imagem de capa", "page:dados/node:root/node:Croqui/campo:caminho_thumbnail"),
    ]

    # 1.2 Localização e Google Maps (1 pico -> omite nome do pico)
    assert [(a.rotulo, a.uri_contexto) for a in t_e1["etapa1_localizacao_picos"].acoes] == [
        (
            "Adicionar localização",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:localizacao",
        ),
        (
            "Adicionar link Google Maps",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:url_google_maps",
        ),
    ]

    # 1.3 Acesso (1 pico -> omite nome do pico)
    assert [(a.rotulo, a.uri_contexto) for a in t_e1["etapa1_instrucoes_acesso"].acoes] == [
        (
            "Adicionar instruções de acesso",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:descricao",
        ),
    ]

    # 1.4 Mapa Geral (sem mapa geral -> Adicionar Mapa Geral no campo:mapas_gerais)
    assert [(a.rotulo, a.uri_contexto) for a in t_e1["etapa1_mapa_geral"].acoes] == [
        (
            "Adicionar Mapa Geral",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:mapas_gerais",
        ),
    ]

    # 1.5 Mapas nos setores -> campo:mapas
    assert t_e1["etapa1_setores_com_mapa"].acoes[0] == (
        t_e1["etapa1_setores_com_mapa"]
        .acoes[0]
        .__class__(
            "Adicionar mapa em Setor Museu",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/campo:mapas",
        )
    )

    # 1.6 Escaladas no mapa (quando o setor ainda não tem mapa -> Adicionar mapa em ...)
    assert t_e1["etapa1_escaladas_no_mapa"].acoes[0].rotulo == "Adicionar mapa em Setor Museu"
    assert t_e1["etapa1_escaladas_no_mapa"].acoes[0].uri_contexto.endswith("/campo:mapas")

    # 1.7 Grau de dificuldade -> Definir grau de Via 1 (/campo:dificuldade)
    assert [(a.rotulo, a.uri_contexto) for a in t_e1["etapa1_grau_dificuldade"].acoes] == [
        (
            "Definir grau de Via 1",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:dificuldade",
        ),
    ]

    # 1.8 Malha de estrada quando não há localização -> Adicionar localização (/campo:localizacao)
    assert [(a.rotulo, a.uri_contexto) for a in t_e1["etapa1_malha_estrada_picos"].acoes] == [
        (
            "Adicionar localização",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:localizacao",
        ),
    ]

    # 2.1 Coordenadas dos setores desmembradas
    assert [(a.rotulo, a.uri_contexto) for a in t_e2["etapa2_coordenadas_setores"].acoes[:2]] == [
        (
            "Adicionar estacionamento (Setor Museu)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/campo:localizacao_estacionamento",
        ),
        (
            "Adicionar localização da parede (Setor Museu)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/campo:localizacao_escalada",
        ),
    ]

    # 2.2 Trilhas -> Adicionar trilha em Setor Museu (/campo:trilhas)
    assert t_e2["etapa2_trilhas_aproximacao"].acoes[0].rotulo == "Adicionar trilha em Setor Museu"
    assert t_e2["etapa2_trilhas_aproximacao"].acoes[0].uri_contexto.endswith("/campo:trilhas")

    # 2.3 Extensão e proteções (via esportiva)
    assert [(a.rotulo, a.uri_contexto) for a in t_e2["etapa2_extensao_protecoes_vias"].acoes] == [
        (
            "Adicionar extensão (Via 1)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:extensao",
        ),
        (
            "Adicionar proteções (Via 1)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:quantidade_protecoes_intermediarias",
        ),
    ]

    # 2.4 Traçados vetoriais -> Desenhar linhas em Setor Museu
    assert t_e2["etapa2_tracados_vetoriais"].acoes[0].rotulo == "Desenhar linhas em Setor Museu"

    # 2.5 Destaques nos setores -> Escolher destaque em Setor Museu (1ª escalada /campo:destaque)
    assert [(a.rotulo, a.uri_contexto) for a in t_e2["etapa2_destaques_setores"].acoes] == [
        (
            "Escolher destaque em Setor Museu",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:destaque",
        ),
    ]

    # 2.6 Descrições nas escaladas -> Adicionar descrição (Via 1) (/campo:descricao)
    assert [(a.rotulo, a.uri_contexto) for a in t_e2["etapa2_descricoes_escaladas"].acoes] == [
        (
            "Adicionar descrição (Via 1)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:descricao",
        ),
    ]

    # 2.7 Fotos de capa -> Adicionar foto de capa (Setor Museu) (/campo:caminho_imagem_capa)
    assert (
        t_e2["etapa2_fotos_capa_setores"].acoes[0].rotulo == "Adicionar foto de capa (Setor Museu)"
    )
    assert (
        t_e2["etapa2_fotos_capa_setores"]
        .acoes[0]
        .uri_contexto.endswith("/campo:caminho_imagem_capa")
    )

    # 3.1 Créditos -> Adicionar créditos (/campo:creditos)
    assert [(a.rotulo, a.uri_contexto) for a in t_e3["etapa3_creditos"].acoes] == [
        ("Adicionar créditos", "page:dados/node:root/node:Croqui/campo:creditos"),
    ]

    # 3.2 Conquistadores -> Adicionar conquistadores (Via 1) (/campo:conquistadores)
    assert [(a.rotulo, a.uri_contexto) for a in t_e3["etapa3_conquistadores_datas"].acoes] == [
        (
            "Adicionar conquistadores (Via 1)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:conquistadores",
        ),
    ]

    # 3.3 Tipo de parede -> Definir tipo de parede (Via 1) (/campo:tipo_parede)
    assert [(a.rotulo, a.uri_contexto) for a in t_e3["etapa3_tipo_parede_exposicao"].acoes] == [
        (
            "Definir tipo de parede (Via 1)",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/expando:escaladas/item:0/campo:tipo_parede",
        ),
    ]

    # 3.4 Indicadores -> Preencher indicadores (Setor Museu) (/campo:sinal_de_celular)
    assert t_e3["etapa3_indicadores_familia_celular"].acoes[0].rotulo == (
        "Preencher indicadores (Setor Museu)"
    )
    assert (
        t_e3["etapa3_indicadores_familia_celular"]
        .acoes[0]
        .uri_contexto.endswith("/campo:sinal_de_celular")
    )

    # 3.5 Betas pendentes -> Revisar betas pendentes (page:betas)
    assert [(a.rotulo, a.uri_contexto) for a in t_e3["etapa3_videos_betas"].acoes] == [
        ("Revisar betas pendentes", "page:betas"),
    ]

    # 3.6 Associação/Pix (1 pico -> omite nome do pico)
    assert [(a.rotulo, a.uri_contexto) for a in t_e3["etapa3_associacao_pix"].acoes] == [
        (
            "Adicionar associação",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:nome_associacao",
        ),
        (
            "Adicionar chave Pix",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:chave_pix_manutencao",
        ),
    ]

    # 3.7 Revisão final desmembrada
    assert [(a.rotulo, a.uri_contexto) for a in t_e3["etapa3_revisao_final"].acoes] == [
        (
            "Marcar revisão manual",
            "page:dados/node:root/node:Croqui/campo:revisado_manualmente",
        ),
        (
            "Marcar revisão de bounding circle",
            "page:dados/node:root/node:Croqui/campo:revisado_bounding_circle",
        ),
    ]

    # Agora adiciona um 2º pico e mapa no 1º pico/setor para validar sufixo (<Nome do Pico>) e Mapear setores/escaladas
    croqui.picos.add(nome="Serra do Cipó")
    pico.mapas_gerais.conteudo.mapas.add(caminho_imagem_mapa="imagens/mg.webp")
    setor.mapas.add(caminho_imagem_mapa="imagens/ms.webp")

    res_multi = avaliar_nota_qualidade_croqui(croqui)
    t_e1_m = {t.id_tarefa: t for t in res_multi.etapas[0].tarefas}
    t_e3_m = {t.id_tarefa: t for t in res_multi.etapas[2].tarefas}

    assert t_e1_m["etapa1_localizacao_picos"].acoes[0].rotulo == (
        "Adicionar localização (Gruta da Lapinha)"
    )
    assert t_e1_m["etapa1_localizacao_picos"].acoes[1].rotulo == (
        "Adicionar link Google Maps (Gruta da Lapinha)"
    )
    assert t_e1_m["etapa1_instrucoes_acesso"].acoes[0].rotulo == (
        "Adicionar instruções de acesso (Gruta da Lapinha)"
    )
    assert t_e1_m["etapa1_mapa_geral"].acoes[0].rotulo == (
        "Mapear setores no Mapa Geral (Gruta da Lapinha)"
    )
    assert t_e1_m["etapa1_escaladas_no_mapa"].acoes[0].rotulo == ("Mapear escaladas em Setor Museu")
    assert t_e3_m["etapa3_videos_betas"].acoes[0].rotulo == "Adicionar vídeo de beta"
    assert t_e3_m["etapa3_associacao_pix"].acoes[0].rotulo == (
        "Adicionar associação (Gruta da Lapinha)"
    )


def test_malha_estrada_versao_antiga_concede_700_pontos_e_exibe_acao_atualizar() -> None:
    """
    Dado um croqui onde o pico possui malha_estrada sincronizada com duracao_minutos válida,
    porém com versao < 2 (ex: 0 ou 1), quando avaliado, então etapa1_malha_estrada_picos
    concede 700 de 1000 pontos, fica com concluida=False (bloqueando pronto_para_publicar)
    e emite a ação 'Atualizar mapa de pontos'.
    """
    croqui = _criar_croqui_etapa1_completa_setor_unico()
    croqui.picos[0].malha_estrada.conteudo.versao = 1

    resultado = avaliar_nota_qualidade_croqui(croqui)
    tarefas_e1 = {t.id_tarefa: t for t in resultado.etapas[0].tarefas}
    t_malha = tarefas_e1["etapa1_malha_estrada_picos"]

    assert t_malha.pontos_obtidos == 700
    assert t_malha.pontos_maximos == 1000
    assert t_malha.ganho_potencial == 300
    assert t_malha.concluida is False
    assert resultado.etapas[0].pontos_obtidos == 7700
    assert resultado.etapas[0].concluida is False
    assert resultado.pronto_para_publicar is False
    assert [(a.rotulo, a.uri_contexto) for a in t_malha.acoes] == [
        (
            "Atualizar mapa de pontos",
            "page:dados/node:root/node:Croqui/expando:picos/item:0/campo:localizacao",
        )
    ]

    # Quando atualizado para versao = 2, passa a conceder 1000 pontos e conclui a Etapa 1
    croqui.picos[0].malha_estrada.conteudo.versao = 2
    resultado_v2 = avaliar_nota_qualidade_croqui(croqui)
    t_malha_v2 = {t.id_tarefa: t for t in resultado_v2.etapas[0].tarefas}[
        "etapa1_malha_estrada_picos"
    ]
    assert t_malha_v2.pontos_obtidos == 1000
    assert t_malha_v2.concluida is True
    assert resultado_v2.pronto_para_publicar is True
