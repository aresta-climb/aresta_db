# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Any
from PySide6.QtGui import QUndoStack
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAlterarPrimitivo,
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarOneof,
    CmdAlterarRepeatedItem,
    CmdMoverRepeated,
    CmdAlterarCampoImagem,
    CmdInserirImagemMarkdown,
)


class CroquiController:
    """
    Controlador da Arquitetura MVC.
    Recebe as intenções da View e orquestra a mutação do Model
    através da criação de Comandos despachados para o histórico/QUndoStack.
    """
    def __init__(self, model: CroquiModel, undo_stack: Any) -> None:
        self.model: CroquiModel = model
        self.undo_stack: Any = undo_stack
        self.contexto_atual_path: Optional[str] = None

    def set_contexto(self, path: Optional[str]) -> None:
        self.contexto_atual_path = path

    def _executar_comando(self, cmd: Any) -> None:
        """Despacha o comando pelo GerenciadorHistorico (persistindo no diário) ou diretamente na pilha."""
        if hasattr(self.undo_stack, "executar"):
            self.undo_stack.executar(cmd)
        elif hasattr(self.undo_stack, "push"):
            self.undo_stack.push(cmd)

    def _obter_comando_renomear_topo(self, session_id: Optional[int], msg: Any) -> Optional[Any]:
        """Retorna o comando do topo se for CmdRenomearEscalada da mesma sessão e mensagem."""
        if session_id is None:
            return None
        pilha = getattr(self.undo_stack, "_pilha", self.undo_stack)
        if not hasattr(pilha, "index") or not hasattr(pilha, "command"):
            return None
        idx = pilha.index()
        if idx <= 0:
            return None
        cmd = pilha.command(idx - 1)
        from editor.commands.comandos_protobuf import CmdRenomearEscalada
        if not isinstance(cmd, CmdRenomearEscalada):
            return None
        if not cmd.pode_mesclar or cmd.session_id != session_id:
            return None
        msg_topo = getattr(cmd, "_msg_cache", None) or cmd.msg_escalada
        msg_real = getattr(msg, "_obj", msg)
        msg_topo_real = getattr(msg_topo, "_obj", msg_topo)
        if msg_topo_real is msg_real:
            return cmd
        return None

    def alterar_primitivo(
        self,
        msg: Any,
        campo_nome: str,
        valor_antigo: Any,
        valor_novo: Any,
        pode_mesclar: bool = False,
        session_id: Optional[int] = None,
    ) -> None:
        if campo_nome == "nome":
            cmd_topo = self._obter_comando_renomear_topo(session_id, msg)
            if cmd_topo is not None:
                self.renomear_escalada(
                    msg_escalada=msg,
                    nome_antigo=cmd_topo.nome_antigo,
                    nome_novo=str(valor_novo) if valor_novo is not None else "",
                    pode_mesclar=pode_mesclar,
                    session_id=session_id,
                    referencias=cmd_topo.referencias,
                    caminhos_referencias=cmd_topo.caminhos_referencias,
                    caminho_msg=cmd_topo.caminho_msg,
                )
                return

            from editor.models.referencias_util import obter_contexto_escalada
            root = self.model.obter_croqui_readonly()
            pico, _, setor, _ = obter_contexto_escalada(root, msg)
            if pico is not None and setor is not None:
                self.renomear_escalada(
                    msg_escalada=msg,
                    nome_antigo=str(valor_antigo) if valor_antigo is not None else "",
                    nome_novo=str(valor_novo) if valor_novo is not None else "",
                    pode_mesclar=pode_mesclar,
                    session_id=session_id,
                )
                return

        cmd = CmdAlterarPrimitivo(
            self.model, msg, campo_nome, valor_antigo, valor_novo, self.contexto_atual_path, pode_mesclar=pode_mesclar
        )
        self._executar_comando(cmd)

    def renomear_escalada(
        self,
        msg_escalada: Any,
        nome_antigo: str,
        nome_novo: str,
        pode_mesclar: bool = True,
        session_id: Optional[int] = None,
        referencias: Optional[Any] = None,
        caminhos_referencias: Optional[Any] = None,
        caminho_msg: Optional[str] = None,
    ) -> None:
        """
        Renomeia uma escalada e atualiza simultaneamente todas as referências
        em mapas que apontam para ela no mesmo pico.
        """
        from editor.commands.comandos_protobuf import CmdRenomearEscalada

        if referencias is None and caminhos_referencias is None:
            cmd_topo = self._obter_comando_renomear_topo(session_id, msg_escalada)
            if cmd_topo is not None:
                referencias = cmd_topo.referencias
                caminhos_referencias = cmd_topo.caminhos_referencias
                caminho_msg = cmd_topo.caminho_msg
            else:
                from editor.models.referencias_util import buscar_referencias_para_escalada
                root = self.model.obter_croqui_readonly()
                referencias = buscar_referencias_para_escalada(root, msg_escalada)

        cmd = CmdRenomearEscalada(
            model=self.model,
            msg_escalada=msg_escalada,
            campo_nome="nome",
            nome_antigo=nome_antigo,
            nome_novo=nome_novo,
            referencias=referencias,
            caminhos_referencias=caminhos_referencias,
            caminho_msg=caminho_msg,
            context_path=self.contexto_atual_path,
            pode_mesclar=pode_mesclar,
            session_id=session_id,
        )
        self._executar_comando(cmd)

    def alterar_campo_imagem(
        self,
        msg: Any,
        campo_nome: str,
        caminho_antigo: Optional[str],
        bytes_antigo: Optional[bytes],
        caminho_novo: Optional[str],
        bytes_novo: Optional[bytes],
    ) -> None:
        """Despacha comando de alteração de imagem com gerenciamento em RAM."""
        cmd = CmdAlterarCampoImagem(
            self.model, msg, campo_nome, caminho_antigo, bytes_antigo, caminho_novo, bytes_novo, self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def inserir_imagem_markdown(
        self,
        msg: Any,
        campo_nome: str,
        texto_antigo: Optional[str],
        texto_novo: str,
        caminho_imagem: Optional[str] = None,
        bytes_imagem: Optional[bytes] = None,
    ) -> None:
        """Despacha comando de inserção de imagem no Markdown com gestão transacional de bytes em RAM."""
        cmd = CmdInserirImagemMarkdown(
            self.model,
            msg,
            campo_nome,
            texto_antigo,
            texto_novo,
            caminho_imagem,
            bytes_imagem,
            self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def adicionar_repeated(self, msg: Any, campo_nome: str, index: int, valor: Any) -> None:
        cmd = CmdAdicionarRepeated(self.model, msg, campo_nome, index, valor, self.contexto_atual_path)
        self._executar_comando(cmd)

    def remover_repeated(self, msg: Any, campo_nome: str, index: int, valor_removido: Any) -> None:
        cmd = CmdRemoverRepeated(self.model, msg, campo_nome, index, valor_removido)
        self._executar_comando(cmd)

    def alterar_repeated_item(
        self,
        msg: Any,
        campo_nome: str,
        index: int,
        valor_antigo: Any,
        valor_novo: Any,
        pode_mesclar: bool = False,
    ) -> None:
        cmd = CmdAlterarRepeatedItem(
            self.model, msg, campo_nome, index, valor_antigo, valor_novo, self.contexto_atual_path, pode_mesclar=pode_mesclar
        )
        self._executar_comando(cmd)

    def alterar_oneof(
        self,
        msg: Any,
        oneof_nome: str,
        nome_antigo: Optional[str],
        valor_antigo: Any,
        campo_novo: Optional[str],
        valor_novo: Any,
    ) -> None:
        """Despacha intenção de alterar um campo do tipo Oneof."""
        comando = CmdAlterarOneof(self.model, msg, oneof_nome, nome_antigo, valor_antigo, campo_novo, valor_novo)
        self._executar_comando(comando)

    def mover_repeated_para_cima(self, msg: Any, campo_nome: str, index: int) -> None:
        """Move o item do index fornecido uma posição para cima."""
        if index <= 0:
            return
            
        cmd = CmdMoverRepeated(self.model, msg, campo_nome, index, index - 1)
        self._executar_comando(cmd)

    def mover_repeated_para_baixo(self, msg: Any, campo_nome: str, index: int) -> None:
        """Move o item do index fornecido uma posição para baixo."""
        tamanho = len(getattr(msg, campo_nome))
        if index >= tamanho - 1:
            return
            
        cmd = CmdMoverRepeated(self.model, msg, campo_nome, index, index + 1)
        self._executar_comando(cmd)

    def alterar_metadados_caminho_novo(self, msg: Any, field_ext: Any, valor_antigo: Any, valor_novo: Any) -> None:
        from editor.commands.comandos_protobuf import CmdAlterarMetadadosCaminhoNovo
        cmd = CmdAlterarMetadadosCaminhoNovo(self.model, msg, field_ext, valor_antigo, valor_novo, self.contexto_atual_path)
        self._executar_comando(cmd)

    def adicionar_mapa_com_arquivo(
        self,
        msg: Any,
        campo_nome: str,
        index: int,
        valor: Any,
        caminho_absoluto: Any,
        img_bytes: Optional[bytes],
    ) -> None:
        from editor.commands.comandos_mapas import CmdAdicionarMapaArquivo
        cmd = CmdAdicionarMapaArquivo(self.model, msg, campo_nome, index, valor, caminho_absoluto, img_bytes, self.contexto_atual_path)
        self._executar_comando(cmd)

    def substituir_imagem(
        self,
        caminho_relativo: str,
        bytes_novo: bytes,
        bytes_antigo: Optional[bytes] = None,
        context_path: Optional[str] = None,
    ) -> None:
        """Despacha comando de substituição de imagem em memória RAM."""
        from editor.commands.comandos_protobuf import CmdSubstituirImagemMemoria
        if bytes_antigo is None:
            bytes_antigo = self.model.obter_bytes_imagem(caminho_relativo)
        ctx = context_path if context_path is not None else self.contexto_atual_path
        cmd = CmdSubstituirImagemMemoria(self.model, caminho_relativo, bytes_antigo, bytes_novo, ctx)
        self._executar_comando(cmd)

