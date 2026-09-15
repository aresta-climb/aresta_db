# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Any, List, Dict, Tuple, Set
from pathlib import Path
from editor.models.croqui_model import CroquiModel
from editor.commands.comandos_protobuf import (
    CmdAdicionarRepeated,
    CmdRemoverRepeated,
    CmdAlterarRepeatedItem,
)


class MapasController:
    """
    Controller para interações específicas do Editor de Mapas.
    Despacha comandos para o Model através de QUndoCommand / GerenciadorHistorico.
    """
    
    def __init__(self, model: CroquiModel, undo_stack: Any) -> None:
        self.model: CroquiModel = model
        self.undo_stack: Any = undo_stack
        self.caminho_db: Optional[Path] = None
        self.contexto_atual_path: Optional[str] = None
        
    def set_contexto(self, path: Optional[str]) -> None:
        self.contexto_atual_path = path
        
    def set_caminho_db(self, caminho: Any) -> None:
        self.caminho_db = Path(caminho) if caminho else None

    def obter_pilha(self) -> Any:
        """Retorna a QUndoStack subjacente se estiver usando GerenciadorHistorico ou QUndoStack."""
        if hasattr(self.undo_stack, "obter_pilha"):
            return self.undo_stack.obter_pilha()
        return self.undo_stack

    def _executar_comando(self, cmd: Any) -> None:
        """Despacha comando pelo GerenciadorHistorico (persistindo no diário) ou diretamente na pilha."""
        if hasattr(self.undo_stack, "executar"):
            self.undo_stack.executar(cmd)
        elif hasattr(self.undo_stack, "push"):
            self.undo_stack.push(cmd)
        else:
            cmd.redo()

    def iniciar_grupo_undo(self, texto: str) -> None:
        """Inicia um macro de undo/redo para agrupar múltiplos comandos em um só."""
        pilha = self.obter_pilha()
        if pilha is not None:
            pilha.beginMacro(texto)

    def finalizar_grupo_undo(self) -> None:
        """Finaliza o macro atual de undo/redo."""
        pilha = self.obter_pilha()
        if pilha is not None:
            pilha.endMacro()


    def converter_boxes_para_circulos(self, msg_mapa_proxy: Any, indices: List[int]) -> None:
        """Converte múltiplos POIs do tipo box para circular de uma só vez."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import _copia_segura
        from editor.commands.comandos_protobuf import CmdAlterarMultiplosRepeatedItems
        
        alteracoes = []
        for index in indices:
            poi_antigo = msg_mapa_proxy.pontos_de_interesse[index]
            if not poi_antigo.HasField('retangulo'):
                continue
                
            poi_novo = _copia_segura(poi_antigo)
            box = poi_antigo.retangulo
            r = (box.comprimento + box.largura) / 4.0
            
            poi_novo.ClearField('tipo_area')
            poi_novo.circulo.x = box.x
            poi_novo.circulo.y = box.y
            poi_novo.circulo.raio = int(round(r))
            
            alteracoes.append((index, poi_antigo, poi_novo))
            
        if alteracoes:
            cmd = CmdAlterarMultiplosRepeatedItems(
                model=self.model,
                msg=msg_mapa_proxy,
                campo_nome="pontos_de_interesse",
                alteracoes=alteracoes,
                context_path=self.contexto_atual_path
            )
            self._executar_comando(cmd)

    def converter_circulos_para_boxes(self, msg_mapa_proxy: Any, indices: List[int]) -> None:
        """Converte múltiplos POIs do tipo circular para box de uma só vez."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import _copia_segura
        from editor.commands.comandos_protobuf import CmdAlterarMultiplosRepeatedItems
        
        alteracoes = []
        for index in indices:
            poi_antigo = msg_mapa_proxy.pontos_de_interesse[index]
            if not poi_antigo.HasField('circulo'):
                continue
                
            poi_novo = _copia_segura(poi_antigo)
            circ = poi_antigo.circulo
            r = circ.raio
            
            poi_novo.ClearField('tipo_area')
            poi_novo.retangulo.x = circ.x
            poi_novo.retangulo.y = circ.y
            poi_novo.retangulo.comprimento = r * 2
            poi_novo.retangulo.largura = r * 2
            
            alteracoes.append((index, poi_antigo, poi_novo))
            
        if alteracoes:
            cmd = CmdAlterarMultiplosRepeatedItems(
                model=self.model,
                msg=msg_mapa_proxy,
                campo_nome="pontos_de_interesse",
                alteracoes=alteracoes,
                context_path=self.contexto_atual_path
            )
            self._executar_comando(cmd)

    def adicionar_poi(self, msg_mapa_proxy: Any, poi_novo: Any) -> None:
        """Adiciona um POI ao mapa."""
        index = len(msg_mapa_proxy.pontos_de_interesse)
        cmd = CmdAdicionarRepeated(
            model=self.model,
            msg=msg_mapa_proxy,
            campo_nome="pontos_de_interesse",
            index=index,
            valor=poi_novo,
            context_path=self.contexto_atual_path
        )
        self._executar_comando(cmd)

    def deletar_poi(self, msg_mapa_proxy: Any, index: int) -> None:
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
        self._executar_comando(cmd)

    def mover_poi(self, msg_mapa_proxy: Any, index: int, poi_antigo: Any, poi_novo: Any) -> None:
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
        self._executar_comando(cmd)

    def alterar_cor_poi(self, msg_mapa_proxy: Any, index: int, nova_cor: str) -> None:
        """Altera a cor de um POI ou elemento visual com suporte a Undo/Redo."""
        from editor.models.readonly_proxy import _copia_segura

        poi_antigo = msg_mapa_proxy.pontos_de_interesse[index]
        poi_novo = _copia_segura(poi_antigo)
        poi_novo.cor = nova_cor
        self.mover_poi(msg_mapa_proxy, index, poi_antigo, poi_novo)

    def adicionar_linha(
        self,
        msg_mapa_proxy: Any,
        id_linha: str,
        label: str = "",
        nos: Optional[List[Dict[str, Any]]] = None,
        estilo: Any = None,
        cor: str = "",
        texto_visivel: str = "",
        espessura: int = 3
    ) -> None:
        """Cria e adiciona uma LinhaTrajeto ao mapa com suporte a Undo/Redo."""
        from aresta_api.proto.generated import croqui_pb2

        cor_final = cor if cor else "#FFD600"
        poi_novo = croqui_pb2.Mapa.PontoDeInteresse(id=id_linha, label=label, cor=cor_final)
        if texto_visivel:
            poi_novo.texto_visivel = texto_visivel
        if estilo is not None:
            poi_novo.linha.estilo = estilo
        else:
            poi_novo.linha.estilo = croqui_pb2.LinhaTrajeto.EstiloTraco.TRACEJADO
        poi_novo.linha.espessura = int(espessura)

        if nos:
            for n in nos:
                no_msg = poi_novo.linha.conteudo.nos.add()
                no_msg.x = int(n.get("x", 0))
                no_msg.y = int(n.get("y", 0))
                if "tipo" in n and n["tipo"] is not None:
                    no_msg.tipo = n["tipo"]
                if "rotulo" in n and n["rotulo"]:
                    no_msg.rotulo = str(n["rotulo"])

        self.adicionar_poi(msg_mapa_proxy, poi_novo)

    def alterar_espessura_linha(self, msg_mapa_proxy: Any, index_poi: int, nova_espessura: int) -> None:
        """Altera a espessura em pixels do traçado da linha com suporte a Undo/Redo."""
        from editor.models.readonly_proxy import _copia_segura

        poi_antigo = msg_mapa_proxy.pontos_de_interesse[index_poi]
        poi_novo = _copia_segura(poi_antigo)

        if poi_novo.HasField("linha"):
            poi_novo.linha.espessura = int(nova_espessura)
            self.mover_poi(msg_mapa_proxy, index_poi, poi_antigo, poi_novo)

    def alterar_tipo_no(self, msg_mapa_proxy: Any, index_poi: int, index_no: int, novo_tipo: Any) -> None:
        """Altera o tipo semântico de um nó em uma linha de traçado."""
        from editor.models.readonly_proxy import _copia_segura

        poi_antigo = msg_mapa_proxy.pontos_de_interesse[index_poi]
        poi_novo = _copia_segura(poi_antigo)

        if poi_novo.HasField("linha") and len(poi_novo.linha.conteudo.nos) > index_no:
            poi_novo.linha.conteudo.nos[index_no].tipo = novo_tipo
            self.mover_poi(msg_mapa_proxy, index_poi, poi_antigo, poi_novo)

    def adicionar_no_linha(self, msg_mapa_proxy: Any, index_poi: int, index_pos: int, novo_no_dict: Dict[str, Any]) -> None:
        """Insere um novo nó na linha em uma posição específica."""
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import _copia_segura

        poi_antigo = msg_mapa_proxy.pontos_de_interesse[index_poi]
        poi_novo = _copia_segura(poi_antigo)

        if poi_novo.HasField("linha"):
            nos_existentes = list(poi_novo.linha.conteudo.nos)
            no_msg = croqui_pb2.NoTrajeto(
                x=int(novo_no_dict.get("x", 0)),
                y=int(novo_no_dict.get("y", 0)),
                tipo=novo_no_dict.get("tipo", croqui_pb2.NoTrajeto.TipoNo.PASSAGEM),
                rotulo=str(novo_no_dict.get("rotulo", ""))
            )
            nos_existentes.insert(index_pos, no_msg)
            poi_novo.linha.conteudo.ClearField("nos")
            for n in nos_existentes:
                poi_novo.linha.conteudo.nos.append(n)
            self.mover_poi(msg_mapa_proxy, index_poi, poi_antigo, poi_novo)

    def remover_no_linha(self, msg_mapa_proxy: Any, index_poi: int, index_no: int) -> None:
        """Remove um nó da linha."""
        from editor.models.readonly_proxy import _copia_segura

        poi_antigo = msg_mapa_proxy.pontos_de_interesse[index_poi]
        poi_novo = _copia_segura(poi_antigo)

        if poi_novo.HasField("linha") and len(poi_novo.linha.conteudo.nos) > index_no:
            nos_existentes = list(poi_novo.linha.conteudo.nos)
            del nos_existentes[index_no]
            poi_novo.linha.conteudo.ClearField("nos")
            for n in nos_existentes:
                poi_novo.linha.conteudo.nos.append(n)
            self.mover_poi(msg_mapa_proxy, index_poi, poi_antigo, poi_novo)

    def adicionar_referencia(self, msg_mapa_proxy: Any, ref_nova: Any) -> None:
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
        self._executar_comando(cmd)

    def deletar_referencia(self, msg_mapa_proxy: Any, index: int) -> None:
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
        self._executar_comando(cmd)

    def alterar_referencia(self, msg_mapa_proxy: Any, index: int, ref_antiga: Any, ref_nova: Any) -> None:
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
        self._executar_comando(cmd)

    def obter_caminho_imagem_mapa(self, msg_mapa_proxy: Any) -> Optional[Path]:
        """Retorna o caminho absoluto para a imagem do mapa."""
        if not self.caminho_db or not msg_mapa_proxy.caminho_imagem_mapa:
            return None
        return Path(self.caminho_db) / str(msg_mapa_proxy.caminho_imagem_mapa)


    def substituir_imagem(
        self,
        caminho_relativo: str,
        bytes_novo: bytes,
        bytes_antigo: Optional[bytes] = None,
        context_path: Optional[str] = None,
    ) -> None:
        """Despacha comando de substituição de imagem em memória RAM via GerenciadorHistorico / QUndoStack."""
        from editor.commands.comandos_protobuf import CmdSubstituirImagemMemoria
        if bytes_antigo is None:
            bytes_antigo = self.model.obter_bytes_imagem(caminho_relativo)
        ctx = context_path if context_path is not None else self.contexto_atual_path
        cmd = CmdSubstituirImagemMemoria(self.model, caminho_relativo, bytes_antigo, bytes_novo, ctx)
        self._executar_comando(cmd)

    def adicionar_rota_com_tracado(
        self,
        msg_mapa_proxy: Any,
        msg_setor_proxy: Any,
        dados_rota: Dict[str, Any],
        pontos_trajeto: List[Tuple[float, float]],
        snaps_info: Optional[List[Any]] = None
    ) -> None:
        """
        Cria ou vincula uma escalada e adiciona seu traçado vetorial no mapa.
        Executa fatiamento automático de traçados sobrepostos ("sticky"),
        aplica a convenção semântica Ouroboulder (inícios sequenciais e topos 'A', 'B'),
        garante IDs mutuamente disjuntos em todo o setor e agrupa todas as mutações
        em um macro atômico de histórico QUndoStack (Princípios II e VII de AGENTS.md).
        """
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import _copia_segura
        from editor.core.topologia_trajeto import (
            Ponto2D,
            detectar_snap_nos,
            detectar_snap_curva,
            fatiar_linha_em_no,
            fatiar_linha_em_ponto_curva,
            fatiar_linha_triplo,
            atualizar_referencias_apos_fatiamento,
            adicionar_numero_inicio,
            obter_rotulo_escalada_no_setor,
            calcular_proximo_numero_inicio_setor,
            gerar_id_poi_disjunto_setor,
            desambiguar_topos,
        )

        nome_rota = dados_rota.get("nome", "Nova Rota")
        self.iniciar_grupo_undo(f"Adicionar Rota: {nome_rota}")

        try:
            # 1. Criação da escalada no Setor (se for nova)
            if dados_rota.get("nova", False) and msg_setor_proxy is not None:
                nomes_existentes = []
                for esc in msg_setor_proxy.escaladas:
                    t = esc.WhichOneof("tipo")
                    if t:
                        nomes_existentes.append(getattr(esc, t).nome)
                if nome_rota not in nomes_existentes:
                    nova_esc = croqui_pb2.Escalada()
                    tipo_str = dados_rota.get("tipo", "boulder")
                    grau_str = dados_rota.get("grau", "")

                    if tipo_str == "boulder":
                        nova_esc.boulder.nome = nome_rota
                        if grau_str:
                            grau_enum = getattr(croqui_pb2.GrauBoulder, grau_str.upper(), None)
                            if grau_enum is not None:
                                nova_esc.boulder.dificuldade = grau_enum
                    elif tipo_str == "via_esportiva":
                        nova_esc.via_esportiva.nome = nome_rota
                        if grau_str:
                            g_norm = grau_str.upper().replace("-", "_").replace(" ", "_")
                            if not g_norm.startswith("BR_") and not g_norm.startswith("FR_") and not g_norm.startswith("US_"):
                                g_norm = f"BR_{g_norm}"
                            grau_enum = getattr(croqui_pb2.GrauVia.GrauVia, g_norm, None) or getattr(croqui_pb2.GrauVia, g_norm, None)
                            if grau_enum is not None:
                                nova_esc.via_esportiva.dificuldade = grau_enum
                    elif tipo_str == "via_movel":
                        nova_esc.via_movel.nome = nome_rota
                    elif tipo_str == "via_multiplas_enfiadas":
                        nova_esc.via_multiplas_enfiadas.nome = nome_rota
                    elif tipo_str == "highline":
                        nova_esc.highline.nome = nome_rota

                    idx_esc = len(msg_setor_proxy.escaladas)
                    cmd_esc = CmdAdicionarRepeated(
                        model=self.model,
                        msg=msg_setor_proxy,
                        campo_nome="escaladas",
                        index=idx_esc,
                        valor=nova_esc,
                        context_path=self.contexto_atual_path
                    )
                    self._executar_comando(cmd_esc)

            # 2. Resolução do rótulo numérico inicial no escopo do setor
            rotulo_inicio = obter_rotulo_escalada_no_setor(msg_setor_proxy, nome_rota) if msg_setor_proxy else None
            if not rotulo_inicio:
                rotulo_inicio = str(calcular_proximo_numero_inicio_setor(msg_setor_proxy)) if msg_setor_proxy else "1"

            # 3. Análise topológica de traçados existentes
            linhas_existentes = [p for p in msg_mapa_proxy.pontos_de_interesse if p.HasField("linha")]
            
            # Identifica se há sobreposição e necessidade de fatiamento
            fatiou = False
            if linhas_existentes and len(pontos_trajeto) >= 2:
                # Mapeia cada ponto do trajeto contra nós e curvas existentes
                matches_nos = []
                for pt in pontos_trajeto:
                    snap_no = detectar_snap_nos(Ponto2D(pt[0], pt[1]), linhas_existentes, raio_snap=5.0)
                    matches_nos.append(snap_no)

                # Cenário Travessia: entra no meio de uma linha, compartilha trecho intermediário e sai
                for linha_cand in linhas_existentes:
                    id_cand = str(linha_cand.id)
                    indices_no_cand = [
                        m.indice_no for m in matches_nos if m is not None and m.id_linha == id_cand and m.indice_no is not None
                    ]
                    if len(indices_no_cand) >= 2 and indices_no_cand[0] > 0 and indices_no_cand[-1] < len(linha_cand.linha.conteudo.nos) - 1:
                        # Identificou travessia intermediária em linha_cand
                        idx_in = min(indices_no_cand)
                        idx_out = max(indices_no_cand)
                        pos_in = [i for i, m in enumerate(matches_nos) if m and m.id_linha == id_cand and m.indice_no == idx_in][0]
                        pos_out = [i for i, m in enumerate(matches_nos) if m and m.id_linha == id_cand and m.indice_no == idx_out][0]

                        ids_reservados: Set[str] = set()
                        id_sub1 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                        ids_reservados.add(id_sub1)
                        id_sub2 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                        ids_reservados.add(id_sub2)
                        id_sub3 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                        ids_reservados.add(id_sub3)
                        sub1, sub2, sub3 = fatiar_linha_triplo(linha_cand, idx_in, idx_out, id_sub1, id_sub2, id_sub3)

                        # Remove linha original
                        idx_original = list(msg_mapa_proxy.pontos_de_interesse).index(linha_cand)
                        self.deletar_poi(msg_mapa_proxy, idx_original)
                        self.adicionar_poi(msg_mapa_proxy, sub1)
                        self.adicionar_poi(msg_mapa_proxy, sub2)
                        self.adicionar_poi(msg_mapa_proxy, sub3)

                        # Atualiza referências que apontavam para linha_cand
                        for i_ref, ref in enumerate(msg_mapa_proxy.referencias):
                            if id_cand in ref.ids:
                                ref_antiga = _copia_segura(ref)
                                ref_nova = _copia_segura(ref)
                                atualizar_referencias_apos_fatiamento([ref_nova], id_cand, [id_sub1, id_sub2, id_sub3])
                                self.alterar_referencia(msg_mapa_proxy, i_ref, ref_antiga, ref_nova)

                        # Cria entrada própria da travessia (se houver pontos antes da junção)
                        ids_travessia = []
                        if pos_in > 0:
                            id_ent = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                            ids_reservados.add(id_ent)
                            pts_ent = [{"x": p[0], "y": p[1]} for p in pontos_trajeto[:pos_in + 1]]
                            self.adicionar_linha(msg_mapa_proxy, id_linha=id_ent, nos=pts_ent)
                            ids_travessia.append(id_ent)
                        
                        ids_travessia.append(id_sub2)

                        # Cria saída própria da travessia (se houver pontos após a junção)
                        if pos_out < len(pontos_trajeto) - 1:
                            id_sai = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                            ids_reservados.add(id_sai)
                            pts_sai = [{"x": p[0], "y": p[1]} for p in pontos_trajeto[pos_out:]]
                            self.adicionar_linha(msg_mapa_proxy, id_linha=id_sai, nos=pts_sai)
                            ids_travessia.append(id_sai)

                        # Cria referência da travessia
                        ref_trav = croqui_pb2.Mapa.Referencia(escalada=nome_rota, ids=ids_travessia)
                        self.adicionar_referencia(msg_mapa_proxy, ref_trav)
                        fatiou = True
                        break

                if not fatiou:
                    # Cenário Bifurcação: compartilha o início e fatiamento em nó ou curva
                    for linha_cand in linhas_existentes:
                        id_cand = str(linha_cand.id)
                        p_primeiro = Ponto2D(pontos_trajeto[0][0], pontos_trajeto[0][1])
                        snap_inicio = detectar_snap_nos(p_primeiro, [linha_cand], raio_snap=5.0)

                        if snap_inicio and snap_inicio.indice_no == 0:
                            # A nova rota começa no mesmo ponto inicial de linha_cand
                            # Procura o ponto de bifurcação (último ponto compartilhado)
                            idx_bifurcacao_novo = 0
                            no_corte_idx = None
                            curva_corte_info = None

                            for idx_p, pt in enumerate(pontos_trajeto):
                                p_cur = Ponto2D(pt[0], pt[1])
                                s_no = detectar_snap_nos(p_cur, [linha_cand], raio_snap=5.0)
                                if s_no:
                                    idx_bifurcacao_novo = idx_p
                                    no_corte_idx = s_no.indice_no
                                else:
                                    s_curva = detectar_snap_curva(p_cur, [linha_cand], raio_snap=5.0)
                                    if s_curva:
                                        idx_bifurcacao_novo = idx_p
                                        curva_corte_info = s_curva
                                    else:
                                        break

                            if (no_corte_idx is not None and 0 < no_corte_idx < len(linha_cand.linha.conteudo.nos) - 1) or curva_corte_info is not None:
                                ids_reservados = set()
                                id_sub1 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                                ids_reservados.add(id_sub1)
                                id_sub2 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                                ids_reservados.add(id_sub2)

                                if no_corte_idx is not None and 0 < no_corte_idx < len(linha_cand.linha.conteudo.nos) - 1:
                                    sub1, sub2 = fatiar_linha_em_no(linha_cand, no_corte_idx, id_sub1, id_sub2)
                                else:
                                    assert curva_corte_info is not None
                                    assert curva_corte_info.indice_segmento is not None
                                    sub1, sub2 = fatiar_linha_em_ponto_curva(
                                        linha_cand,
                                        curva_corte_info.coordenada,
                                        curva_corte_info.indice_segmento,
                                        id_sub1,
                                        id_sub2
                                    )

                                # Atualiza rótulo de início compartilhado (ex: '1, 2')
                                rot_antigo = str(sub1.linha.conteudo.nos[0].rotulo)
                                rot_novo = adicionar_numero_inicio(rot_antigo, int(rotulo_inicio))
                                sub1.linha.conteudo.nos[0].rotulo = rot_novo
                                sub1.linha.conteudo.nos[0].tipo = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR

                                # Substitui linha_cand pelas sublinhas
                                idx_original = list(msg_mapa_proxy.pontos_de_interesse).index(linha_cand)
                                self.deletar_poi(msg_mapa_proxy, idx_original)
                                self.adicionar_poi(msg_mapa_proxy, sub1)
                                self.adicionar_poi(msg_mapa_proxy, sub2)

                                # Atualiza referências existentes de linha_cand
                                for i_ref, ref in enumerate(msg_mapa_proxy.referencias):
                                    if id_cand in ref.ids:
                                        ref_antiga = _copia_segura(ref)
                                        ref_nova = _copia_segura(ref)
                                        atualizar_referencias_apos_fatiamento([ref_nova], id_cand, [id_sub1, id_sub2])
                                        self.alterar_referencia(msg_mapa_proxy, i_ref, ref_antiga, ref_nova)

                                # Cria trecho exclusivo da nova rota
                                id_novo = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
                                ids_reservados.add(id_novo)
                                pts_exclusivos = [{"x": p[0], "y": p[1]} for p in pontos_trajeto[idx_bifurcacao_novo:]]
                                self.adicionar_linha(msg_mapa_proxy, id_linha=id_novo, nos=pts_exclusivos)

                                # Referência da nova rota
                                ref_nova = croqui_pb2.Mapa.Referencia(escalada=nome_rota, ids=[id_sub1, id_novo])
                                self.adicionar_referencia(msg_mapa_proxy, ref_nova)
                                fatiou = True
                                break

            # 4. Caso simples (sem fatiamento de linha existente)
            if not fatiou:
                id_nova_linha = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha") if msg_setor_proxy else "linha_1"
                nos_dicts = []
                for idx, pt in enumerate(pontos_trajeto):
                    tipo_no = croqui_pb2.NoTrajeto.TipoNo.PASSAGEM
                    rotulo_no = ""
                    if idx == 0:
                        tipo_no = croqui_pb2.NoTrajeto.TipoNo.CIRCULO_IDENTIFICADOR
                        rotulo_no = rotulo_inicio
                    nos_dicts.append({
                        "x": pt[0],
                        "y": pt[1],
                        "tipo": tipo_no,
                        "rotulo": rotulo_no
                    })

                self.adicionar_linha(msg_mapa_proxy, id_linha=id_nova_linha, nos=nos_dicts)
                nova_ref = croqui_pb2.Mapa.Referencia(escalada=nome_rota, ids=[id_nova_linha])
                self.adicionar_referencia(msg_mapa_proxy, nova_ref)

            # 5. Desambiguação de topos sob demanda
            linhas_atuais = [p for p in msg_mapa_proxy.pontos_de_interesse if p.HasField("linha")]
            refs_atuais = list(msg_mapa_proxy.referencias)
            linhas_copia = [_copia_segura(l) for l in linhas_atuais]
            desambiguar_topos(linhas_copia, refs_atuais)

            # Aplica modificações de topos calculadas
            for idx_poi, (l_original, l_modificada) in enumerate(zip(linhas_atuais, linhas_copia)):
                if l_original != l_modificada:
                    self.mover_poi(msg_mapa_proxy, idx_poi, l_original, l_modificada)

        finally:
            self.finalizar_grupo_undo()

    def separar_linha_em_no(
        self,
        msg_mapa_proxy: Any,
        msg_setor_proxy: Optional[Any],
        id_linha: str,
        indice_no: int
    ) -> Tuple[str, str]:
        """
        Divide uma linha existente em duas sublinhas no nó de índice especificado.
        Substitui o POI antigo pelas duas novas sublinhas com IDs disjuntos e
        atualiza todas as referências existentes mantendo a ordenação.
        Tudo executado dentro de uma transação atômica no QUndoStack.
        """
        from aresta_api.proto.generated import croqui_pb2
        from editor.models.readonly_proxy import _copia_segura
        from editor.core.topologia_trajeto import (
            fatiar_linha_em_no,
            gerar_id_poi_disjunto_setor,
            atualizar_referencias_apos_fatiamento,
        )

        idx_linha = -1
        linha_alvo = None
        for idx, p in enumerate(msg_mapa_proxy.pontos_de_interesse):
            if str(p.id) == id_linha and p.HasField("linha"):
                idx_linha = idx
                linha_alvo = p
                break

        if idx_linha == -1 or linha_alvo is None:
            raise ValueError(f"Linha com ID '{id_linha}' não encontrada no mapa.")

        nos = linha_alvo.linha.conteudo.nos
        if indice_no <= 0 or indice_no >= len(nos) - 1:
            raise ValueError(
                f"O índice do nó para separação ({indice_no}) deve ser intermediário "
                f"(entre 1 e {len(nos) - 2})."
            )

        self.iniciar_grupo_undo(f"Separar Traço no Nó {indice_no}")
        try:
            ids_reservados: Set[str] = set()
            id_sub1 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
            ids_reservados.add(id_sub1)
            id_sub2 = gerar_id_poi_disjunto_setor(msg_setor_proxy, "linha", ids_reservados=ids_reservados)
            ids_reservados.add(id_sub2)

            sub1, sub2 = fatiar_linha_em_no(
                linha_alvo,
                indice_no,
                id_sub1,
                id_sub2,
                preservar_tipo_no_corte=True
            )

            # 1. Substitui a linha original pelas duas novas sublinhas
            self.deletar_poi(msg_mapa_proxy, idx_linha)
            self.adicionar_poi(msg_mapa_proxy, sub1)
            self.adicionar_poi(msg_mapa_proxy, sub2)

            # 2. Atualiza referências existentes de id_linha
            for i_ref, ref in enumerate(msg_mapa_proxy.referencias):
                if id_linha in ref.ids:
                    ref_antiga = _copia_segura(ref)
                    ref_nova = _copia_segura(ref)
                    atualizar_referencias_apos_fatiamento([ref_nova], id_linha, [id_sub1, id_sub2])
                    self.alterar_referencia(msg_mapa_proxy, i_ref, ref_antiga, ref_nova)

            return id_sub1, id_sub2
        finally:
            self.finalizar_grupo_undo()


