# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import sys

# Define explicitamente a API PySide6 para bibliotecas auxiliares como QtAwesome e QtPy
os.environ.setdefault("QT_API", "pyside6")


def configurar_streams_utf8(streams: tuple[object, ...] | None = None) -> None:
    """
    Garante que sys.stdout e sys.stderr nunca sejam None (como ocorre em executáveis GUI com
    console=False abertos pelo Menu Iniciar / MSIX no Windows) e utilizem UTF-8 com substituição
    segura ('replace'), evitando AttributeError ('NoneType' has no attribute 'isatty' no Uvicorn)
    e UnicodeEncodeError (cp1252).
    """
    if streams is None:
        if sys.stdout is None:
            sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
        if sys.stderr is None:
            sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")
        alvos: tuple[object, ...] = (sys.stdout, sys.stderr)
    else:
        alvos = streams

    for stream in alvos:
        reconfigurar = getattr(stream, "reconfigure", None)
        if callable(reconfigurar):
            reconfigurar(encoding="utf-8", errors="replace")


configurar_streams_utf8()

from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path para permitir imports do pacote 'editor'
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:  # pragma: no cover
    sys.path.insert(0, parent_dir)

from editor.plataforma import (
    configurar_ambiente_plataforma,
    configurar_identidade_processo,
)

configurar_ambiente_plataforma()

from pathlib import Path
from typing import Any

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from editor.views.estilo import configurar_tema_claro_aplicacao


def __getattr__(name: str) -> Any:
    """Carregamento tardio e sob demanda de classes pesadas para acelerar o arranque do editor."""
    if name == "TarefaInicializacao":
        from editor.core.worker import TarefaInicializacao

        return TarefaInicializacao
    if name == "TelaDeCarregamento":
        from editor.legacy_views.tela_de_carregamento import TelaDeCarregamento

        return TelaDeCarregamento
    if name == "TelaDeAbertura":
        from editor.views.tela_de_abertura import TelaDeAbertura

        return TelaDeAbertura
    if name == "GerenciadorCaminhos":
        from editor.core.storage import GerenciadorCaminhos

        return GerenciadorCaminhos
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Configuração de identidade do processo no shell da plataforma (preservando MSIX no Windows)
from editor.core.configuracao_canal import obter_configuracao_canal

config_canal_global = obter_configuracao_canal()
configurar_identidade_processo(config_canal_global.app_user_model_id)

# Placeholder para o Client ID do GitHub (deve ser substituído por um real em produção)
ID_CLIENTE_GITHUB: str = "Iv23li5kcnSYgMgEfvAC"


class ControladorAplicativo:
    """
    Controla o ciclo de vida da aplicação (Abertura -> Diálogo de Seleção -> Janela Principal).
    Permite a navegação de retorno da Janela Principal para a Seleção.
    """

    def __init__(
        self,
        tarefa: Any | None = None,
        diretorio_sessao_mcp: Path | None = None,
        iniciar_rede_mcp: bool = True,
        storage: Any | None = None,
        gerenciador_sessao: Any | None = None,
        cliente_auth: Any | None = None,
        servico_loja: Any | None = None,
        servico_submissao: Any | None = None,
        fabrica_servidor_celular: Any | None = None,
        caminho_croqui_local: Path | None = None,
    ) -> None:
        inst = QApplication.instance()
        self.app: QApplication = inst if isinstance(inst, QApplication) else QApplication(sys.argv)

        config_canal = obter_configuracao_canal()
        self.app.setApplicationName(config_canal.nome_aplicativo)
        configurar_tema_claro_aplicacao(self.app)

        caminho_logo_app = config_canal.obter_caminho_icone_aplicacao()
        self.app.setWindowIcon(QIcon(str(caminho_logo_app)))

        from editor.core.version import VERSION

        self.app.setApplicationVersion(VERSION)

        self._storage: Any | None = storage
        self._gerenciador_sessao: Any | None = gerenciador_sessao
        self._cliente_auth: Any | None = cliente_auth
        self._servico_loja: Any | None = servico_loja
        self._servico_submissao: Any | None = servico_submissao
        self._fabrica_servidor_celular: Any | None = fabrica_servidor_celular
        self._caminho_croqui_local: Path | None = (
            Path(caminho_croqui_local) if caminho_croqui_local is not None else None
        )

        abertura_cls = sys.modules[__name__].TelaDeAbertura
        self.abertura: Any = abertura_cls()
        if self._cliente_auth is not None:
            self.abertura.cliente_auth = self._cliente_auth
        if self._gerenciador_sessao is not None:
            self.abertura.gerenciador_sessao = self._gerenciador_sessao
        self.janela_principal: Any | None = None
        self.janelas_secundarias: list[Any] = []
        self.tela_carregamento: Any | None = None
        self.tarefa: Any | None = None
        self._tarefa_injetada: Any | None = tarefa
        self._diretorio_sessao_mcp: Path | None = diretorio_sessao_mcp
        self._iniciar_rede_mcp: bool = iniciar_rede_mcp
        self.servidor_mcp: Any | None = None
        self._logout_em_andamento: bool = False
        self._modo_smoke_test: bool = False

        self.app.aboutToQuit.connect(self.encerrar_servidores_locais)
        self.iniciar_inicializacao()

    def iniciar_inicializacao(self) -> None:
        """Inicia ou reinicia a tarefa de inicialização e sincronização."""
        if self._tarefa_injetada is not None:
            self.tarefa = self._tarefa_injetada
            self._tarefa_injetada = None
        else:
            tarefa_cls = sys.modules[__name__].TarefaInicializacao
            kwargs_tarefa: dict[str, Any] = {}
            if self._storage is not None:
                kwargs_tarefa["storage"] = self._storage
            if self._gerenciador_sessao is not None:
                kwargs_tarefa["gerenciador_sessao"] = self._gerenciador_sessao
            if self._cliente_auth is not None:
                kwargs_tarefa["cliente_auth"] = self._cliente_auth
            if self._servico_loja is not None:
                kwargs_tarefa["servico_loja"] = self._servico_loja
            if self._caminho_croqui_local is not None:
                kwargs_tarefa["sincronizar_git"] = False
                kwargs_tarefa["intervalo_espera_cofre"] = 0.0
            self.tarefa = (
                tarefa_cls(ID_CLIENTE_GITHUB, **kwargs_tarefa)
                if kwargs_tarefa
                else tarefa_cls(ID_CLIENTE_GITHUB)
            )
        if (
            hasattr(self.tarefa, "gerenciador_sessao")
            and self.tarefa.gerenciador_sessao is not None
        ):
            self.abertura.gerenciador_sessao = self.tarefa.gerenciador_sessao
        if hasattr(self.tarefa, "cliente_auth") and self.tarefa.cliente_auth is not None:
            self.abertura.cliente_auth = self.tarefa.cliente_auth
        self.tarefa.status.connect(self.abertura.atualizar_status)
        self.tarefa.progresso.connect(self.abertura.atualizar_progresso)
        self.tarefa.mostrar_progresso.connect(self.abertura.exibir_barra_progresso)
        self.tarefa.solicitar_login_ui.connect(self.abertura.iniciar_fluxo_login)
        self.tarefa.atualizacao_disponivel.connect(self.ao_detectar_atualizacao)
        self.tarefa.sucesso.connect(self.executar_selecao)
        self.tarefa.erro.connect(self.mostrar_erro)

        self.abertura.login_concluido.connect(self.ao_login_concluido)
        self.abertura.login_cancelado.connect(self.ao_login_cancelado)

        self.abertura.show()
        self.tarefa.start()

    def ao_login_concluido(self, sessao: Any | None) -> None:
        """Persiste a sessão e desbloqueia a tarefa de inicialização."""
        if sessao and self.tarefa:
            print(f"💾 [Main] Salvando sessão de {sessao.nome_completo}...")
            self.tarefa.gerenciador_sessao.salvar_sessao(sessao)
            print("🚀 [Main] Desbloqueando thread de inicialização...")
            self.tarefa.definir_sessao_concluida(sessao)

    def ao_login_cancelado(self) -> None:
        """Cancela a inicialização se o usuário desistir do login."""
        print("⚠️ [Main] Login cancelado pelo usuário.")
        if self.tarefa:
            self.tarefa.definir_sessao_concluida(None)

    def ao_detectar_atualizacao(self, resultado: Any) -> None:
        """
        Exibe a notificação de atualização na Tela de Abertura e configura a ação de atualização.
        """
        if self.tarefa:
            self.abertura.exibir_aviso_atualizacao(
                resultado,
                callback_atualizar=lambda: (
                    self.tarefa.servico_loja.solicitar_instalacao_atualizacao(resultado)
                    if self.tarefa
                    else None
                ),
            )

    def executar_selecao(self) -> None:
        """
        Exibe a Tela de Carregamento como um diálogo modal.
        """
        print("✨ [Main] Inicialização de dados concluída. Abrindo TelaDeCarregamento...")
        # Desativa temporariamente quitOnLastWindowClosed durante a transição entre janelas
        # para evitar que o fechamento da abertura/janela anterior ou do diálogo encerre o app.exec()
        self.app.setQuitOnLastWindowClosed(False)

        # Garante que a tela de abertura e a janela principal estejam fechadas
        if self.abertura:
            self.abertura.close()

        if self.janela_principal:
            self.janela_principal._forcar_fechamento = True
            self.janela_principal.close()
            self.janela_principal = None

        if not self.tarefa:
            self.app.setQuitOnLastWindowClosed(True)
            return

        try:
            if self._caminho_croqui_local is not None:
                self.mostrar_janela_principal()
                return

            usuario = self.tarefa.sessao_usuario.nome_completo if self.tarefa.sessao_usuario else ""
            tela_carregamento_cls = sys.modules[__name__].TelaDeCarregamento
            self.tela_carregamento = tela_carregamento_cls(
                self.tarefa.storage,
                usuario=usuario,
                servidor_mcp=self.servidor_mcp,
                diretorio_sessao_mcp=self._diretorio_sessao_mcp,
            )

            if hasattr(self.tela_carregamento, "garantir_servidor_mcp"):
                srv = self.tela_carregamento.garantir_servidor_mcp(
                    iniciar_rede=self._iniciar_rede_mcp
                )
                if srv is not None and hasattr(srv, "parar"):
                    self.servidor_mcp = srv

            self.tela_carregamento.solicitar_logout.connect(self.ao_solicitar_logout)

            resultado = self.tela_carregamento.exec()
            print(f"📋 [Main] TelaDeCarregamento finalizou com resultado: {resultado}")
            if resultado == QDialog.DialogCode.Accepted:
                self.mostrar_janela_principal()
            elif self._logout_em_andamento:
                self._logout_em_andamento = False
                self.app.setQuitOnLastWindowClosed(True)
            else:
                # Se cancelar na tela de seleção, sai do app
                print("👋 [Main] Aplicação encerrada pelo usuário a partir da TelaDeCarregamento.")
                self.encerrar_servidores_locais()
                self.app.setQuitOnLastWindowClosed(True)
                QApplication.quit()
        except Exception as erro:
            self._tratar_falha_fatal_transicao(erro, etapa="executar_selecao")

    def ao_solicitar_logout(self) -> None:
        """Reinicia a inicialização e exibe a Tela de Abertura para novo login."""
        self._logout_em_andamento = True
        self.iniciar_inicializacao()

    def mostrar_janela_principal(self) -> None:
        """
        Cria e exibe a Janela Principal do Editor.
        """
        self.app.setQuitOnLastWindowClosed(False)
        if self.janela_principal:
            self.janela_principal._forcar_fechamento = True
            self.janela_principal.close()
            self.janela_principal = None

        try:
            from editor.core.workspace import ExperimentalWorkspace, LocalRepoWorkspace
            from editor.legacy_views.area_principal import JanelaPrincipal

            if self._caminho_croqui_local is not None and self.tarefa:
                workspace: Any = LocalRepoWorkspace(self._caminho_croqui_local)
            else:
                if (
                    not self.tela_carregamento
                    or not self.tela_carregamento.caminho_croqui_selecionado
                    or not self.tarefa
                ):
                    self.app.setQuitOnLastWindowClosed(True)
                    return
                workspace = ExperimentalWorkspace(self.tela_carregamento.caminho_croqui_selecionado)

            self.janela_principal = JanelaPrincipal(
                storage=self.tarefa.storage,
                auth=getattr(self.tarefa, "gerenciador_sessao", None),
                workspace=workspace,
                iniciar_rede_mcp=self._iniciar_rede_mcp,
                diretorio_sessao_mcp=self._diretorio_sessao_mcp,
                servidor_mcp=self.servidor_mcp,
                callback_abrir_croqui_mcp=self.abrir_croqui_via_mcp,
                servico_submissao=self._servico_submissao,
                fabrica_servidor_celular=self._fabrica_servidor_celular,
                servico_loja=self._servico_loja,
            )
            if getattr(self.janela_principal, "servidor_mcp", None) is not None:
                self.servidor_mcp = self.janela_principal.servidor_mcp
            # Conecta o sinal para permitir voltar para a seleção
            self.janela_principal.solicitar_abrir_novo.connect(self.executar_selecao)
            self.janela_principal.show()
            self.app.setQuitOnLastWindowClosed(True)
        except Exception as erro:
            self._tratar_falha_fatal_transicao(erro, etapa="mostrar_janela_principal")

    def abrir_croqui_via_mcp(
        self, caminho_croqui: Path, iniciar_rede_mcp_janela: bool = True
    ) -> dict[str, Any]:
        """
        Abre um croqui solicitado via ferramenta MCP:
        - Se não houver janela principal aberta, abre na janela principal atual.
        - Se já houver uma janela principal com outro croqui aberto, instancia uma nova janela independente.
        """
        from editor.core.workspace import ExperimentalWorkspace
        from editor.legacy_views.area_principal import JanelaPrincipal

        storage = self.tarefa.storage if self.tarefa else None
        auth = getattr(self.tarefa, "gerenciador_sessao", None) if self.tarefa else None
        workspace = ExperimentalWorkspace(caminho_croqui)

        if self.janela_principal is None:
            self.app.setQuitOnLastWindowClosed(False)
            if self.tela_carregamento is not None:
                self.tela_carregamento.caminho_croqui_selecionado = caminho_croqui
                self.tela_carregamento.accept()
            if self.janela_principal is None:
                self.janela_principal = JanelaPrincipal(
                    storage=storage,
                    auth=auth,
                    workspace=workspace,
                    iniciar_rede_mcp=iniciar_rede_mcp_janela,
                    diretorio_sessao_mcp=self._diretorio_sessao_mcp,
                    servidor_mcp=self.servidor_mcp if iniciar_rede_mcp_janela else None,
                    callback_abrir_croqui_mcp=self.abrir_croqui_via_mcp,
                    servico_submissao=self._servico_submissao,
                    fabrica_servidor_celular=self._fabrica_servidor_celular,
                    servico_loja=self._servico_loja,
                )
                self.janela_principal.solicitar_abrir_novo.connect(self.executar_selecao)
                self.janela_principal.show()
            self.app.setQuitOnLastWindowClosed(True)
            return {"janela_aberta": True, "nova_janela": False}

        nova_janela = JanelaPrincipal(
            storage=storage,
            auth=auth,
            workspace=workspace,
            iniciar_rede_mcp=iniciar_rede_mcp_janela,
            diretorio_sessao_mcp=self._diretorio_sessao_mcp,
            callback_abrir_croqui_mcp=self.abrir_croqui_via_mcp,
            servico_submissao=self._servico_submissao,
            fabrica_servidor_celular=self._fabrica_servidor_celular,
            servico_loja=self._servico_loja,
        )
        self.janelas_secundarias.append(nova_janela)
        nova_janela.show()
        return {"janela_aberta": True, "nova_janela": True}

    def encerrar_servidor_mcp(self) -> None:
        """Encerra o servidor MCP primário compartilhado da aplicação."""
        srv_carregamento = getattr(self.tela_carregamento, "servidor_mcp", None)
        if (
            srv_carregamento is not None
            and srv_carregamento is not self.servidor_mcp
            and hasattr(srv_carregamento, "parar")
        ):
            srv_carregamento.parar()
        if self.servidor_mcp is not None and hasattr(self.servidor_mcp, "parar"):
            self.servidor_mcp.parar()
            self.servidor_mcp = None

    def encerrar_servidores_locais(self) -> None:
        """Encerra o servidor MCP e libera o QLocalServer de instância única se presente."""
        self.encerrar_servidor_mcp()
        servidor_local = getattr(self.app, "servidor_local", None)
        if servidor_local is not None and hasattr(servidor_local, "close"):
            servidor_local.close()
            setattr(self.app, "servidor_local", None)

    def _tratar_falha_fatal_transicao(self, erro: Exception, etapa: str) -> None:
        """
        Captura falhas inesperadas ocorridas após o fechamento da TelaDeAbertura,
        envia ao Sentry, fecha servidores locais e encerra o app exibindo erro visível.
        """
        import traceback

        from editor.core.telemetria import capturar_excecao

        traceback.print_exc(file=sys.stderr)
        capturar_excecao(erro, etapa=etapa, nivel_severidade="fatal")
        self.encerrar_servidores_locais()
        self.app.setQuitOnLastWindowClosed(True)
        self.mostrar_erro(f"Falha crítica ao iniciar o Editor ({etapa}):\n{erro}")

    def mostrar_erro(self, mensagem: str) -> None:
        if self.abertura:
            self.abertura.hide()
        if self._modo_smoke_test:
            print(f"🚨 [SmokeTest] {mensagem}", file=sys.stderr)
            dir_env = os.environ.get("ARESTA_DIRETORIO_DADOS", "").strip()
            if dir_env:
                (Path(dir_env) / ".smoke_test_erro.log").write_text(mensagem, encoding="utf-8")
            if self.abertura:
                self.abertura.close()
            self.encerrar_servidores_locais()
            self.app.exit(1)
            return
        QMessageBox.critical(None, "Erro de Inicialização", mensagem)
        if self.abertura:
            self.abertura.close()
        QApplication.quit()

    def executar(self) -> int:
        return int(self.app.exec())


def _validar_dependencias_internas_smoke() -> dict[str, Any]:
    """
    Valida em tempo de execução dentro do interpretador empacotado que todas as extensões
    C/C++/Rust críticas do Editor importam e executam suas operações base sem erro.
    """
    import brotli  # type: ignore[import-untyped]
    import pillow_heif
    import pymupdf as _pymupdf
    import zstandard
    from ddgs import DDGS
    from lxml import html as lxml_html

    from editor.core.serializacao_util import carregar_yaml, serializar_yaml

    pymupdf_mod: Any = _pymupdf
    _ = (pillow_heif.__name__, DDGS.__name__)
    doc = pymupdf_mod.open()
    pagina = doc.new_page(width=120, height=80)
    _ = pagina.rect
    doc.close()

    arvore_html = lxml_html.fromstring(
        '<html><body><div class="algo-sr"><a href="https://arestaclimb.com/v">Beta</a></div></body></html>'
    )
    links = arvore_html.xpath('//div[@class="algo-sr"]/a/@href')
    assert links == ["https://arestaclimb.com/v"]

    amostra = b"aresta-smoke-test"
    assert (
        zstandard.ZstdDecompressor().decompress(zstandard.ZstdCompressor().compress(amostra))
        == amostra
    )
    assert brotli.decompress(brotli.compress(amostra)) == amostra
    assert carregar_yaml(serializar_yaml({"ok": True})) == {"ok": True}

    return {
        "status": "ok",
        "modulos_verificados": [
            "pymupdf",
            "ddgs",
            "lxml",
            "pillow_heif",
            "zstandard",
            "brotli",
            "libyaml",
        ],
    }


def _instalar_condutor_smoke_test(
    controlador: ControladorAplicativo,
    timeout_segundos: float = 40.0,
) -> Any:
    """
    Instala um temporizador não-bloqueante para conduzir o login OTP na TelaDeAbertura
    e aguardar o sinal de conclusão do orquestrador externo durante --smoke-test.
    """
    import json
    import time

    from PySide6.QtCore import QTimer

    from editor.core.storage import GerenciadorCaminhos

    controlador._modo_smoke_test = True
    if controlador.tarefa is not None and hasattr(controlador.tarefa, "intervalo_espera_cofre"):
        controlador.tarefa.intervalo_espera_cofre = 0.0

    dir_env = os.environ.get("ARESTA_DIRETORIO_DADOS", "").strip()
    dir_dados = Path(dir_env) if dir_env else GerenciadorCaminhos().obter_diretorio_base()
    prazo = time.monotonic() + timeout_segundos
    estado = {"otp_solicitado": False, "otp_validado": False, "concluido": False}

    timer = QTimer(controlador.app)
    timer.setInterval(25)

    def _pulso() -> None:
        if time.monotonic() > prazo:
            estado["concluido"] = True
            timer.stop()
            print("🚨 [SmokeTest] Tempo limite excedido.", file=sys.stderr)
            controlador.encerrar_servidores_locais()
            controlador.app.exit(2)
            return

        modal = QApplication.activeModalWidget()
        if isinstance(modal, QMessageBox):
            estado["concluido"] = True
            timer.stop()
            print(f"🚨 [SmokeTest] QMessageBox inesperado: {modal.text()}", file=sys.stderr)
            modal.reject()
            controlador.encerrar_servidores_locais()
            controlador.app.exit(1)
            return

        abertura = controlador.abertura
        if (
            not estado["otp_solicitado"]
            and abertura is not None
            and abertura.isVisible()
            and abertura.auth_container.isVisible()
            and abertura.container_auth_selecao.isVisible()
        ):
            estado["otp_solicitado"] = True
            abertura.mostrar_formulario_email()
            abertura.edit_email.setText("smoke@arestaclimb.com")
            abertura.solicitar_otp()
            return

        if (
            not estado["otp_validado"]
            and abertura is not None
            and abertura.isVisible()
            and abertura.container_auth_codigo.isVisible()
            and abertura.btn_validar_codigo.isEnabled()
        ):
            estado["otp_validado"] = True
            abertura.edit_codigo.setText("123456")
            abertura.validar_otp()
            return

        if (
            controlador.janela_principal is not None
            and (dir_dados / ".encerrar_smoke_test").is_file()
        ):
            estado["concluido"] = True
            timer.stop()
            relatorio = _validar_dependencias_internas_smoke()
            (dir_dados / ".smoke_test_concluido.json").write_text(
                json.dumps(relatorio, ensure_ascii=False),
                encoding="utf-8",
            )
            controlador.janela_principal._forcar_fechamento = True
            controlador.janela_principal.close()
            controlador.encerrar_servidores_locais()
            controlador.app.quit()

    timer.timeout.connect(_pulso)
    timer.start()
    return timer


def main() -> None:
    configurar_streams_utf8()
    modo_smoke_test = "--smoke-test" in sys.argv[1:]
    argumentos_posicionais = [arg for arg in sys.argv[1:] if arg != "--smoke-test"]

    # Inicializa telemetria Sentry com sanitização universal de dados
    from editor.core.telemetria import inicializar_telemetria

    inicializar_telemetria()

    # Garante a instância global do QApplication
    inst = QApplication.instance()
    app: QApplication = inst if isinstance(inst, QApplication) else QApplication(sys.argv)
    from editor.core.configuracao_canal import obter_configuracao_canal

    config_canal = obter_configuracao_canal()
    app.setApplicationName(config_canal.nome_aplicativo)
    configurar_tema_claro_aplicacao(app)

    caminho_icone_app = config_canal.obter_caminho_icone_aplicacao()
    app.setWindowIcon(QIcon(str(caminho_icone_app)))
    app.processEvents()

    # Previne múltiplas instâncias do editor usando QLocalServer / QLocalSocket
    # com health-check ativo e recuperação de processos zumbis
    from editor.core.instancia_unica import (
        NOME_SERVIDOR_PADRAO,
        iniciar_servidor_instancia_unica,
        verificar_se_ja_em_execucao,
    )

    nome_servidor = (
        f"{NOME_SERVIDOR_PADRAO}_Smoke_{os.getpid()}" if modo_smoke_test else NOME_SERVIDOR_PADRAO
    )

    if verificar_se_ja_em_execucao(nome_servidor):
        msg = (
            "O Aresta Editor já está em execução. A janela ativa foi trazida para o primeiro plano."
        )
        print(msg, file=sys.stderr)
        QMessageBox.information(None, "Aresta Editor", msg)
        sys.exit(0)

    servidor_local = iniciar_servidor_instancia_unica(nome_servidor)
    if servidor_local:
        setattr(app, "servidor_local", servidor_local)

    # Verificação de modo LocalRepo: argumento fornecido na linha de comando
    caminho_croqui_local: Path | None = None
    if argumentos_posicionais:
        caminho_str = argumentos_posicionais[0]
        caminho_path = Path(caminho_str).resolve()

        # Se apontar diretamente para o arquivo croqui.yaml, obtém a pasta pai
        if caminho_path.is_file() and caminho_path.name == "croqui.yaml":
            caminho_path = caminho_path.parent

        if caminho_path.is_dir() and (caminho_path / "croqui.yaml").exists():
            caminho_croqui_local = caminho_path
        elif "database" in caminho_str or caminho_str.endswith("croqui.yaml"):
            msg_erro = (
                f"Erro: O caminho especificado '{caminho_str}' não contém um croqui.yaml válido."
            )
            print(msg_erro, file=sys.stderr)
            QMessageBox.critical(None, "Erro ao Abrir Croqui", msg_erro)
            sys.exit(1)

    # Inicialização Unificada (com Autenticação; sincronização Git apenas no modo padrão)
    controlador = (
        ControladorAplicativo(caminho_croqui_local=caminho_croqui_local)
        if caminho_croqui_local is not None
        else ControladorAplicativo()
    )
    if modo_smoke_test:
        _instalar_condutor_smoke_test(controlador)
    sys.exit(controlador.executar())


if __name__ == "__main__":  # pragma: no cover
    main()
