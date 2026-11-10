# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import random
from dataclasses import dataclass
from pathlib import Path

import pygit2
from PySide6.QtGui import QColor, QImage

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from editor.core.serializacao_util import serializar_yaml
from editor.core.storage import GerenciadorCaminhos
from editor.models.croqui_model import CroquiModel
from scripts.gerenciar_uids_lib import gerar_uid
from scripts.migrador import obter_ultima_versao_migracao

DICT_ENTRADAS_FUZZ: tuple[str, ...] = (
    "",
    " ",
    "   \t\n  ",
    "Setor do Caos 🧗‍♀️🔥🪨",
    "Via RTL العربية עברית",
    "Acentuação: áéíóú âêô ãõ ç ñ ü",
    "YAML: 'aspas' \"duplas\" : # --- ... [ ] { } & * ! | > @ `",
    "Linha 1\nLinha 2\n\nLinha 4",
    "-999999",
    "0",
    "99999999",
    "3.14159265",
    "-20.385574, -43.503578",
    "<script>alert('caos')</script> & <b>bold</b>",
    "A" * 512,
)


def gerar_texto_fuzz(rng: random.Random) -> str:
    """Seleciona deterministicamente uma string do dicionário de fuzzing a partir da PRNG."""
    return rng.choice(DICT_ENTRADAS_FUZZ)


def _salvar_png_sintetico(caminho: Path, largura: int, altura: int, cor_hex: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    imagem = QImage(largura, altura, QImage.Format.Format_RGBA8888)
    imagem.fill(QColor(cor_hex))
    imagem.save(str(caminho))


def _persistir_croqui_no_disco(croqui: croqui_pb2.Croqui, pasta_db: Path) -> None:
    pasta_db.mkdir(parents=True, exist_ok=True)
    model = CroquiModel(croqui)
    dados_dict = model.extrair_arquivos_e_serializar(pasta_db)
    texto_yaml = serializar_yaml(dados_dict, sort_keys=False)
    cabecalho = (
        "# SPDX-License-Identifier: ODbL-1.0\n# Copyright (C) 2026 Aresta Climb Contributors\n"
    )
    (pasta_db / "croqui.yaml").write_text(cabecalho + texto_yaml, encoding="utf-8")


@dataclass(frozen=True)
class AmbienteInstalacaoCaos:
    """Representa um ambiente de instalação 100% isolado em tmp_path com Git upstream local."""

    diretorio_dados: Path
    url_git_upstream: str
    storage: GerenciadorCaminhos
    caminho_croqui_experimental: Path
    id_croqui_experimental: str


class FabricaDatasetCaos:
    """
    Fábrica determinística de datasets ('normal' e 'toxico') e repositório Git upstream local
    em tmp_path para campanhas e replay do Robô Caótico.
    """

    @staticmethod
    def criar_croqui_normal(
        pasta_db: Path, id_croqui: str = "br_mg_ouro_preto_normal"
    ) -> croqui_pb2.Croqui:
        """Gera um croqui válido e completo com pico, setor, grupo, mapas, imagens e betas."""
        pasta_db.mkdir(parents=True, exist_ok=True)
        _salvar_png_sintetico(pasta_db / "imagens" / "mapa_setor.png", 320, 240, "#4a6fa5")
        _salvar_png_sintetico(pasta_db / "imagens" / "thumbnail.png", 160, 120, "#2b580c")

        croqui = croqui_pb2.Croqui()
        croqui.id = id_croqui
        croqui.uid = gerar_uid()
        croqui.nome = "Ouroboulder Normal"
        croqui.descricao = "Croqui sintético normal para testes do Editor Aresta."
        croqui.creditos.extend(["Equipe Aresta", "Robô Caótico"])
        croqui.ultima_migracao = obter_ultima_versao_migracao()
        croqui.publicar_croqui = True

        botao = croqui.botoes.add()
        botao.uid = gerar_uid()
        botao.texto = "Guia de Acesso"
        botao.destino.secao_textual.conteudo = "# Acesso Normal\n\nTrilha tranquila de 10 minutos."

        pico = croqui.picos.add()
        pico.nome = "Pico Normal"
        pico.estado = "MG"
        pico.cidade = "Ouro Preto"
        pico.localizacao.latitude = -203855740
        pico.localizacao.longitude = -435035780

        mapa_geral = pico.mapas_gerais.conteudo.mapas.add()
        mapa_geral.caminho_imagem_mapa = "imagens/mapa_setor.png"
        mapa_geral.largura_mapa = 320
        mapa_geral.altura_mapa = 240
        ponto_mg = mapa_geral.pontos_de_interesse.add()
        ponto_mg.uid = gerar_uid()
        ponto_mg.rotulo = "S1"
        ponto_mg.circulo.x = 120
        ponto_mg.circulo.y = 100
        ponto_mg.circulo.raio = 16

        # 1. Setor direto com duas escaladas e mapa completo
        sg_setor = pico.setores_ou_grupos.add()
        setor = sg_setor.setor.conteudo
        setor.uid = gerar_uid()
        setor.nome = "Setor Principal"
        setor.descricao = "Setor ensolarado com vias e boulders."

        esc_via = setor.escaladas.add()
        esc_via.uid = gerar_uid()
        esc_via.via_esportiva.nome = "Aresta Clássica"
        esc_via.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP
        esc_via.via_esportiva.extensao = 22
        esc_via.via_esportiva.quantidade_protecoes_intermediarias = 8
        esc_via.via_esportiva.descricao = "Via clássica em agarras positivas."

        esc_boulder = setor.escaladas.add()
        esc_boulder.uid = gerar_uid()
        esc_boulder.boulder.nome = "Bloco do Cristal"
        esc_boulder.boulder.dificuldade = croqui_pb2.GrauBoulder.V4
        esc_boulder.boulder.tipo_parede = croqui_pb2.TipoParede.VERTICAL

        mapa_setor = setor.mapas.add()
        mapa_setor.caminho_imagem_mapa = "imagens/mapa_setor.png"
        mapa_setor.largura_mapa = 320
        mapa_setor.altura_mapa = 240

        p_circ = mapa_setor.pontos_de_interesse.add()
        p_circ.uid = gerar_uid()
        p_circ.rotulo = "01"
        p_circ.circulo.x = 80
        p_circ.circulo.y = 180
        p_circ.circulo.raio = 14

        p_linha = mapa_setor.pontos_de_interesse.add()
        p_linha.uid = gerar_uid()
        p_linha.rotulo = "L1"
        p_linha.linha.estilo = croqui_pb2.LinhaTrajeto.TRACEJADO
        p_linha.linha.espessura = 3
        no1 = p_linha.linha.conteudo.nos.add()
        no1.x = 80
        no1.y = 180
        no1.tipo = croqui_pb2.NoTrajeto.CIRCULO_IDENTIFICADOR
        no1.rotulo = "01"
        no2 = p_linha.linha.conteudo.nos.add()
        no2.x = 90
        no2.y = 60
        no2.tipo = croqui_pb2.NoTrajeto.TOP_PARADA

        ref_via = mapa_setor.referencias.add()
        ref_via.alvo_uid = esc_via.uid
        ref_via.pontos_uids.extend([p_circ.uid, p_linha.uid])

        # 2. Grupo com sub-setor
        sg_grupo = pico.setores_ou_grupos.add()
        grupo = sg_grupo.grupo.conteudo
        grupo.uid = gerar_uid()
        grupo.nome = "Grupo da Floresta"
        sub = grupo.setores.add().conteudo
        sub.uid = gerar_uid()
        sub.nome = "Subsetor Sombra"
        esc_sub = sub.escaladas.add()
        esc_sub.uid = gerar_uid()
        esc_sub.via_movel.nome = "Fenda da Sombra"
        esc_sub.via_movel.dificuldade = croqui_pb2.GrauVia.BR_5SUP

        # Betas pendentes para exercitar PainelCuradoria
        croqui.curadoria_betas.caminho = "curadoria_betas.yaml"
        cur_esc = croqui.curadoria_betas.conteudo.escaladas.add(escalada_uid=esc_via.uid)
        cand_alta = cur_esc.betas_nao_revisados.add()
        cand_alta.midia.url = "https://www.youtube.com/watch?v=normal00001"
        cand_alta.midia.titulo = "Beta Aresta Clássica"
        cand_alta.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
        cand_alta.resultado_llm.llm_confidence_score = 92
        cand_alta.resultado_llm.llm_reasoning = "Mesmo nome de via e setor."

        cand_baixa = cur_esc.betas_nao_revisados.add()
        cand_baixa.midia.url = "https://www.instagram.com/p/normal00002/"
        cand_baixa.midia.titulo = "Post escalada genérica"
        cand_baixa.midia.fonte = beta_pb2.FonteMidia.INSTAGRAM
        cand_baixa.resultado_llm.llm_confidence_score = 45
        cand_baixa.resultado_llm.llm_reasoning = "Apenas menciona a região."

        _persistir_croqui_no_disco(croqui, pasta_db)
        return croqui

    @staticmethod
    def criar_croqui_toxico(
        pasta_db: Path, id_croqui: str = "br_sp_caos_toxico"
    ) -> croqui_pb2.Croqui:
        """Gera um croqui tóxico com casos de borda extremos de Unicode, geometria e aninhamento."""
        pasta_db.mkdir(parents=True, exist_ok=True)
        _salvar_png_sintetico(pasta_db / "imagens" / "parede_toxica.png", 320, 240, "#8b2635")
        _salvar_png_sintetico(pasta_db / "imagens" / "micro_4x4.png", 4, 4, "#f4a261")

        croqui = croqui_pb2.Croqui()
        croqui.id = id_croqui
        croqui.uid = gerar_uid()
        croqui.nome = "Croqui Tóxico 🧗‍♀️🔥 العربية 'aspas' #yaml"
        croqui.descricao = "Linha 1 com 'aspas' e \"duplas\"\n\nLinha 3 com emojis 🪨⚡ e RTL."
        croqui.creditos.extend(["Autor 1 (Tóxico)", "Autor 2: #teste", "Autor 3"])
        croqui.ultima_migracao = obter_ultima_versao_migracao()

        for idx_b in range(2):
            botao = croqui.botoes.add()
            botao.uid = gerar_uid()
            botao.texto = f"Seção Tóxica {idx_b + 1}"
            botao.destino.secao_textual.conteudo = f"# Seção {idx_b + 1}\n\nTexto com caracteres especiais: `code`, *italico*, **negrito**."

        pico = croqui.picos.add()
        pico.nome = "Pico Extremo ⛰️"
        pico.estado = "SP"
        pico.cidade = "São Bento do Sapucaí"
        pico.localizacao.latitude = -226812345
        pico.localizacao.longitude = -456543210

        # Setor 1: cheio de tipos variados de escalada e primitivas de mapa
        sg_cheio = pico.setores_ou_grupos.add()
        setor_cheio = sg_cheio.setor.conteudo
        setor_cheio.uid = gerar_uid()
        setor_cheio.nome = "Setor Poligonal & Trajetos"
        setor_cheio.descricao = "Descrição com múltiplas linhas\ne símbolos: --- : [ ] { }."

        esc1 = setor_cheio.escaladas.add()
        esc1.uid = gerar_uid()
        esc1.via_esportiva.nome = "Via Limite Zero"
        esc1.via_esportiva.dificuldade = croqui_pb2.GrauVia.PROJETO
        esc1.via_esportiva.extensao = 0

        esc2 = setor_cheio.escaladas.add()
        esc2.uid = gerar_uid()
        esc2.boulder.nome = "Highball Tóxico 🧨"
        esc2.boulder.dificuldade = croqui_pb2.GrauBoulder.V15
        esc2.boulder.tipo_parede = croqui_pb2.TipoParede.NEGATIVO

        esc3 = setor_cheio.escaladas.add()
        esc3.uid = gerar_uid()
        esc3.highline.nome = "Travessia do Abismo"
        esc3.highline.distancia = 180
        esc3.highline.altura = 95

        mapa_tox = setor_cheio.mapas.add()
        mapa_tox.caminho_imagem_mapa = "imagens/parede_toxica.png"
        mapa_tox.largura_mapa = 320
        mapa_tox.altura_mapa = 240

        p1 = mapa_tox.pontos_de_interesse.add()
        p1.uid = gerar_uid()
        p1.rotulo = "00"
        p1.circulo.x = 0
        p1.circulo.y = 0
        p1.circulo.raio = 10

        p2 = mapa_tox.pontos_de_interesse.add()
        p2.uid = gerar_uid()
        p2.rotulo = "R1"
        p2.retangulo.x = 160
        p2.retangulo.y = 120
        p2.retangulo.comprimento = 60
        p2.retangulo.largura = 40
        p2.retangulo.angulo_graus_x100 = 1500

        p3 = mapa_tox.pontos_de_interesse.add()
        p3.uid = gerar_uid()
        p3.rotulo = "P1"
        p3.poligono.coordenadas.extend([10, 10, 80, 20, 60, 90, 15, 75])

        p4 = mapa_tox.pontos_de_interesse.add()
        p4.uid = gerar_uid()
        p4.rotulo = "L_TOX"
        p4.linha.estilo = croqui_pb2.LinhaTrajeto.PONTILHADO
        p4.linha.espessura = 5
        for nx, ny, ntipo in (
            (20, 220, croqui_pb2.NoTrajeto.INICIO_AGACHADO),
            (100, 140, croqui_pb2.NoTrajeto.CRUX),
            (200, 80, croqui_pb2.NoTrajeto.PROTECAO_FIXA),
            (300, 20, croqui_pb2.NoTrajeto.FIM_TOP),
        ):
            no = p4.linha.conteudo.nos.add()
            no.x = nx
            no.y = ny
            no.tipo = ntipo
            no.rotulo = "X"

        ref1 = mapa_tox.referencias.add()
        ref1.alvo_uid = esc1.uid
        ref1.pontos_uids.extend([p1.uid, p4.uid])

        # Setor 2: vazio (sem escaladas) para exercitar listas vazias
        sg_vazio = pico.setores_ou_grupos.add()
        setor_vazio = sg_vazio.setor.conteudo
        setor_vazio.uid = gerar_uid()
        setor_vazio.nome = "Setor Vazio"

        croqui.curadoria_betas.caminho = "curadoria_betas.yaml"
        cur1 = croqui.curadoria_betas.conteudo.escaladas.add(escalada_uid=esc1.uid)
        for score, url_suf, titulo in (
            (100, "tox100", "Beta Perfeito 100% 🔥"),
            (80, "tox080", "Beta Limiar 80%"),
            (0, "tox000", "Beta Ruído 0%"),
        ):
            cand = cur1.betas_nao_revisados.add()
            cand.midia.url = f"https://www.youtube.com/watch?v={url_suf}"
            cand.midia.titulo = titulo
            cand.midia.fonte = beta_pb2.FonteMidia.YOUTUBE
            cand.resultado_llm.llm_confidence_score = score
            cand.resultado_llm.llm_reasoning = f"Score extremo {score}"
            cand.snippets.extend(["Snippet 1", "Snippet 2"])

        _persistir_croqui_no_disco(croqui, pasta_db)
        return croqui

    @classmethod
    def inicializar_ambiente_instalacao_caos(
        cls, raiz_tmp: Path, dataset: str = "toxico"
    ) -> AmbienteInstalacaoCaos:
        """
        Inicializa em raiz_tmp:
        1. O repositório Git upstream local (remoto_oficial.git) com commits reais de ambos os datasets.
        2. O diretório de dados da instalação (GerenciadorCaminhos) isolado em raiz_tmp.
        3. Um croqui experimental pré-populado para abertura rápida ou seleção na TelaDeCarregamento.
        """
        caminho_remoto = raiz_tmp / "remoto_oficial.git"
        caminho_remoto.mkdir(parents=True, exist_ok=True)
        repo_upstream = pygit2.init_repository(str(caminho_remoto), initial_head="main")

        cls.criar_croqui_normal(
            caminho_remoto / "database" / "br_mg_ouro_preto_normal",
            id_croqui="br_mg_ouro_preto_normal",
        )
        cls.criar_croqui_toxico(
            caminho_remoto / "database" / "br_sp_caos_toxico",
            id_croqui="br_sp_caos_toxico",
        )

        repo_upstream.index.add_all()
        repo_upstream.index.write()
        tree_id = repo_upstream.index.write_tree()
        assinatura = pygit2.Signature("Aresta Upstream Local", "upstream@arestaclimb.com")
        repo_upstream.create_commit(
            "refs/heads/main",
            assinatura,
            assinatura,
            "Commit inicial dos datasets normal e toxico para o Robo Caotico",
            tree_id,
            [],
        )

        diretorio_dados = raiz_tmp / "dados_instalacao"
        storage = GerenciadorCaminhos(diretorio_base=diretorio_dados)
        storage.inicializar_diretorios()

        if dataset == "normal":
            id_exp = "br_mg_ouro_preto_normal"
            pasta_exp = storage.obter_caminho_croquis_experimentais() / id_exp
            cls.criar_croqui_normal(pasta_exp / "database", id_croqui=id_exp)
        else:
            id_exp = "br_sp_caos_toxico"
            pasta_exp = storage.obter_caminho_croquis_experimentais() / id_exp
            cls.criar_croqui_toxico(pasta_exp / "database", id_croqui=id_exp)

        return AmbienteInstalacaoCaos(
            diretorio_dados=diretorio_dados,
            url_git_upstream=str(caminho_remoto),
            storage=storage,
            caminho_croqui_experimental=pasta_exp,
            id_croqui_experimental=id_exp,
        )
