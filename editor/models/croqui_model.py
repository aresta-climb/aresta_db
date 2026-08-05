# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

from editor.models.readonly_proxy import _copia_segura
from PyQt6.QtCore import QObject, pyqtSignal
from google.protobuf.message import Message

class CroquiModel(QObject):
    """
    Modelo de domínio que encapsula os dados do Croqui (Protobuf).
    Emite sinais Qt quando ocorre alguma mutação nos dados subjacentes.
    As mutações devem ser feitas EXCLUSIVAMENTE via Comandos na arquitetura MVC.
    """
    
    # Sinais genéricos para a View assinar
    dado_alterado = pyqtSignal(object, str) # msg_pai, campo_nome
    repeated_adicionado = pyqtSignal(object, str, int) # msg_pai, campo_nome, indice
    repeated_removido = pyqtSignal(object, str, int) # msg_pai, campo_nome, indice
    repeated_item_alterado = pyqtSignal(object, str, int) # msg_pai, campo_nome, indice
    repeated_movido = pyqtSignal(object, str, int, int) # msg_pai, campo_nome, index_from, index_to
    oneof_alterado = pyqtSignal(object, str) # msg_pai, oneof_nome
    foco_requisitado = pyqtSignal(object) # msg_id


    @staticmethod
    def __desembrulhar_proxy(obj):
        from editor.models.readonly_proxy import ReadOnlyProxy, ReadOnlyListProxy, ReadOnlyExtensionProxy
        if isinstance(obj, ReadOnlyProxy):
            return object.__getattribute__(obj, "_obj")
        if isinstance(obj, ReadOnlyExtensionProxy):
            return object.__getattribute__(obj, "_obj")
        if isinstance(obj, ReadOnlyListProxy):
            return object.__getattribute__(obj, "_lst")
        return obj

    def __init__(self, croqui, parent=None):
        super().__init__(parent)
        self.__croqui = croqui
        from editor.models.readonly_proxy import ReadOnlyProxy
        self.__croqui_proxy = ReadOnlyProxy(self.__croqui)

    def obter_croqui_readonly(self):
        """Retorna uma view somente leitura do Croqui encapsulado."""
        return self.__croqui_proxy


    def _set_primitivo(self, msg, campo_nome, valor_novo):
        msg = self.__desembrulhar_proxy(msg)
        setattr(msg, campo_nome, _copia_segura(valor_novo))
        self.dado_alterado.emit(msg, campo_nome)

    def _adicionar_repeated(self, msg, campo_nome, index, valor):
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        repeated_container.insert(index, _copia_segura(valor))
        self.repeated_adicionado.emit(msg, campo_nome, index)

    def _remover_repeated(self, msg, campo_nome, index):
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        repeated_container.pop(index)
        self.repeated_removido.emit(msg, campo_nome, index)

    def _mover_repeated(self, msg, campo_nome, index_from, index_to):
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        item = repeated_container.pop(index_from)
        repeated_container.insert(index_to, item)
        self.repeated_movido.emit(msg, campo_nome, index_from, index_to)

    def _alterar_repeated_item(self, msg, campo_nome, index, valor_novo):
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        
        valor_seguro = _copia_segura(valor_novo)
        if isinstance(valor_seguro, Message):
            repeated_container[index].CopyFrom(valor_seguro)
        else:
            repeated_container[index] = valor_seguro
        
        self.repeated_item_alterado.emit(msg, campo_nome, index)

    def _alterar_oneof(self, msg, oneof_nome, nome_antigo, campo_novo, valor_novo):
        msg = self.__desembrulhar_proxy(msg)
        # Limpa o antigo se existir
        if nome_antigo is not None:
            msg.ClearField(nome_antigo)
            
        # Seta o novo
        if campo_novo is not None:
            valor_seguro = _copia_segura(valor_novo)
            if isinstance(valor_seguro, Message):
                getattr(msg, campo_novo).CopyFrom(valor_seguro)
            else:
                setattr(msg, campo_novo, valor_seguro)
                
        campo_afetado = oneof_nome or nome_antigo or campo_novo
        self.oneof_alterado.emit(msg, campo_afetado)



    def _alterar_metadados_caminho_novo(self, msg, ext_descriptor, valor_novo):
        msg = self.__desembrulhar_proxy(msg)
        msg.Extensions[ext_descriptor].caminho_novo = valor_novo
        self.dado_alterado.emit(msg, ext_descriptor.name)

    def carregar_arquivos_externos(self, caminho_db):
        """Carrega e mescla no protobuf os arquivos externos de Setor/Grupo e Markdowns."""
        if not caminho_db:
            return
            
        self._caminho_db_atual = caminho_db
        from google.protobuf import json_format
        import yaml
        
        croqui_msg = self.__croqui
        
        if not caminho_db.exists():
            return

        def _ler_objeto_com_frontmatter(caminho_arquivo, message_ref, ext_descriptor):
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                content = f.read()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_str = parts[1]
                    body_str = parts[2]
                    # Se o frontmatter terminava logo na linha anterior, e o markdown começou logo depois
                    # do "---", parts[2] começará com "\n". Removemos apenas esse \n e preservamos o resto.
                    if body_str.startswith("\n"):
                        body_str = body_str[1:]
                    
                    try:
                        dados = yaml.safe_load(frontmatter_str) or {}
                    except Exception:
                        dados = {}
                    # Configura a extensão se não existir e salva os metadados
                    if not message_ref.HasExtension(ext_descriptor):
                        message_ref.Extensions[ext_descriptor].caminho_original = ""
                    
                    import json
                    message_ref.Extensions[ext_descriptor].dados_json_originais = json.dumps(dados, ensure_ascii=False)
                    
                    if body_str:
                        dados["descricao"] = body_str
                    return dados
            try:
                return yaml.safe_load(content) or {}
            except Exception:
                return {}

        def _carregar_arquivo_setor(arq_setor):
            if arq_setor.WhichOneof("arquivo") == "caminho" and arq_setor.caminho:
                nome_relativo = arq_setor.caminho
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor
                        dados_setor = _ler_objeto_com_frontmatter(caminho_arquivo, arq_setor, ArquivoSetor.ext_metadados_arquivo)
                        if dados_setor:
                            json_format.ParseDict(dados_setor, arq_setor.conteudo, ignore_unknown_fields=True)
                            arq_setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_original = nome_relativo
                            arq_setor.Extensions[ArquivoSetor.ext_metadados_arquivo].caminho_novo = nome_relativo
                            arq_setor.ClearField("caminho")
                    except Exception as e:
                        print(f"Erro ao carregar setor externo {arq_setor.caminho}: {e}")

        def _carregar_arquivo_grupo(arq_grupo):
            if arq_grupo.WhichOneof("arquivo") == "caminho" and arq_grupo.caminho:
                nome_relativo = arq_grupo.caminho
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo
                        dados_grupo = _ler_objeto_com_frontmatter(caminho_arquivo, arq_grupo, ArquivoGrupo.ext_metadados_arquivo)
                        if dados_grupo:
                            json_format.ParseDict(dados_grupo, arq_grupo.conteudo, ignore_unknown_fields=True)
                            arq_grupo.Extensions[ArquivoGrupo.ext_metadados_arquivo].caminho_original = nome_relativo
                            arq_grupo.Extensions[ArquivoGrupo.ext_metadados_arquivo].caminho_novo = nome_relativo
                            arq_grupo.ClearField("caminho")
                            for s in arq_grupo.conteudo.setores:
                                _carregar_arquivo_setor(s)
                    except Exception as e:
                        print(f"Erro ao carregar grupo externo {arq_grupo.caminho}: {e}")

        def _carregar_arquivo_mapas(arq_mapas):
            if arq_mapas.WhichOneof("arquivo") == "caminho" and arq_mapas.caminho:
                nome_relativo = arq_mapas.caminho
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoMapas
                        dados_mapas = _ler_objeto_com_frontmatter(caminho_arquivo, arq_mapas, ArquivoMapas.ext_metadados_arquivo)
                        if dados_mapas:
                            json_format.ParseDict(dados_mapas, arq_mapas.conteudo, ignore_unknown_fields=True)
                            arq_mapas.Extensions[ArquivoMapas.ext_metadados_arquivo].caminho_original = nome_relativo
                            arq_mapas.Extensions[ArquivoMapas.ext_metadados_arquivo].caminho_novo = nome_relativo
                            arq_mapas.ClearField("caminho")
                    except Exception as e:
                        print(f"Erro ao carregar mapas externos {arq_mapas.caminho}: {e}")

        # 1. Carrega Botões (Markdown)
        for botao in croqui_msg.botoes:
            if botao.HasField("destino") and botao.destino.WhichOneof("destino") == "secao_textual":
                md = botao.destino.secao_textual
                if md.WhichOneof("arquivo") == "caminho" and md.caminho:
                    nome_relativo = md.caminho
                    caminho_arquivo = caminho_db / nome_relativo
                    if caminho_arquivo.exists():
                        try:
                            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                                conteudo_md = f.read()
                            md.conteudo = conteudo_md
                            from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown
                            md.Extensions[ArquivoMarkdown.ext_metadados_arquivo].caminho_original = nome_relativo
                            md.Extensions[ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = nome_relativo
                            md.ClearField("caminho")
                        except Exception as e:
                            print(f"Erro ao carregar markdown externo {nome_relativo}: {e}")

        # 2. Carrega Picos -> Setores e Grupos
        for pico in croqui_msg.picos:
            if pico.HasField("mapas_gerais"):
                _carregar_arquivo_mapas(pico.mapas_gerais)
            for sg in pico.setores_ou_grupos:
                if sg.HasField("setor"):
                    _carregar_arquivo_setor(sg.setor)
                elif sg.HasField("grupo"):
                    _carregar_arquivo_grupo(sg.grupo)

    def extrair_arquivos_e_serializar(self, caminho_db):
        from google.protobuf.json_format import MessageToDict
        from aresta_api.proto.generated.croqui_pb2 import Croqui, ArquivoSetor, ArquivoGrupo, ArquivoMarkdown
        import yaml
        
        croqui_msg_copy = Croqui()
        croqui_msg_copy.CopyFrom(self.__croqui)

        def _reordenar_recursivamente(d_novo, d_original):
            if isinstance(d_novo, list) and isinstance(d_original, list):
                res = []
                for item_novo, item_orig in zip(d_novo, d_original):
                    res.append(_reordenar_recursivamente(item_novo, item_orig))
                if len(d_novo) > len(d_original):
                    res.extend(d_novo[len(d_original):])
                return res
            if not isinstance(d_novo, dict) or not isinstance(d_original, dict):
                return d_novo
                
            resultado = {}
            for k in d_original.keys():
                if k in d_novo:
                    resultado[k] = _reordenar_recursivamente(d_novo.pop(k), d_original[k])
            
            for k, v in d_novo.items():
                resultado[k] = v
            return resultado

        def _salvar_objeto_com_frontmatter(caminho_arquivo, dados_dict, json_original=None):
            dados = dados_dict.copy()
            descricao = dados.pop("descricao", "")
            
            if json_original:
                import json
                try:
                    d_original = json.loads(json_original)
                    dados = _reordenar_recursivamente(dados, d_original)
                except Exception as e:
                    print(f"Aviso: falha ao decodificar JSON original: {e}")

            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write("---\n")
                
                # Garante que strings compostas apenas por dígitos sejam entre aspas 
                # (evita que parser YAML confunda com números inteiros no futuro, ex: id '09' -> 09)
                def _str_representer(dumper, data):
                    style = None
                    if data.isdigit() or (data.startswith('-') and data[1:].isdigit()):
                        style = "'"
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)
                yaml.add_representer(str, _str_representer)
                
                yaml.dump(dados, f, allow_unicode=True, sort_keys=False)
                f.write("---\n")
                if descricao is not None:
                    f.write(descricao)

        def _extrair_arquivo_setor(arq_setor, arq_setor_ref):
            if not arq_setor.HasField("conteudo"):
                return
            ext = None
            if arq_setor_ref.HasExtension(ArquivoSetor.ext_metadados_arquivo):
                ext = arq_setor_ref.Extensions[ArquivoSetor.ext_metadados_arquivo]
            original_caminho = ext.caminho_original if ext else None
            novo_caminho = ext.caminho_novo if ext and ext.caminho_novo else None
            
            if not novo_caminho and original_caminho:
                novo_caminho = original_caminho
            if not novo_caminho:
                novo_caminho = f"setor_{arq_setor.conteudo.nome.replace(' ', '_').lower()}.md"
            
            if original_caminho and original_caminho != novo_caminho:
                old_file_path = caminho_db / original_caminho
                if old_file_path.exists():
                    try: old_file_path.unlink()
                    except Exception: pass
            
            conteudo_dict = MessageToDict(arq_setor.conteudo, preserving_proto_field_name=True)
            json_original = ext.dados_json_originais if ext and ext.dados_json_originais else None
            _salvar_objeto_com_frontmatter(caminho_db / novo_caminho, conteudo_dict, json_original=json_original)
            arq_setor.caminho = novo_caminho
            arq_setor.ClearField("conteudo")
            arq_setor.ClearExtension(ArquivoSetor.ext_metadados_arquivo)
            if ext:
                ext.caminho_original = novo_caminho

        def _extrair_arquivo_mapas(arq_mapas, arq_mapas_ref):
            if not arq_mapas.HasField("conteudo"):
                return
            ext = None
            from aresta_api.proto.generated.croqui_pb2 import ArquivoMapas
            if arq_mapas_ref.HasExtension(ArquivoMapas.ext_metadados_arquivo):
                ext = arq_mapas_ref.Extensions[ArquivoMapas.ext_metadados_arquivo]
            original_caminho = ext.caminho_original if ext else None
            novo_caminho = ext.caminho_novo if ext and ext.caminho_novo else None
            
            if not novo_caminho and original_caminho:
                novo_caminho = original_caminho
            if not novo_caminho:
                novo_caminho = "mapas_gerais.md"
            
            if original_caminho and original_caminho != novo_caminho:
                old_file_path = caminho_db / original_caminho
                if old_file_path.exists():
                    try: old_file_path.unlink()
                    except Exception: pass
            
            conteudo_dict = MessageToDict(arq_mapas.conteudo, preserving_proto_field_name=True)
            json_original = ext.dados_json_originais if ext and ext.dados_json_originais else None
            _salvar_objeto_com_frontmatter(caminho_db / novo_caminho, conteudo_dict, json_original=json_original)
            arq_mapas.caminho = novo_caminho
            arq_mapas.ClearField("conteudo")
            arq_mapas.ClearExtension(ArquivoMapas.ext_metadados_arquivo)
            if ext:
                ext.caminho_original = novo_caminho

        # Picos e Grupos/Setores
        for idx_pico, pico in enumerate(croqui_msg_copy.picos):
            pico_ref = self.__croqui.picos[idx_pico]
            
            if pico.HasField("mapas_gerais") and pico.mapas_gerais.HasField("conteudo"):
                _extrair_arquivo_mapas(pico.mapas_gerais, pico_ref.mapas_gerais)
                
            for idx_sg, sg in enumerate(pico.setores_ou_grupos):
                sg_ref = pico_ref.setores_ou_grupos[idx_sg]

                if sg.HasField("setor") and sg.setor.HasField("conteudo"):
                    _extrair_arquivo_setor(sg.setor, sg_ref.setor)

                elif sg.HasField("grupo") and sg.grupo.HasField("conteudo"):
                    # Extrai os setores internos primeiro
                    for idx_setor, setor_arq in enumerate(sg.grupo.conteudo.setores):
                        setor_arq_ref = sg_ref.grupo.conteudo.setores[idx_setor]
                        _extrair_arquivo_setor(setor_arq, setor_arq_ref)

                    # Agora extrai o grupo
                    ext = None
                    if sg_ref.grupo.HasExtension(ArquivoGrupo.ext_metadados_arquivo):
                        ext = sg_ref.grupo.Extensions[ArquivoGrupo.ext_metadados_arquivo]
                    original_caminho = ext.caminho_original if ext else None
                    novo_caminho = ext.caminho_novo if ext and ext.caminho_novo else None
                    
                    if not novo_caminho and original_caminho:
                        novo_caminho = original_caminho
                    if not novo_caminho:
                        novo_caminho = f"grupo_{sg.grupo.conteudo.nome.replace(' ', '_').lower()}.md"
                    
                    if original_caminho and original_caminho != novo_caminho:
                        old_file_path = caminho_db / original_caminho
                        if old_file_path.exists():
                            try: old_file_path.unlink()
                            except Exception: pass
                    
                    conteudo_dict = MessageToDict(sg.grupo.conteudo, preserving_proto_field_name=True)
                    json_original = ext.dados_json_originais if ext and ext.dados_json_originais else None
                    _salvar_objeto_com_frontmatter(caminho_db / novo_caminho, conteudo_dict, json_original=json_original)
                    sg.grupo.caminho = novo_caminho
                    sg.grupo.ClearField("conteudo")
                    sg.grupo.ClearExtension(ArquivoGrupo.ext_metadados_arquivo)
                    if ext:
                        ext.caminho_original = novo_caminho

        # Botões textuais
        for idx_botao, botao in enumerate(croqui_msg_copy.botoes):
            botao_ref = self.__croqui.botoes[idx_botao]
            if botao.HasField("destino") and botao.destino.WhichOneof("destino") == "secao_textual":
                md = botao.destino.secao_textual
                md_ref = botao_ref.destino.secao_textual
                if md.WhichOneof("arquivo") == "conteudo":
                    ext = None
                    if md_ref.HasExtension(ArquivoMarkdown.ext_metadados_arquivo):
                        ext = md_ref.Extensions[ArquivoMarkdown.ext_metadados_arquivo]
                    original_caminho = ext.caminho_original if ext else None
                    novo_caminho = ext.caminho_novo if ext and ext.caminho_novo else None
                    
                    if not novo_caminho and original_caminho:
                        novo_caminho = original_caminho
                    if not novo_caminho:
                        novo_caminho = f"secao_{botao.texto.replace(' ', '_').lower()}.md"
                    
                    if original_caminho and original_caminho != novo_caminho:
                        old_file_path = caminho_db / original_caminho
                        if old_file_path.exists():
                            try: old_file_path.unlink()
                            except Exception: pass
                    
                    with open(caminho_db / novo_caminho, "w", encoding="utf-8") as f:
                        f.write(md.conteudo)
                    md.caminho = novo_caminho
                    md.ClearField("conteudo")
                    md.ClearExtension(ArquivoMarkdown.ext_metadados_arquivo)
                    if ext:
                        ext.caminho_original = novo_caminho

        ext = None
        from aresta_api.proto.generated.croqui_pb2 import Croqui
        if self.__croqui.HasExtension(Croqui.ext_metadados_arquivo):
            ext = self.__croqui.Extensions[Croqui.ext_metadados_arquivo]
            croqui_msg_copy.ClearExtension(Croqui.ext_metadados_arquivo)
            
        resultado = MessageToDict(croqui_msg_copy, preserving_proto_field_name=True)
            
        if ext and ext.dados_json_originais:
            import json
            try:
                d_original = json.loads(ext.dados_json_originais)
                resultado = _reordenar_recursivamente(resultado, d_original)
            except Exception as e:
                print(f"Aviso: falha ao decodificar JSON original do root: {e}")
            
        return resultado

    def notificar_foco_requisitado(self, path):
        if path:
            self.foco_requisitado.emit(path)