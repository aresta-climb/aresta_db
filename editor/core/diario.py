# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any, Dict, List, Optional
import pickle
from pathlib import Path
from editor.core.imagem_anonimizada import gerar_webp_anonimizado


class GerenciadorDiario:
    """
    Gerencia o diário de operações do croqui em dois níveis:
    - diario_pendente.bin: grava cada comando de alteração em tempo real (append-only).
    - diario_salvo.bin: consolidado após o salvamento bem-sucedido do croqui no Git.
    """
    
    def __init__(self, pasta_croqui: Path | str, apenas_pendente: bool = False) -> None:
        self.pasta_croqui: Path = Path(pasta_croqui)
        self.apenas_pendente: bool = apenas_pendente
        self.caminho_pendente: Path = self.pasta_croqui / "diario_pendente.bin"
        self.caminho_salvo: Path = self.pasta_croqui / "diario_salvo.bin"
        self._cache_salvo: Optional[List[Dict[str, Any]]] = None
        self._cache_pendente: Optional[List[Dict[str, Any]]] = None

    @property
    def _comandos_anonimizados_cache(self) -> Optional[List[Dict[str, Any]]]:
        if self._cache_salvo is None and self._cache_pendente is None:
            return None
        salvos = self._cache_salvo or []
        pendentes = self._cache_pendente or []
        return salvos + pendentes

    @_comandos_anonimizados_cache.setter
    def _comandos_anonimizados_cache(self, valor: Optional[List[Dict[str, Any]]]) -> None:
        if valor is None:
            self._cache_salvo = None
            self._cache_pendente = None

    @staticmethod
    def _anonimizar_comando(cmd: Dict[str, Any]) -> Dict[str, Any]:
        cmd_copia = dict(cmd)
        for chave in ("bytes_antigo", "bytes_novo", "img_bytes"):
            if chave in cmd_copia and isinstance(cmd_copia[chave], (bytes, bytearray)):
                cmd_copia[chave] = gerar_webp_anonimizado(cmd_copia[chave])
        return cmd_copia

    @staticmethod
    def _converter_para_dict(comando_ou_dict: Any) -> Dict[str, Any]:
        if hasattr(comando_ou_dict, "serializar"):
            res = comando_ou_dict.serializar(anonimizado=False)
            return dict(res) if isinstance(res, dict) else {}
        elif isinstance(comando_ou_dict, dict):
            return dict(comando_ou_dict)
        raise TypeError(f"Objeto inválido para gravação no diário: {type(comando_ou_dict)}")

    def gravar_comando_pendente(self, comando_ou_dict: Any) -> None:
        """Grava um comando serializado de forma append-only no diário pendente."""
        self.pasta_croqui.mkdir(parents=True, exist_ok=True)
        dados = self._converter_para_dict(comando_ou_dict)

        with open(self.caminho_pendente, "ab") as f:
            pickle.dump(dados, f, protocol=5)

        if self._cache_pendente is not None:
            self._cache_pendente.append(self._anonimizar_comando(dados))

    def substituir_comandos_pendentes(self, comandos: List[Any]) -> None:
        """Substitui os comandos do diário pendente preservando intacto o cache de comandos salvos."""
        self.pasta_croqui.mkdir(parents=True, exist_ok=True)
        lista_dados: List[Dict[str, Any]] = []
        for cmd in comandos:
            try:
                lista_dados.append(self._converter_para_dict(cmd))
            except TypeError:
                continue

        with open(self.caminho_pendente, "wb") as f:
            for dados in lista_dados:
                pickle.dump(dados, f, protocol=5)

        self._cache_pendente = [self._anonimizar_comando(dados) for dados in lista_dados]

    def tem_alteracoes_pendentes(self) -> bool:
        """Verifica se existem comandos não consolidados no diário pendente."""
        return self.caminho_pendente.exists() and self.caminho_pendente.stat().st_size > 0

    def ler_diario_pendente(self) -> List[Dict[str, Any]]:
        """Lê todos os comandos do diário pendente de forma tolerante a falhas de final de arquivo."""
        return self._ler_arquivo_pickle(self.caminho_pendente)

    def ler_diario_salvo(self) -> List[Dict[str, Any]]:
        """Lê todos os comandos do diário salvo consolidado."""
        return self._ler_arquivo_pickle(self.caminho_salvo)

    def consolidar_salvamento(self) -> None:
        """
        Transfere todos os comandos do diário pendente para o diário salvo (se não for apenas_pendente)
        e trunca o pendente. Chamado após salvamento e compilação com sucesso do croqui.
        """
        if not self.caminho_pendente.exists() or self.caminho_pendente.stat().st_size == 0:
            return

        if not self.apenas_pendente:
            comandos_pendentes = self.ler_diario_pendente()
            if comandos_pendentes:
                with open(self.caminho_salvo, "ab") as f_salvo:
                    for cmd in comandos_pendentes:
                        pickle.dump(cmd, f_salvo, protocol=5)

        # Trunca o arquivo pendente para 0 bytes
        with open(self.caminho_pendente, "wb") as f_pendente:
            f_pendente.truncate(0)

        # Atualiza caches em memória
        if self._cache_salvo is not None and self._cache_pendente is not None:
            if not self.apenas_pendente:
                self._cache_salvo.extend(self._cache_pendente)
            self._cache_pendente = []
        else:
            self._cache_salvo = None
            self._cache_pendente = []

    def descartar_pendente(self) -> None:
        """Descarta e limpa todas as alterações pendentes não salvas, preservando o cache salvo."""
        self._cache_pendente = []
        if self.caminho_pendente.exists():
            with open(self.caminho_pendente, "wb") as f:
                f.truncate(0)

    def exportar_diario_anonimizado(self, limite_comandos: int = 100) -> List[Dict[str, Any]]:
        """
        Exporta uma lista dos comandos mais recentes com dados de imagem anonimizados (WebP dummy),
        ideal para anexo em relatórios de diagnóstico e telemetria.
        """
        if self._cache_salvo is None:
            comandos_salvos = self.ler_diario_salvo()
            self._cache_salvo = [self._anonimizar_comando(c) for c in comandos_salvos]

        if self._cache_pendente is None:
            comandos_pendentes = self.ler_diario_pendente()
            self._cache_pendente = [self._anonimizar_comando(c) for c in comandos_pendentes]

        todos_comandos = self._cache_salvo + self._cache_pendente
        return list(todos_comandos[-limite_comandos:])

    def _ler_arquivo_pickle(self, caminho: Path) -> List[Dict[str, Any]]:
        """Lê um arquivo de streaming de pickle até o fim, ignorando bytes parciais corrompidos."""
        comandos: List[Dict[str, Any]] = []
        if not caminho.exists() or caminho.stat().st_size == 0:
            return comandos

        with open(caminho, "rb") as f:
            while True:
                try:
                    comandos.append(pickle.load(f))
                except EOFError:
                    break
                except Exception:
                    # Final corrompido ou erro de deserialização; encerra preservando registros lidos
                    break
        return comandos
