from PyQt6.QtGui import QUndoCommand
from google.protobuf.message import Message
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import _copia_segura

class CmdAlterarPrimitivo(QUndoCommand):
    """Comando para alterar um campo primitivo de uma mensagem Protobuf via Model."""
    def __init__(self, model, msg, campo_nome, valor_antigo, valor_novo, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.valor_antigo = _copia_segura(valor_antigo)
        self.valor_novo = _copia_segura(valor_novo)
        self.context_path = context_path

    def undo(self):
        self.model._set_primitivo(self.msg, self.campo_nome, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._set_primitivo(self.msg, self.campo_nome, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)


class CmdAdicionarRepeated(QUndoCommand):
    """Comando para adicionar um item em um campo repeated via Model."""
    def __init__(self, model, msg, campo_nome, index, valor, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.index = index
        self.valor = _copia_segura(valor)
        self.context_path = context_path

    def undo(self):
        self.model._remover_repeated(self.msg, self.campo_nome, self.index)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)


class CmdRemoverRepeated(QUndoCommand):
    """Comando para remover um item de um campo repeated via Model."""
    def __init__(self, model, msg, campo_nome, index, valor_removido, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.index = index
        self.valor_removido = _copia_segura(valor_removido)
        self.context_path = context_path

    def undo(self):
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor_removido)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._remover_repeated(self.msg, self.campo_nome, self.index)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)


class CmdAlterarOneof(QUndoCommand):
    """Comando para alterar a escolha ativa de um campo oneof via Model."""
    def __init__(self, model, msg, oneof_nome, nome_antigo, valor_antigo, nome_novo, valor_novo, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.oneof_nome = oneof_nome
        self.nome_antigo = nome_antigo
        self.valor_antigo = _copia_segura(valor_antigo)
        self.nome_novo = nome_novo
        self.valor_novo = _copia_segura(valor_novo)
        self.context_path = context_path

    def undo(self):
        self.model._alterar_oneof(self.msg, self.oneof_nome, self.nome_novo, self.nome_antigo, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._alterar_oneof(self.msg, self.oneof_nome, self.nome_antigo, self.nome_novo, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)


class CmdAlterarRepeatedItem(QUndoCommand):
    """Comando para alterar um item específico em uma coleção repeated via Model."""
    def __init__(self, model, msg, campo_nome, index, valor_antigo, valor_novo, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.index = index
        self.valor_antigo = _copia_segura(valor_antigo)
        self.valor_novo = _copia_segura(valor_novo)
        self.context_path = context_path

    def undo(self):
        self.model._alterar_repeated_item(self.msg, self.campo_nome, self.index, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._alterar_repeated_item(self.msg, self.campo_nome, self.index, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)


class CmdAlterarMultiplosRepeatedItems(QUndoCommand):
    """Comando para alterar múltiplos itens em uma coleção repeated simultaneamente via Model."""
    def __init__(self, model, msg, campo_nome, alteracoes, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.alteracoes = []
        for index, valor_antigo, valor_novo in alteracoes:
            self.alteracoes.append((index, _copia_segura(valor_antigo), _copia_segura(valor_novo)))
        self.context_path = context_path
        self.setText(f"Alterados {len(self.alteracoes)} itens em {self.campo_nome}")

    def undo(self):
        # Desfazer na ordem normal (se não houver deleção, tanto faz, mas iteramos normal)
        for index, valor_antigo, _ in self.alteracoes:
            self.model._alterar_repeated_item(self.msg, self.campo_nome, index, valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        for index, _, valor_novo in self.alteracoes:
            self.model._alterar_repeated_item(self.msg, self.campo_nome, index, valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)


class CmdMoverRepeated(QUndoCommand):
    """Comando para mover um item de uma coleção repeated para outra posição via Model."""
    def __init__(self, model, msg, campo_nome, index_from, index_to, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.index_from = index_from
        self.index_to = index_to
        self.context_path = context_path

    def undo(self):
        self.model._mover_repeated(self.msg, self.campo_nome, self.index_to, self.index_from)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._mover_repeated(self.msg, self.campo_nome, self.index_from, self.index_to)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)




class CmdAlterarMetadadosCaminhoNovo(QUndoCommand):
    """Comando para alterar o sub-campo caminho_novo de uma extensão MetadadosArquivoNoEditor via Model."""
    def __init__(self, model, msg, field_ext, valor_antigo, valor_novo, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.field_ext = field_ext
        self.valor_antigo = _copia_segura(valor_antigo)
        self.valor_novo = _copia_segura(valor_novo)
        self.context_path = context_path

    def undo(self):
        self.model._alterar_metadados_caminho_novo(self.msg, self.field_ext, self.valor_antigo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        self.model._alterar_metadados_caminho_novo(self.msg, self.field_ext, self.valor_novo)
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)



