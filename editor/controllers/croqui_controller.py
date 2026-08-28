# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PyQt6.QtGui import QUndoStack
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAlterarPrimitivo,
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarOneof,
    CmdAlterarRepeatedItem,
    CmdMoverRepeated,
    CmdAlterarCampoImagem
)

class CroquiController:
    """
    Controlador da Arquitetura MVC.
    Recebe as intenções da View e orquestra a mutação do Model
    através da criação de Comandos despachados para o histórico/QUndoStack.
    """
    def __init__(self, model: CroquiModel, undo_stack):
        self.model = model
        self.undo_stack = undo_stack
        self.contexto_atual_path = None

    def set_contexto(self, path):
        self.contexto_atual_path = path

    def _executar_comando(self, cmd):
        """Despacha o comando pelo GerenciadorHistorico (persistindo no diário) ou diretamente na pilha."""
        if hasattr(self.undo_stack, "executar"):
            self.undo_stack.executar(cmd)
        elif hasattr(self.undo_stack, "push"):
            self.undo_stack.push(cmd)

    def alterar_primitivo(self, msg, campo_nome, valor_antigo, valor_novo, pode_mesclar: bool = False):
        cmd = CmdAlterarPrimitivo(self.model, msg, campo_nome, valor_antigo, valor_novo, self.contexto_atual_path, pode_mesclar=pode_mesclar)
        self._executar_comando(cmd)

    def alterar_campo_imagem(self, msg, campo_nome, caminho_antigo, bytes_antigo, caminho_novo, bytes_novo):
        """Despacha comando de alteração de imagem com gerenciamento em RAM."""
        cmd = CmdAlterarCampoImagem(
            self.model, msg, campo_nome, caminho_antigo, bytes_antigo, caminho_novo, bytes_novo, self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def adicionar_repeated(self, msg, campo_nome, index, valor):
        cmd = CmdAdicionarRepeated(self.model, msg, campo_nome, index, valor, self.contexto_atual_path)
        self._executar_comando(cmd)

    def remover_repeated(self, msg, campo_nome, index, valor_removido):
        cmd = CmdRemoverRepeated(self.model, msg, campo_nome, index, valor_removido)
        self._executar_comando(cmd)

    def alterar_repeated_item(self, msg, campo_nome, index, valor_antigo, valor_novo, pode_mesclar: bool = False):
        cmd = CmdAlterarRepeatedItem(self.model, msg, campo_nome, index, valor_antigo, valor_novo, self.contexto_atual_path, pode_mesclar=pode_mesclar)
        self._executar_comando(cmd)

    def alterar_oneof(self, msg, oneof_nome, nome_antigo, valor_antigo, campo_novo, valor_novo):
        """Despacha intenção de alterar um campo do tipo Oneof."""
        comando = CmdAlterarOneof(self.model, msg, oneof_nome, nome_antigo, valor_antigo, campo_novo, valor_novo)
        self._executar_comando(comando)

    def mover_repeated_para_cima(self, msg, campo_nome, index):
        """Move o item do index fornecido uma posição para cima."""
        if index <= 0:
            return
            
        cmd = CmdMoverRepeated(self.model, msg, campo_nome, index, index - 1)
        self._executar_comando(cmd)

    def mover_repeated_para_baixo(self, msg, campo_nome, index):
        """Move o item do index fornecido uma posição para baixo."""
        tamanho = len(getattr(msg, campo_nome))
        if index >= tamanho - 1:
            return
            
        cmd = CmdMoverRepeated(self.model, msg, campo_nome, index, index + 1)
        self._executar_comando(cmd)

    def alterar_metadados_caminho_novo(self, msg, field_ext, valor_antigo, valor_novo):
        from editor.commands.comandos_protobuf import CmdAlterarMetadadosCaminhoNovo
        cmd = CmdAlterarMetadadosCaminhoNovo(self.model, msg, field_ext, valor_antigo, valor_novo, self.contexto_atual_path)
        self._executar_comando(cmd)

    def adicionar_mapa_com_arquivo(self, msg, campo_nome, index, valor, caminho_absoluto, img_bytes):
        from editor.commands.comandos_mapas import CmdAdicionarMapaArquivo
        cmd = CmdAdicionarMapaArquivo(self.model, msg, campo_nome, index, valor, caminho_absoluto, img_bytes, self.contexto_atual_path)
        self._executar_comando(cmd)

    def substituir_imagem(self, caminho_relativo: str, bytes_novo: bytes, bytes_antigo: bytes | None = None, context_path: str | None = None):
        """Despacha comando de substituição de imagem em memória RAM."""
        from editor.commands.comandos_protobuf import CmdSubstituirImagemMemoria
        if bytes_antigo is None:
            bytes_antigo = self.model.obter_bytes_imagem(caminho_relativo)
        ctx = context_path if context_path is not None else self.contexto_atual_path
        cmd = CmdSubstituirImagemMemoria(self.model, caminho_relativo, bytes_antigo, bytes_novo, ctx)
        self._executar_comando(cmd)
