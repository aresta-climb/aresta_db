# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from PyQt6.QtGui import QUndoCommand
from pathlib import Path
from editor.models.readonly_proxy import _copia_segura
from editor.commands.comandos_protobuf import (
    ComandoEditor,
    resolver_caminho_mensagem,
    navegar_para_mensagem,
    _serializar_valor,
    _deserializar_valor,
)


class CmdAdicionarMapaArquivo(ComandoEditor):
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

    def executar_redo(self):
        # 1. Registra imagem no buffer de RAM
        if self.caminho_relativo and self.img_bytes:
            self.model.definir_imagem_memoria(self.caminho_relativo, self.img_bytes)
        # 2. Adiciona ao modelo
        self.model._adicionar_repeated(self.msg, self.campo_nome, self.index, self.valor)
        
        if hasattr(self, 'context_path') and self.context_path:
            self.model.notificar_foco_requisitado(self.context_path)

    def serializar(self, anonimizado: bool = False) -> dict:
        img_bytes = self.img_bytes
        caminho_abs_str = str(self.caminho_absoluto) if self.caminho_absoluto else ""
        if anonimizado:
            from editor.core.imagem_anonimizada import gerar_webp_anonimizado
            img_bytes = gerar_webp_anonimizado(self.img_bytes)
            caminho_abs_str = "[ARQUIVO_MAPA_ANONIMIZADO]"
            
        return {
            "classe": "CmdAdicionarMapaArquivo",
            "caminho_msg": resolver_caminho_mensagem(self.model.obter_croqui_readonly(), self.msg),
            "campo_nome": self.campo_nome,
            "index": self.index,
            "valor": _serializar_valor(self.valor, anonimizado=anonimizado),
            "caminho_absoluto": caminho_abs_str,
            "img_bytes": img_bytes,
            "context_path": self.context_path
        }

    @staticmethod
    def deserializar(dados: dict, model) -> "CmdAdicionarMapaArquivo":
        msg = navegar_para_mensagem(model.obter_croqui_readonly(), dados.get("caminho_msg", ""))
        valor = _deserializar_valor(dados["valor"], model=model)
        caminho_abs = Path(dados["caminho_absoluto"]) if dados.get("caminho_absoluto") else None
        return CmdAdicionarMapaArquivo(
            model=model,
            msg=msg,
            campo_nome=dados["campo_nome"],
            index=dados["index"],
            valor=valor,
            caminho_absoluto=caminho_abs,
            img_bytes=dados.get("img_bytes"),
            context_path=dados.get("context_path")
        )
