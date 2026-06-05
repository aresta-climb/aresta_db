from PyQt6.QtGui import QUndoStack
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAlterarPrimitivo,
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarOneof,
    CmdAlterarRepeatedItem,
    CmdMoverRepeated
)

class CroquiController:
    """
    Controlador da Arquitetura MVC.
    Recebe as intenções da View e orquestra a mutação do Model
    através da criação de Comandos despachados para a QUndoStack.
    """
    def __init__(self, model: CroquiModel, undo_stack: QUndoStack):
        self.model = model
        self.undo_stack = undo_stack
        self.contexto_atual_path = None

    def set_contexto(self, path):
        self.contexto_atual_path = path

    def alterar_primitivo(self, msg, campo_nome, valor_antigo, valor_novo):
        cmd = CmdAlterarPrimitivo(self.model, msg, campo_nome, valor_antigo, valor_novo, self.contexto_atual_path)
        self.undo_stack.push(cmd)

    def adicionar_repeated(self, msg, campo_nome, index, valor):
        cmd = CmdAdicionarRepeated(self.model, msg, campo_nome, index, valor, self.contexto_atual_path)
        self.undo_stack.push(cmd)

    def remover_repeated(self, msg, campo_nome, index, valor_removido):
        cmd = CmdRemoverRepeated(self.model, msg, campo_nome, index, valor_removido)
        self.undo_stack.push(cmd)

    def alterar_repeated_item(self, msg, campo_nome, index, valor_antigo, valor_novo):
        cmd = CmdAlterarRepeatedItem(self.model, msg, campo_nome, index, valor_antigo, valor_novo, self.contexto_atual_path)
        self.undo_stack.push(cmd)

    def alterar_oneof(self, msg, oneof_nome, nome_antigo, valor_antigo, campo_novo, valor_novo):
        """Despacha intenção de alterar um campo do tipo Oneof."""
        comando = CmdAlterarOneof(self.model, msg, oneof_nome, nome_antigo, valor_antigo, campo_novo, valor_novo)
        self.undo_stack.push(comando)

    def mover_repeated_para_cima(self, msg, campo_nome, index):
        """Move o item do index fornecido uma posição para cima."""
        if index <= 0:
            return
            
        cmd = CmdMoverRepeated(self.model, msg, campo_nome, index, index - 1)
        self.undo_stack.push(cmd)

    def mover_repeated_para_baixo(self, msg, campo_nome, index):
        """Move o item do index fornecido uma posição para baixo."""
        tamanho = len(getattr(msg, campo_nome))
        if index >= tamanho - 1:
            return
            
        cmd = CmdMoverRepeated(self.model, msg, campo_nome, index, index + 1)
        self.undo_stack.push(cmd)

    def alterar_metadados_caminho_novo(self, msg, field_ext, valor_antigo, valor_novo):
        from editor.commands.comandos_protobuf import CmdAlterarMetadadosCaminhoNovo
        cmd = CmdAlterarMetadadosCaminhoNovo(self.model, msg, field_ext, valor_antigo, valor_novo, self.contexto_atual_path)
        self.undo_stack.push(cmd)
