# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from dataclasses import dataclass, field

from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QMessageBox

from aresta_api.proto.generated import beta_pb2, croqui_pb2
from coleta_de_betas.curadoria.dialogo_coletar_betas import (
    DialogoColetarBetas,
    WorkerColetaBetas,
    criar_extratores_padrao,
    extrair_escaladas_do_croqui,
)
from coleta_de_betas.extratores.blog import ExtratorBlog
from editor.controllers.croqui_controller import CroquiController
from editor.models.croqui_model import CroquiModel


@dataclass
class _ExtratorBetaFake:
    """Extrator determinístico em memória para testar o Wizard de coleta de betas."""

    respostas_por_via: dict[str, list[beta_pb2.CandidatoMidiaBeta]] = field(default_factory=dict)
    rejeitados_por_via: dict[str, list[beta_pb2.MidiaBeta]] = field(default_factory=dict)
    falhar_em: str | None = None
    chamadas: list[tuple[str, str, str]] = field(default_factory=list)

    def buscar(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
    ) -> list[beta_pb2.CandidatoMidiaBeta]:
        cands, _ = self.buscar_com_rejeitados(
            nome_escalada=nome_escalada,
            nome_setor=nome_setor,
            nome_pico=nome_pico,
            max_resultados=max_resultados,
        )
        return cands

    def buscar_com_rejeitados(
        self,
        nome_escalada: str,
        nome_setor: str = "",
        nome_pico: str = "",
        max_resultados: int = 10,
    ) -> tuple[list[beta_pb2.CandidatoMidiaBeta], list[beta_pb2.MidiaBeta]]:
        _ = max_resultados
        self.chamadas.append((nome_escalada, nome_setor, nome_pico))
        if self.falhar_em == nome_escalada:
            raise RuntimeError("Erro de rede simulado")
        return (
            list(self.respostas_por_via.get(nome_escalada, [])),
            list(self.rejeitados_por_via.get(nome_escalada, [])),
        )


def _criar_croqui_exemplo() -> croqui_pb2.Croqui:
    croqui = croqui_pb2.Croqui(uid="croqui_1", nome="Serra do Cipó")
    pico = croqui.picos.add(nome="Morro da Pedreira")

    sg_setor = pico.setores_ou_grupos.add()
    setor1 = sg_setor.setor.conteudo
    setor1.uid = "setor_1"
    setor1.nome = "Salão Principal"
    esc1 = setor1.escaladas.add(uid="esc_1")
    esc1.via_esportiva.nome = "Via do Sol"

    sg_grupo = pico.setores_ou_grupos.add()
    grupo = sg_grupo.grupo.conteudo
    grupo.uid = "grupo_1"
    grupo.nome = "Grupo Norte"
    subsetor = grupo.setores.add().conteudo
    subsetor.uid = "setor_2"
    subsetor.nome = "Fendas"
    esc2 = subsetor.escaladas.add(uid="esc_2")
    esc2.boulder.nome = "Boulder da Lua"

    return croqui


def test_extrair_escaladas_do_croqui_lista_setores_e_grupos() -> None:
    croqui = _criar_croqui_exemplo()
    itens = extrair_escaladas_do_croqui(croqui)
    assert len(itens) == 2
    assert itens[0].escalada_uid == "esc_1"
    assert itens[0].nome_escalada == "Via do Sol"
    assert itens[0].nome_setor == "Salão Principal"
    assert itens[0].nome_pico == "Morro da Pedreira"

    assert itens[1].escalada_uid == "esc_2"
    assert itens[1].nome_escalada == "Boulder da Lua"
    assert itens[1].nome_setor == "Fendas"


def test_dialogo_coletar_betas_seleciona_executa_coleta_injeta_rejeitados_e_suporta_undo(
    qtbot,
) -> None:
    croqui = _criar_croqui_exemplo()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    cand_yt = beta_pb2.CandidatoMidiaBeta()
    cand_yt.midia.url = "https://www.youtube.com/watch?v=sol123"
    cand_yt.midia.titulo = "Via do Sol Beta"
    cand_yt.midia.fonte = beta_pb2.FonteMidia.YOUTUBE

    cand_blog = beta_pb2.CandidatoMidiaBeta()
    cand_blog.midia.url = "https://blog.com/boulder-lua"
    cand_blog.midia.titulo = "Boulder da Lua Relato"
    cand_blog.midia.fonte = beta_pb2.FonteMidia.BLOG

    rej_scribd = beta_pb2.MidiaBeta(
        url="https://pt.scribd.com/document/111/Croqui",
        titulo="[Query: geral | Auto-filtrado: domínio bloqueado] Croqui PDF",
        fonte=beta_pb2.FonteMidia.BLOG,
    )

    extrator_ok = _ExtratorBetaFake(
        respostas_por_via={
            "Via do Sol": [cand_yt],
            "Boulder da Lua": [cand_blog],
        },
        rejeitados_por_via={
            "Via do Sol": [rej_scribd],
        },
    )
    extrator_falho = _ExtratorBetaFake(falhar_em="Via do Sol")

    dialogo = DialogoColetarBetas(
        model=model,
        controller=controller,
        extratores=[extrator_ok, extrator_falho],
    )
    qtbot.addWidget(dialogo)
    dialogo.show()

    # Estado inicial: Iniciar Coleta e Cancelar visíveis; Finalizar oculto
    assert dialogo.btn_iniciar.isVisible() is True
    assert dialogo.btn_cancelar.isVisible() is True
    assert dialogo.btn_finalizar.isVisible() is False

    assert len(dialogo.checkboxes_por_uid) == 2

    # Testa Desmarcar Todas e Marcar Todas
    dialogo.btn_desmarcar_todas.click()
    assert all(not cb.isChecked() for cb in dialogo.checkboxes_por_uid.values())
    assert dialogo.executar_coleta_sincrona() == 0

    dialogo.btn_marcar_todas.click()
    assert all(cb.isChecked() for cb in dialogo.checkboxes_por_uid.values())

    # Executa coleta síncrona e verifica injeção em betas_nao_scorados, betas_rejeitados e botões finais
    total_adicionados = dialogo.executar_coleta_sincrona()
    assert total_adicionados == 2
    assert dialogo.barra_progresso.value() == 2
    assert len(croqui.curadoria_betas.conteudo.escaladas) == 2
    assert len(croqui.curadoria_betas.conteudo.escaladas[0].betas_rejeitados) == 1
    assert croqui.curadoria_betas.conteudo.escaladas[0].betas_rejeitados[0].titulo.startswith(
        "[Query: geral | Auto-filtrado: domínio bloqueado]"
    )

    # Estado concluído: Iniciar e Cancelar ocultos; apenas Finalizar visível
    assert dialogo.btn_iniciar.isVisible() is False
    assert dialogo.btn_cancelar.isVisible() is False
    assert dialogo.btn_finalizar.isVisible() is True

    # Um único Undo reverte toda a sessão de coleta (candidatos + auto-rejeitados)
    assert stack.count() == 1
    stack.undo()
    assert len(croqui.curadoria_betas.conteudo.escaladas) == 0


def test_dialogo_coletar_betas_cancelamento_com_confirmacao(qtbot) -> None:
    croqui = _criar_croqui_exemplo()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    respostas_confirmacao = [False, True]
    dialogo = DialogoColetarBetas(
        model=model,
        controller=controller,
        extratores=[],
        confirmador_cancelamento=lambda: respostas_confirmacao.pop(0),
    )
    qtbot.addWidget(dialogo)
    dialogo.show()

    # Simula estado "coletando": 1º clique em Cancelar responde "Não" (False) -> mantém ativo
    dialogo._definir_estado_botoes("coletando")
    assert dialogo.btn_iniciar.isVisible() is False
    assert dialogo.btn_cancelar.isVisible() is True
    assert dialogo.btn_cancelar.text() == "Cancelar Coleta"
    assert dialogo.btn_finalizar.isVisible() is False

    dialogo._ao_clicar_cancelar()
    assert dialogo.cancelado is False

    # 2º clique em Cancelar responde "Sim" (True) -> cancela e fecha
    dialogo._ao_clicar_cancelar()
    assert dialogo.cancelado is True
    assert dialogo.executar_coleta_sincrona() == 0


def test_dialogo_coletar_betas_executa_em_background_via_qthread_e_permite_cancelar(qtbot) -> None:
    croqui = _criar_croqui_exemplo()
    model = CroquiModel(croqui)
    stack = QUndoStack()
    controller = CroquiController(model, stack)

    cand_yt = beta_pb2.CandidatoMidiaBeta()
    cand_yt.midia.url = "https://www.youtube.com/watch?v=sol_bg"
    cand_yt.midia.titulo = "Via do Sol Background"
    cand_yt.midia.fonte = beta_pb2.FonteMidia.YOUTUBE

    cand_blog = beta_pb2.CandidatoMidiaBeta()
    cand_blog.midia.url = "https://blog.com/boulder-lua-bg"
    cand_blog.midia.titulo = "Boulder da Lua Background"
    cand_blog.midia.fonte = beta_pb2.FonteMidia.BLOG

    extrator = _ExtratorBetaFake(
        respostas_por_via={
            "Via do Sol": [cand_yt],
            "Boulder da Lua": [cand_blog],
        }
    )

    dialogo = DialogoColetarBetas(
        model=model,
        controller=controller,
        extratores=[extrator],
    )
    qtbot.addWidget(dialogo)
    dialogo.show()

    # Clicar em Iniciar Coleta dispara WorkerColetaBetas em background (QThread)
    dialogo.btn_iniciar.click()
    assert isinstance(dialogo.worker_ativo, WorkerColetaBetas)

    qtbot.waitUntil(
        lambda: dialogo.worker_ativo is None and len(croqui.curadoria_betas.conteudo.escaladas) == 2,
        timeout=3000,
    )
    assert dialogo.barra_progresso.value() == 2
    assert "2 novo(s) candidato(s)" in dialogo.label_progresso.text()
    assert dialogo.btn_finalizar.isVisible() is True
    assert dialogo.btn_iniciar.isVisible() is False
    assert dialogo.btn_cancelar.isVisible() is False
    assert stack.count() == 1

    # Clicar em Finalizar aceita o diálogo
    dialogo.btn_finalizar.click()
    assert dialogo.result() == DialogoColetarBetas.DialogCode.Accepted

    # Testa cancelamento cooperativo diretamente no WorkerColetaBetas (max_workers=1 determinístico)
    escaladas = extrair_escaladas_do_croqui(croqui)
    worker_cancel = WorkerColetaBetas(
        escaladas=escaladas,
        extratores=[extrator],
        max_workers=1,
    )
    worker_cancel.progresso_alterado.connect(
        lambda idx, _total, _nome: worker_cancel.solicitar_cancelamento() if idx == 1 else None
    )
    resultados_finais: list = []
    worker_cancel.concluido.connect(
        lambda lote, cancelado: resultados_finais.append((lote, cancelado))
    )
    worker_cancel.run()
    assert len(resultados_finais) == 1
    lote_parcial, flag_cancelado = resultados_finais[0]
    assert flag_cancelado is True
    assert worker_cancel.foi_cancelado() is True
    assert len(lote_parcial) == 1
    assert lote_parcial[0][0] == "esc_1"


def test_criar_extratores_padrao_usa_busca_unificada_ddgs() -> None:
    extratores = criar_extratores_padrao()
    assert len(extratores) == 1
    assert isinstance(extratores[0], ExtratorBlog)
    _ = QMessageBox
