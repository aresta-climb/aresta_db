# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import contextlib
import os
import random
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QTextEdit,
    QTreeView,
)

from editor.caos.bloqueador_rede import BloqueadorRedeCaos
from editor.caos.encolhedor_caminho_crash import EncolhedorCaminhoCrash
from editor.caos.fabrica_dataset_caos import (
    AmbienteInstalacaoCaos,
    FabricaDatasetCaos,
    gerar_texto_fuzz,
)
from editor.caos.oraculos_caos import OraculosCaos
from editor.caos.receita_crash_robo import (
    FalhaCapturadaRobo,
    PassoRobo,
    ReceitaCrashRobo,
    SeletorAlvoQt,
)
from editor.core.cliente_auth_supabase_fake import ClienteAuthSupabaseFake
from editor.core.gerenciador_sessao import SessaoUsuario
from editor.core.gerenciador_sessao_fake import GerenciadorSessaoFake
from editor.core.servico_submissao import StatusSincronizacao
from editor.core.servico_submissao_fake import ServicoSubmissaoFake
from editor.core.servidor_celular_fake import ServidorCelularFake
from editor.core.telemetria import capturar_crash_robo_caotico
from editor.core.workspace import ExperimentalWorkspace
from editor.legacy_views.area_principal import JanelaPrincipal
from editor.main import ControladorAplicativo
from editor.plataforma.adaptador_plataforma_fake import AdaptadorPlataformaFake
from editor.plataforma.contrato import ResultadoAtualizacao, StatusAtualizacao


@dataclass(frozen=True)
class ConfiguracaoSessaoCaos:
    """Parâmetros determinísticos de uma sessão do Robô Caótico."""

    seed: int = 1
    max_passos: int = 40
    dataset: str = "toxico"
    escopo: str = "aplicativo_completo"
    exigir_login_otp: bool = False
    atualizacao_disponivel: bool = False
    injetar_falha_no_passo: int | None = None


@dataclass(frozen=True)
class ResultadoSessaoCaos:
    """Resultado consolidado de uma execução de semente do Robô Caótico."""

    seed: int
    passos_executados: tuple[PassoRobo, ...]
    falha: FalhaCapturadaRobo | None


@dataclass(frozen=True)
class ResumoCampanhaCaos:
    """Métricas e receitas geradas durante uma campanha por orçamento de tempo."""

    sementes_executadas: int
    falhas_totais: int
    falhas_unicas: int
    receitas_salvas: tuple[Path, ...]


def _bombear_eventos_qt(ciclos: int = 3) -> None:
    for _ in range(ciclos):
        QApplication.processEvents()


def _aguardar_thread_se_ativa(thread_obj: Any, timeout_ms: int = 3000) -> None:
    if thread_obj is not None and hasattr(thread_obj, "isRunning"):
        inicio = time.monotonic()
        while thread_obj.isRunning() and (time.monotonic() - inicio) * 1000 < timeout_ms:
            QApplication.processEvents()
            thread_obj.wait(15)
        QApplication.processEvents()


def _coletar_indices_visiveis_arvore(tree_view: QTreeView) -> list[QModelIndex]:
    model = tree_view.model()
    assert model is not None
    resultado: list[QModelIndex] = []

    def _visitar(pai: QModelIndex) -> None:
        linhas = model.rowCount(pai)
        for r in range(linhas):
            idx = model.index(r, 0, pai)
            if idx.isValid():
                resultado.append(idx)
                if tree_view.isExpanded(idx) or len(resultado) < 12:
                    _visitar(idx)

    _visitar(QModelIndex())
    return resultado


@contextlib.contextmanager
def _isolar_variaveis_ambiente_caos(ambiente: AmbienteInstalacaoCaos) -> Iterator[None]:
    chaves = ("ARESTA_DIRETORIO_DADOS", "ARESTA_GIT_UPSTREAM_URL")
    anteriores = {k: os.environ.get(k) for k in chaves}
    os.environ["ARESTA_DIRETORIO_DADOS"] = str(ambiente.diretorio_dados)
    os.environ["ARESTA_GIT_UPSTREAM_URL"] = ambiente.url_git_upstream
    try:
        yield
    finally:
        for k, valor in anteriores.items():
            if valor is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = valor


class MotorRoboCaoticoQt:
    """
    Motor determinístico de exploração caótica (Monkey/Fuzz Testing) para o Editor Aresta.
    Opera com Orçamento Ponderado:
    - Fase A (10-15% dos passos): TelaDeAbertura + TelaDeCarregamento.
    - Fase B (85-90% dos passos): JanelaPrincipal integrada e seus diálogos.
    """

    def __init__(
        self,
        raiz_tmp: Path,
        config: ConfiguracaoSessaoCaos,
    ) -> None:
        if QApplication.instance() is None:
            import sys

            QApplication(sys.argv)
        self.raiz_tmp = Path(raiz_tmp)
        self.config = config
        self._rng = random.Random(config.seed)
        self.oraculos = OraculosCaos()
        self.ambiente: AmbienteInstalacaoCaos | None = None
        self.cliente_auth_fake = ClienteAuthSupabaseFake(
            codigo_otp_padrao="123456",
            nome_autor_inicial="" if config.exigir_login_otp else "Autor Caótico",
        )
        sessao_inicial = (
            None
            if config.exigir_login_otp
            else SessaoUsuario(
                email="caos@arestaclimb.com",
                nome_completo="Autor Caótico",
                jwt_supabase="jwt-caos-valido",
                token_atualizacao="refresh-caos-valido",
                token_github="gh-token-caos",
            )
        )
        self.sessao_fake = GerenciadorSessaoFake(sessao_inicial=sessao_inicial)
        res_atualizacao = (
            ResultadoAtualizacao(
                status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
                versao_disponivel="9.9.9",
            )
            if config.atualizacao_disponivel
            else ResultadoAtualizacao(status=StatusAtualizacao.NAO_APLICAVEL)
        )
        self.adaptador_loja_fake = AdaptadorPlataformaFake(
            diretorio_dados=self.raiz_tmp / "dados_instalacao",
            resultado_atualizacao_inicial=res_atualizacao,
        )
        self.submissao_fake: ServicoSubmissaoFake | None = None
        self.controlador_app: ControladorAplicativo | None = None
        self.janela: JanelaPrincipal | None = None
        self._passos_executados: list[PassoRobo] = []
        self._fila_passos_fase_a: list[PassoRobo] = []

    @contextlib.contextmanager
    def vigiar_dialogos_modais(self) -> Iterator[None]:
        """
        Mantém uma cadeia reentrante de QTimer.singleShot que interage com qualquer
        QDialog/QMessageBox modal aberto por .exec() (inclusive modais aninhados)
        e o fecha sem bloquear o loop de eventos do teste.
        """
        vigilancia_ativa = True

        def _inspecionar_modal() -> None:
            if not vigilancia_ativa:
                return
            # Agenda o próximo pulso ANTES de interagir com o modal atual para que
            # eventuais .exec() aninhados continuem sendo vigiados sem bloqueio!
            QTimer.singleShot(10, _inspecionar_modal)

            modal = QApplication.activeModalWidget() or QApplication.activePopupWidget()
            if modal is None:
                return
            nome_cls = type(modal).__name__
            if nome_cls == "TelaDeCarregamento":
                self._conduzir_modal_tela_carregamento(modal)
            elif isinstance(modal, QMessageBox):
                modal.accept()
            elif isinstance(modal, QDialog):
                self._interagir_e_fechar_dialogo_generico(modal)

        QTimer.singleShot(10, _inspecionar_modal)
        try:
            yield
        finally:
            vigilancia_ativa = False

    def _interagir_e_fechar_dialogo_generico(self, dialogo: QDialog) -> None:
        nome_cls = type(dialogo).__name__
        if nome_cls == "DialogoPerfilAutor":
            for edit in dialogo.findChildren(QLineEdit):
                edit.setText("Escalador Caótico Silva")
            dialogo.accept()
            return

        if nome_cls == "DialogoNovoCroqui":
            if hasattr(dialogo, "edit_pico"):
                dialogo.edit_pico.setText(gerar_texto_fuzz(self._rng)[:25] or "Pico Caos")
            if hasattr(dialogo, "edit_cidade"):
                dialogo.edit_cidade.setText("Ouro Preto")
            if hasattr(dialogo, "edit_estado"):
                dialogo.edit_estado.setText("MG")
            dialogo.reject()
            return

        if nome_cls == "DialogoBuscaCroqui":
            for edit in dialogo.findChildren(QLineEdit):
                edit.setText("br_")
            dialogo.reject()
            return

        # Diálogos gerais (PublishDialog, DialogoConexaoCelular, DialogoConflitoSincronizacao, etc.)
        for edit in dialogo.findChildren(QLineEdit):
            if edit.isVisible() and not edit.isReadOnly():
                edit.setText("Proposta Caótica Automática")
        for txt in dialogo.findChildren(QTextEdit):
            if txt.isVisible() and not txt.isReadOnly():
                txt.setPlainText("Descrição gerada pelo Robô Caótico.")

        if self._rng.random() < 0.7:
            dialogo.accept()
        else:
            dialogo.reject()

    def _conduzir_modal_tela_carregamento(self, tela: Any) -> None:
        """Executa ações da Fase A na TelaDeCarregamento e seleciona o croqui para abrir a JanelaPrincipal."""
        if not getattr(tela, "_fase_a_exercitada", False):
            tela._fase_a_exercitada = True
            # 1. Exercita abertura rápida e fechamento do DialogoNovoCroqui
            if hasattr(tela, "ao_clicar_novo"):
                tela.ao_clicar_novo()
                self._fila_passos_fase_a.append(
                    PassoRobo(
                        indice=len(self._passos_executados) + len(self._fila_passos_fase_a) + 1,
                        tipo_acao="fase_a_dialogo_novo_croqui",
                        seletor=SeletorAlvoQt(estrategia="objeto_ou_texto", valor="Novo croqui"),
                        mutou_estado=False,
                    )
                )
            # 2. Exercita abertura rápida e fechamento do DialogoBuscaCroqui
            if hasattr(tela, "ao_clicar_oficial"):
                tela.ao_clicar_oficial()
                self._fila_passos_fase_a.append(
                    PassoRobo(
                        indice=len(self._passos_executados) + len(self._fila_passos_fase_a) + 1,
                        tipo_acao="fase_a_dialogo_busca_oficial",
                        seletor=SeletorAlvoQt(
                            estrategia="objeto_ou_texto", valor="Editar croqui oficial"
                        ),
                        mutou_estado=False,
                    )
                )

        # 3. Seleciona o primeiro item do histórico de croquis experimentais e abre a JanelaPrincipal
        item = tela.lista_croquis.item(0)
        self._fila_passos_fase_a.append(
            PassoRobo(
                indice=len(self._passos_executados) + len(self._fila_passos_fase_a) + 1,
                tipo_acao="fase_a_selecionar_croqui_historico",
                seletor=SeletorAlvoQt(
                    estrategia="objeto_ou_texto",
                    valor="lista_croquis:0",
                    classe_widget="QListWidget",
                ),
                mutou_estado=True,
            )
        )
        tela.ao_clicar_item(item)

    def _preparar_ambiente(self) -> AmbienteInstalacaoCaos:
        self.raiz_tmp.mkdir(parents=True, exist_ok=True)
        self.ambiente = FabricaDatasetCaos.inicializar_ambiente_instalacao_caos(
            self.raiz_tmp, dataset=self.config.dataset
        )
        self.submissao_fake = ServicoSubmissaoFake(
            caminho_repo_base=self.ambiente.storage.obter_caminho_base_repo(),
        )
        return self.ambiente

    def _executar_fase_a_entrada(self) -> None:
        """Conduz a Fase A (TelaDeAbertura -> TelaDeCarregamento -> JanelaPrincipal)."""
        from editor.core.worker import TarefaInicializacao

        assert self.ambiente is not None
        tarefa_inicial = TarefaInicializacao(
            storage=self.ambiente.storage,
            gerenciador_sessao=self.sessao_fake,
            cliente_auth=self.cliente_auth_fake,
            servico_loja=self.adaptador_loja_fake,
            intervalo_espera_cofre=0.0,
        )
        self.controlador_app = ControladorAplicativo(
            tarefa=tarefa_inicial,
            iniciar_mcp=False,
            storage=self.ambiente.storage,
            gerenciador_sessao=self.sessao_fake,
            cliente_auth=self.cliente_auth_fake,
            servico_loja=self.adaptador_loja_fake,
            servico_submissao=self.submissao_fake,
            fabrica_servidor_celular=ServidorCelularFake,
        )
        abertura = self.controlador_app.abertura
        tarefa = self.controlador_app.tarefa
        login_processado = False

        inicio = time.monotonic()
        while self.controlador_app.janela_principal is None and (time.monotonic() - inicio) < 8.0:
            _bombear_eventos_qt(4)
            if abertura.update_container.isVisible():
                abertura.btn_atualizar_store.click()
                abertura.esconder_aviso_atualizacao()
                self._passos_executados.append(
                    PassoRobo(
                        indice=len(self._passos_executados) + 1,
                        tipo_acao="fase_a_aviso_atualizacao",
                        seletor=SeletorAlvoQt(
                            estrategia="objeto_ou_texto", valor="Atualizar Agora"
                        ),
                        mutou_estado=False,
                    )
                )
                self.adaptador_loja_fake.configurar_resultado_atualizacao(
                    ResultadoAtualizacao(status=StatusAtualizacao.NAO_APLICAVEL)
                )
                _aguardar_thread_se_ativa(tarefa)
                with contextlib.suppress(RuntimeError, TypeError):
                    abertura.login_concluido.disconnect(self.controlador_app.ao_login_concluido)
                    abertura.login_cancelado.disconnect(self.controlador_app.ao_login_cancelado)
                self.controlador_app._tarefa_injetada = TarefaInicializacao(
                    storage=self.ambiente.storage,
                    gerenciador_sessao=self.sessao_fake,
                    cliente_auth=self.cliente_auth_fake,
                    servico_loja=self.adaptador_loja_fake,
                    intervalo_espera_cofre=0.0,
                )
                self.controlador_app.iniciar_inicializacao()
                tarefa = self.controlador_app.tarefa
                continue

            if abertura.auth_container.isVisible() and not login_processado:
                login_processado = True
                abertura.mostrar_formulario_email()
                abertura.edit_email.setText("caos@arestaclimb.com")
                abertura.solicitar_otp()
                _aguardar_thread_se_ativa(getattr(abertura, "_tarefa_otp", None))
                _bombear_eventos_qt(5)
                self._passos_executados.append(
                    PassoRobo(
                        indice=len(self._passos_executados) + 1,
                        tipo_acao="fase_a_solicitar_otp",
                        seletor=SeletorAlvoQt(
                            estrategia="campo_formulario",
                            valor="edit_email",
                            classe_widget="QLineEdit",
                        ),
                        parametros={"email": "caos@arestaclimb.com"},
                        mutou_estado=True,
                    )
                )

                abertura.edit_codigo.setText("123456")
                abertura.validar_otp()
                _aguardar_thread_se_ativa(getattr(abertura, "_tarefa_validar", None))
                _bombear_eventos_qt(5)
                self._passos_executados.append(
                    PassoRobo(
                        indice=len(self._passos_executados) + 1,
                        tipo_acao="fase_a_validar_otp",
                        seletor=SeletorAlvoQt(
                            estrategia="campo_formulario",
                            valor="edit_codigo",
                            classe_widget="QLineEdit",
                        ),
                        parametros={"codigo": "123456"},
                        mutou_estado=True,
                    )
                )
                continue

            if (
                tarefa is not None
                and not tarefa.isRunning()
                and not abertura.update_container.isVisible()
                and not abertura.auth_container.isVisible()
            ):
                _bombear_eventos_qt(6)
                if (
                    not abertura.update_container.isVisible()
                    and not abertura.auth_container.isVisible()
                ):
                    break
            time.sleep(0.01)

        _aguardar_thread_se_ativa(tarefa)
        _bombear_eventos_qt(5)

        for p_a in self._fila_passos_fase_a:
            if len(self._passos_executados) < self.config.max_passos:
                self._passos_executados.append(
                    PassoRobo(
                        indice=len(self._passos_executados) + 1,
                        tipo_acao=p_a.tipo_acao,
                        seletor=p_a.seletor,
                        parametros=p_a.parametros,
                        mutou_estado=p_a.mutou_estado,
                    )
                )
        self._fila_passos_fase_a.clear()

        self.janela = self.controlador_app.janela_principal
        if self.janela is not None and self.janela.croqui_model is not None:
            self.oraculos.ressincronizar_estado_base(
                self.janela.croqui_model, self.janela.historico
            )

    def _iniciar_janela_principal_direta(self) -> None:
        assert self.ambiente is not None
        ws = ExperimentalWorkspace(self.ambiente.caminho_croqui_experimental)
        self.janela = JanelaPrincipal(
            storage=self.ambiente.storage,
            auth=self.sessao_fake,
            workspace=ws,
            iniciar_mcp=False,
            servico_submissao=self.submissao_fake,
            fabrica_servidor_celular=ServidorCelularFake,
            servico_loja=self.adaptador_loja_fake,
        )
        self.janela.show()
        _bombear_eventos_qt(4)
        if self.janela.croqui_model is not None:
            self.oraculos.ressincronizar_estado_base(
                self.janela.croqui_model, self.janela.historico
            )

    def _sortear_e_executar_passo_fase_b(self, indice_passo: int) -> PassoRobo:
        assert self.janela is not None

        if self.config.injetar_falha_no_passo == indice_passo:
            return self._executar_acao_fase_b(indice_passo, "injecao_falha_teste")

        catalogo_acoes = [
            "trocar_aba",
            "selecionar_no_arvore",
            "editar_campo_linha",
            "editar_campo_texto",
            "alterar_combo_box",
            "interagir_editor_mapas",
            "interagir_editor_imagens",
            "interagir_painel_betas",
            "desfazer_ou_refazer",
            "salvar_croqui",
            "abrir_dialogo_celular",
            "publicar_ou_sincronizar",
        ]
        escolha = self._rng.choice(catalogo_acoes)
        return self._executar_acao_fase_b(indice_passo, escolha)

    def _executar_acao_fase_b(
        self,
        indice_passo: int,
        tipo_acao: str,
        parametros_fixos: dict[str, Any] | None = None,
    ) -> PassoRobo:
        assert self.janela is not None
        janela = self.janela
        pilha = janela.historico.obter_pilha()
        idx_antes = pilha.index()

        if tipo_acao == "injecao_falha_teste":
            err = RuntimeError(f"Falha determinística injetada no passo {indice_passo}")
            self.oraculos.registrar_excecao(RuntimeError, err, None)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="injecao_falha_teste",
                seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="InjetarFalha"),
                mutou_estado=True,
            )

        if tipo_acao == "trocar_aba":
            aba = (
                int(parametros_fixos["aba"])
                if parametros_fixos and "aba" in parametros_fixos
                else self._rng.choice([0, 0, 1, 2, 3])
            )
            janela._trocar_pagina(aba)
            _bombear_eventos_qt(2)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="trocar_aba",
                seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor=f"aba:{aba}"),
                parametros={"aba": aba},
                mutou_estado=False,
            )

        if tipo_acao == "selecionar_no_arvore":
            janela._trocar_pagina(0)
            editor_dados = getattr(janela.pagina_dados, "editor_dados", None)
            tree_view = getattr(editor_dados, "tree_view", None)
            if isinstance(tree_view, QTreeView):
                indices = _coletar_indices_visiveis_arvore(tree_view)
                if indices:
                    pos = (
                        int(parametros_fixos["pos"]) % len(indices)
                        if parametros_fixos and "pos" in parametros_fixos
                        else self._rng.randrange(len(indices))
                    )
                    idx_alvo = indices[pos]
                    tree_view.expand(idx_alvo)
                    tree_view.setCurrentIndex(idx_alvo)
                    _bombear_eventos_qt(2)
                    return PassoRobo(
                        indice=indice_passo,
                        tipo_acao="selecionar_no_arvore",
                        seletor=SeletorAlvoQt(
                            estrategia="caminho_no_arvore",
                            valor=f"no_visivel:{pos}",
                            classe_widget="QTreeView",
                            indice=pos,
                        ),
                        parametros={"pos": pos},
                        mutou_estado=False,
                    )

        if tipo_acao == "editar_campo_linha":
            janela._trocar_pagina(0)
            editor_dados = getattr(janela.pagina_dados, "editor_dados", None)
            if editor_dados is not None:
                edits = [
                    w
                    for w in editor_dados.findChildren(QLineEdit)
                    if w.isVisible() and w.isEnabled() and not w.isReadOnly()
                ]
                if edits:
                    pos = (
                        int(parametros_fixos["pos"]) % len(edits)
                        if parametros_fixos and "pos" in parametros_fixos
                        else self._rng.randrange(len(edits))
                    )
                    texto = (
                        str(parametros_fixos["texto"])
                        if parametros_fixos and "texto" in parametros_fixos
                        else gerar_texto_fuzz(self._rng)
                    )
                    alvo = edits[pos]
                    alvo.setFocus()
                    alvo.setText(texto)
                    alvo.textEdited.emit(texto)
                    alvo.editingFinished.emit()
                    _bombear_eventos_qt(2)
                    return PassoRobo(
                        indice=indice_passo,
                        tipo_acao="editar_campo_linha",
                        seletor=SeletorAlvoQt(
                            estrategia="campo_formulario",
                            valor=alvo.objectName() or f"QLineEdit:{pos}",
                            classe_widget="QLineEdit",
                            indice=pos,
                        ),
                        parametros={"pos": pos, "texto": texto},
                        mutou_estado=(pilha.index() != idx_antes),
                    )

        if tipo_acao == "editar_campo_texto":
            janela._trocar_pagina(0)
            editor_dados = getattr(janela.pagina_dados, "editor_dados", None)
            if editor_dados is not None:
                txts = [
                    w
                    for w in editor_dados.findChildren(QTextEdit)
                    if w.isVisible() and w.isEnabled() and not w.isReadOnly()
                ]
                if txts:
                    pos = (
                        int(parametros_fixos["pos"]) % len(txts)
                        if parametros_fixos and "pos" in parametros_fixos
                        else self._rng.randrange(len(txts))
                    )
                    texto = (
                        str(parametros_fixos["texto"])
                        if parametros_fixos and "texto" in parametros_fixos
                        else gerar_texto_fuzz(self._rng)
                    )
                    alvo_txt = txts[pos]
                    alvo_txt.setFocus()
                    alvo_txt.setPlainText(texto)
                    alvo_txt.clearFocus()
                    _bombear_eventos_qt(2)
                    return PassoRobo(
                        indice=indice_passo,
                        tipo_acao="editar_campo_texto",
                        seletor=SeletorAlvoQt(
                            estrategia="campo_formulario",
                            valor=f"QTextEdit:{pos}",
                            classe_widget="QTextEdit",
                            indice=pos,
                        ),
                        parametros={"pos": pos, "texto": texto},
                        mutou_estado=(pilha.index() != idx_antes),
                    )

        if tipo_acao == "alterar_combo_box":
            janela._trocar_pagina(0)
            editor_dados = getattr(janela.pagina_dados, "editor_dados", None)
            if editor_dados is not None:
                combos = [
                    w
                    for w in editor_dados.findChildren(QComboBox)
                    if w.isVisible() and w.isEnabled() and w.count() > 1
                ]
                if combos:
                    pos = (
                        int(parametros_fixos["pos"]) % len(combos)
                        if parametros_fixos and "pos" in parametros_fixos
                        else self._rng.randrange(len(combos))
                    )
                    cmb = combos[pos]
                    novo_idx = (
                        int(parametros_fixos["idx_item"]) % cmb.count()
                        if parametros_fixos and "idx_item" in parametros_fixos
                        else self._rng.randrange(cmb.count())
                    )
                    cmb.setCurrentIndex(novo_idx)
                    _bombear_eventos_qt(2)
                    return PassoRobo(
                        indice=indice_passo,
                        tipo_acao="alterar_combo_box",
                        seletor=SeletorAlvoQt(
                            estrategia="campo_formulario",
                            valor=f"QComboBox:{pos}",
                            classe_widget="QComboBox",
                            indice=pos,
                        ),
                        parametros={"pos": pos, "idx_item": novo_idx},
                        mutou_estado=(pilha.index() != idx_antes),
                    )

        if tipo_acao == "interagir_editor_mapas":
            janela._trocar_pagina(2)
            ed_mapas = janela.pagina_mapas.garantir_editor_criado()
            if ed_mapas is not None:
                if ed_mapas.list_widget.count() > 0 and ed_mapas.list_widget.currentRow() < 0:
                    ed_mapas.list_widget.setCurrentRow(0)
                    _bombear_eventos_qt(2)
                sub_op = (
                    str(parametros_fixos["sub_op"])
                    if parametros_fixos and "sub_op" in parametros_fixos
                    else self._rng.choice(["circulo", "retangulo", "slider_circ", "converter"])
                )
                if sub_op in ("circulo", "retangulo"):
                    ed_mapas.adicionar_poi(sub_op)
                    if hasattr(ed_mapas, "visualizador") and ed_mapas.visualizador.viewport():
                        vp = ed_mapas.visualizador.viewport()
                        QTest.mouseClick(
                            vp,
                            Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier,
                            QPoint(40, 40),
                        )
                elif sub_op == "slider_circ" and hasattr(ed_mapas, "slider_circ"):
                    ed_mapas.slider_circ.sliderPressed.emit()
                    ed_mapas.slider_circ.setValue(10)
                    ed_mapas.slider_circ.sliderReleased.emit()
                elif sub_op == "converter" and hasattr(ed_mapas, "alternar_modo_conversao"):
                    ed_mapas.alternar_modo_conversao()
                    ed_mapas.alternar_modo_conversao()
                _bombear_eventos_qt(2)
                if janela.croqui_model is not None:
                    self.oraculos.ressincronizar_estado_base(janela.croqui_model, janela.historico)
                return PassoRobo(
                    indice=indice_passo,
                    tipo_acao="interagir_editor_mapas",
                    seletor=SeletorAlvoQt(
                        estrategia="cena_grafica",
                        valor=f"mapa:{sub_op}",
                        classe_widget="WidgetEditorMapas",
                    ),
                    parametros={"sub_op": sub_op},
                    mutou_estado=True,
                )

        if tipo_acao == "interagir_editor_imagens":
            janela._trocar_pagina(1)
            ed_img = janela.pagina_imagens.editor
            if hasattr(ed_img, "list_widget") and isinstance(ed_img.list_widget, QListWidget):
                if ed_img.list_widget.count() > 0:
                    ed_img.list_widget.setCurrentRow(0)
            _bombear_eventos_qt(2)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="interagir_editor_imagens",
                seletor=SeletorAlvoQt(
                    estrategia="cena_grafica",
                    valor="imagem_selecionar",
                    classe_widget="WidgetEditorImagens",
                ),
                mutou_estado=False,
            )

        if tipo_acao == "interagir_painel_betas":
            janela._trocar_pagina(3)
            painel = janela.pagina_betas.garantir_painel_criado()
            if painel is not None and hasattr(painel, "btn_auto_selecionar"):
                painel.btn_auto_selecionar.click()
            _bombear_eventos_qt(2)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="interagir_painel_betas",
                seletor=SeletorAlvoQt(
                    estrategia="objeto_ou_texto",
                    valor="painel_betas",
                    classe_widget="PainelCuradoria",
                ),
                mutou_estado=False,
            )

        if tipo_acao == "desfazer_ou_refazer":
            operacao = (
                str(parametros_fixos["op"])
                if parametros_fixos and "op" in parametros_fixos
                else ("undo" if pilha.canUndo() and self._rng.random() < 0.65 else "redo")
            )
            if operacao == "undo" and pilha.canUndo():
                janela.historico.desfazer()
            elif operacao == "redo" and pilha.canRedo():
                janela.historico.refazer()
            _bombear_eventos_qt(2)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="desfazer_ou_refazer",
                seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor=operacao),
                parametros={"op": operacao},
                mutou_estado=(pilha.index() != idx_antes),
            )

        if tipo_acao == "salvar_croqui":
            janela.salvar_croqui()
            _aguardar_thread_se_ativa(getattr(janela, "_worker_salvar", None))
            _bombear_eventos_qt(3)
            if janela.croqui_model is not None:
                self.oraculos.ressincronizar_estado_base(janela.croqui_model, janela.historico)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="salvar_croqui",
                seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="Salvar"),
                mutou_estado=True,
            )

        if tipo_acao == "abrir_dialogo_celular":
            janela._exibir_conexao_celular()
            _aguardar_thread_se_ativa(getattr(janela, "_worker_salvar", None))
            _bombear_eventos_qt(3)
            if janela.croqui_model is not None:
                self.oraculos.ressincronizar_estado_base(janela.croqui_model, janela.historico)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="abrir_dialogo_celular",
                seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="Celular"),
                mutou_estado=False,
            )

        if tipo_acao == "publicar_ou_sincronizar":
            if self.submissao_fake is not None:
                self.submissao_fake.configurar_proxima_sincronizacao(
                    self._rng.choice(
                        [
                            StatusSincronizacao.ATUALIZADO,
                            StatusSincronizacao.MESCLADO,
                            StatusSincronizacao.CONFLITO,
                        ]
                    )
                )
            janela.sincronizar_croqui(silencioso=True)
            _aguardar_thread_se_ativa(getattr(janela, "_tarefa_sincronizacao", None))
            _bombear_eventos_qt(3)
            if janela.croqui_model is not None:
                self.oraculos.ressincronizar_estado_base(janela.croqui_model, janela.historico)
            return PassoRobo(
                indice=indice_passo,
                tipo_acao="publicar_ou_sincronizar",
                seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="Sincronizar"),
                mutou_estado=True,
            )

        # Fallback determinístico caso a ação sorteada não tenha alvo visível no momento
        janela._trocar_pagina(0)
        _bombear_eventos_qt(1)
        return PassoRobo(
            indice=indice_passo,
            tipo_acao="noop_fallback",
            seletor=SeletorAlvoQt(estrategia="acao_toolbar", valor="Dados"),
            mutou_estado=False,
        )

    def _verificar_todos_oraculos(self, passo: PassoRobo) -> FalhaCapturadaRobo | None:
        if self.janela is not None and self.janela.croqui_model is not None:
            self.oraculos.verificar_integridade_objetos_qt([self.janela, self.janela.croqui_model])
            foi_undo_redo = passo.tipo_acao == "desfazer_ou_refazer" and passo.mutou_estado
            self.oraculos.auditar_passo_historico(
                self.janela.croqui_model,
                self.janela.historico,
                foi_undo_ou_redo=foi_undo_redo,
            )
            if self.janela.workspace is not None:
                diario = self.janela.workspace.obter_diario()
                self.janela.historico.flush_diario_pendente()
                self.oraculos.verificar_integridade_diario(diario)

        return self.oraculos.obter_primeira_falha()

    def _encerrar_instancias_qt(self) -> None:
        if self.janela is not None:
            _aguardar_thread_se_ativa(getattr(self.janela, "_worker_salvar", None))
            _aguardar_thread_se_ativa(getattr(self.janela, "_tarefa_sincronizacao", None))
            if hasattr(self.janela, "_encerrar_servidor_celular"):
                self.janela._encerrar_servidor_celular()
            self.janela._forcar_fechamento = True
            self.janela.close()
            self.janela.deleteLater()
            self.janela = None
        if self.controlador_app is not None:
            _aguardar_thread_se_ativa(getattr(self.controlador_app, "tarefa", None))
            if self.controlador_app.abertura is not None:
                if hasattr(self.controlador_app.abertura, "_timer_reenvio"):
                    self.controlador_app.abertura._timer_reenvio.stop()
                self.controlador_app.abertura.close()
            self.controlador_app = None
        _bombear_eventos_qt(3)

    def executar_sessao(self) -> ResultadoSessaoCaos:
        """Executa uma sessão exploratória completa respeitando o bloqueio de rede e os 3 oráculos."""
        self._passos_executados.clear()
        self.oraculos.limpar_falhas()
        ambiente = self._preparar_ambiente()

        try:
            with (
                _isolar_variaveis_ambiente_caos(ambiente),
                BloqueadorRedeCaos(),
                self.oraculos.monitorar_excecoes(),
                self.vigiar_dialogos_modais(),
            ):
                if self.config.escopo == "aplicativo_completo":
                    self._executar_fase_a_entrada()
                else:
                    self._iniciar_janela_principal_direta()

                while len(self._passos_executados) < self.config.max_passos:
                    idx_passo = len(self._passos_executados) + 1
                    passo = self._sortear_e_executar_passo_fase_b(idx_passo)
                    self._passos_executados.append(passo)
                    falha_oraculo = self._verificar_todos_oraculos(passo)
                    if falha_oraculo is not None:
                        return ResultadoSessaoCaos(
                            seed=self.config.seed,
                            passos_executados=tuple(self._passos_executados),
                            falha=falha_oraculo,
                        )

                return ResultadoSessaoCaos(
                    seed=self.config.seed,
                    passos_executados=tuple(self._passos_executados),
                    falha=None,
                )
        finally:
            self._encerrar_instancias_qt()

    def reproduzir_passos(
        self, passos: Sequence[PassoRobo], subpasta_replay: str = "replay"
    ) -> FalhaCapturadaRobo | None:
        """
        Reexecuta uma sequência de PassoRobo em um ambiente limpo, tratando alvos ausentes
        como no-op e retornando a FalhaCapturadaRobo caso ocorra.
        """
        pasta_isolada = self.raiz_tmp / subpasta_replay
        motor_replay = MotorRoboCaoticoQt(pasta_isolada, self.config)
        motor_replay.oraculos.limpar_falhas()
        ambiente = motor_replay._preparar_ambiente()

        try:
            with (
                _isolar_variaveis_ambiente_caos(ambiente),
                BloqueadorRedeCaos(),
                motor_replay.oraculos.monitorar_excecoes(),
                motor_replay.vigiar_dialogos_modais(),
            ):
                motor_replay._iniciar_janela_principal_direta()
                for idx, passo in enumerate(passos, start=1):
                    if passo.tipo_acao.startswith("fase_a_"):
                        continue
                    passo_exec = motor_replay._executar_acao_fase_b(
                        idx, passo.tipo_acao, parametros_fixos=passo.parametros
                    )
                    falha = motor_replay._verificar_todos_oraculos(passo_exec)
                    if falha is not None:
                        return falha
                return None
        finally:
            motor_replay._encerrar_instancias_qt()

    @classmethod
    def executar_campanha(
        cls,
        raiz_tmp: Path,
        duracao_segundos: float = 5.0,
        seed_inicial: int = 1000,
        max_sementes: int = 1000,
        passos_por_semente: int = 35,
        diretorio_receitas: Path | None = None,
        reportar_sentry: bool = True,
        injetar_falha_no_passo: int | None = None,
        callback_reportar_sentry: Callable[[ReceitaCrashRobo], None] | None = None,
    ) -> ResumoCampanhaCaos:
        """
        Executa uma campanha de exploração caótica por orçamento de tempo com:
        - Deduplicação de falhas por assinatura_deduplicacao();
        - Shrinking automático (ddmin) apenas para falhas inéditas;
        - Gravação de receitas JSON e envio ao Sentry com o arquivo '.json' anexado.
        """
        inicio = time.monotonic()
        sementes_executadas = 0
        falhas_totais = 0
        assinaturas_vistas: set[str] = set()
        receitas_salvas: list[Path] = []

        while sementes_executadas < max_sementes and (time.monotonic() - inicio) < duracao_segundos:
            seed_atual = seed_inicial + sementes_executadas
            dataset = "toxico" if sementes_executadas % 2 == 0 else "normal"
            cfg = ConfiguracaoSessaoCaos(
                seed=seed_atual,
                max_passos=passos_por_semente,
                dataset=dataset,
                escopo="janela_principal",
                injetar_falha_no_passo=injetar_falha_no_passo,
            )
            pasta_semente = Path(raiz_tmp) / f"seed_{seed_atual}"
            motor = cls(pasta_semente, cfg)
            resultado = motor.executar_sessao()
            sementes_executadas += 1

            if resultado.falha is not None:
                falhas_totais += 1
                assinatura = resultado.falha.assinatura_deduplicacao()
                if assinatura not in assinaturas_vistas:
                    assinaturas_vistas.add(assinatura)
                    receita_bruta = ReceitaCrashRobo(
                        seed=seed_atual,
                        dataset=dataset,
                        escopo=cfg.escopo,
                        falha=resultado.falha,
                        passos_minimos=resultado.passos_executados,
                        passos_originais=resultado.passos_executados,
                    )
                    tentativa_idx = 0

                    def _avaliar(cand: Sequence[PassoRobo]) -> FalhaCapturadaRobo | None:
                        nonlocal tentativa_idx
                        tentativa_idx += 1
                        return motor.reproduzir_passos(
                            cand, subpasta_replay=f"ddmin_{tentativa_idx}"
                        )

                    encolhedor = EncolhedorCaminhoCrash(_avaliar, max_tentativas=10)
                    receita_minima = encolhedor.encolher(receita_bruta)

                    pasta_destino_json = (
                        Path(diretorio_receitas)
                        if diretorio_receitas is not None
                        else (Path(raiz_tmp) / "receitas_temporarias")
                    )
                    caminho_arq = (
                        pasta_destino_json
                        / f"crash_seed_{seed_atual}_{resultado.falha.tipo_excecao.lower()}.json"
                    )
                    receita_minima.salvar_json(caminho_arq)
                    if diretorio_receitas is not None:
                        receitas_salvas.append(caminho_arq)

                    if callback_reportar_sentry is not None:
                        callback_reportar_sentry(receita_minima)
                    if reportar_sentry:
                        erro_sentry = resultado.falha.excecao_original or RuntimeError(
                            f"[{receita_minima.falha.oraculo}] {receita_minima.falha.mensagem}"
                        )
                        id_croqui_crash = (
                            "br_sp_caos_toxico" if dataset == "toxico" else "br_mg_caos_normal"
                        )
                        capturar_crash_robo_caotico(
                            erro=erro_sentry,
                            receita_robo_caotico=receita_minima.para_dicionario(),
                            id_croqui=id_croqui_crash,
                            caminho_arquivo_json=caminho_arq,
                        )

        return ResumoCampanhaCaos(
            sementes_executadas=sementes_executadas,
            falhas_totais=falhas_totais,
            falhas_unicas=len(assinaturas_vistas),
            receitas_salvas=tuple(receitas_salvas),
        )
