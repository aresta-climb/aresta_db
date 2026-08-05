# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

from PyQt6.QtGui import QUndoCommand
import os
from editor.models.readonly_proxy import _copia_segura

class CmdAdicionarMapaArquivo(QUndoCommand):
    """
    Comando para adicionar um Mapa no Protobuf e criar seu arquivo correspondente no disco simultaneamente.
    """
    def __init__(self, model, msg, campo_nome, index, valor, caminho_absoluto, img_bytes, context_path=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.msg = msg
        self.campo_nome = campo_nome
        self.index = index
        self.valor = _copia_segura(valor)
        self.caminho_absoluto = caminho_absoluto
        self.img_bytes = img_bytes
        self.context_path = context_path

    def undo(self):
        # 1. Remove do modelo
        self.model._remover_repeated(self.msg, self.campo_nome, self.index)
        
        # 2. Deleta o arquivo se ele existir
        if self.caminho_absoluto.exists():
            try:
                os.remove(self.caminho_absoluto)
            except Exception as e:
                print(f"Erro ao remover arquivo no undo: {e}")

        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def redo(self):
        # 1. Garante que a pasta existe e escreve o arquivo
        self.caminho_absoluto.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.caminho_absoluto, 'wb') as f:
                f.write(self.img_bytes)
        except Exception as e:
            print(f"Erro ao criar arquivo no redo: {e}")
            
        # 2. Adiciona ao modelo
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor)
        
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)
