from pathlib import Path
from PyQt6.QtGui import QUndoStack
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarRepeatedItem
)

class MapasController:
    """
    Controller para interações específicas do Editor de Mapas.
    Despacha comandos para o Model através de QUndoCommand.
    """
    
    def __init__(self, model: CroquiModel, undo_stack: QUndoStack):
        self.model = model
        self.undo_stack = undo_stack
        self.caminho_db = None
        self.contexto_atual_path = None
        
    def set_contexto(self, path):
        self.contexto_atual_path = path
        
    def set_caminho_db(self, caminho):
        self.caminho_db = Path(caminho)

    def iniciar_grupo_undo(self, texto: str):
        """Inicia um macro de undo/redo para agrupar múltiplos comandos em um só."""
        if self.undo_stack is not None:
            self.undo_stack.beginMacro(texto)

    def finalizar_grupo_undo(self):
        """Finaliza o macro atual de undo/redo."""
        if self.undo_stack is not None:
            self.undo_stack.endMacro()

    def mover_ponto_de_interesse(self, historico, chave_mapa, idx_poi, estado_inicial, estado_final, widget_editor):
        from editor.commands.comandos_mapas import CmdMoverPonto
        historico.executar(CmdMoverPonto(chave_mapa, idx_poi, estado_inicial, estado_final, widget_editor))

    def converter_boxes_para_circulos(self, msg_mapa_proxy, indices):
        """Converte múltiplos POIs do tipo box para circular de uma só vez."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import ReadOnlyProxy
        from editor.commands.comandos_protobuf import CmdAlterarMultiplosRepeatedItems
        
        alteracoes = []
        for index in indices:
            poi_antigo = msg_mapa_proxy.pontos_de_interesse[index]
            if not poi_antigo.HasField('box'):
                continue
                
            poi_novo = croqui_pb2.Mapa.PontoDeInteresse()
            if isinstance(poi_antigo, ReadOnlyProxy):
                poi_novo.CopyFrom(poi_antigo._obj)
            else:
                poi_novo.CopyFrom(poi_antigo)
            
            box = poi_antigo.box
            r = (box.comprimento + box.largura) / 4.0
            
            poi_novo.ClearField('tipo_area')
            poi_novo.circular.x = box.x
            poi_novo.circular.y = box.y
            poi_novo.circular.raio = int(round(r))
            
            alteracoes.append((index, poi_antigo, poi_novo))
            
        if alteracoes:
            cmd = CmdAlterarMultiplosRepeatedItems(
                model=self.model,
                msg=msg_mapa_proxy,
                campo_nome="pontos_de_interesse",
                alteracoes=alteracoes,
                context_path=self.contexto_atual_path
            )
            self.undo_stack.push(cmd)

    def adicionar_poi(self, msg_mapa_proxy, poi_novo):
        """Adiciona um POI ao mapa."""
        from aresta_api.proto.generated.croqui_pb2 import Mapa
        index = len(msg_mapa_proxy.pontos_de_interesse)
        # Assuming msg_mapa_proxy gives us the context we need, wait, CmdAdicionarRepeated needs the raw message?
        # CmdAdicionarRepeated handles unwrapping the proxy inside Model._adicionar_repeated, but let's pass proxy directly
        cmd = CmdAdicionarRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor=poi_novo,
            context_path=self.contexto_atual_path
        )
        self.undo_stack.push(cmd)

    def deletar_poi(self, msg_mapa_proxy, index):
        """Remove um POI do mapa."""
        poi_removido = msg_mapa_proxy.pontos_de_interesse[index]
        cmd = CmdRemoverRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor_removido=poi_removido,
            context_path=self.contexto_atual_path
        )
        self.undo_stack.push(cmd)

    def mover_poi(self, msg_mapa_proxy, index, poi_antigo, poi_novo):
        """Altera um POI (posição, nome, etc)."""
        cmd = CmdAlterarRepeatedItem(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor_antigo=poi_antigo,
            valor_novo=poi_novo,
            context_path=self.contexto_atual_path
        )
        self.undo_stack.push(cmd)

    def adicionar_referencia(self, msg_mapa_proxy, ref_nova):
        """Adiciona uma referência ao mapa."""
        index = len(msg_mapa_proxy.referencias)
        cmd = CmdAdicionarRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="referencias",
            index=index,
            valor=ref_nova,
            context_path=self.contexto_atual_path
        )
        self.undo_stack.push(cmd)

    def deletar_referencia(self, msg_mapa_proxy, index):
        """Remove uma referência do mapa."""
        ref_removida = msg_mapa_proxy.referencias[index]
        cmd = CmdRemoverRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="referencias",
            index=index,
            valor_removido=ref_removida,
            context_path=self.contexto_atual_path
        )
        self.undo_stack.push(cmd)

    def alterar_referencia(self, msg_mapa_proxy, index, ref_antiga, ref_nova):
        """Altera uma referência."""
        cmd = CmdAlterarRepeatedItem(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="referencias",
            index=index,
            valor_antigo=ref_antiga,
            valor_novo=ref_nova,
            context_path=self.contexto_atual_path
        )
        self.undo_stack.push(cmd)

        
    def obter_caminho_imagem_mapa(self, msg_mapa_proxy):
        """Retorna o caminho absoluto para a imagem do mapa."""
        if not self.caminho_db or not msg_mapa_proxy.caminho_imagem_mapa:
            return None
        return self.caminho_db / msg_mapa_proxy.caminho_imagem_mapa
