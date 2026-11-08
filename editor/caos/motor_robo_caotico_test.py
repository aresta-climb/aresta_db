# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtWidgets import QDialog, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout

from editor.caos.motor_robo_caotico import (
    ConfiguracaoSessaoCaos,
    MotorRoboCaoticoQt,
)
from editor.caos.receita_crash_robo import PassoRobo, SeletorAlvoQt


def test_motor_robo_caotico_executa_fluxo_completo_ponderado_deterministico(
    tmp_path: Path,
) -> None:
    cfg_1 = ConfiguracaoSessaoCaos(
        seed=101,
        max_passos=25,
        dataset="toxico",
        escopo="aplicativo_completo",
        exigir_login_otp=True,
        atualizacao_disponivel=True,
    )
    motor_1 = MotorRoboCaoticoQt(tmp_path / "exec_1", cfg_1)
    resultado_1 = motor_1.executar_sessao()

    assert resultado_1.falha is None
    assert len(resultado_1.passos_executados) == 25

    tipos_1 = [p.tipo_acao for p in resultado_1.passos_executados]
    assert any(t.startswith("fase_a_") for t in tipos_1[:5])
    assert any(not t.startswith("fase_a_") for t in tipos_1[5:])

    # Segunda execução com a mesma seed deve gerar a mesma sequência de tipos e seletores
    motor_2 = MotorRoboCaoticoQt(tmp_path / "exec_2", cfg_1)
    resultado_2 = motor_2.executar_sessao()
    assert [p.para_dicionario() for p in resultado_2.passos_executados] == [
        p.para_dicionario() for p in resultado_1.passos_executados
    ]


def test_motor_robo_caotico_exercita_todas_as_abas_e_acoes_janela_principal(
    tmp_path: Path,
) -> None:
    cfg = ConfiguracaoSessaoCaos(
        seed=202,
        max_passos=45,
        dataset="normal",
        escopo="janela_principal",
    )
    motor = MotorRoboCaoticoQt(tmp_path / "exec_janela", cfg)
    resultado = motor.executar_sessao()
    assert resultado.falha is None
    assert len(resultado.passos_executados) == 45

    # Reproduzir a receita gerada deve funcionar deterministicamente (incluindo passo órfão no-op)
    passo_fase_a = PassoRobo(
        indice=1,
        tipo_acao="fase_a_solicitar_otp",
        seletor=SeletorAlvoQt(estrategia="campo_formulario", valor="edit_email"),
        mutou_estado=True,
    )
    passo_edicao = PassoRobo(
        indice=95,
        tipo_acao="editar_campo_linha",
        seletor=SeletorAlvoQt(estrategia="campo_formulario", valor="QLineEdit:0"),
        parametros={"pos": 0, "texto": "Novo Nome Replay"},
        mutou_estado=True,
    )
    passo_undo = PassoRobo(
        indice=96,
        tipo_acao="desfazer_ou_refazer",
        seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="undo"),
        parametros={"op": "undo"},
        mutou_estado=True,
    )
    passo_redo = PassoRobo(
        indice=97,
        tipo_acao="desfazer_ou_refazer",
        seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="redo"),
        parametros={"op": "redo"},
        mutou_estado=True,
    )
    passo_slider = PassoRobo(
        indice=98,
        tipo_acao="interagir_editor_mapas",
        seletor=SeletorAlvoQt(estrategia="cena_grafica", valor="mapa:slider_circ"),
        parametros={"sub_op": "slider_circ"},
        mutou_estado=True,
    )
    passo_orfao = PassoRobo(
        indice=99,
        tipo_acao="clicar_botao_formulario",
        seletor=SeletorAlvoQt(estrategia="objeto_ou_texto", valor="botao_inexistente_xyz"),
        mutou_estado=False,
    )
    import os

    os.environ["ARESTA_DIRETORIO_DADOS"] = str(tmp_path / "anterior")
    try:
        falha_replay = motor.reproduzir_passos(
            [passo_fase_a, passo_edicao, passo_undo, passo_redo, passo_slider, passo_orfao]
        )
        assert os.environ.get("ARESTA_DIRETORIO_DADOS") == str(tmp_path / "anterior")
    finally:
        os.environ.pop("ARESTA_DIRETORIO_DADOS", None)
    assert falha_replay is None


def test_interceptador_modal_desbloqueia_qdialog_exec_automaticamente(
    tmp_path: Path,
) -> None:
    cfg = ConfiguracaoSessaoCaos(seed=303, max_passos=5, dataset="normal", escopo="janela_principal")
    motor = MotorRoboCaoticoQt(tmp_path / "modal_test", cfg)

    dlg = QDialog()
    dlg.setWindowTitle("Diálogo Modal Bloqueante")
    layout = QVBoxLayout(dlg)
    edit = QLineEdit(dlg)
    txt = QTextEdit(dlg)
    btn_ok = QPushButton("Confirmar", dlg)
    btn_ok.clicked.connect(dlg.accept)
    layout.addWidget(edit)
    layout.addWidget(txt)
    layout.addWidget(btn_ok)

    msg = QMessageBox()
    msg.setWindowTitle("Aviso")
    msg.setText("Mensagem Modal")

    with motor.vigiar_dialogos_modais():
        codigo = dlg.exec()
        msg.exec()

    assert codigo in (QDialog.DialogCode.Accepted, QDialog.DialogCode.Rejected)


def test_campanha_por_tempo_captura_encolhe_deduplica_e_salva_receita(
    tmp_path: Path,
) -> None:
    pasta_saida = tmp_path / "caminhos_regressao"
    eventos_sentry: list[object] = []

    resumo = MotorRoboCaoticoQt.executar_campanha(
        raiz_tmp=tmp_path / "campanha",
        duracao_segundos=15.0,
        max_sementes=2,
        passos_por_semente=8,
        diretorio_receitas=pasta_saida,
        reportar_sentry=True,
        injetar_falha_no_passo=4,
        callback_reportar_sentry=eventos_sentry.append,
    )

    assert resumo.sementes_executadas == 2
    assert resumo.falhas_totais == 2
    assert resumo.falhas_unicas == 1
    assert len(resumo.receitas_salvas) == 1
    assert resumo.receitas_salvas[0].is_file()
    assert len(eventos_sentry) == 1
