# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from PyQt6.QtGui import QUndoCommand
import os
from editor.models.readonly_proxy import _copia_segura

class CmdAdicionarMapaArquivo(QUndoCommand):
    """
    Comando para adicionar um Mapa no Protobuf e registrar sua imagem no buffer em memória RAM (CroquiModel).
    """
    def __init__(self, model, msg, campo_nome, index, valor, caminho_absoluto, img_bytes, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.index = index
        self.valor = _copia_segura(valor)
        self.caminho_absoluto = caminho_absoluto
        caminho_rel = str(valor.caminho_imagem_mapa) if hasattr(valor, "caminho_imagem_mapa") else str(caminho_absoluto)
        self.caminho_relativo = caminho_rel
        self.img_bytes = img_bytes
        self.context_path = context_path

    def undo(self):
        # 1. Remove do modelo
        self.model._remover_repeated(self.msg, self.campo_nome, self.index)
        # 2. Remove do buffer de RAM
        if self.caminho_relativo:
            self.model.remover_imagem_memoria(self.caminho_relativo)

        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        # 1. Registra imagem no buffer de RAM
        if self.caminho_relativo and self.img_bytes:
            self.model.definir_imagem_memoria(self.caminho_relativo, self.img_bytes)
        # 2. Adiciona ao modelo
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor)
        
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)
