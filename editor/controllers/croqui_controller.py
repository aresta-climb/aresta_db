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
    _ajustar_submensagem_variante_se_necessario,
    _eh_campo_repeated,
    _validar_tipo_valor_campo,
    navegar_para_alvo,
    validar_pertence_ao_croqui,
)
from editor.core.geometrias_poi import redimensionar_pois_proporcionalmente
from editor.core.imagens_croqui import extrair_caminhos_imagens
from editor.models.croqui_model import CroquiModel
from editor.models.readonly_proxy import _copia_segura


def _eh_campo_compativel_oneof(f_orig: Any, f_dest: Any | None) -> bool:
    """Retorna True se dois FieldDescriptors de variantes oneof possuem tipos idênticos."""
    if (
        f_dest is None
        or f_dest.type != f_orig.type
        or _eh_campo_repeated(f_dest) != _eh_campo_repeated(f_orig)
    ):
        return False
    if f_dest.enum_type is not None:
        return f_orig.enum_type is not None and (
            f_dest.enum_type.full_name == f_orig.enum_type.full_name
        )
    return f_dest.message_type is None


def _mesclar_campos_compativeis_oneof(msg_origem: Any, msg_destino: Any) -> Any:
    """
    Copia para uma cópia de `msg_destino` os campos homônimos compatíveis presentes em
    `msg_origem` que ainda não foram explicitamente definidos em `msg_destino`.
    """
    orig_raw = getattr(msg_origem, "_obj", msg_origem)
    dest_copia = _copia_segura(getattr(msg_destino, "_obj", msg_destino))
    desc_dest = dest_copia.DESCRIPTOR

    for f_orig, val_orig in orig_raw.ListFields():
        f_dest = desc_dest.fields_by_name.get(f_orig.name)
        if not _eh_campo_compativel_oneof(f_orig, f_dest):
            continue
        if _eh_campo_repeated(f_dest):
            colecao_dest = getattr(dest_copia, f_dest.name)
            if len(colecao_dest) == 0:
                colecao_dest.extend(val_orig)
        elif not dest_copia.HasField(f_dest.name):
            setattr(dest_copia, f_dest.name, val_orig)

    return dest_copia


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

    def _aplicar_preservacao_oneof(self, alvo: Any, nome_c: str, val_c: Any) -> Any:
        """Se `nome_c` altera um ramo oneof em `alvo`, mescla os campos compatíveis da variante anterior."""
        caminho_res = validar_pertence_ao_croqui(
            self.model, alvo, nome_c, nome_comando="CmdAlterarCampo"
        )
        msg_alvo = (
            navegar_para_alvo(
                self.model.obter_croqui_readonly(), caminho_res, self.model.indice_uids
            )
            if isinstance(alvo, str)
            else alvo
        )
        desc = msg_alvo.DESCRIPTOR
        if nome_c in desc.oneofs_by_name and isinstance(val_c, tuple) and len(val_c) == 2:
            var_antiga = msg_alvo.WhichOneof(nome_c)
            var_nova, msg_nova = val_c
            if var_antiga and msg_nova is not None:
                return (
                    var_nova,
                    _mesclar_campos_compativeis_oneof(getattr(msg_alvo, var_antiga), msg_nova),
                )
        elif nome_c in desc.fields_by_name and desc.fields_by_name[nome_c].containing_oneof:
            var_antiga = msg_alvo.WhichOneof(desc.fields_by_name[nome_c].containing_oneof.name)
            if var_antiga and val_c is not None:
                return _mesclar_campos_compativeis_oneof(getattr(msg_alvo, var_antiga), val_c)
        return val_c

    def _construir_comandos_para_alvo(
        self,
        alvo: Any,
        mapa_campos: dict[str, Any],
        pode_mesclar: bool = False,
        session_id: int | str | None = None,
        preservar_campos_compativeis: bool = False,
    ) -> list[ComandoEditor]:
        """Constrói e valida previamente os comandos folha para atualizar `mapa_campos` em `alvo`."""
        comandos: list[ComandoEditor] = []
        for nome_c, val_c in mapa_campos.items():
            if preservar_campos_compativeis:
                val_c = self._aplicar_preservacao_oneof(alvo, nome_c, val_c)
            if "." not in nome_c and isinstance(val_c, (list, tuple)):
                caminho_res = validar_pertence_ao_croqui(
                    self.model, alvo, nome_c, nome_comando="CmdAlterarCampo"
                )
                msg_alvo = (
                    navegar_para_alvo(
                        self.model.obter_croqui_readonly(), caminho_res, self.model.indice_uids
                    )
                    if isinstance(alvo, str)
                    else alvo
                )
                msg_alvo, _ = _ajustar_submensagem_variante_se_necessario(
                    msg_alvo, caminho_res, nome_c
                )
                field_desc = msg_alvo.DESCRIPTOR.fields_by_name.get(nome_c)
                if field_desc is not None and _eh_campo_repeated(field_desc):
                    for item_novo in val_c:
                        _validar_tipo_valor_campo(field_desc, item_novo, nome_c)
                    caminhos_mantidos = {
                        c for item_novo in val_c for c in extrair_caminhos_imagens(item_novo)
                    }
                    colecao_atual = getattr(msg_alvo, nome_c)
                    for idx_rem in range(len(colecao_atual) - 1, -1, -1):
                        cmd_rem = CmdRemoverRepeated(
                            model=self.model,
                            alvo=msg_alvo,
                            campo_nome=nome_c,
                            index=idx_rem,
                            valor_removido=colecao_atual[idx_rem],
                            context_path=self.contexto_atual_path,
                        )
                        for cam in caminhos_mantidos:
                            cmd_rem.imagens_removidas_ram.pop(cam, None)
                        comandos.append(cmd_rem)
                    for idx_add, item_novo in enumerate(val_c):
                        comandos.append(
                            CmdAdicionarRepeated(
                                model=self.model,
                                alvo=msg_alvo,
                                campo_nome=nome_c,
                                index=idx_add,
                                valor=item_novo,
                                context_path=self.contexto_atual_path,
                            )
                        )
                    continue

            comandos.append(
                CmdAlterarCampo(
                    model=self.model,
                    alvo=alvo,
                    campo_nome=nome_c,
                    valor_novo=val_c,
                    pode_mesclar=pode_mesclar if len(mapa_campos) == 1 else False,
                    session_id=session_id if len(mapa_campos) == 1 else None,
                    context_path=self.contexto_atual_path,
                )
            )
        return comandos

    def alterar_em_lote(
        self,
        operacoes: list[dict[str, Any]],
        texto_macro: str | None = None,
        pode_mesclar: bool = False,
        session_id: int | str | None = None,
        preservar_campos_compativeis: bool = False,
    ) -> None:
        """
        Despacha alterações para múltiplos alvos e campos em um único CmdMacro atômico.
        Todos os comandos folha são instanciados e validados previamente (fail-fast).
        """
        comandos: list[ComandoEditor] = []
        permitir_mescla = len(operacoes) == 1 and pode_mesclar
        sessao = session_id if len(operacoes) == 1 else None
        for op in operacoes:
            alvo_op = op.get("alvo")
            mapa_campos: dict[str, Any] = {}
            if isinstance(op.get("campos"), dict):
                mapa_campos.update(op["campos"])
            if op.get("campo"):
                mapa_campos[str(op["campo"])] = op.get("valor")
            if not mapa_campos:
                continue
            preservar_op = bool(
                op.get("preservar_campos_compativeis", preservar_campos_compativeis)
            )
            comandos.extend(
                self._construir_comandos_para_alvo(
                    alvo=alvo_op,
                    mapa_campos=mapa_campos,
                    pode_mesclar=permitir_mescla,
                    session_id=sessao,
                    preservar_campos_compativeis=preservar_op,
                )
            )
        if not comandos:
            return
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        else:
            rotulo = texto_macro or f"Alterar {len(comandos)} campos"
            self._executar_comando(CmdMacro(comandos, texto=rotulo))

    def alterar_campo(
        self,
        alvo: Any,
        campo_nome: str | None = None,
        valor_novo: Any = None,
        campos: dict[str, Any] | None = None,
        pode_mesclar: bool = False,
        session_id: int | str | None = None,
        preservar_campos_compativeis: bool = False,
    ) -> None:
        """
        Despacha comando canônico para alterar um único campo ou um lote de campos (via CmdMacro).
        Todos os CmdAlterarCampo são instanciados e validados antes da execução na pilha.
        """
        mapa_campos: dict[str, Any] = {}
        if campos:
            mapa_campos.update(campos)
        if campo_nome:
            mapa_campos[campo_nome] = valor_novo
        self.alterar_em_lote(
            [{"alvo": alvo, "campos": mapa_campos}],
            pode_mesclar=pode_mesclar,
            session_id=session_id,
            preservar_campos_compativeis=preservar_campos_compativeis,
        )

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
        self.adicionar_multiplos_repeated(msg, campo_nome, index, [valor])

    def adicionar_multiplos_repeated(
        self, msg: Any, campo_nome: str, index_inicial: int, valores: list[Any]
    ) -> None:
        """Adiciona um ou mais itens consecutivos em coleção repeated (em CmdMacro quando múltiplos)."""
        if not valores:
            return
        comandos: list[ComandoEditor] = [
            CmdAdicionarRepeated(
                model=self.model,
                alvo=msg,
                campo_nome=campo_nome,
                index=index_inicial + offset,
                valor=item,
                context_path=self.contexto_atual_path,
            )
            for offset, item in enumerate(valores)
        ]
        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        else:
            self._executar_comando(
                CmdMacro(comandos, texto=f"Adicionar {len(comandos)} itens em {campo_nome}")
            )

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

    def substituir_imagem_mapa(
        self,
        msg_mapa: Any,
        caminho_relativo_novo: str,
        bytes_novo: bytes | None,
        largura_nova: int,
        altura_nova: int,
        reescalar_pois: bool = True,
        largura_referencia_pois: int | None = None,
        altura_referencia_pois: int | None = None,
        context_path: str | None = None,
    ) -> None:
        """
        Substitui atomicamente a imagem de um Mapa, atualizando `caminho_imagem_mapa`,
        `largura_mapa`, `altura_mapa` e opcionalmente reescalando proporcionalmente
        os Pontos de Interesse via CmdMacro.
        """
        if isinstance(msg_mapa, str):
            msg_obj = navegar_para_alvo(
                self.model.obter_croqui_readonly(), msg_mapa, self.model.indice_uids
            )
        else:
            msg_obj = getattr(msg_mapa, "_obj", msg_mapa)

        caminho_antigo = str(getattr(msg_obj, "caminho_imagem_mapa", "") or "")
        largura_antiga = int(getattr(msg_obj, "largura_mapa", 0) or 0)
        altura_antiga = int(getattr(msg_obj, "altura_mapa", 0) or 0)
        larg_ref = (
            largura_referencia_pois
            if largura_referencia_pois and largura_referencia_pois > 0
            else largura_antiga
        )
        alt_ref = (
            altura_referencia_pois
            if altura_referencia_pois and altura_referencia_pois > 0
            else altura_antiga
        )
        ctx = context_path if context_path is not None else self.contexto_atual_path

        comandos: list[ComandoEditor] = []
        if bytes_novo is not None:
            bytes_antigo = self.model.obter_bytes_imagem(caminho_relativo_novo)
            comandos.append(
                CmdAlterarImagem(
                    model=self.model,
                    caminho_relativo=caminho_relativo_novo,
                    bytes_novos=bytes_novo,
                    bytes_antigos=bytes_antigo,
                    context_path=ctx,
                )
            )

        if caminho_relativo_novo and caminho_relativo_novo != caminho_antigo:
            comandos.append(
                CmdAlterarCampo(
                    model=self.model,
                    alvo=msg_mapa,
                    campo_nome="caminho_imagem_mapa",
                    valor_antigo=caminho_antigo,
                    valor_novo=caminho_relativo_novo,
                    context_path=ctx,
                )
            )

        if largura_nova > 0 and largura_nova != largura_antiga:
            comandos.append(
                CmdAlterarCampo(
                    model=self.model,
                    alvo=msg_mapa,
                    campo_nome="largura_mapa",
                    valor_antigo=largura_antiga,
                    valor_novo=int(largura_nova),
                    context_path=ctx,
                )
            )

        if altura_nova > 0 and altura_nova != altura_antiga:
            comandos.append(
                CmdAlterarCampo(
                    model=self.model,
                    alvo=msg_mapa,
                    campo_nome="altura_mapa",
                    valor_antigo=altura_antiga,
                    valor_novo=int(altura_nova),
                    context_path=ctx,
                )
            )

        if (
            reescalar_pois
            and larg_ref > 0
            and alt_ref > 0
            and largura_nova > 0
            and altura_nova > 0
            and (larg_ref != largura_nova or alt_ref != altura_nova)
            and len(msg_obj.pontos_de_interesse) > 0
        ):
            pois_novos = redimensionar_pois_proporcionalmente(
                msg_obj.pontos_de_interesse,
                larg_ref,
                alt_ref,
                largura_nova,
                altura_nova,
            )
            for idx, (poi_orig, poi_novo) in enumerate(
                zip(msg_obj.pontos_de_interesse, pois_novos, strict=False)
            ):
                comandos.append(
                    CmdAlterarCampo(
                        model=self.model,
                        alvo=msg_mapa,
                        campo_nome=f"pontos_de_interesse.{idx}",
                        valor_antigo=_copia_segura(poi_orig),
                        valor_novo=poi_novo,
                        context_path=ctx,
                    )
                )

        if len(comandos) == 1:
            self._executar_comando(comandos[0])
        elif len(comandos) > 1:
            self._executar_comando(CmdMacro(comandos, texto="Substituir Imagem do Mapa"))

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
            sg = croqui_pb2.SetorOuGrupo()
            sg.setor.CopyFrom(arq_setor)
            item_destino: Any = sg
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

    def migrar_escalada(
        self,
        setor_origem: Any,
        indice_origem: int,
        setor_destino: Any,
        indice_destino: int | None = None,
        context_path: str | None = None,
    ) -> int:
        """
        Migra atomicamente uma Escalada de setor_origem.escaladas[indice_origem]
        para setor_destino.escaladas[indice_destino] via CmdMacro, preservando seu UID
        e imagens em memória RAM. Retorna o índice final no setor de destino.
        """
        caminho_orig = validar_pertence_ao_croqui(
            self.model, setor_origem, "escaladas", nome_comando="CmdRemoverRepeated"
        )
        caminho_dest = validar_pertence_ao_croqui(
            self.model, setor_destino, "escaladas", nome_comando="CmdAdicionarRepeated"
        )
        raiz = self.model.obter_croqui_readonly()
        msg_orig = (
            navegar_para_alvo(raiz, caminho_orig, self.model.indice_uids)
            if isinstance(setor_origem, str)
            else setor_origem
        )
        msg_dest = (
            navegar_para_alvo(raiz, caminho_dest, self.model.indice_uids)
            if isinstance(setor_destino, str)
            else setor_destino
        )
        setor_orig_raw = getattr(msg_orig, "_obj", msg_orig)
        setor_dest_raw = getattr(msg_dest, "_obj", msg_dest)

        escaladas_orig = setor_orig_raw.escaladas
        if indice_origem < 0 or indice_origem >= len(escaladas_orig):
            raise IndexError(
                f"Índice de origem fora de alcance ({indice_origem}) em 'escaladas' "
                f"(tamanho {len(escaladas_orig)})."
            )

        from aresta_api.proto.generated import croqui_pb2

        item_origem = escaladas_orig[indice_origem]
        item_destino = croqui_pb2.Escalada()
        item_destino.CopyFrom(item_origem)

        tamanho_apos_remocao = len(setor_dest_raw.escaladas) - (
            1 if setor_orig_raw is setor_dest_raw else 0
        )
        idx_final = (
            tamanho_apos_remocao
            if indice_destino is None or int(indice_destino) < 0
            else min(max(0, int(indice_destino)), tamanho_apos_remocao)
        )

        ctx = context_path or self.contexto_atual_path
        cmd_remover = CmdRemoverRepeated(
            model=self.model,
            alvo=setor_orig_raw,
            campo_nome="escaladas",
            index=indice_origem,
            valor_removido=item_origem,
            context_path=ctx,
        )
        cmd_remover.imagens_removidas_ram.clear()
        cmd_adicionar = CmdAdicionarRepeated(
            model=self.model,
            alvo=setor_dest_raw,
            campo_nome="escaladas",
            index=idx_final,
            valor=item_destino,
            context_path=ctx,
        )
        self._executar_comando(CmdMacro([cmd_remover, cmd_adicionar], texto="Migrar Escalada"))
        return idx_final

    def _obter_escalada_por_uid(self, escalada_uid: str) -> Any:
        alvo = self.model.obter_objeto_por_uid(escalada_uid)
        if alvo is None:
            raise KeyError(f"Escalada com UID '{escalada_uid}' não encontrada no croqui.")
        return getattr(alvo, "_obj", alvo)

    def _obter_curadoria_escalada(self, escalada_uid: str) -> Any | None:
        raiz = getattr(
            self.model.obter_croqui_readonly(), "_obj", self.model.obter_croqui_readonly()
        )
        for item in raiz.curadoria_betas.conteudo.escaladas:
            if item.escalada_uid == escalada_uid:
                return item
        return None

    def _garantir_curadoria_escalada(self, escalada_uid: str, ctx: str | None) -> Any:
        existente = self._obter_curadoria_escalada(escalada_uid)
        if existente is not None:
            return existente

        from aresta_api.proto.generated import beta_pb2

        raiz = getattr(
            self.model.obter_croqui_readonly(), "_obj", self.model.obter_croqui_readonly()
        )
        if not raiz.curadoria_betas.HasField("conteudo"):
            raiz.curadoria_betas.conteudo.SetInParent()
        nova_curadoria = beta_pb2.CuradoriaBetasEscalada(escalada_uid=escalada_uid)
        cmd_criar = CmdAdicionarRepeated(
            model=self.model,
            alvo=raiz.curadoria_betas.conteudo,
            campo_nome="escaladas",
            index=len(raiz.curadoria_betas.conteudo.escaladas),
            valor=nova_curadoria,
            context_path=ctx,
        )
        self._executar_comando(cmd_criar)
        criada = self._obter_curadoria_escalada(escalada_uid)
        assert criada is not None
        return criada

    def adicionar_candidatos_nao_scorados(
        self,
        escalada_uid: str,
        candidatos: Any,
        context_path: str | None = None,
    ) -> int:
        """
        Adiciona candidatos recém-coletados em betas_nao_scorados da escalada,
        descartando URLs já presentes nas 4 listas da via e empilhando um único comando Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2
        from coleta_de_betas.extratores.deduplicador import (
            normalizar_url,
            obter_urls_conhecidas_escalada,
        )

        esc_raw = self._obter_escalada_por_uid(escalada_uid)
        curadoria_atual = self._obter_curadoria_escalada(escalada_uid)
        urls_conhecidas = obter_urls_conhecidas_escalada(esc_raw, curadoria_atual)

        novos: list[beta_pb2.CandidatoMidiaBeta] = []
        for cand in candidatos:
            url_norm = normalizar_url(cand.midia.url)
            if not url_norm or url_norm in urls_conhecidas:
                continue
            urls_conhecidas.add(url_norm)
            copia = beta_pb2.CandidatoMidiaBeta()
            copia.CopyFrom(cand)
            copia.midia.url = url_norm
            novos.append(copia)

        if not novos:
            return 0

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo("Coletar Betas")
        try:
            curadoria_esc = self._garantir_curadoria_escalada(escalada_uid, ctx)
            for item in novos:
                cmd_add = CmdAdicionarRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_nao_scorados",
                    index=len(curadoria_esc.betas_nao_scorados),
                    valor=item,
                    context_path=ctx,
                )
                self._executar_comando(cmd_add)
        finally:
            self.finalizar_grupo_undo()
        return len(novos)

    def adicionar_betas_rejeitados_lote(
        self,
        escalada_uid: str,
        midias_rejeitadas: Any,
        context_path: str | None = None,
    ) -> int:
        """
        Adiciona itens auto-filtrados em lote em betas_rejeitados da escalada,
        descartando URLs já presentes nas 4 listas da via e empilhando comandos Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2
        from coleta_de_betas.extratores.deduplicador import (
            normalizar_url,
            obter_urls_conhecidas_escalada,
        )

        esc_raw = self._obter_escalada_por_uid(escalada_uid)
        curadoria_atual = self._obter_curadoria_escalada(escalada_uid)
        urls_conhecidas = obter_urls_conhecidas_escalada(esc_raw, curadoria_atual)

        novos: list[beta_pb2.MidiaBeta] = []
        for midia in midias_rejeitadas:
            url_norm = normalizar_url(midia.url)
            if not url_norm or url_norm in urls_conhecidas:
                continue
            urls_conhecidas.add(url_norm)
            copia = beta_pb2.MidiaBeta()
            copia.CopyFrom(midia)
            copia.url = url_norm
            novos.append(copia)

        if not novos:
            return 0

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo("Registrar Betas Auto-Filtrados")
        try:
            curadoria_esc = self._garantir_curadoria_escalada(escalada_uid, ctx)
            for item in novos:
                cmd_add = CmdAdicionarRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_rejeitados",
                    index=len(curadoria_esc.betas_rejeitados),
                    valor=item,
                    context_path=ctx,
                )
                self._executar_comando(cmd_add)
        finally:
            self.finalizar_grupo_undo()
        return len(novos)

    def promover_candidato_para_nao_revisado(
        self,
        escalada_uid: str,
        indice_nao_scorado: int,
        score: int,
        justificativa: str,
        context_path: str | None = None,
    ) -> None:
        """
        Move 1 candidato de betas_nao_scorados para betas_nao_revisados preenchendo o resultado
        do LLM e mantendo a lista ordenada por score decrescente via comando reversível.
        """
        from aresta_api.proto.generated import beta_pb2

        self._obter_escalada_por_uid(escalada_uid)
        curadoria_esc = self._obter_curadoria_escalada(escalada_uid)
        if curadoria_esc is None or not (
            0 <= indice_nao_scorado < len(curadoria_esc.betas_nao_scorados)
        ):
            raise IndexError("Candidato não scorado fora de alcance.")

        cand_orig = curadoria_esc.betas_nao_scorados[indice_nao_scorado]
        cand_avaliado = beta_pb2.CandidatoMidiaBeta()
        cand_avaliado.CopyFrom(cand_orig)
        cand_avaliado.resultado_llm.llm_confidence_score = int(score)
        cand_avaliado.resultado_llm.llm_reasoning = str(justificativa)

        idx_insercao = len(curadoria_esc.betas_nao_revisados)
        for i, existente in enumerate(curadoria_esc.betas_nao_revisados):
            if int(score) > existente.resultado_llm.llm_confidence_score:
                idx_insercao = i
                break

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo("Avaliar Beta (LLM)")
        try:
            self._executar_comando(
                CmdRemoverRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_nao_scorados",
                    index=indice_nao_scorado,
                    valor_removido=cand_orig,
                    context_path=ctx,
                )
            )
            self._executar_comando(
                CmdAdicionarRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_nao_revisados",
                    index=idx_insercao,
                    valor=cand_avaliado,
                    context_path=ctx,
                )
            )
        finally:
            self.finalizar_grupo_undo()

    def aprovar_beta_curadoria(
        self,
        escalada_uid: str,
        origem: str,
        indice: int,
        context_path: str | None = None,
    ) -> None:
        """
        Aprova individualmente (1 a 1) um candidato de betas_nao_revisados ou betas_nao_scorados,
        extraindo seu MidiaBeta limpo para escalada.betas via comando Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2

        if origem not in ("betas_nao_revisados", "betas_nao_scorados"):
            raise ValueError(f"Origem inválida para aprovação de beta: '{origem}'.")

        esc_raw = self._obter_escalada_por_uid(escalada_uid)
        curadoria_esc = self._obter_curadoria_escalada(escalada_uid)
        if curadoria_esc is None:
            raise IndexError("Nenhum candidato de curadoria encontrado para esta escalada.")

        colecao = getattr(curadoria_esc, origem)
        if not (0 <= indice < len(colecao)):
            raise IndexError(f"Índice {indice} fora de alcance em '{origem}'.")

        cand_orig = colecao[indice]
        midia_aprovada = beta_pb2.MidiaBeta(
            url=cand_orig.midia.url,
            titulo=cand_orig.midia.titulo,
            fonte=cand_orig.midia.fonte,
        )

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo("Aprovar Beta")
        try:
            self._executar_comando(
                CmdRemoverRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome=origem,
                    index=indice,
                    valor_removido=cand_orig,
                    context_path=ctx,
                )
            )
            self._executar_comando(
                CmdAdicionarRepeated(
                    model=self.model,
                    alvo=esc_raw,
                    campo_nome="betas",
                    index=len(esc_raw.betas),
                    valor=midia_aprovada,
                    context_path=ctx,
                )
            )
        finally:
            self.finalizar_grupo_undo()

    def rejeitar_beta_curadoria(
        self,
        escalada_uid: str,
        origem: str,
        indice: int,
        context_path: str | None = None,
    ) -> None:
        """
        Rejeita individualmente (1 a 1) um item de betas_nao_revisados, betas_nao_scorados
        ou escalada.betas, movendo-o para betas_rejeitados via comando Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2

        if origem not in ("betas_nao_revisados", "betas_nao_scorados", "betas"):
            raise ValueError(f"Origem inválida para rejeição de beta: '{origem}'.")

        esc_raw = self._obter_escalada_por_uid(escalada_uid)
        ctx = context_path or self.contexto_atual_path

        if origem == "betas":
            if not (0 <= indice < len(esc_raw.betas)):
                raise IndexError(f"Índice {indice} fora de alcance em 'betas'.")
            item_orig = esc_raw.betas[indice]
            midia_rej = beta_pb2.MidiaBeta(
                url=item_orig.url,
                titulo=item_orig.titulo,
                fonte=item_orig.fonte,
            )
            alvo_remocao: Any = esc_raw
        else:
            curadoria_atual = self._obter_curadoria_escalada(escalada_uid)
            if curadoria_atual is None:
                raise IndexError("Nenhum candidato de curadoria encontrado para esta escalada.")
            colecao = getattr(curadoria_atual, origem)
            if not (0 <= indice < len(colecao)):
                raise IndexError(f"Índice {indice} fora de alcance em '{origem}'.")
            item_orig = colecao[indice]
            midia_rej = beta_pb2.MidiaBeta(
                url=item_orig.midia.url,
                titulo=item_orig.midia.titulo,
                fonte=item_orig.midia.fonte,
            )
            alvo_remocao = curadoria_atual

        self.iniciar_grupo_undo("Rejeitar Beta")
        try:
            curadoria_esc = self._garantir_curadoria_escalada(escalada_uid, ctx)
            self._executar_comando(
                CmdRemoverRepeated(
                    model=self.model,
                    alvo=alvo_remocao,
                    campo_nome=origem,
                    index=indice,
                    valor_removido=item_orig,
                    context_path=ctx,
                )
            )
            self._executar_comando(
                CmdAdicionarRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_rejeitados",
                    index=len(curadoria_esc.betas_rejeitados),
                    valor=midia_rej,
                    context_path=ctx,
                )
            )
        finally:
            self.finalizar_grupo_undo()

    def restaurar_beta_rejeitado(
        self,
        escalada_uid: str,
        indice_rejeitado: int,
        context_path: str | None = None,
    ) -> None:
        """
        Restaura individualmente (1 a 1) um item de betas_rejeitados de volta para
        betas_nao_scorados via comando Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2

        self._obter_escalada_por_uid(escalada_uid)
        curadoria_esc = self._obter_curadoria_escalada(escalada_uid)
        if curadoria_esc is None or not (
            0 <= indice_rejeitado < len(curadoria_esc.betas_rejeitados)
        ):
            raise IndexError("Beta rejeitado fora de alcance.")

        midia_orig = curadoria_esc.betas_rejeitados[indice_rejeitado]
        cand_restaurado = beta_pb2.CandidatoMidiaBeta()
        cand_restaurado.midia.CopyFrom(midia_orig)

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo("Restaurar Beta Rejeitado")
        try:
            self._executar_comando(
                CmdRemoverRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_rejeitados",
                    index=indice_rejeitado,
                    valor_removido=midia_orig,
                    context_path=ctx,
                )
            )
            self._executar_comando(
                CmdAdicionarRepeated(
                    model=self.model,
                    alvo=curadoria_esc,
                    campo_nome="betas_nao_scorados",
                    index=len(curadoria_esc.betas_nao_scorados),
                    valor=cand_restaurado,
                    context_path=ctx,
                )
            )
        finally:
            self.finalizar_grupo_undo()

    def aprovar_betas_nao_revisados_por_score(
        self,
        score_minimo: int,
        escalada_uid: str = "",
        context_path: str | None = None,
    ) -> int:
        """
        Aprova em lote todos os candidatos de betas_nao_revisados com llm_confidence_score >= score_minimo
        (restritos a escalada_uid se informado), empilhando um único grupo Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2

        limiar = int(score_minimo)
        uid_filtro = escalada_uid.strip()
        raiz = getattr(
            self.model.obter_croqui_readonly(), "_obj", self.model.obter_croqui_readonly()
        )

        alvos: list[tuple[Any, Any, list[tuple[int, Any]]]] = []
        total_aprovados = 0
        for cur_esc in raiz.curadoria_betas.conteudo.escaladas:
            if uid_filtro and cur_esc.escalada_uid != uid_filtro:
                continue
            esc_obj = self.model.obter_objeto_por_uid(cur_esc.escalada_uid)
            if esc_obj is None:
                continue
            esc_raw = getattr(esc_obj, "_obj", esc_obj)
            itens_match = [
                (idx, cand)
                for idx, cand in enumerate(cur_esc.betas_nao_revisados)
                if int(cand.resultado_llm.llm_confidence_score) >= limiar
            ]
            if itens_match:
                alvos.append((esc_raw, cur_esc, itens_match))
                total_aprovados += len(itens_match)

        if total_aprovados == 0:
            return 0

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo(f"Aprovar Betas >= {limiar}%")
        try:
            for esc_raw, cur_esc, itens_match in alvos:
                midias_aprovadas = [
                    beta_pb2.MidiaBeta(
                        url=cand.midia.url,
                        titulo=cand.midia.titulo,
                        fonte=cand.midia.fonte,
                    )
                    for _idx, cand in itens_match
                ]
                for idx_rem, cand_rem in reversed(itens_match):
                    self._executar_comando(
                        CmdRemoverRepeated(
                            model=self.model,
                            alvo=cur_esc,
                            campo_nome="betas_nao_revisados",
                            index=idx_rem,
                            valor_removido=cand_rem,
                            context_path=ctx,
                        )
                    )
                for midia_ap in midias_aprovadas:
                    self._executar_comando(
                        CmdAdicionarRepeated(
                            model=self.model,
                            alvo=esc_raw,
                            campo_nome="betas",
                            index=len(esc_raw.betas),
                            valor=midia_ap,
                            context_path=ctx,
                        )
                    )
        finally:
            self.finalizar_grupo_undo()
        return total_aprovados

    def rejeitar_betas_nao_revisados_por_score(
        self,
        score_maximo_exclusivo: int,
        escalada_uid: str = "",
        context_path: str | None = None,
    ) -> int:
        """
        Rejeita em lote todos os candidatos de betas_nao_revisados com llm_confidence_score < score_maximo_exclusivo
        (restritos a escalada_uid se informado), movendo-os para betas_rejeitados em um único grupo Undo/Redo.
        """
        from aresta_api.proto.generated import beta_pb2

        limiar = int(score_maximo_exclusivo)
        uid_filtro = escalada_uid.strip()
        raiz = getattr(
            self.model.obter_croqui_readonly(), "_obj", self.model.obter_croqui_readonly()
        )

        alvos: list[tuple[Any, list[tuple[int, Any]]]] = []
        total_rejeitados = 0
        for cur_esc in raiz.curadoria_betas.conteudo.escaladas:
            if uid_filtro and cur_esc.escalada_uid != uid_filtro:
                continue
            if self.model.obter_objeto_por_uid(cur_esc.escalada_uid) is None:
                continue
            itens_match = [
                (idx, cand)
                for idx, cand in enumerate(cur_esc.betas_nao_revisados)
                if int(cand.resultado_llm.llm_confidence_score) < limiar
            ]
            if itens_match:
                alvos.append((cur_esc, itens_match))
                total_rejeitados += len(itens_match)

        if total_rejeitados == 0:
            return 0

        ctx = context_path or self.contexto_atual_path
        self.iniciar_grupo_undo(f"Rejeitar Betas < {limiar}%")
        try:
            for cur_esc, itens_match in alvos:
                midias_rej = [
                    beta_pb2.MidiaBeta(
                        url=cand.midia.url,
                        titulo=cand.midia.titulo,
                        fonte=cand.midia.fonte,
                    )
                    for _idx, cand in itens_match
                ]
                for idx_rem, cand_rem in reversed(itens_match):
                    self._executar_comando(
                        CmdRemoverRepeated(
                            model=self.model,
                            alvo=cur_esc,
                            campo_nome="betas_nao_revisados",
                            index=idx_rem,
                            valor_removido=cand_rem,
                            context_path=ctx,
                        )
                    )
                for midia_r in midias_rej:
                    self._executar_comando(
                        CmdAdicionarRepeated(
                            model=self.model,
                            alvo=cur_esc,
                            campo_nome="betas_rejeitados",
                            index=len(cur_esc.betas_rejeitados),
                            valor=midia_r,
                            context_path=ctx,
                        )
                    )
        finally:
            self.finalizar_grupo_undo()
        return total_rejeitados
