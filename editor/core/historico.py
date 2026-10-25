# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from editor.core.registro_log import obter_logger
from editor.core.telemetria import anexar_diario_escopo, registrar_breadcrumb_comando

logger = obter_logger("historico")


class GerenciadorHistorico(QObject):
    """
    Gerenciador global da pilha de desfazer/refazer (Undo/Redo) do Editor Aresta.
    Utiliza o QUndoStack do PySide6 sob o capô para manter o histórico unificado
    e emite sinais reativos para sincronização eficiente da UI.
    """

    sinal_campo_alterado: Signal = Signal(object, str, object)  # id_msg, campo, novo_valor
    sinal_item_adicionado: Signal = Signal(object, str, int)  # id_msg, campo, indice
    sinal_item_removido: Signal = Signal(object, str, int)  # id_msg, campo, indice
    sinal_foco_requisitado: Signal = Signal(str)  # contexto_ui

    def __init__(self, parent: QObject | None = None, diario: Any = None) -> None:
        super().__init__(parent)
        self._pilha: QUndoStack = QUndoStack(self)
        self._ultimo_index: int = 0
        self._diario: Any = diario
        self._gravacao_pausada: bool = False
        self.intervalo_debounce_ms: int = 300
        self._timer_sincronizacao: QTimer = QTimer(self)
        self._timer_sincronizacao.setSingleShot(True)
        self._timer_sincronizacao.timeout.connect(self._sincronizar_diario_pendente_imediato)
        if self._diario and hasattr(self._diario, "_hook_flush"):
            self._diario._hook_flush = self.flush_diario_pendente
        self._pilha.indexChanged.connect(self._on_index_changed)

    def definir_gerenciador_diario(self, diario: Any) -> None:
        """Configura o GerenciadorDiario associado para persistência append-only."""
        self.flush_diario_pendente()
        if (
            self._diario
            and getattr(self._diario, "_hook_flush", None) == self.flush_diario_pendente
        ):
            self._diario._hook_flush = None
        self._diario = diario
        if self._diario and hasattr(self._diario, "_hook_flush"):
            self._diario._hook_flush = self.flush_diario_pendente

    def obter_gerenciador_diario(self) -> Any:
        """Retorna o GerenciadorDiario associado, se houver."""
        return self._diario

    def obter_pilha(self) -> QUndoStack:
        """Retorna a pilha interna do QUndoStack."""
        return self._pilha

    def executar(self, comando: QUndoCommand) -> None:
        """Executa um comando e o empilha no histórico, persistindo no diário se ativo."""
        count_antes = self._pilha.count()
        self._pilha.push(comando)
        count_depois = self._pilha.count()

        registrar_breadcrumb_comando(comando)

        if self._diario and not self._gravacao_pausada:
            # Se o comando foi mesclado pelo QUndoStack (a contagem não aumentou),
            # agenda a sincronização do diário pendente no disco com debounce para digitação fluida.
            if count_depois == count_antes and count_depois > 0:
                self._sincronizar_diario_pendente()
            else:
                self.flush_diario_pendente()
                self._diario.gravar_comando_pendente(comando)
                anexar_diario_escopo(self._diario)

    def _sincronizar_diario_pendente(self) -> None:
        """Agenda a sincronização do diário pendente no disco respeitando o debounce."""
        if not self._diario:
            return
        from PySide6.QtCore import QCoreApplication

        if self.intervalo_debounce_ms > 0 and QCoreApplication.instance() is not None:
            self._timer_sincronizacao.start(self.intervalo_debounce_ms)
        else:
            self._sincronizar_diario_pendente_imediato()

    def flush_diario_pendente(self) -> None:
        """Força a persistência imediata de quaisquer alterações pendentes agendadas via debounce."""
        if hasattr(self, "_timer_sincronizacao") and self._timer_sincronizacao.isActive():
            self._timer_sincronizacao.stop()
            self._sincronizar_diario_pendente_imediato()

    def _sincronizar_diario_pendente_imediato(self) -> None:
        """Reescreve diario_pendente.bin imediatamente com os comandos pendentes atualmente na pilha."""
        if not self._diario:
            return
        clean_idx = self._pilha.cleanIndex()
        start_idx = max(0, clean_idx) if clean_idx >= 0 else 0
        current_idx = self._pilha.index()
        comandos_pendentes = []
        for i in range(start_idx, current_idx):
            cmd = self._pilha.command(i)
            if cmd:
                comandos_pendentes.append(cmd)
        self._diario.substituir_comandos_pendentes(comandos_pendentes)
        anexar_diario_escopo(self._diario)

    def push(self, comando: QUndoCommand) -> None:
        """Atalho compatível com QUndoStack que executa e persiste no diário."""
        self.executar(comando)

    def __getattr__(self, name: str) -> Any:
        """Delega chamadas desconhecidas para a pilha interna QUndoStack."""
        return getattr(self._pilha, name)

    def carregar_diario_salvo(self, model: Any, diario: Any) -> int:
        """
        Popula a QUndoStack com os comandos de `diario_salvo.bin` de forma silenciosa e instantânea.

        Como o `croqui.yaml` lido do disco já se encontra no estado consolidado final pós-salvamento,
        não realizamos mutações redundantes no modelo Protobuf. Cada comando deserializado é armado
        com `armar_carregamento_silencioso()`. Quando o Qt invoca `redo()` internamente durante o `push()`,
        a mutação é ignorada e a flag é desarmada.

        Dessa forma, o boot é instantâneo e qualquer `undo()` (Ctrl+Z) subsequente funciona normalmente.

        Retorna o número de comandos salvos carregados na pilha.
        """
        from editor.commands.comandos_protobuf import deserializar_comando

        comandos_salvos = diario.ler_diario_salvo()
        if not comandos_salvos:
            return 0

        self.limpar()
        self._gravacao_pausada = True
        total_carregados = 0

        try:
            for cmd_dict in comandos_salvos:
                try:
                    cmd = deserializar_comando(cmd_dict, model)
                    if hasattr(cmd, "armar_carregamento_silencioso"):
                        cmd.armar_carregamento_silencioso()
                    else:
                        cmd._ignorar_primeiro_redo = True
                    self._pilha.push(cmd)

                    total_carregados += 1
                except (ValueError, AttributeError, LookupError, TypeError) as e:
                    logger.warning("Comando corrompido ou órfão descartado do diário salvo: %s", e)
                    continue
                except Exception as e:
                    logger.error("Erro inesperado ao deserializar comando salvo: %s", e)
                    continue
        finally:
            self._pilha.setClean()
            self._gravacao_pausada = False

        return total_carregados

    def restaurar_do_diario(self, model: Any, diario: Any) -> int:
        """
        Reconstrói o estado do modelo e popula a QUndoStack a partir do diário pendente.
        Retorna o número de comandos restaurados com sucesso.
        """
        from editor.commands.comandos_protobuf import deserializar_comando

        comandos_dados = diario.ler_diario_pendente()
        if not comandos_dados:
            self.definir_gerenciador_diario(diario)
            return 0

        self._gravacao_pausada = True
        total_restaurados = 0
        try:
            for cmd_dict in comandos_dados:
                try:
                    cmd = deserializar_comando(cmd_dict, model)
                    self._pilha.push(cmd)
                    total_restaurados += 1
                except (ValueError, AttributeError, LookupError, TypeError) as e:
                    logger.warning(
                        "Comando corrompido ou órfão descartado do diário pendente: %s", e
                    )
                    continue
                except Exception as e:
                    logger.error("Erro inesperado ao restaurar comando do diário pendente: %s", e)
                    continue
        finally:
            self._gravacao_pausada = False
            self.definir_gerenciador_diario(diario)
            self._sincronizar_diario_pendente_imediato()

        return total_restaurados

    def desfazer(self) -> None:
        """Desfaz o último comando empilhado."""
        if self._pilha.canUndo():
            self.flush_diario_pendente()
            self._pilha.undo()
            if self._diario and not self._gravacao_pausada:
                self._sincronizar_diario_pendente_imediato()

    def refazer(self) -> None:
        """Refaz o próximo comando na pilha."""
        if self._pilha.canRedo():
            self.flush_diario_pendente()
            self._pilha.redo()
            if self._diario and not self._gravacao_pausada:
                self._sincronizar_diario_pendente_imediato()

    def limpar(self) -> None:
        """Limpa o histórico atual."""
        if hasattr(self, "_timer_sincronizacao"):
            self._timer_sincronizacao.stop()
        self._pilha.clear()
        self._ultimo_index = 0

    def _on_index_changed(self, novo_index: int) -> None:
        diff = novo_index - self._ultimo_index
        if diff == 0:
            return

        if self._gravacao_pausada:
            self._ultimo_index = novo_index
            return

        if diff > 0:
            # Redo ou Push: o comando executado está no índice anterior
            cmd = self._pilha.command(novo_index - 1)
            self._despachar_sinal(cmd, is_undo=False)
        else:
            # Undo: o comando desfeito está no índice atual (onde a pilha estava antes)
            cmd = self._pilha.command(novo_index)
            self._despachar_sinal(cmd, is_undo=True)
        self._ultimo_index = novo_index

    def _despachar_sinal(self, cmd: QUndoCommand | None, is_undo: bool) -> None:
        from editor.commands.comandos_protobuf import (
            CmdAdicionarRepeated,
            CmdAlterarCampo,
            CmdRemoverRepeated,
            MensagemAlvoNaoEncontradaError,
        )

        if not cmd:
            return

        if hasattr(cmd, "contexto_ui") and cmd.contexto_ui:
            self.sinal_foco_requisitado.emit(cmd.contexto_ui)

        if cmd.childCount() > 0:
            for i in range(cmd.childCount()):
                self._despachar_sinal(cmd.child(i), is_undo)
            return

        if hasattr(cmd, "comandos") and cmd.comandos:
            sub_comandos = reversed(cmd.comandos) if is_undo else cmd.comandos
            for sub_cmd in sub_comandos:
                self._despachar_sinal(sub_cmd, is_undo)
            return

        def _obter_msg_segura(comando: Any) -> Any:
            try:
                obter_fn = getattr(comando, "_obter_msg", None)
                if callable(obter_fn):
                    return obter_fn(levantar_se_nao_encontrado=True)
                return getattr(comando, "msg", None)
            except (MensagemAlvoNaoEncontradaError, LookupError, AttributeError):
                return None

        if isinstance(cmd, CmdAlterarCampo):
            msg = _obter_msg_segura(cmd)
            if msg is None:
                return
            valor = cmd.valor_antigo if is_undo else cmd.valor_novo
            self.sinal_campo_alterado.emit(id(msg), cmd.campo_nome, valor)

        elif isinstance(cmd, CmdAdicionarRepeated):
            msg = _obter_msg_segura(cmd)
            if msg is None:
                return
            if is_undo:
                self.sinal_item_removido.emit(id(msg), cmd.campo_nome, cmd.index)
            else:
                self.sinal_item_adicionado.emit(id(msg), cmd.campo_nome, cmd.index)

        elif isinstance(cmd, CmdRemoverRepeated):
            msg = _obter_msg_segura(cmd)
            if msg is None:
                return
            if is_undo:
                self.sinal_item_adicionado.emit(id(msg), cmd.campo_nome, cmd.index)
            else:
                self.sinal_item_removido.emit(id(msg), cmd.campo_nome, cmd.index)
