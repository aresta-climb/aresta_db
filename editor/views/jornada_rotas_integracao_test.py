# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes de Integração de Ponta a Ponta para a Jornada de Anotação de Rotas em Mapas.
Princípio V de AGENTS.md: Testes de Integração em Primeiro Lugar.

Cada teste documenta detalhadamente seu contrato e comportamento esperado antes
da implementação dos componentes subjacentes.
"""

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QUndoStack
from google.protobuf.json_format import MessageToDict

from aresta_api.proto.generated import croqui_pb2
from editor.models.croqui_model import CroquiModel
from editor.controllers.mapas_controller import MapasController
from editor.views.widget_editor_mapas import WidgetEditorMapas
from scripts.preparar_submissao_lib import validar_referencias_mapa


def _criar_ambiente_teste(tmp_path, num_mapas: int = 1):
    """
    Cria um ambiente de teste com CroquiModel, Setor, Mapas e WidgetEditorMapas.
    """
    app = QApplication.instance() or QApplication([])

    # Cria arquivo de imagem fake no tmp_path
    caminhos_img = []
    for i in range(num_mapas):
        nome_img = f"mapa_{i+1}.webp"
        p = tmp_path / nome_img
        p.write_bytes(b"\x00" * 100)
        caminhos_img.append(nome_img)

    croqui = croqui_pb2.Croqui()
    pico = croqui.picos.add(nome="Pico dos Testes")
    sg = pico.setores_ou_grupos.add()
    setor = sg.setor.conteudo
    setor.nome = "Setor Central"

    for i in range(num_mapas):
        m = setor.mapas.add(
            caminho_imagem_mapa=caminhos_img[i],
            largura_mapa=800
        )

    model = CroquiModel(croqui)
    model.definir_caminho_db(tmp_path)

    undo_stack = QUndoStack()
    mapas_ctrl = MapasController(model, undo_stack)
    mapas_ctrl.set_caminho_db(tmp_path)

    widget = WidgetEditorMapas(croqui_model=model, mapas_controller=mapas_ctrl)
    
    # Carrega o primeiro mapa como ativo
    proxy_mapa = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    widget.set_mapa_atual(proxy_mapa, pico_idx=0, grupo_idx=0, mapa_idx=0, tipo="setor")

    return {
        "app": app,
        "model": model,
        "undo_stack": undo_stack,
        "mapas_ctrl": mapas_ctrl,
        "widget": widget,
        "setor": setor,
        "tmp_path": tmp_path,
    }


def test_01_criacao_direta_nova_rota(qtbot, tmp_path):
    """
    Cenário 1: Criação direta de nova rota isolada com '+ Nova Rota'.
    Contrato:
    - O botão legado `btn_add_linha` ("Nova Linha / Escalada") NÃO deve existir no widget.
    - O botão `btn_nova_rota` deve existir com atalho 'R'.
    - Ao iniciar o desenho com nova rota ('Via Central', Boulder, V4) e adicionar nós,
      o nó de início recebe CIRCULO_IDENTIFICADOR com rótulo '1'.
      O nó final NÃO recebe círculo redundante de TOP (rota isolada limpa).
    - A entidade é criada em `setor.escaladas`.
    - O POI da linha é criado no mapa e linkado em `mapa.referencias`.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    qtbot.addWidget(widget)

    # Verifica ausência do botão legado e presença do novo botão
    assert not hasattr(widget, "btn_add_linha"), "O botão legado btn_add_linha deve ser removido"
    assert hasattr(widget, "btn_nova_rota"), "O widget deve conter o botão btn_nova_rota (+ Nova Rota)"
    assert widget.btn_nova_rota.shortcut().toString() == "R" or "R" in widget.btn_nova_rota.text()

    # Inicia modo de criação de rota
    dados_rota = {
        "nome": "Via Central",
        "tipo": "boulder",
        "grau": "V4",
        "nova": True
    }
    widget.iniciar_modo_nova_rota(dados_rota)
    assert widget.modo_nova_rota is True

    # Adiciona 4 pontos na cena
    pontos = [QPointF(100, 500), QPointF(120, 350), QPointF(130, 200), QPointF(140, 100)]
    for p in pontos:
        widget.adicionar_ponto_nova_rota(p)

    # Conclui traçado
    widget.finalizar_modo_nova_rota()
    assert widget.modo_nova_rota is False

    # Checagens no Model
    croqui_ro = env["model"].obter_croqui_readonly()
    setor_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo
    mapa_ro = setor_ro.mapas[0]

    # 1. Entidade criada no setor
    assert len(setor_ro.escaladas) == 1
    assert setor_ro.escaladas[0].boulder.nome == "Via Central"

    # 2. POI linha criado
    assert len(mapa_ro.pontos_de_interesse) == 1
    poi_linha = mapa_ro.pontos_de_interesse[0]
    assert poi_linha.HasField("linha")
    nos = poi_linha.linha.conteudo.nos
    assert len(nos) == 4

    # 3. Rótulo de início '1' e término sem círculo TOP
    assert nos[0].tipo == croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
    assert nos[0].rotulo == "1"
    assert nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
    assert nos[-1].rotulo == ""

    # 4. Referência linkada
    assert len(mapa_ro.referencias) == 1
    ref = mapa_ro.referencias[0]
    assert ref.escalada == "Via Central"
    assert list(ref.ids) == [poi_linha.id]


def test_02_variante_fatiamento_meio_curva_e_desambiguacao_top(qtbot, tmp_path):
    """
    Cenário 2: Variante com bifurcação e fatiamento automático no meio de curva existente.
    Contrato:
    - Desenha uma rota base 'Via Central'.
    - Desenha 'Variante Direita' começando com snap no nó 1, snap no nó 2 e clicando
      no meio da curva entre nó 2 e nó 3, bifurcando depois para a direita.
    - O nó de início compartilhado atualiza seu rótulo para '1, 2'.
    - A linha original é fatiada em `seg_comum` e `seg_via_central`.
    - A linha da variante `seg_variante` é criada.
    - Referências são atualizadas:
      - 'Via Central' -> [seg_comum, seg_via_central]
      - 'Variante Direita' -> [seg_comum, seg_variante]
    - Desambiguação de TOP sob demanda:
      - Como agora há duas saídas distintas, o topo da 'Via Central' ganha rótulo 'A'
      - O topo da 'Variante Direita' ganha rótulo 'B'.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    qtbot.addWidget(widget)

    # 1. Cria 'Via Central'
    widget.iniciar_modo_nova_rota({"nome": "Via Central", "tipo": "boulder", "grau": "V4", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 350), QPointF(130, 200), QPointF(140, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # 2. Cria 'Variante Direita' conectando e fatiando
    widget.iniciar_modo_nova_rota({"nome": "Variante Direita", "tipo": "boulder", "grau": "V6", "nova": True})
    # Snap no início (100, 500)
    widget.adicionar_ponto_nova_rota(QPointF(100, 500))
    # Snap no segundo nó (120, 350)
    widget.adicionar_ponto_nova_rota(QPointF(120, 350))
    # Clique no meio do segmento (125, 275) - corte na curva
    widget.adicionar_ponto_nova_rota(QPointF(125, 275))
    # Ponto exclusivo da variante
    widget.adicionar_ponto_nova_rota(QPointF(250, 150))
    widget.finalizar_modo_nova_rota()

    croqui_ro = env["model"].obter_croqui_readonly()
    setor_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo
    mapa_ro = setor_ro.mapas[0]

    # Ambas as escaladas cadastradas
    nomes_escaladas = [e.boulder.nome for e in setor_ro.escaladas]
    assert "Via Central" in nomes_escaladas
    assert "Variante Direita" in nomes_escaladas

    # Referências
    refs = {r.escalada: list(r.ids) for r in mapa_ro.referencias}
    assert "Via Central" in refs
    assert "Variante Direita" in refs

    ids_central = refs["Via Central"]
    ids_variante = refs["Variante Direita"]

    # Devem compartilhar o primeiro segmento (comum) e ter segmentos exclusivos distintos
    assert len(ids_central) == 2
    assert len(ids_variante) == 2
    assert ids_central[0] == ids_variante[0], "O segmento inicial deve ser compartilhado"
    assert ids_central[1] != ids_variante[1], "Os segmentos finais devem ser exclusivos"

    # Verificação de nós e rótulos
    pois_por_id = {p.id: p for p in mapa_ro.pontos_de_interesse}
    seg_comum = pois_por_id[ids_central[0]]
    nos_comuns = seg_comum.linha.conteudo.nos

    # Início compartilhado atualizado para '1, 2'
    assert nos_comuns[0].rotulo == "1, 2"

    # Desambiguação de topos: topo original vira 'A', topo novo vira 'B'
    seg_fim_central = pois_por_id[ids_central[1]]
    seg_fim_variante = pois_por_id[ids_variante[1]]

    assert seg_fim_central.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    assert seg_fim_central.linha.conteudo.nos[-1].rotulo == "A"

    assert seg_fim_variante.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    assert seg_fim_variante.linha.conteudo.nos[-1].rotulo == "B"


def test_03_convergencia_mesmo_top_compartilhado(qtbot, tmp_path):
    """
    Cenário 3: Rota convergindo no mesmo topo de via existente com compartilhamento harmônico.
    Contrato:
    - Com 'Via Central' desenhada (topo em 140, 100), traça 'Entrada Esquerda'.
    - 'Entrada Esquerda' inicia em ponto livre (ganha início sequencial '2') e termina
      com snap no nó final da 'Via Central'.
    - Ambas as vias terminam no mesmo topo e compartilham o mesmo nó e identificador de TOP ('A').
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    qtbot.addWidget(widget)

    # 1. Cria 'Via Central'
    widget.iniciar_modo_nova_rota({"nome": "Via Central", "tipo": "boulder", "grau": "V4", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 350), QPointF(140, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # 2. Cria 'Entrada Esquerda' convergindo no mesmo topo (140, 100)
    widget.iniciar_modo_nova_rota({"nome": "Entrada Esquerda", "tipo": "boulder", "grau": "V2", "nova": True})
    for p in [QPointF(20, 480), QPointF(50, 300), QPointF(140, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    croqui_ro = env["model"].obter_croqui_readonly()
    mapa_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]

    refs = {r.escalada: list(r.ids) for r in mapa_ro.referencias}
    pois_por_id = {p.id: p for p in mapa_ro.pontos_de_interesse}

    linha_central = pois_por_id[refs["Via Central"][0]]
    linha_esq = pois_por_id[refs["Entrada Esquerda"][0]]

    # Início da Entrada Esquerda deve ser '2'
    assert linha_esq.linha.conteudo.nos[0].rotulo == "2"

    # Ambas convergem para topo compartilhado 'A'
    top_central = linha_central.linha.conteudo.nos[-1]
    top_esq = linha_esq.linha.conteudo.nos[-1]

    assert top_central.rotulo == "A"
    assert top_esq.rotulo == "A"
    assert top_central.tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    assert top_esq.tipo == croqui_pb2.NoTrajeto.TipoNo.FIM_TOP
    assert top_central.x == top_esq.x == 140
    assert top_central.y == top_esq.y == 100


def test_04_travessia_fatiamento_triplo_intermediario(qtbot, tmp_path):
    """
    Cenário 4: Rota de travessia compartilhando segmento intermediário de via existente.
    Contrato:
    - Rota base hospedeira possui nós N0, N1, N2, N3.
    - Travessia entra em N1, percorre até N2, e sai para N_saida.
    - A linha hospedeira é dividida em 3 partes: início [N0..N1], meio compartilhado [N1..N2], fim [N2..N3].
    - Referência da hospedeira contém os 3 segmentos contíguos ordenados.
    - Referência da travessia contém [entrada_propria, meio_compartilhado, saida_propria].
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    qtbot.addWidget(widget)

    # 1. Rota hospedeira
    widget.iniciar_modo_nova_rota({"nome": "Linha Base", "tipo": "boulder", "grau": "V3", "nova": True})
    for p in [QPointF(100, 500), QPointF(100, 400), QPointF(100, 300), QPointF(100, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # 2. Travessia
    widget.iniciar_modo_nova_rota({"nome": "Travessia", "tipo": "boulder", "grau": "V7", "nova": True})
    for p in [QPointF(20, 400), QPointF(100, 400), QPointF(100, 300), QPointF(180, 250)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    croqui_ro = env["model"].obter_croqui_readonly()
    mapa_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]

    refs = {r.escalada: list(r.ids) for r in mapa_ro.referencias}
    ids_base = refs["Linha Base"]
    ids_trav = refs["Travessia"]

    # Hospedeira dividida em 3 partes
    assert len(ids_base) == 3
    # Travessia possui entrada, meio compartilhado e saída
    assert len(ids_trav) == 3
    # O segmento intermediário é exatamente o mesmo
    assert ids_base[1] == ids_trav[1]


def test_05_reversao_total_undo_redo_atomico(qtbot, tmp_path):
    """
    Cenário 5: Reversão total atômica via Undo (Ctrl+Z) e Restabelecimento via Redo (Ctrl+Y).
    Contrato:
    - Executa o cenário de variante com fatiamento (Cenário 2).
    - Executa `undo()`:
      - Escalada da variante é removida de `setor.escaladas`.
      - Referência da variante é removida de `mapa.referencias`.
      - Sublinhas são removidas e linha original íntegra é restabelecida.
      - Rótulos de início e fim da rota base retornam ao estado anterior ('1', sem TOP).
    - Executa `redo()`:
      - Todo o estado fatiado e desambiguado é restabelecido com exatidão.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    undo_stack = env["undo_stack"]
    qtbot.addWidget(widget)

    # 1. Cria Rota Base
    widget.iniciar_modo_nova_rota({"nome": "Via Base", "tipo": "boulder", "grau": "V4", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 350), QPointF(130, 200), QPointF(140, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # Guarda ID original da linha
    id_original = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0].pontos_de_interesse[0].id

    # 2. Cria Variante
    widget.iniciar_modo_nova_rota({"nome": "Variante", "tipo": "boulder", "grau": "V5", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 350), QPointF(200, 200)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # Verifica que variante foi criada
    setor_ro = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    assert len(setor_ro.escaladas) == 2

    # 3. Executa Undo atômico
    undo_stack.undo()

    setor_pos_undo = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    mapa_pos_undo = setor_pos_undo.mapas[0]

    # Variante desapareceu
    assert len(setor_pos_undo.escaladas) == 1
    assert setor_pos_undo.escaladas[0].boulder.nome == "Via Base"
    assert len(mapa_pos_undo.referencias) == 1
    assert mapa_pos_undo.referencias[0].escalada == "Via Base"

    # Linha original íntegra restaurada
    assert len(mapa_pos_undo.pontos_de_interesse) == 1
    linha_restaurada = mapa_pos_undo.pontos_de_interesse[0]
    assert linha_restaurada.id == id_original
    assert linha_restaurada.linha.conteudo.nos[0].rotulo == "1"
    assert linha_restaurada.linha.conteudo.nos[-1].tipo == croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
    assert linha_restaurada.linha.conteudo.nos[-1].rotulo == ""

    # 4. Executa Redo atômico
    undo_stack.redo()

    setor_pos_redo = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    assert len(setor_pos_redo.escaladas) == 2
    mapa_pos_redo = setor_pos_redo.mapas[0]
    assert len(mapa_pos_redo.referencias) == 2


def test_06_multiplos_mapas_setor_consistencia_e_ids_disjuntos(qtbot, tmp_path):
    """
    Cenário 6: Múltiplos mapas no mesmo setor com persistência de número e IDs disjuntos.
    Contrato:
    - Setor com Mapa 1 e Mapa 2.
    - Traça 'Via Central' no Mapa 1 -> início '1', gera IDs com prefixo.
    - Alterna para Mapa 2 e traça a mesma 'Via Central' na outra foto ->
      reutiliza automaticamente o rótulo de início '1'.
    - Traça uma rota nova 'Via Lateral' no Mapa 2 -> recebe início '2' (próximo global do setor).
    - Todos os IDs de POI entre Mapa 1 e Mapa 2 são mutuamente disjuntos.
    """
    env = _criar_ambiente_teste(tmp_path, num_mapas=2)
    widget = env["widget"]
    qtbot.addWidget(widget)

    # 1. Mapa 1: Traça 'Via Central'
    widget.iniciar_modo_nova_rota({"nome": "Via Central", "tipo": "boulder", "grau": "V4", "nova": True})
    for p in [QPointF(100, 500), QPointF(100, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # 2. Alterna para Mapa 2
    proxy_mapa_2 = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[1]
    widget.set_mapa_atual(proxy_mapa_2, pico_idx=0, grupo_idx=0, mapa_idx=1, tipo="setor")

    # Traça 'Via Central' no Mapa 2 (já existente no setor)
    widget.iniciar_modo_nova_rota({"nome": "Via Central", "tipo": "boulder", "grau": "V4", "nova": False})
    for p in [QPointF(200, 600), QPointF(200, 150)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # Traça 'Via Lateral' no Mapa 2 (nova)
    widget.iniciar_modo_nova_rota({"nome": "Via Lateral", "tipo": "boulder", "grau": "V6", "nova": True})
    for p in [QPointF(300, 600), QPointF(300, 150)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    croqui_ro = env["model"].obter_croqui_readonly()
    setor_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo
    m1 = setor_ro.mapas[0]
    m2 = setor_ro.mapas[1]

    # No Mapa 2, a 'Via Central' reutilizou o rótulo '1'
    linha_m2_central = m2.pontos_de_interesse[0]
    assert linha_m2_central.linha.conteudo.nos[0].rotulo == "1"

    # No Mapa 2, a 'Via Lateral' pegou o próximo global '2'
    linha_m2_lateral = m2.pontos_de_interesse[1]
    assert linha_m2_lateral.linha.conteudo.nos[0].rotulo == "2"

    # IDs de POIs do Mapa 1 e Mapa 2 devem ser estritamente disjuntos
    ids_m1 = {p.id for p in m1.pontos_de_interesse}
    ids_m2 = {p.id for p in m2.pontos_de_interesse}
    assert ids_m1.isdisjoint(ids_m2), f"Colisão detectada entre mapas: {ids_m1 & ids_m2}"


def test_07_sincronizacao_arrasto_nos_soldados_sticky(qtbot, tmp_path):
    """
    Cenário 7: Sincronização de nós soldados ('sticky') ao arrastar alça compartilhada.
    Contrato:
    - Duas linhas que compartilham um nó de junção.
    - Ao arrastar a alça na cena gráfica para uma nova posição, ambas as linhas
      são atualizadas simultaneamente no modelo.
    - Ao acionar `undo()`, ambas retornam juntas à posição original.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    undo_stack = env["undo_stack"]
    qtbot.addWidget(widget)

    # 1. Cria base
    widget.iniciar_modo_nova_rota({"nome": "Linha 1", "tipo": "boulder", "grau": "V3", "nova": True})
    for p in [QPointF(100, 500), QPointF(100, 300), QPointF(100, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # 2. Cria ramificação a partir de (100, 300)
    widget.iniciar_modo_nova_rota({"nome": "Linha 2", "tipo": "boulder", "grau": "V5", "nova": True})
    for p in [QPointF(100, 300), QPointF(200, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # Simula arrasto do nó compartilhado (100, 300) para (150, 320)
    widget.mover_no_soldado(QPointF(100, 300), QPointF(150, 320))

    mapa_ro = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    for poi in mapa_ro.pontos_de_interesse:
        for no in poi.linha.conteudo.nos:
            if (no.x, no.y) == (100, 300):
                pytest.fail("Nenhum nó deveria permanecer na coordenada antiga após o arrasto soldado")

    # Verifica que ambas as linhas agora possuem nós em (150, 320)
    nos_encontrados = 0
    for poi in mapa_ro.pontos_de_interesse:
        for no in poi.linha.conteudo.nos:
            if (no.x, no.y) == (150, 320):
                nos_encontrados += 1
    assert nos_encontrados >= 2

    # Undo restaura as duas coordenadas
    undo_stack.undo()
    mapa_pos_undo = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    nos_originais = 0
    for poi in mapa_pos_undo.pontos_de_interesse:
        for no in poi.linha.conteudo.nos:
            if (no.x, no.y) == (100, 300):
                nos_originais += 1
    assert nos_originais >= 2


def test_08_busca_escalada_preexistente_sem_duplicacao(qtbot, tmp_path):
    """
    Cenário 8: Vinculação de linha a escalada já existente no setor sem gerar duplicatas.
    Contrato:
    - Setor já possui 'Boulder Antigo' cadastrado previamente no Editor de Dados.
    - Inicia o traçado selecionando 'Boulder Antigo' (nova=False).
    - `setor.escaladas` continua com 1 única escalada (sem duplicações).
    - A linha é criada e a referência vinculada corretamente.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    setor = env["setor"]
    qtbot.addWidget(widget)

    # Cadastra previamente a escalada no setor
    boulder_antigo = croqui_pb2.Escalada()
    boulder_antigo.boulder.nome = "Boulder Antigo"
    boulder_antigo.boulder.dificuldade = croqui_pb2.GrauBoulder.V5

    # Adiciona via controller
    from editor.commands.comandos_protobuf import CmdAdicionarRepeated
    proxy_setor = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    cmd = CmdAdicionarRepeated(env["model"], proxy_setor, "escaladas", 0, boulder_antigo)
    env["mapas_ctrl"]._executar_comando(cmd)

    assert len(env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.escaladas) == 1

    # Inicia traçado selecionando escalada existente
    widget.iniciar_modo_nova_rota({"nome": "Boulder Antigo", "tipo": "boulder", "grau": "V5", "nova": False})
    for p in [QPointF(100, 500), QPointF(100, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    setor_final = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    # Não duplicou
    assert len(setor_final.escaladas) == 1
    # Referência criada
    assert len(setor_final.mapas[0].referencias) == 1
    assert setor_final.mapas[0].referencias[0].escalada == "Boulder Antigo"


def test_09_cancelamento_gracioso_sem_efeitos_colaterais(qtbot, tmp_path):
    """
    Cenário 9: Cancelamento gracioso pelo usuário (Esc) durante o desenho.
    Contrato:
    - Usuário aciona '+ Nova Rota', clica 2 pontos e cancela com Esc.
    - A cena deve ser limpa de itens temporários.
    - Nenhuma escalada é criada em `setor.escaladas`.
    - Nenhum comando é empilhado no `QUndoStack`.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    undo_stack = env["undo_stack"]
    qtbot.addWidget(widget)

    widget.iniciar_modo_nova_rota({"nome": "Via Incompleta", "tipo": "boulder", "grau": "V1", "nova": True})
    widget.adicionar_ponto_nova_rota(QPointF(50, 50))
    widget.adicionar_ponto_nova_rota(QPointF(80, 80))

    # Cancela
    widget.cancelar_modo_nova_rota()

    assert widget.modo_nova_rota is False
    assert widget.item_desenho_temp is None

    # Nada no modelo
    croqui_ro = env["model"].obter_croqui_readonly()
    setor_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo
    assert len(setor_ro.escaladas) == 0
    assert len(setor_ro.mapas[0].pontos_de_interesse) == 0
    assert undo_stack.count() == 0


def test_10_validacao_compilacao_croqui_sem_erros(qtbot, tmp_path):
    """
    Cenário 10: Conformidade total com o pipeline de compilação do croqui.
    Contrato:
    - Após traçar múltiplas rotas com variantes e fatiamentos, executa
      `validar_referencias_mapa(croqui_dict)`.
    - Não deve haver nenhum POI órfão nem referências quebradas.
    - A lista de erros retornada deve ser rigorosamente vazia.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    qtbot.addWidget(widget)

    # 1. Rota 1
    widget.iniciar_modo_nova_rota({"nome": "Via Alpha", "tipo": "boulder", "grau": "V3", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 300), QPointF(130, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # 2. Variante Beta fatiando a Alpha
    widget.iniciar_modo_nova_rota({"nome": "Via Beta", "tipo": "boulder", "grau": "V6", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 300), QPointF(200, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    # Valida usando a biblioteca oficial de compilação
    croqui_ro = env["model"].obter_croqui_readonly()
    croqui_obj = getattr(croqui_ro, "_obj", croqui_ro)
    croqui_dict = MessageToDict(croqui_obj, preserving_proto_field_name=True)
    erros = validar_referencias_mapa(croqui_dict)

    assert erros == [], f"Erros de validação de mapa encontrados: {erros}"


def test_11_separar_traco_em_no_e_desfazer(qtbot, tmp_path):
    """
    Cenário 11: Separação de traço em nó intermediário com atualização de referências e reversibilidade por Undo.
    Contrato:
    - Linha traçada com 3 nós (0, 1, 2) e vinculada a uma referência.
    - Aciona 'separar_traco_no' no nó intermediário de índice 1.
    - O POI original é substituído por 2 novos POIs de linha contíguos com IDs disjuntos.
    - A referência da via é atualizada para conter ambos os novos IDs ordenados.
    - Undo restaura o traçado original e a referência; Redo reaplica a separação.
    """
    from editor.views.widget_editor_mapas import ItemTrajetoLinha

    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    undo_stack = env["undo_stack"]
    qtbot.addWidget(widget)

    # 1. Cria a rota base com 3 nós
    widget.iniciar_modo_nova_rota({"nome": "Via Longa", "tipo": "boulder", "grau": "V4", "nova": True})
    for p in [QPointF(100, 500), QPointF(120, 300), QPointF(140, 100)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    croqui_ro = env["model"].obter_croqui_readonly()
    mapa_ro = croqui_ro.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    assert len(mapa_ro.pontos_de_interesse) == 1
    id_orig = str(mapa_ro.pontos_de_interesse[0].id)
    assert list(mapa_ro.referencias[0].ids) == [id_orig]

    # 2. Executa a separação no nó intermediário 1
    widget.separar_traco_no(id_orig, 1)

    croqui_pos_split = env["model"].obter_croqui_readonly()
    mapa_pos_split = croqui_pos_split.picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    # Linha dividida em 2 POIs
    assert len(mapa_pos_split.pontos_de_interesse) == 2
    sub1 = mapa_pos_split.pontos_de_interesse[0]
    sub2 = mapa_pos_split.pontos_de_interesse[1]
    assert sub1.id != id_orig and sub2.id != id_orig
    assert len(sub1.linha.conteudo.nos) == 2
    assert len(sub2.linha.conteudo.nos) == 2
    # Ponto de junção coincide
    assert (sub1.linha.conteudo.nos[1].x, sub1.linha.conteudo.nos[1].y) == (120, 300)
    assert (sub2.linha.conteudo.nos[0].x, sub2.linha.conteudo.nos[0].y) == (120, 300)

    # Referência contém os dois novos IDs
    assert list(mapa_pos_split.referencias[0].ids) == [str(sub1.id), str(sub2.id)]

    # 3. Testa Undo
    undo_stack.undo()
    mapa_undo = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    assert len(mapa_undo.pontos_de_interesse) == 1
    assert str(mapa_undo.pontos_de_interesse[0].id) == id_orig
    assert list(mapa_undo.referencias[0].ids) == [id_orig]

    # 4. Testa Redo
    undo_stack.redo()
    mapa_redo = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    assert len(mapa_redo.pontos_de_interesse) == 2
    assert list(mapa_redo.referencias[0].ids) == [str(sub1.id), str(sub2.id)]


def test_12_adicionar_nova_linha_avulsa_a_partir_de_ponto_final(qtbot, tmp_path):
    """
    Cenário 12: Criação de nova linha avulsa sem ligação iniciada a partir do ponto final de uma linha existente.
    Contrato:
    - Cria uma linha inicial A -> B.
    - Aciona o desenho de linha avulsa (sem_ligacao=True) com ponto inicial em B.
    - Clica no ponto C e conclui o desenho.
    - Uma nova linha B -> C é persistida com ID disjunto.
    - Nenhuma nova escalada ou referência é criada (linha avulsa).
    - Undo remove a linha avulsa sem afetar a linha original.
    """
    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    undo_stack = env["undo_stack"]
    qtbot.addWidget(widget)

    # 1. Cria a primeira linha com escalada
    widget.iniciar_modo_nova_rota({"nome": "Via Base", "tipo": "boulder", "grau": "V2", "nova": True})
    for p in [QPointF(100, 400), QPointF(100, 200)]:
        widget.adicionar_ponto_nova_rota(p)
    widget.finalizar_modo_nova_rota()

    mapa_ini = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    assert len(mapa_ini.pontos_de_interesse) == 1
    assert len(mapa_ini.referencias) == 1

    # 2. Inicia nova linha avulsa a partir do ponto final (100, 200)
    widget.iniciar_modo_nova_rota(
        dados_rota={"sem_ligacao": True},
        ponto_inicial=QPointF(100, 200)
    )
    assert len(widget.pontos_nova_rota) == 1
    assert widget.pontos_nova_rota[0] == QPointF(100, 200)

    # Adiciona próximo ponto (200, 100) e finaliza
    widget.adicionar_ponto_nova_rota(QPointF(200, 100))
    widget.finalizar_modo_nova_rota()

    setor_pos = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    mapa_pos = setor_pos.mapas[0]
    # Agora existem 2 linhas no mapa
    assert len(mapa_pos.pontos_de_interesse) == 2
    # Escaladas e referências permanecem apenas 1 (sem ligação para a nova linha)
    assert len(setor_pos.escaladas) == 1
    assert len(mapa_pos.referencias) == 1

    linha_avulsa = mapa_pos.pontos_de_interesse[1]
    assert (linha_avulsa.linha.conteudo.nos[0].x, linha_avulsa.linha.conteudo.nos[0].y) == (100, 200)
    assert (linha_avulsa.linha.conteudo.nos[1].x, linha_avulsa.linha.conteudo.nos[1].y) == (200, 100)

    # 3. Undo remove a linha avulsa
    undo_stack.undo()
    mapa_undo = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo.mapas[0]
    assert len(mapa_undo.pontos_de_interesse) == 1


def test_jornada_navegacao_pan_zoom_durante_desenho_de_rota(tmp_path, qtbot):
    """
    [TDD - Princípio V] Teste de integração de ponta a ponta:
    Verifica que o escalador consegue navegar pelo mapa (pan com botão do meio,
    pan com Barra de Espaço + Drag, e zoom com Scroll) durante o desenho de uma rota,
    sem que nenhum nó espúrio seja inserido no traçado.
    """
    from PySide6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent
    from PySide6.QtCore import QPoint, QPointF

    env = _criar_ambiente_teste(tmp_path)
    widget = env["widget"]
    vis = widget.visualizador
    qtbot.addWidget(widget)

    # 1. Inicia traçado de nova rota
    widget.iniciar_modo_nova_rota({"nome": "Via Falésia Alta", "tipo": "esportiva", "grau": "7a", "nova": True})
    assert widget.modo_nova_rota is True
    assert len(widget.pontos_nova_rota) == 0

    # 2. Adiciona o primeiro nó na base da falésia (100, 400)
    widget.adicionar_ponto_nova_rota(QPointF(100, 400))
    assert len(widget.pontos_nova_rota) == 1

    # 3. Dá zoom in com a roda do mouse (WheelEvent)
    pos_mouse = QPoint(200, 200)
    evento_wheel = QWheelEvent(
        QPointF(pos_mouse),
        QPointF(pos_mouse),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    vis.wheelEvent(evento_wheel)
    assert len(widget.pontos_nova_rota) == 1, "Zoom não deve adicionar nós"

    # 4. Pan com Botão do Meio (Middle Click Drag)
    h_scroll_antes = vis.horizontalScrollBar().value()
    v_scroll_antes = vis.verticalScrollBar().value()

    ev_press_meio = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(150, 150),
        Qt.MouseButton.MiddleButton,
        Qt.MouseButton.MiddleButton,
        Qt.KeyboardModifier.NoModifier
    )
    vis.mousePressEvent(ev_press_meio)
    assert vis._arrastando_mapa is True

    ev_move_meio = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(100, 100),
        Qt.MouseButton.MiddleButton,
        Qt.MouseButton.MiddleButton,
        Qt.KeyboardModifier.NoModifier
    )
    vis.mouseMoveEvent(ev_move_meio)

    ev_release_meio = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(100, 100),
        Qt.MouseButton.MiddleButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    vis.mouseReleaseEvent(ev_release_meio)
    assert vis._arrastando_mapa is False
    assert len(widget.pontos_nova_rota) == 1, "Arrasto com botão do meio não deve adicionar nós"

    # 5. Pan com Barra de Espaço + Botão Esquerdo (Space + Left Drag)
    ev_space_down = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    vis.keyPressEvent(ev_space_down)
    assert getattr(vis, "_modo_espaco_pan", False) is True

    ev_press_space_esq = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(120, 120),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    vis.mousePressEvent(ev_press_space_esq)
    assert vis._arrastando_mapa is True

    ev_move_space_esq = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(80, 80),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    vis.mouseMoveEvent(ev_move_space_esq)

    ev_release_space_esq = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(80, 80),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    vis.mouseReleaseEvent(ev_release_space_esq)
    assert vis._arrastando_mapa is False

    ev_space_up = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    vis.keyReleaseEvent(ev_space_up)
    assert getattr(vis, "_modo_espaco_pan", False) is False
    assert len(widget.pontos_nova_rota) == 1, "Arrasto com Espaço + Botão Esquerdo não deve adicionar nós"

    # 6. Adiciona o segundo ponto no topo da falésia (100, 100)
    widget.adicionar_ponto_nova_rota(QPointF(100, 100))
    assert len(widget.pontos_nova_rota) == 2

    # 7. Finaliza a rota
    widget.finalizar_modo_nova_rota()

    setor = env["model"].obter_croqui_readonly().picos[0].setores_ou_grupos[0].setor.conteudo
    mapa = setor.mapas[0]
    assert len(mapa.pontos_de_interesse) == 1
    linha_poi = mapa.pontos_de_interesse[0]
    assert len(linha_poi.linha.conteudo.nos) == 2
    assert (linha_poi.linha.conteudo.nos[0].x, linha_poi.linha.conteudo.nos[0].y) == (100, 400)
    assert (linha_poi.linha.conteudo.nos[1].x, linha_poi.linha.conteudo.nos[1].y) == (100, 100)


