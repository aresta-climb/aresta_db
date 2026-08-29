# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any, Dict, List
import pickle
from pathlib import Path
from editor.core.imagem_anonimizada import gerar_webp_anonimizado


class GerenciadorDiario:
    """
    Gerenciador transacional da persistência em disco do diário de comandos (QUndoCommand).
    Mantém separação entre diario_salvo.bin e diario_pendente.bin usando pickle em modo append-only.
    """
    
    def __init__(self, pasta_croqui: Path | str, apenas_pendente: bool = False) -> None:
        self.pasta_croqui: Path = Path(pasta_croqui)
        self.apenas_pendente: bool = apenas_pendente
        self.caminho_pendente: Path = self.pasta_croqui / "diario_pendente.bin"
        self.caminho_salvo: Path = self.pasta_croqui / "diario_salvo.bin"

    def gravar_comando_pendente(self, comando_ou_dict: Any) -> None:
        """Grava um comando serializado de forma append-only no diário pendente."""
        self.pasta_croqui.mkdir(parents=True, exist_ok=True)
        if hasattr(comando_ou_dict, "serializar"):
            dados = comando_ou_dict.serializar(anonimizado=False)
        elif isinstance(comando_ou_dict, dict):
            dados = comando_ou_dict
        else:
            raise TypeError(f"Objeto inválido para gravação no diário: {type(comando_ou_dict)}")

        with open(self.caminho_pendente, "ab") as f:
            pickle.dump(dados, f, protocol=5)

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

    def descartar_pendente(self) -> None:
        """Descarta e limpa todas as alterações pendentes não salvas."""
        if self.caminho_pendente.exists():
            with open(self.caminho_pendente, "wb") as f:
                f.truncate(0)

    def exportar_diario_anonimizado(self, limite_comandos: int = 100) -> List[Dict[str, Any]]:
        """
        Exporta uma lista dos comandos mais recentes com dados de imagem anonimizados (WebP dummy),
        ideal para anexo em relatórios de diagnóstico e telemetria.
        """
        todos_comandos = self.ler_diario_salvo() + self.ler_diario_pendente()
        recentes = todos_comandos[-limite_comandos:] if len(todos_comandos) > limite_comandos else todos_comandos
        
        resultado = []
        for cmd in recentes:
            cmd_copia = dict(cmd)
            # Anonimiza campos de bytes de imagens
            for chave in ("bytes_antigo", "bytes_novo", "img_bytes"):
                if chave in cmd_copia and isinstance(cmd_copia[chave], (bytes, bytearray)):
                    cmd_copia[chave] = gerar_webp_anonimizado(cmd_copia[chave])
            resultado.append(cmd_copia)
        return resultado

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

