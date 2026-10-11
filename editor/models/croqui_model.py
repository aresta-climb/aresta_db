# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any, cast

from google.protobuf.message import Message
from PySide6.QtCore import QObject, Signal

from editor.models.readonly_proxy import _copia_segura
from scripts.gerenciar_uids_lib import gerar_uid, validar_uid


class CroquiModel(QObject):
    """
    Modelo de domínio que encapsula os dados do Croqui (Protobuf).
    Emite sinais Qt quando ocorre alguma mutação nos dados subjacentes.
    As mutações devem ser feitas EXCLUSIVAMENTE via Comandos na arquitetura MVC.
    """

    # Sinais genéricos para a View assinar
    dado_alterado = Signal(object, str)  # msg_pai, campo_nome
    repeated_adicionado = Signal(object, str, int)  # msg_pai, campo_nome, indice
    repeated_removido = Signal(object, str, int)  # msg_pai, campo_nome, indice
    repeated_item_alterado = Signal(object, str, int)  # msg_pai, campo_nome, indice
    repeated_movido = Signal(object, str, int, int)  # msg_pai, campo_nome, index_from, index_to
    oneof_alterado = Signal(object, str)  # msg_pai, oneof_nome
    foco_requisitado = Signal(object)  # msg_id
    imagem_alterada = Signal(str)  # caminho_relativo_imagem

    @staticmethod
    def __desembrulhar_proxy(obj: Any) -> Any:
        from editor.models.readonly_proxy import (
            ReadOnlyExtensionProxy,
            ReadOnlyListProxy,
            ReadOnlyProxy,
        )

        if isinstance(obj, ReadOnlyProxy):
            return object.__getattribute__(obj, "_obj")
        if isinstance(obj, ReadOnlyExtensionProxy):
            return object.__getattribute__(obj, "_obj")
        if isinstance(obj, ReadOnlyListProxy):
            return object.__getattribute__(obj, "_lst")
        return obj

    def __init__(self, croqui: Any, parent: Any = None) -> None:
        super().__init__(parent)
        self.__croqui: Any = croqui
        from editor.models.readonly_proxy import ReadOnlyProxy

        self.__croqui_proxy: Any = ReadOnlyProxy(self.__croqui)
        self._imagens_em_memoria: dict[str, bytes] = {}
        self._anexos_em_memoria: dict[str, bytes] = {}
        self._caminho_db_atual: Any = None
        from editor.models.indice_uids_model import IndiceUidsModel

        self._indice_uids: Any = IndiceUidsModel(self.__croqui, parent=self)

    @property
    def indice_uids(self) -> Any:
        """Retorna o modelo de índice de UIDs universal do croqui."""
        return self._indice_uids

    def obter_indice_uids(self) -> Any:
        """Retorna o modelo de índice de UIDs universal do croqui."""
        return self._indice_uids

    def definir_caminho_db(self, caminho_db: Any) -> None:
        """Define o caminho base do banco de dados/croqui no disco para busca de arquivos."""
        from pathlib import Path

        self._caminho_db_atual = Path(caminho_db) if caminho_db else None

    def obter_bytes_imagem(self, caminho_relativo: str) -> Any:
        """
        Obtém os bytes da imagem.
        Verifica primeiro o buffer em memória; se não encontrar, tenta ler do disco no caminho_db_atual.
        """
        if not caminho_relativo:
            return None
        caminho_padrao = str(caminho_relativo).replace("\\", "/")
        if caminho_padrao in self._imagens_em_memoria:
            return self._imagens_em_memoria[caminho_padrao]
        if self._caminho_db_atual:
            caminho_disco = self._caminho_db_atual / caminho_padrao
            if caminho_disco.exists() and caminho_disco.is_file():
                try:
                    return caminho_disco.read_bytes()
                except Exception:
                    return None
        return None

    def definir_imagem_memoria(self, caminho_relativo: str, bytes_conteudo: bytes) -> None:
        """Armazena os bytes de uma imagem no buffer em memória RAM e emite sinal de alteração."""
        caminho_padrao = str(caminho_relativo).replace("\\", "/")
        self._imagens_em_memoria[caminho_padrao] = bytes_conteudo
        self.imagem_alterada.emit(caminho_padrao)

    def remover_imagem_memoria(self, caminho_relativo: str) -> None:
        """Remove os bytes de uma imagem do buffer em memória RAM e emite sinal de alteração."""
        caminho_padrao = str(caminho_relativo).replace("\\", "/")
        if caminho_padrao in self._imagens_em_memoria:
            self._imagens_em_memoria.pop(caminho_padrao, None)
            self.imagem_alterada.emit(caminho_padrao)

    def obter_imagens_em_memoria(self) -> dict[str, bytes]:
        """Retorna uma cópia do dicionário de imagens no buffer de memória."""
        return dict(self._imagens_em_memoria)

    def limpar_imagens_em_memoria(self) -> None:
        """Limpa o buffer de imagens em memória."""
        self._imagens_em_memoria.clear()

    def obter_bytes_anexo(self, caminho_relativo: str) -> bytes | None:
        """
        Obtém os bytes do documento anexo.
        Verifica primeiro o buffer em memória; se não encontrar, tenta ler do disco no caminho_db_atual.
        """
        if not caminho_relativo:
            return None
        caminho_padrao = str(caminho_relativo).replace("\\", "/")
        if caminho_padrao in self._anexos_em_memoria:
            return self._anexos_em_memoria[caminho_padrao]
        if self._caminho_db_atual:
            caminho_disco = self._caminho_db_atual / caminho_padrao
            if caminho_disco.exists() and caminho_disco.is_file():
                try:
                    return cast(bytes, caminho_disco.read_bytes())
                except Exception:
                    return None
        return None

    def definir_anexo_memoria(self, caminho_relativo: str, bytes_conteudo: bytes) -> None:
        """Armazena os bytes de um documento anexo no buffer em memória RAM."""
        caminho_padrao = str(caminho_relativo).replace("\\", "/")
        self._anexos_em_memoria[caminho_padrao] = bytes_conteudo

    def remover_anexo_memoria(self, caminho_relativo: str) -> None:
        """Remove os bytes de um documento anexo do buffer em memória RAM."""
        caminho_padrao = str(caminho_relativo).replace("\\", "/")
        self._anexos_em_memoria.pop(caminho_padrao, None)

    def obter_anexos_em_memoria(self) -> dict[str, bytes]:
        """Retorna uma cópia do dicionário de anexos no buffer de memória."""
        return dict(self._anexos_em_memoria)

    def limpar_anexos_em_memoria(self) -> None:
        """Limpa o buffer de anexos em memória."""
        self._anexos_em_memoria.clear()

    def obter_croqui_readonly(self) -> Any:
        """Retorna uma view somente leitura do Croqui encapsulado."""
        return self.__croqui_proxy

    def _set_primitivo(self, msg: Any, campo_nome: str, valor_novo: Any) -> None:
        msg = self.__desembrulhar_proxy(msg)
        if valor_novo is None or valor_novo == "":
            try:
                msg.ClearField(campo_nome)
            except ValueError:
                # Campo já limpo ou não presente
                pass
        else:
            setattr(msg, campo_nome, _copia_segura(valor_novo))

        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            from editor.models.indice_uids_model import TipoEntidadeUid

            if campo_nome == "nome":
                uid = self._indice_uids.obter_uid_por_objeto(msg)
                if uid:
                    reg = self._indice_uids.obter(uid)
                    if reg:
                        if reg.tipo_id == TipoEntidadeUid.GRUPO:
                            self._indice_uids.atualizar_nome_grupo(uid, str(valor_novo or ""))
                        elif reg.tipo_id == TipoEntidadeUid.SETOR:
                            self._indice_uids.atualizar_nome_setor(uid, str(valor_novo or ""))
                        elif reg.tipo_id == TipoEntidadeUid.ESCALADA:
                            self._indice_uids.atualizar_nome_escalada(uid, str(valor_novo or ""))
                else:
                    self._indice_uids.carregar_do_croqui(self.__croqui)
            elif campo_nome == "texto":
                uid = self._indice_uids.obter_uid_por_objeto(msg)
                if uid:
                    self._indice_uids.atualizar_texto_botao(uid, str(valor_novo or ""))

        self.dado_alterado.emit(msg, campo_nome)

    def _adicionar_repeated(self, msg: Any, campo_nome: str, index: int, valor: Any) -> None:
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        repeated_container.insert(index, _copia_segura(valor))
        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)
        self.repeated_adicionado.emit(msg, campo_nome, index)

    def _remover_repeated(self, msg: Any, campo_nome: str, index: int) -> None:
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        repeated_container.pop(index)
        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)
        self.repeated_removido.emit(msg, campo_nome, index)

    def _mover_repeated(self, msg: Any, campo_nome: str, index_from: int, index_to: int) -> None:
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)
        item = repeated_container.pop(index_from)
        repeated_container.insert(index_to, item)
        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)
        self.repeated_movido.emit(msg, campo_nome, index_from, index_to)

    def _migrar_setor(
        self,
        pai_origem: Any,
        campo_origem: str,
        indice_origem: int,
        pai_destino: Any,
        campo_destino: str,
        indice_destino: int,
        novo_caminho: str | None = None,
    ) -> None:
        """
        Migra um setor de uma coleção/pai para outra, atualizando opcionalmente seu caminho_novo.
        Remove do pai de origem (emitindo repeated_removido) e insere no pai de destino
        (emitindo repeated_adicionado).
        """
        pai_origem = self.__desembrulhar_proxy(pai_origem)
        pai_destino = self.__desembrulhar_proxy(pai_destino)
        from aresta_api.proto.generated import croqui_pb2

        container_origem = getattr(pai_origem, campo_origem)
        item_removido = container_origem[indice_origem]

        arq_setor = croqui_pb2.ArquivoSetor()
        if campo_origem == "setores_ou_grupos":
            arq_setor.CopyFrom(item_removido.setor)
        else:
            arq_setor.CopyFrom(item_removido)

        if novo_caminho is not None:
            arq_setor.Extensions[
                croqui_pb2.ArquivoSetor.ext_metadados_arquivo
            ].caminho_novo = novo_caminho

        container_origem.pop(indice_origem)
        self.repeated_removido.emit(pai_origem, campo_origem, indice_origem)

        container_destino = getattr(pai_destino, campo_destino)
        if campo_destino == "setores_ou_grupos":
            sg = croqui_pb2.SetorOuGrupo()
            sg.setor.CopyFrom(arq_setor)
            container_destino.insert(indice_destino, sg)
        else:
            container_destino.insert(indice_destino, arq_setor)
        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)
        self.repeated_adicionado.emit(pai_destino, campo_destino, indice_destino)

    def _alterar_repeated_item(
        self, msg: Any, campo_nome: str, index: int, valor_novo: Any
    ) -> None:
        msg = self.__desembrulhar_proxy(msg)
        repeated_container = getattr(msg, campo_nome)

        valor_seguro = _copia_segura(valor_novo)
        if isinstance(valor_seguro, Message):
            repeated_container[index].CopyFrom(valor_seguro)
        else:
            repeated_container[index] = valor_seguro
        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)
        self.repeated_item_alterado.emit(msg, campo_nome, index)

    def _alterar_oneof(
        self, msg: Any, oneof_nome: str, nome_antigo: Any, campo_novo: Any, valor_novo: Any
    ) -> None:
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
        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)
        self.oneof_alterado.emit(msg, campo_afetado)

    def _alterar_metadados_caminho_novo(
        self, msg: Any, ext_descriptor: Any, valor_novo: Any
    ) -> None:
        msg = self.__desembrulhar_proxy(msg)
        msg.Extensions[ext_descriptor].caminho_novo = valor_novo
        self.dado_alterado.emit(msg, ext_descriptor.name)

    def carregar_arquivos_externos(self, caminho_db: Any) -> None:
        """Carrega e mescla no protobuf os arquivos externos de Setor/Grupo e Markdowns."""
        if not caminho_db:
            return

        self._caminho_db_atual = caminho_db
        import yaml
        from google.protobuf import json_format

        croqui_msg = self.__croqui

        if not caminho_db.exists():
            return

        def _ler_objeto_com_frontmatter(
            caminho_arquivo: Any, message_ref: Any, ext_descriptor: Any
        ) -> dict[str, Any]:
            with open(caminho_arquivo, encoding="utf-8") as f:
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

                    message_ref.Extensions[ext_descriptor].dados_json_originais = json.dumps(
                        dados, ensure_ascii=False
                    )

                    if body_str:
                        dados["descricao"] = body_str
                    return dados if isinstance(dados, dict) else {}
            try:
                carregado = yaml.safe_load(content) or {}
                return carregado if isinstance(carregado, dict) else {}
            except Exception:
                return {}

        def _carregar_arquivo_setor(arq_setor: Any) -> None:
            if arq_setor.WhichOneof("arquivo") == "caminho" and arq_setor.caminho:
                nome_relativo = arq_setor.caminho
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor

                        dados_setor = _ler_objeto_com_frontmatter(
                            caminho_arquivo, arq_setor, ArquivoSetor.ext_metadados_arquivo
                        )
                        if dados_setor:
                            json_format.ParseDict(
                                dados_setor, arq_setor.conteudo, ignore_unknown_fields=True
                            )
                            arq_setor.Extensions[
                                ArquivoSetor.ext_metadados_arquivo
                            ].caminho_original = nome_relativo
                            arq_setor.Extensions[
                                ArquivoSetor.ext_metadados_arquivo
                            ].caminho_novo = nome_relativo
                            arq_setor.ClearField("caminho")
                        else:
                            if arq_setor.HasExtension(ArquivoSetor.ext_metadados_arquivo):
                                arq_setor.ClearExtension(ArquivoSetor.ext_metadados_arquivo)
                    except Exception as e:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor

                        if arq_setor.HasExtension(ArquivoSetor.ext_metadados_arquivo):
                            arq_setor.ClearExtension(ArquivoSetor.ext_metadados_arquivo)
                        print(f"Erro ao carregar setor externo {arq_setor.caminho}: {e}")

        def _carregar_arquivo_grupo(arq_grupo: Any) -> None:
            if arq_grupo.WhichOneof("arquivo") == "caminho" and arq_grupo.caminho:
                nome_relativo = arq_grupo.caminho
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo

                        dados_grupo = _ler_objeto_com_frontmatter(
                            caminho_arquivo, arq_grupo, ArquivoGrupo.ext_metadados_arquivo
                        )
                        if dados_grupo:
                            json_format.ParseDict(
                                dados_grupo, arq_grupo.conteudo, ignore_unknown_fields=True
                            )
                            arq_grupo.Extensions[
                                ArquivoGrupo.ext_metadados_arquivo
                            ].caminho_original = nome_relativo
                            arq_grupo.Extensions[
                                ArquivoGrupo.ext_metadados_arquivo
                            ].caminho_novo = nome_relativo
                            arq_grupo.ClearField("caminho")
                            for s in arq_grupo.conteudo.setores:
                                _carregar_arquivo_setor(s)
                        else:
                            if arq_grupo.HasExtension(ArquivoGrupo.ext_metadados_arquivo):
                                arq_grupo.ClearExtension(ArquivoGrupo.ext_metadados_arquivo)
                    except Exception as e:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo

                        if arq_grupo.HasExtension(ArquivoGrupo.ext_metadados_arquivo):
                            arq_grupo.ClearExtension(ArquivoGrupo.ext_metadados_arquivo)
                        print(f"Erro ao carregar grupo externo {arq_grupo.caminho}: {e}")

        def _carregar_arquivo_mapas(arq_mapas: Any) -> None:
            if arq_mapas.WhichOneof("arquivo") == "caminho" and arq_mapas.caminho:
                nome_relativo = arq_mapas.caminho
                caminho_arquivo = caminho_db / nome_relativo
                if caminho_arquivo.exists():
                    try:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoMapas

                        dados_mapas = _ler_objeto_com_frontmatter(
                            caminho_arquivo, arq_mapas, ArquivoMapas.ext_metadados_arquivo
                        )
                        if dados_mapas:
                            json_format.ParseDict(
                                dados_mapas, arq_mapas.conteudo, ignore_unknown_fields=True
                            )
                            arq_mapas.Extensions[
                                ArquivoMapas.ext_metadados_arquivo
                            ].caminho_original = nome_relativo
                            arq_mapas.Extensions[
                                ArquivoMapas.ext_metadados_arquivo
                            ].caminho_novo = nome_relativo
                            arq_mapas.ClearField("caminho")
                        else:
                            if arq_mapas.HasExtension(ArquivoMapas.ext_metadados_arquivo):
                                arq_mapas.ClearExtension(ArquivoMapas.ext_metadados_arquivo)
                    except Exception as e:
                        from aresta_api.proto.generated.croqui_pb2 import ArquivoMapas

                        if arq_mapas.HasExtension(ArquivoMapas.ext_metadados_arquivo):
                            arq_mapas.ClearExtension(ArquivoMapas.ext_metadados_arquivo)
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
                            with open(caminho_arquivo, encoding="utf-8") as f:
                                conteudo_md = f.read()

                            frontmatter_bloco = ""
                            corpo_md = conteudo_md
                            if conteudo_md.startswith("---"):
                                parts = conteudo_md.split("---", 2)
                                if len(parts) >= 3:
                                    frontmatter_bloco = f"---{parts[1]}---\n"
                                    corpo_md = parts[2]
                                    if corpo_md.startswith("\n"):
                                        corpo_md = corpo_md[1:]

                            md.conteudo = corpo_md
                            from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown

                            md.Extensions[
                                ArquivoMarkdown.ext_metadados_arquivo
                            ].caminho_original = nome_relativo
                            md.Extensions[
                                ArquivoMarkdown.ext_metadados_arquivo
                            ].caminho_novo = nome_relativo
                            if frontmatter_bloco:
                                md.Extensions[
                                    ArquivoMarkdown.ext_metadados_arquivo
                                ].dados_json_originais = frontmatter_bloco
                            md.ClearField("caminho")
                        except Exception as e:
                            from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown

                            if md.HasExtension(ArquivoMarkdown.ext_metadados_arquivo):
                                md.ClearExtension(ArquivoMarkdown.ext_metadados_arquivo)
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

        if hasattr(self, "_indice_uids") and self._indice_uids is not None:
            self._indice_uids.carregar_do_croqui(self.__croqui)

    def extrair_arquivos_e_serializar(self, caminho_db: Any) -> dict[str, Any]:
        from pathlib import Path

        import yaml
        from google.protobuf.json_format import MessageToDict

        from aresta_api.proto.generated.croqui_pb2 import (
            ArquivoGrupo,
            ArquivoMapas,
            ArquivoMarkdown,
            ArquivoSetor,
            Croqui,
        )
        from editor.core.serializacao_util import sanitizar_dicionario_sem_extensoes

        caminho_db_path = Path(caminho_db)
        if self._imagens_em_memoria:
            for caminho_rel, bytes_img in self._imagens_em_memoria.items():
                destino = caminho_db_path / caminho_rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                if (
                    bytes_img.startswith(b"RIFF")
                    and len(bytes_img) > 16
                    and bytes_img[8:12] == b"WEBP"
                    and bytes_img[12:16] == b"VP8L"
                ):
                    from editor.core.transformacoes_imagem import converter_para_webp_disco

                    bytes_img = converter_para_webp_disco(bytes_img, qualidade=90)
                destino.write_bytes(bytes_img)

        if self._anexos_em_memoria:
            for caminho_rel, bytes_anexo in self._anexos_em_memoria.items():
                destino = caminho_db_path / caminho_rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(bytes_anexo)

        croqui_msg_copy = Croqui()
        croqui_msg_copy.CopyFrom(self.__croqui)

        if not validar_uid(croqui_msg_copy.uid):
            croqui_msg_copy.uid = gerar_uid()
            self.__croqui.uid = croqui_msg_copy.uid

        for idx_b, b in enumerate(croqui_msg_copy.botoes):
            if not validar_uid(b.uid):
                b.uid = gerar_uid()
                if len(self.__croqui.botoes) > idx_b:
                    self.__croqui.botoes[idx_b].uid = b.uid

        def _reordenar_recursivamente(d_novo: Any, d_original: Any) -> Any:
            if isinstance(d_novo, list) and isinstance(d_original, list):
                res = []
                for item_novo, item_orig in zip(d_novo, d_original):
                    res.append(_reordenar_recursivamente(item_novo, item_orig))
                if len(d_novo) > len(d_original):
                    res.extend(d_novo[len(d_original) :])
                return res
            if not isinstance(d_novo, dict) or not isinstance(d_original, dict):
                return d_novo

            resultado: dict[str, Any] = {}
            for k in d_original.keys():
                if k in d_novo:
                    resultado[k] = _reordenar_recursivamente(d_novo.pop(k), d_original[k])

            for k, v in d_novo.items():
                resultado[k] = v
            return resultado

        def _limpar_e_garantir_mapas_dict(
            mapas_lista: list[dict[str, Any]], nome_para_uid: dict[str, str] | None = None
        ) -> None:
            for mapa_dict in mapas_lista:
                if not isinstance(mapa_dict, dict):
                    continue
                poi_id_para_uid: dict[str, str] = {}
                for poi_dict in mapa_dict.get("pontos_de_interesse", []):
                    if not isinstance(poi_dict, dict):
                        continue
                    if "label" in poi_dict and "rotulo" not in poi_dict:
                        poi_dict["rotulo"] = poi_dict.pop("label")
                    else:
                        poi_dict.pop("label", None)
                    if not validar_uid(poi_dict.get("uid", "")):
                        poi_dict["uid"] = gerar_uid()
                    if "id" in poi_dict:
                        poi_id_para_uid[str(poi_dict["id"])] = poi_dict["uid"]
                        poi_dict.pop("id", None)

                    poi_itens = []
                    if "uid" in poi_dict:
                        poi_itens.append(("uid", poi_dict.pop("uid")))
                    if "rotulo" in poi_dict:
                        poi_itens.append(("rotulo", poi_dict.pop("rotulo")))
                    poi_resto = list(poi_dict.items())
                    poi_dict.clear()
                    for k, v in poi_itens + poi_resto:
                        poi_dict[k] = v

                for ref_dict in mapa_dict.get("referencias", []):
                    if not isinstance(ref_dict, dict):
                        continue
                    if "pontos_uids" not in ref_dict and "ids" in ref_dict:
                        ref_dict["pontos_uids"] = [
                            poi_id_para_uid.get(str(pid), pid) for pid in ref_dict.get("ids", [])
                        ]
                    ref_dict.pop("ids", None)
                    ref_dict.pop("indice_mapa_alvo", None)
                    if not validar_uid(ref_dict.get("alvo_uid", "")):
                        alvo_nome = (
                            ref_dict.get("escalada")
                            or ref_dict.get("setor")
                            or ref_dict.get("grupo")
                        )
                        if nome_para_uid and alvo_nome and alvo_nome in nome_para_uid:
                            ref_dict["alvo_uid"] = nome_para_uid[alvo_nome]
                    if validar_uid(ref_dict.get("alvo_uid", "")):
                        ref_dict.pop("escalada", None)
                        ref_dict.pop("setor", None)
                        ref_dict.pop("grupo", None)

                    ref_itens = []
                    if "alvo_uid" in ref_dict:
                        ref_itens.append(("alvo_uid", ref_dict.pop("alvo_uid")))
                    if "pontos_uids" in ref_dict:
                        ref_itens.append(("pontos_uids", ref_dict.pop("pontos_uids")))
                    ref_resto = list(ref_dict.items())
                    ref_dict.clear()
                    for k, v in ref_itens + ref_resto:
                        ref_dict[k] = v

        def _salvar_objeto_com_frontmatter(
            caminho_arquivo: Any, dados_dict: dict[str, Any], json_original: str | None = None
        ) -> None:
            dados = sanitizar_dicionario_sem_extensoes(dados_dict)
            descricao = dados.pop("descricao", "")
            if descricao:
                descricao = str(descricao).replace("\r\n", "\n")

            if json_original:
                import json

                try:
                    d_original = json.loads(json_original)
                    dados = _reordenar_recursivamente(dados, d_original)
                except Exception as e:
                    print(f"Aviso: falha ao decodificar JSON original: {e}")

            if "uid" in dados:
                uid_val = dados.pop("uid")
                novo_dados = {"uid": uid_val}
                novo_dados.update(dados)
                dados = novo_dados

            for esc in dados.get("escaladas", []):
                if isinstance(esc, dict) and "uid" in esc:
                    esc_uid = esc.pop("uid")
                    novo_esc = {"uid": esc_uid}
                    novo_esc.update(esc)
                    esc.clear()
                    esc.update(novo_esc)

            with open(caminho_arquivo, "w", encoding="utf-8", newline="\n") as f:
                f.write("---\n")
                f.write("# SPDX-License-Identifier: ODbL-1.0\n")
                f.write("# Copyright (C) 2026 Aresta Climb Contributors\n")

                # Garante que strings compostas apenas por dígitos sejam entre aspas
                # (evita que parser YAML confunda com números inteiros no futuro, ex: id '09' -> 09)
                def _str_representer(dumper: Any, data: Any) -> Any:
                    style = None
                    if data.isdigit() or (data.startswith("-") and data[1:].isdigit()):
                        style = "'"
                    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

                yaml.add_representer(str, _str_representer)

                yaml_str = yaml.dump(dados, allow_unicode=True, sort_keys=False)
                yaml_str = yaml_str.replace("\r\n", "\n")
                f.write(yaml_str)
                f.write("---\n")
                if descricao is not None:
                    f.write(descricao)

        def _garantir_uids_setor(conteudo_setor: Any, ref_setor: Any) -> dict[str, str]:
            if not validar_uid(conteudo_setor.uid):
                conteudo_setor.uid = gerar_uid()
                if ref_setor.HasField("conteudo"):
                    ref_setor.conteudo.uid = conteudo_setor.uid

            nome_para_uid_vias: dict[str, str] = {}
            if conteudo_setor.nome:
                nome_para_uid_vias[conteudo_setor.nome] = conteudo_setor.uid

            for idx_esc, esc in enumerate(conteudo_setor.escaladas):
                if not validar_uid(esc.uid):
                    esc.uid = gerar_uid()
                    if (
                        ref_setor.HasField("conteudo")
                        and len(ref_setor.conteudo.escaladas) > idx_esc
                    ):
                        ref_setor.conteudo.escaladas[idx_esc].uid = esc.uid
                t = esc.WhichOneof("tipo")
                if t:
                    nome_via = getattr(esc, t).nome
                    if nome_via:
                        nome_para_uid_vias[nome_via] = esc.uid

            for idx_mapa, mapa in enumerate(conteudo_setor.mapas):
                for idx_poi, poi in enumerate(mapa.pontos_de_interesse):
                    if not validar_uid(poi.uid):
                        poi.uid = gerar_uid()
                        if (
                            ref_setor.HasField("conteudo")
                            and len(ref_setor.conteudo.mapas) > idx_mapa
                        ):
                            ref_m = ref_setor.conteudo.mapas[idx_mapa]
                            if len(ref_m.pontos_de_interesse) > idx_poi:
                                ref_m.pontos_de_interesse[idx_poi].uid = poi.uid
                for idx_ref, ref in enumerate(mapa.referencias):
                    if not validar_uid(ref.alvo_uid):
                        alvo_nome = (
                            getattr(ref, "escalada", "")
                            or getattr(ref, "setor", "")
                            or getattr(ref, "grupo", "")
                        )
                        if alvo_nome in nome_para_uid_vias:
                            ref.alvo_uid = nome_para_uid_vias[alvo_nome]
                            if (
                                ref_setor.HasField("conteudo")
                                and len(ref_setor.conteudo.mapas) > idx_mapa
                            ):
                                ref_m = ref_setor.conteudo.mapas[idx_mapa]
                                if len(ref_m.referencias) > idx_ref:
                                    ref_m.referencias[idx_ref].alvo_uid = ref.alvo_uid
            return nome_para_uid_vias

        def _extrair_arquivo_setor(arq_setor: Any, arq_setor_ref: Any) -> None:
            if not arq_setor.HasField("conteudo"):
                arq_setor.ClearExtension(ArquivoSetor.ext_metadados_arquivo)
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
                old_file_path = caminho_db_path / original_caminho
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except Exception:
                        pass

            nome_para_uid = _garantir_uids_setor(arq_setor.conteudo, arq_setor_ref)
            conteudo_dict = MessageToDict(arq_setor.conteudo, preserving_proto_field_name=True)
            if "mapas" in conteudo_dict:
                _limpar_e_garantir_mapas_dict(conteudo_dict["mapas"], nome_para_uid=nome_para_uid)

            json_original = ext.dados_json_originais if ext and ext.dados_json_originais else None
            _salvar_objeto_com_frontmatter(
                caminho_db_path / novo_caminho, conteudo_dict, json_original=json_original
            )
            arq_setor.caminho = novo_caminho
            arq_setor.ClearField("conteudo")
            arq_setor.ClearExtension(ArquivoSetor.ext_metadados_arquivo)
            if ext:
                ext.caminho_original = novo_caminho

        def _extrair_arquivo_mapas(arq_mapas: Any, arq_mapas_ref: Any) -> None:
            from aresta_api.proto.generated.croqui_pb2 import ArquivoMapas

            if not arq_mapas.HasField("conteudo"):
                arq_mapas.ClearExtension(ArquivoMapas.ext_metadados_arquivo)
                return
            ext = None
            if arq_mapas_ref.HasExtension(ArquivoMapas.ext_metadados_arquivo):
                ext = arq_mapas_ref.Extensions[ArquivoMapas.ext_metadados_arquivo]
            original_caminho = ext.caminho_original if ext else None
            novo_caminho = ext.caminho_novo if ext and ext.caminho_novo else None

            if not novo_caminho and original_caminho:
                novo_caminho = original_caminho
            if not novo_caminho:
                novo_caminho = "mapas_gerais.md"

            if original_caminho and original_caminho != novo_caminho:
                old_file_path = caminho_db_path / original_caminho
                if old_file_path.exists():
                    try:
                        old_file_path.unlink()
                    except Exception:
                        pass

            for mapa in arq_mapas.conteudo.mapas:
                for poi in mapa.pontos_de_interesse:
                    if not validar_uid(poi.uid):
                        poi.uid = gerar_uid()

            conteudo_dict = MessageToDict(arq_mapas.conteudo, preserving_proto_field_name=True)
            if "mapas" in conteudo_dict:
                _limpar_e_garantir_mapas_dict(conteudo_dict["mapas"])

            json_original = ext.dados_json_originais if ext and ext.dados_json_originais else None
            _salvar_objeto_com_frontmatter(
                caminho_db_path / novo_caminho, conteudo_dict, json_original=json_original
            )
            arq_mapas.caminho = novo_caminho
            arq_mapas.ClearField("conteudo")
            arq_mapas.ClearExtension(ArquivoMapas.ext_metadados_arquivo)
            if ext:
                ext.caminho_original = novo_caminho

        # Picos e Grupos/Setores
        for idx_pico, pico in enumerate(croqui_msg_copy.picos):
            pico_ref = self.__croqui.picos[idx_pico]

            if pico.HasField("mapas_gerais"):
                if pico.mapas_gerais.HasField("conteudo"):
                    _extrair_arquivo_mapas(pico.mapas_gerais, pico_ref.mapas_gerais)
                else:
                    pico.mapas_gerais.ClearExtension(ArquivoMapas.ext_metadados_arquivo)

            for idx_sg, sg in enumerate(pico.setores_ou_grupos):
                sg_ref = pico_ref.setores_ou_grupos[idx_sg]

                if sg.HasField("setor"):
                    if sg.setor.HasField("conteudo"):
                        _extrair_arquivo_setor(sg.setor, sg_ref.setor)
                    else:
                        sg.setor.ClearExtension(ArquivoSetor.ext_metadados_arquivo)

                elif sg.HasField("grupo"):
                    if sg.grupo.HasField("conteudo"):
                        if not validar_uid(sg.grupo.conteudo.uid):
                            sg.grupo.conteudo.uid = gerar_uid()
                            if sg_ref.grupo.HasField("conteudo"):
                                sg_ref.grupo.conteudo.uid = sg.grupo.conteudo.uid

                        # Extrai os setores internos primeiro
                        for idx_setor, setor_arq in enumerate(sg.grupo.conteudo.setores):
                            setor_arq_ref = sg_ref.grupo.conteudo.setores[idx_setor]
                            if setor_arq.HasField("conteudo"):
                                _extrair_arquivo_setor(setor_arq, setor_arq_ref)
                            else:
                                setor_arq.ClearExtension(ArquivoSetor.ext_metadados_arquivo)

                        # Agora extrai o grupo
                        ext = None
                        if sg_ref.grupo.HasExtension(ArquivoGrupo.ext_metadados_arquivo):
                            ext = sg_ref.grupo.Extensions[ArquivoGrupo.ext_metadados_arquivo]
                        original_caminho = ext.caminho_original if ext else None
                        novo_caminho = ext.caminho_novo if ext and ext.caminho_novo else None

                        if not novo_caminho and original_caminho:
                            novo_caminho = original_caminho
                        if not novo_caminho:
                            novo_caminho = (
                                f"grupo_{sg.grupo.conteudo.nome.replace(' ', '_').lower()}.md"
                            )

                        if original_caminho and original_caminho != novo_caminho:
                            old_file_path = caminho_db_path / original_caminho
                            if old_file_path.exists():
                                try:
                                    old_file_path.unlink()
                                except Exception:
                                    pass

                        conteudo_dict = MessageToDict(
                            sg.grupo.conteudo, preserving_proto_field_name=True
                        )
                        if "mapas" in conteudo_dict:
                            _limpar_e_garantir_mapas_dict(conteudo_dict["mapas"])

                        json_original = (
                            ext.dados_json_originais if ext and ext.dados_json_originais else None
                        )
                        _salvar_objeto_com_frontmatter(
                            caminho_db_path / novo_caminho,
                            conteudo_dict,
                            json_original=json_original,
                        )
                        sg.grupo.caminho = novo_caminho
                        sg.grupo.ClearField("conteudo")
                        sg.grupo.ClearExtension(ArquivoGrupo.ext_metadados_arquivo)
                        if ext:
                            ext.caminho_original = novo_caminho
                    else:
                        sg.grupo.ClearExtension(ArquivoGrupo.ext_metadados_arquivo)

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
                        old_file_path = caminho_db_path / original_caminho
                        if old_file_path.exists():
                            try:
                                old_file_path.unlink()
                            except Exception:
                                pass

                    frontmatter_bloco = (
                        ext.dados_json_originais if ext and ext.dados_json_originais else ""
                    )
                    conteudo_normalizado = (md.conteudo or "").replace("\r\n", "\n")
                    if frontmatter_bloco:
                        if not frontmatter_bloco.endswith("\n"):
                            frontmatter_bloco += "\n"
                        conteudo_final = frontmatter_bloco + conteudo_normalizado
                    else:
                        conteudo_final = conteudo_normalizado

                    with open(
                        caminho_db_path / novo_caminho, "w", encoding="utf-8", newline="\n"
                    ) as f:
                        f.write(conteudo_final)
                    md.caminho = novo_caminho
                    md.ClearField("conteudo")
                    md.ClearExtension(ArquivoMarkdown.ext_metadados_arquivo)
                    if ext:
                        ext.caminho_original = novo_caminho
                else:
                    md.ClearExtension(ArquivoMarkdown.ext_metadados_arquivo)

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

        resultado = sanitizar_dicionario_sem_extensoes(resultado)

        if isinstance(resultado, dict):
            if "uid" in resultado:
                res_uid = resultado.pop("uid")
                novo_res = {"uid": res_uid}
                novo_res.update(resultado)
                resultado = novo_res
            for b in resultado.get("botoes", []):
                if isinstance(b, dict) and "uid" in b:
                    b_uid = b.pop("uid")
                    novo_b = {"uid": b_uid}
                    novo_b.update(b)
                    b.clear()
                    b.update(novo_b)

        return resultado if isinstance(resultado, dict) else {}

    def notificar_foco_requisitado(self, path: Any) -> None:
        if path:
            self.foco_requisitado.emit(path)
