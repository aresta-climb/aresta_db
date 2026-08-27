# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import shutil
import uuid
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QUndoStack, QUndoCommand

class GerenciadorHistorico(QObject):
    """
    Gerenciador global da pilha de desfazer/refazer (Undo/Redo) do Editor Aresta.
    Utiliza o QUndoStack do PyQt6 sob o capô para manter o histórico unificado
    e emite sinais reativos para sincronização eficiente da UI.
    """
    sinal_campo_alterado = pyqtSignal(object, str, object)  # id_msg, campo, novo_valor
    sinal_item_adicionado = pyqtSignal(object, str, int)    # id_msg, campo, indice
    sinal_item_removido = pyqtSignal(object, str, int)      # id_msg, campo, indice
    sinal_foco_requisitado = pyqtSignal(str)                # contexto_ui

    def __init__(self, parent=None, diario=None):
        super().__init__(parent)
        self._pilha = QUndoStack(self)
        self._ultimo_index = 0
        self._diario = diario
        self._gravacao_pausada = False
        self._pilha.indexChanged.connect(self._on_index_changed)

    def definir_gerenciador_diario(self, diario):
        """Configura o GerenciadorDiario associado para persistência append-only."""
        self._diario = diario

    def obter_gerenciador_diario(self):
        """Retorna o GerenciadorDiario associado, se houver."""
        return self._diario

    def obter_pilha(self) -> QUndoStack:
        """Retorna a pilha interna do QUndoStack."""
        return self._pilha

    def executar(self, comando: QUndoCommand):
        """Executa um comando e o empilha no histórico, persistindo no diário se ativo."""
        if self._diario and not self._gravacao_pausada:
            try:
                self._diario.gravar_comando_pendente(comando)
            except Exception:
                pass
        self._pilha.push(comando)

    def restaurar_do_diario(self, model, diario) -> int:
        """
        Reconstrói o estado do modelo e popula a QUndoStack a partir do diário pendente.
        Retorna o número de comandos restaurados com sucesso.
        """
        from editor.commands.comandos_protobuf import deserializar_comando
        comandos_dados = diario.ler_diario_pendente()
        if not comandos_dados:
            self.definir_gerenciador_diario(diario)
            return 0

        self.limpar()
        self._gravacao_pausada = True
        total_restaurados = 0
        try:
            for cmd_dict in comandos_dados:
                try:
                    cmd = deserializar_comando(cmd_dict, model)
                    self.executar(cmd)
                    total_restaurados += 1
                except Exception:
                    # Se um comando falhar ao ser reconstruído, continua com os anteriores
                    break
        finally:
            self._gravacao_pausada = False
            self.definir_gerenciador_diario(diario)
        return total_restaurados

    def desfazer(self):
        """Desfaz o último comando empilhado."""
        if self._pilha.canUndo():
            self._pilha.undo()

    def refazer(self):
        """Refaz o próximo comando na pilha."""
        if self._pilha.canRedo():
            self._pilha.redo()

    def limpar(self):
        """Limpa o histórico atual."""
        self._pilha.clear()
        self._ultimo_index = 0

    def _on_index_changed(self, novo_index):
        diff = novo_index - self._ultimo_index
        if diff == 0:
            return

        try:
            if diff > 0:
                # Redo ou Push: o comando executado está no índice anterior
                cmd = self._pilha.command(novo_index - 1)
                self._despachar_sinal(cmd, is_undo=False)
            else:
                # Undo: o comando desfeito está no índice atual (onde a pilha estava antes)
                cmd = self._pilha.command(novo_index)
                self._despachar_sinal(cmd, is_undo=True)
        except RuntimeError:
            # O objeto C++ QUndoStack pode já ter sido deletado se a aplicação estiver fechando
            pass
        finally:
            self._ultimo_index = novo_index

    def _despachar_sinal(self, cmd, is_undo: bool):
        from editor.commands.comandos_protobuf import (
            CmdAlterarPrimitivo,
            CmdAdicionarRepeated,
            CmdRemoverRepeated,
            CmdAlterarOneof,
            CmdAlterarRepeatedItem,
            CmdAlterarMultiplosRepeatedItems
        )

        if not cmd:
            return

        if hasattr(cmd, 'contexto_ui') and cmd.contexto_ui:
            self.sinal_foco_requisitado.emit(cmd.contexto_ui)

        if cmd.childCount() > 0:
            for i in range(cmd.childCount()):
                self._despachar_sinal(cmd.child(i), is_undo)
            return

        if isinstance(cmd, CmdAlterarPrimitivo):
            valor = cmd.valor_antigo if is_undo else cmd.valor_novo
            self.sinal_campo_alterado.emit(id(cmd.msg), cmd.campo_nome, valor)

        elif isinstance(cmd, CmdAdicionarRepeated):
            if is_undo:
                self.sinal_item_removido.emit(id(cmd.msg), cmd.campo_nome, cmd.index)
            else:
                self.sinal_item_adicionado.emit(id(cmd.msg), cmd.campo_nome, cmd.index)

        elif isinstance(cmd, CmdRemoverRepeated):
            if is_undo:
                self.sinal_item_adicionado.emit(id(cmd.msg), cmd.campo_nome, cmd.index)
            else:
                self.sinal_item_removido.emit(id(cmd.msg), cmd.campo_nome, cmd.index)

        elif isinstance(cmd, CmdAlterarRepeatedItem):
            valor = cmd.valor_antigo if is_undo else cmd.valor_novo
            chave = f"{cmd.campo_nome}[{cmd.index}]"
            self.sinal_campo_alterado.emit(id(cmd.msg), chave, valor)

        elif isinstance(cmd, CmdAlterarMultiplosRepeatedItems):
            # Para múltiplos itens, emitimos o sinal de alteração no nome do campo repetido (apenas informativo)
            self.sinal_campo_alterado.emit(id(cmd.msg), cmd.campo_nome, cmd.alteracoes)

        elif isinstance(cmd, CmdAlterarOneof):
            valor = cmd.nome_antigo if is_undo else cmd.nome_novo
            self.sinal_campo_alterado.emit(id(cmd.msg), cmd.oneof_nome, valor)



class CmdRemoverArquivoFisico(QUndoCommand):
    """
    Comando para remoção de arquivo físico com suporte a desfazer/refazer.
    Move o arquivo para a lixeira interna temporária em vez de removê-lo em definitivo.
    """
    def __init__(self, caminho_arquivo, gerenciador_caminhos, parent=None):
        super().__init__(parent)
        self._caminho_arquivo = Path(caminho_arquivo)
        self._gerenciador = gerenciador_caminhos
        self._caminho_lixeira = None

    def undo(self):
        """Restaura o arquivo da lixeira interna para o caminho original."""
        if self._caminho_lixeira and self._caminho_lixeira.exists():
            # Garante que a pasta pai original exista
            self._caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(self._caminho_lixeira), str(self._caminho_arquivo))
            self._caminho_lixeira = None

    def redo(self):
        """Move o arquivo para a lixeira interna."""
        if self._caminho_arquivo.exists():
            lixeira_dir = self._gerenciador.obter_caminho_lixeira()
            lixeira_dir.mkdir(parents=True, exist_ok=True)
            
            # Gera um nome único para evitar colisões
            id_unico = uuid.uuid4().hex
            nome_arquivo_lixeira = f"{id_unico}_{self._caminho_arquivo.name}"
            self._caminho_lixeira = lixeira_dir / nome_arquivo_lixeira
            
            shutil.move(str(self._caminho_arquivo), str(self._caminho_lixeira))

    def __del__(self):
        # Se o objeto do comando for destruído e o arquivo ainda estiver na lixeira,
        # removemos em definitivo para evitar lixo em disco.
        try:
            if self._caminho_lixeira and self._caminho_lixeira.exists():
                self._caminho_lixeira.unlink()
        except Exception:
            pass
