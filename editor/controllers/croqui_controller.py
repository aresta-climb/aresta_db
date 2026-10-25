# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Controlador da Arquitetura MVC para o Croqui.
Orquestra intenções da UI gerando comandos canônicos no QUndoStack / histórico.
"""

from pathlib import Path
from typing import Any

from editor.commands.comandos_protobuf import (
    CmdAdicionarRepeated,
    CmdAlterarAnexo,
    CmdAlterarCampo,
    CmdAlterarImagem,
    CmdMacro,
    CmdMoverRepeated,
    CmdRemoverRepeated,
    ComandoEditor,
)
from editor.models.croqui_model import CroquiModel


class CroquiController:
    """
    Controlador da Arquitetura MVC.
    Recebe as intenções da View e orquestra a mutação do Model
    através da criação de Comandos despachados para o histórico/QUndoStack.
    """

    def __init__(self, model: CroquiModel, undo_stack: Any) -> None:
        self.model: CroquiModel = model
        self.undo_stack: Any = undo_stack
        self.contexto_atual_path: str | None = None
        if not hasattr(model, "_pilha_macros"):
            model._pilha_macros = []  # type: ignore[attr-defined]
        self._pilha_macros: list[CmdMacro] = model._pilha_macros  # type: ignore[attr-defined]

    def set_contexto(self, path: str | None) -> None:
        self.contexto_atual_path = path

    def _executar_comando(self, cmd: Any) -> None:
        """Despacha o comando pelo GerenciadorHistorico (persistindo no diário) ou diretamente na pilha."""
        if self._pilha_macros:
            cmd.redo()
            self._pilha_macros[-1].adicionar_comando(cmd)
            return

        if hasattr(self.undo_stack, "executar"):
            self.undo_stack.executar(cmd)
        else:
            self.undo_stack.push(cmd)

    def iniciar_grupo_undo(self, texto: str) -> None:
        """Inicia um macro de undo/redo para agrupar múltiplos comandos em um só."""
        macro = CmdMacro(texto=texto)
        self._pilha_macros.append(macro)

    def finalizar_grupo_undo(self) -> None:
        """Finaliza o macro atual de undo/redo e o empilha na pilha de histórico."""
        if not self._pilha_macros:
            return
        macro = self._pilha_macros.pop()
        if self._pilha_macros:
            self._pilha_macros[-1].adicionar_comando(macro)
        elif macro.comandos:
            macro.armar_carregamento_silencioso()
            self._executar_comando(macro)

    def alterar_primitivo(
        self,
        msg: Any,
        campo_nome: str,
        valor_antigo: Any,
        valor_novo: Any,
        pode_mesclar: bool = False,
        session_id: int | None = None,
    ) -> None:
        """Despacha comando para alterar um campo primitivo via CmdAlterarCampo."""
        cmd = CmdAlterarCampo(
            model=self.model,
            alvo=msg,
            campo_nome=campo_nome,
            valor_novo=valor_novo,
            valor_antigo=valor_antigo,
            pode_mesclar=pode_mesclar,
            session_id=session_id,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def renomear_escalada(
        self,
        msg_escalada: Any,
        nome_antigo: str,
        nome_novo: str,
        pode_mesclar: bool = True,
        session_id: int | None = None,
        referencias: Any | None = None,
        caminhos_referencias: Any | None = None,
        caminho_msg: str | None = None,
        contexto: Any | None = None,
    ) -> None:
        """
        Renomeia uma escalada de forma atômica e atualiza referências por UID via CmdAlterarCampo.
        """
        cmd = CmdAlterarCampo(
            model=self.model,
            alvo=msg_escalada,
            campo_nome="nome",
            valor_novo=nome_novo,
            valor_antigo=nome_antigo,
            pode_mesclar=pode_mesclar,
            session_id=session_id,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def alterar_campo_imagem(
        self,
        msg: Any,
        campo_nome: str,
        caminho_antigo: str | None,
        bytes_antigo: bytes | None,
        caminho_novo: str | None,
        bytes_novo: bytes | None,
    ) -> None:
        """Despacha comando de alteração de imagem com gerenciamento em RAM via CmdMacro/CmdAlterarImagem."""
        comandos: list[ComandoEditor] = []
        if caminho_novo and bytes_novo is not None:
            comandos.append(
                CmdAlterarImagem(
                    model=self.model,
                    caminho_relativo=caminho_novo,
                    bytes_novos=bytes_novo,
                    bytes_antigos=bytes_antigo if caminho_novo == caminho_antigo else None,
                    context_path=self.contexto_atual_path,
                )
            )
        if caminho_novo != caminho_antigo:
            comandos.append(
                CmdAlterarCampo(
                    model=self.model,
                    alvo=msg,
                    campo_nome=campo_nome,
                    valor_novo=caminho_novo or "",
                    valor_antigo=caminho_antigo,
                    context_path=self.contexto_atual_path,
                )
            )
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        elif comandos:
            self._executar_comando(CmdMacro(comandos, texto=f"Alterar Imagem {campo_nome}"))

    def inserir_imagem_markdown(
        self,
        msg: Any,
        campo_nome: str,
        texto_antigo: str | None,
        texto_novo: str,
        caminho_imagem: str | None = None,
        bytes_imagem: bytes | None = None,
    ) -> None:
        """Despacha comando de inserção de imagem no Markdown com gestão de RAM via CmdMacro."""
        comandos: list[ComandoEditor] = []
        if caminho_imagem and bytes_imagem:
            comandos.append(
                CmdAlterarImagem(
                    model=self.model,
                    caminho_relativo=caminho_imagem,
                    bytes_novos=bytes_imagem,
                    context_path=self.contexto_atual_path,
                )
            )
        comandos.append(
            CmdAlterarCampo(
                model=self.model,
                alvo=msg,
                campo_nome=campo_nome,
                valor_novo=texto_novo,
                valor_antigo=texto_antigo,
                context_path=self.contexto_atual_path,
            )
        )
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        else:
            self._executar_comando(CmdMacro(comandos, texto="Inserir Imagem Markdown"))

    def inserir_botao_markdown(
        self,
        msg: Any,
        campo_nome: str,
        texto_antigo: str | None,
        texto_novo: str,
        caminho_anexo: str | None = None,
        bytes_anexo: bytes | None = None,
    ) -> None:
        """Despacha comando de inserção de botão/link no Markdown com gestão de anexo em RAM via CmdMacro."""
        comandos: list[ComandoEditor] = []
        if caminho_anexo and bytes_anexo:
            comandos.append(
                CmdAlterarAnexo(
                    model=self.model,
                    nome_arquivo=caminho_anexo,
                    bytes_novos=bytes_anexo,
                    context_path=self.contexto_atual_path,
                )
            )
        comandos.append(
            CmdAlterarCampo(
                model=self.model,
                alvo=msg,
                campo_nome=campo_nome,
                valor_novo=texto_novo,
                valor_antigo=texto_antigo,
                context_path=self.contexto_atual_path,
            )
        )
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        else:
            self._executar_comando(CmdMacro(comandos, texto="Inserir Botão Markdown"))

    def adicionar_repeated(self, msg: Any, campo_nome: str, index: int, valor: Any) -> None:
        """Adiciona item em coleção repeated via CmdAdicionarRepeated."""
        cmd = CmdAdicionarRepeated(
            model=self.model,
            alvo=msg,
            campo_nome=campo_nome,
            index=index,
            valor=valor,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def remover_repeated(
        self, msg: Any, campo_nome: str, index: int, valor_removido: Any = None
    ) -> None:
        """Remove item de coleção repeated com captura de imagens órfãs via CmdRemoverRepeated."""
        cmd = CmdRemoverRepeated(
            model=self.model,
            alvo=msg,
            campo_nome=campo_nome,
            index=index,
            valor_removido=valor_removido,
            context_path=self.contexto_atual_path,
        )
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
        """Altera item em coleção repeated via CmdAlterarCampo indexado."""
        cmd = CmdAlterarCampo(
            model=self.model,
            alvo=msg,
            campo_nome=f"{campo_nome}.{index}",
            valor_novo=valor_novo,
            valor_antigo=valor_antigo,
            pode_mesclar=pode_mesclar,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def alterar_multiplos_repeated_items(
        self,
        msg: Any,
        campo_nome: str,
        alteracoes: list[tuple[int, Any, Any]],
    ) -> None:
        """Altera múltiplos itens de uma coleção repeated simultaneamente via CmdMacro."""
        if not alteracoes:
            return
        comandos: list[ComandoEditor] = [
            CmdAlterarCampo(
                model=self.model,
                alvo=msg,
                campo_nome=f"{campo_nome}.{idx}",
                valor_novo=v_novo,
                valor_antigo=v_antigo,
                context_path=self.contexto_atual_path,
            )
            for idx, v_antigo, v_novo in alteracoes
        ]
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        else:
            self._executar_comando(
                CmdMacro(comandos, texto=f"Alterar {len(comandos)} itens em {campo_nome}")
            )

    def alterar_oneof(
        self,
        msg: Any,
        oneof_nome: str,
        nome_antigo: str | None,
        valor_antigo: Any,
        campo_novo: str | None,
        valor_novo: Any,
    ) -> None:
        """Altera o campo ativo de um oneof via CmdAlterarCampo."""
        alvo_campo = campo_novo if campo_novo else oneof_nome
        cmd = CmdAlterarCampo(
            model=self.model,
            alvo=msg,
            campo_nome=alvo_campo,
            valor_novo=valor_novo,
            valor_antigo=valor_antigo,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def mover_repeated_para_cima(self, msg: Any, campo_nome: str, index: int) -> None:
        """Move o item do index fornecido uma posição para cima."""
        if index <= 0:
            return
        cmd = CmdMoverRepeated(
            model=self.model,
            alvo=msg,
            campo_nome=campo_nome,
            index_from=index,
            index_to=index - 1,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def mover_repeated_para_baixo(self, msg: Any, campo_nome: str, index: int) -> None:
        """Move o item do index fornecido uma posição para baixo."""
        tamanho = len(getattr(msg, campo_nome))
        if index >= tamanho - 1:
            return
        cmd = CmdMoverRepeated(
            model=self.model,
            alvo=msg,
            campo_nome=campo_nome,
            index_from=index,
            index_to=index + 1,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def mover_repeated_para_posicao(
        self,
        msg: Any,
        campo_nome: str,
        index_from: int,
        index_to: int,
    ) -> None:
        """Move o item do index_from para index_to na coleção repeated."""
        if index_from == index_to:
            return
        cmd = CmdMoverRepeated(
            model=self.model,
            alvo=msg,
            campo_nome=campo_nome,
            index_from=index_from,
            index_to=index_to,
            context_path=self.contexto_atual_path,
        )
        self._executar_comando(cmd)

    def alterar_metadados_caminho_novo(
        self, msg: Any, field_ext: Any, valor_antigo: Any, valor_novo: Any
    ) -> None:
        """Altera metadados de arquivo (caminho_novo) via CmdAlterarCampo."""
        cmd = CmdAlterarCampo(
            model=self.model,
            alvo=msg,
            campo_nome=getattr(field_ext, "name", str(field_ext)),
            valor_novo=valor_novo,
            valor_antigo=valor_antigo,
            context_path=self.contexto_atual_path,
            field_ext=field_ext,
        )
        self._executar_comando(cmd)


    def adicionar_mapa_com_arquivo(
        self,
        msg: Any,
        campo_nome: str,
        index: int,
        valor: Any,
        caminho_absoluto: Any,
        img_bytes: bytes | None,
    ) -> None:
        """Adiciona mapa e carrega seus bytes em RAM atomicamente via CmdMacro."""
        caminho_rel = (
            str(valor.caminho_imagem_mapa)
            if hasattr(valor, "caminho_imagem_mapa") and valor.caminho_imagem_mapa
            else (Path(caminho_absoluto).name if caminho_absoluto else "")
        )
        comandos: list[ComandoEditor] = []
        if caminho_rel and img_bytes:
            comandos.append(
                CmdAlterarImagem(
                    model=self.model,
                    caminho_relativo=caminho_rel,
                    bytes_novos=img_bytes,
                    context_path=self.contexto_atual_path,
                )
            )
        comandos.append(
            CmdAdicionarRepeated(
                model=self.model,
                alvo=msg,
                campo_nome=campo_nome,
                index=index,
                valor=valor,
                context_path=self.contexto_atual_path,
            )
        )
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        else:
            self._executar_comando(CmdMacro(comandos, texto="Adicionar Mapa com Arquivo"))

    def substituir_imagem(
        self,
        caminho_relativo: str,
        bytes_novo: bytes,
        bytes_antigo: bytes | None = None,
        context_path: str | None = None,
    ) -> None:
        """Despacha comando de substituição de imagem em memória RAM via CmdAlterarImagem."""
        if bytes_antigo is None:
            bytes_antigo = self.model.obter_bytes_imagem(caminho_relativo)
        ctx = context_path if context_path is not None else self.contexto_atual_path
        cmd = CmdAlterarImagem(
            model=self.model,
            caminho_relativo=caminho_relativo,
            bytes_novos=bytes_novo,
            bytes_antigos=bytes_antigo,
            context_path=ctx,
        )
        self._executar_comando(cmd)

    def migrar_setor(
        self,
        pai_origem: Any = None,
        campo_origem: str = "",
        indice_origem: int = 0,
        pai_destino: Any = None,
        campo_destino: str = "",
        indice_destino: int = 0,
        caminho_novo: str | None = None,
        caminho_antigo: str | None = None,
        caminho_msg_origem: str | None = None,
        caminho_msg_destino: str | None = None,
        context_path: str | None = None,
    ) -> None:
        """
        Despacha migração de setor atômica entre pais hierárquicos via CmdMacro,
        reutilizando CmdRemoverRepeated e CmdAdicionarRepeated canônicos.
        """
        pai_origem_raw = getattr(pai_origem, "_obj", pai_origem)
        container_origem = getattr(pai_origem_raw, campo_origem)
        item_origem = container_origem[indice_origem]

        from aresta_api.proto.generated import croqui_pb2

        arq_setor = croqui_pb2.ArquivoSetor()
        if campo_origem == "setores_ou_grupos":
            arq_setor.CopyFrom(item_origem.setor)
        else:
            arq_setor.CopyFrom(item_origem)

        if caminho_novo is not None:
            arq_setor.Extensions[
                croqui_pb2.ArquivoSetor.ext_metadados_arquivo
            ].caminho_novo = caminho_novo

        if campo_destino == "setores_ou_grupos":
            item_destino = croqui_pb2.SetorOuGrupo()
            item_destino.setor.CopyFrom(arq_setor)
        else:
            item_destino = arq_setor

        ctx = context_path or self.contexto_atual_path
        cmd_remover = CmdRemoverRepeated(
            model=self.model,
            alvo=pai_origem,
            campo_nome=campo_origem,
            index=indice_origem,
            valor_removido=item_origem,
            context_path=ctx,
        )
        cmd_adicionar = CmdAdicionarRepeated(
            model=self.model,
            alvo=pai_destino,
            campo_nome=campo_destino,
            index=indice_destino,
            valor=item_destino,
            context_path=ctx,
        )
        macro = CmdMacro([cmd_remover, cmd_adicionar], texto="Migrar Setor")
        self._executar_comando(macro)
