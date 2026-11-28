# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes orientados a comportamento para `editor.core.carregador_croqui`."""

from __future__ import annotations

import threading
from pathlib import Path

from editor.core.carregador_croqui import (
    PacoteCroquiCarregado,
    carregar_pacote_croqui,
    hidratar_arquivos_externos_protobuf,
    pre_aquecer_modulos_editor,
)
from editor.models.croqui_model import CroquiModel
from scripts.gerenciar_uids_lib import gerar_uid
from scripts.migrador import obter_ultima_versao_migracao


def _criar_croqui_completo_disco(pasta_db: Path) -> tuple[str, str]:
    pasta_db.mkdir(parents=True, exist_ok=True)
    uid_croqui = gerar_uid()
    uid_botao = gerar_uid()
    uid_pico = gerar_uid()
    uid_setor = gerar_uid()
    uid_grupo = gerar_uid()
    uid_subsetor = gerar_uid()
    uid_esc = gerar_uid()
    uid_poi = gerar_uid()

    (pasta_db / "historia.md").write_text(
        "---\ntitulo: Historia\n---\nTexto historico do pico.\n",
        encoding="utf-8",
    )
    (pasta_db / "resumo.md").write_text(
        "Texto sem frontmatter.\n",
        encoding="utf-8",
    )
    (pasta_db / "mapas_gerais.md").write_text(
        f"---\nmapas:\n  - caminho_imagem_mapa: imagens/geral.webp\n    pontos_de_interesse:\n      - uid: {uid_poi}\n        rotulo: P1\n---\n",
        encoding="utf-8",
    )
    (pasta_db / "malha.yaml").write_text(
        "versao: 3\nlatitude_referencia_e7: -195000000\nlongitude_referencia_e7: -439000000\nnos:\n  - latitude_e7: -195000000\n    longitude_e7: -439000000\n    distancia_metros: 100\n    duracao_minutos: 2\n",
        encoding="utf-8",
    )
    (pasta_db / "setor_principal.md").write_text(
        f"---\nuid: {uid_setor}\nnome: Setor Principal\nescaladas:\n  - uid: {uid_esc}\n    via:\n      nome: Via Classica\n---\nDescricao do setor.\n",
        encoding="utf-8",
    )
    (pasta_db / "subsetor_a.md").write_text(
        f"---\nuid: {uid_subsetor}\nnome: Subsetor A\n---\r\nDescricao CRLF.\n",
        encoding="utf-8",
    )
    (pasta_db / "grupo_norte.md").write_text(
        f"---\nuid: {uid_grupo}\nnome: Grupo Norte\nsetores:\n  - caminho: subsetor_a.md\n---\nDescricao do grupo.\n",
        encoding="utf-8",
    )
    (pasta_db / "curadoria_betas.yaml").write_text(
        f"uid: ignorar\nescaladas:\n  - escalada_uid: {uid_esc}\n    uid: ignorar\n    betas_nao_scorados:\n      - url: https://youtube.com/watch?v=abc12345678\n        titulo: Beta 1\n",
        encoding="utf-8",
    )

    # Note: referencia legada curadoria_betas.md para exercitar fallback automatico para .yaml
    (pasta_db / "croqui.yaml").write_text(
        f"id: br_mg_teste\n"
        f"uid: {uid_croqui}\n"
        f"nome: Croqui Completo\n"
        f"ultima_migracao: {obter_ultima_versao_migracao()}\n"
        f"curadoria_betas:\n  caminho: curadoria_betas.md\n"
        f"botoes:\n"
        f"  - uid: {uid_botao}\n    rotulo: Historia\n    destino:\n      secao_textual:\n        caminho: historia.md\n"
        f"  - uid: {gerar_uid()}\n    rotulo: Resumo\n    destino:\n      secao_textual:\n        caminho: resumo.md\n"
        f"picos:\n"
        f"  - uid: {uid_pico}\n"
        f"    nome: Pico Central\n"
        f"    localizacao:\n      latitude: -195000000\n      longitude: -439000000\n"
        f"    mapas_gerais:\n      caminho: mapas_gerais.md\n"
        f"    malha_estrada:\n      caminho: malha.yaml\n"
        f"    setores_ou_grupos:\n"
        f"      - setor:\n          caminho: setor_principal.md\n"
        f"      - grupo:\n          caminho: grupo_norte.md\n",
        encoding="utf-8",
    )
    return uid_setor, uid_esc


def test_carregar_pacote_croqui_em_thread_secundaria_e_instanciar_croqui_model(
    qapp, tmp_path: Path
) -> None:
    _ = qapp
    pasta_db = tmp_path / "database" / "br_mg_teste"
    uid_setor, uid_esc = _criar_croqui_completo_disco(pasta_db)

    caixa: list[PacoteCroquiCarregado | None] = []

    def _worker() -> None:
        pre_aquecer_modulos_editor()
        caixa.append(
            carregar_pacote_croqui(
                pasta_db,
                obter_commit_sha=lambda: "abc123def456",
            )
        )

    th = threading.Thread(target=_worker)
    th.start()
    th.join(timeout=10.0)

    pacote = caixa[0]
    assert pacote is not None
    assert pacote.commit_base_sha == "abc123def456"
    assert pacote.croqui_data["nome"] == "Croqui Completo"
    assert pacote.resultado_qualidade_inicial.nota_qualidade > 0

    # Instancia CroquiModel na UI thread sem refazer I/O e valida resolução de UIDs e serialização
    model = CroquiModel.criar_de_pacote_carregado(pacote)
    assert model.obter_objeto_por_uid(uid_setor) is not None
    assert model.obter_objeto_por_uid(uid_esc) is not None
    ro = model.obter_croqui_readonly()
    assert len(ro.curadoria_betas.conteudo.escaladas) == 1
    assert ro.botoes[0].destino.secao_textual.conteudo.strip() == "Texto historico do pico."
    assert ro.botoes[1].destino.secao_textual.conteudo.strip() == "Texto sem frontmatter."
    assert (
        ro.picos[0].setores_ou_grupos[1].grupo.conteudo.setores[0].conteudo.descricao.strip()
        == "Descricao CRLF."
    )

    serializado = model.extrair_arquivos_e_serializar(pasta_db, persistir_no_disco=False)
    assert serializado["id"] == "br_mg_teste"


def test_carregar_pacote_croqui_ausente_vazio_e_arquivos_invalidos(tmp_path: Path) -> None:
    # Diretório inexistente ou sem croqui.yaml retorna None
    assert carregar_pacote_croqui(tmp_path / "inexistente", executar_migracoes=False) is None
    pasta_sem_yaml = tmp_path / "sem_yaml"
    pasta_sem_yaml.mkdir()
    assert carregar_pacote_croqui(pasta_sem_yaml, executar_migracoes=False) is None

    # Hidratação defensiva para caminhos vazios, ausentes, inline e YAML/tipos corrompidos
    from aresta_api.proto.generated.croqui_pb2 import Croqui

    hidratar_arquivos_externos_protobuf(Croqui(), tmp_path / "nao_existe")

    pasta_err = tmp_path / "croqui_quebrado"
    pasta_err.mkdir()
    (pasta_err / "vazio.md").write_text("---\n---\n", encoding="utf-8")
    (pasta_err / "yaml_ruim.md").write_text("---\n: [invalido\n---\n", encoding="utf-8")
    (pasta_err / "yaml_puro_ruim.yaml").write_text(": [invalido", encoding="utf-8")
    (pasta_err / "tipo_errado.md").write_text(
        "---\nescaladas: nao_eh_lista\n---\n", encoding="utf-8"
    )
    (pasta_err / "md_sem_corpo.md").write_text("---\na: 1\n---", encoding="utf-8")
    (pasta_err / "dir_md.md").mkdir()

    (pasta_err / "croqui.yaml").write_text(
        f"id: quebrado\nnome: Quebrado\nultima_migracao: {obter_ultima_versao_migracao()}\n"
        "curadoria_betas:\n  caminho: yaml_puro_ruim.yaml\n"
        "botoes:\n"
        "  - rotulo: B1\n    destino:\n      secao_textual:\n        caminho: md_sem_corpo.md\n"
        "  - rotulo: B2\n    destino:\n      secao_textual:\n        caminho: dir_md.md\n"
        "picos:\n"
        "  - nome: P1\n"
        "    mapas_gerais:\n      caminho: vazio.md\n"
        "    malha_estrada:\n      caminho: ausente.yaml\n"
        "    setores_ou_grupos:\n"
        "      - setor:\n          caminho: tipo_errado.md\n"
        "      - setor:\n          conteudo:\n            nome: Setor Inline\n"
        "      - grupo:\n          caminho: yaml_ruim.md\n",
        encoding="utf-8",
    )
    pacote = carregar_pacote_croqui(pasta_err, executar_migracoes=False)
    assert pacote is not None
    assert pacote.croqui_msg.botoes[0].destino.secao_textual.conteudo == ""
