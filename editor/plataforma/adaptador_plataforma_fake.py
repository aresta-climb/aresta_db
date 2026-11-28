# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from editor.plataforma.contrato import ResultadoAtualizacao, StatusAtualizacao


class AdaptadorPlataformaFake:
    """
    Dublê determinístico em memória para AdaptadorPlataforma (test-only).
    Permite simular verificações de atualização e diretórios temporários sem chamadas ao SO.
    """

    def __init__(
        self,
        diretorio_dados: Path,
        resultado_atualizacao_inicial: ResultadoAtualizacao | None = None,
    ) -> None:
        self._diretorio_dados: Path = diretorio_dados
        self._resultado_atualizacao: ResultadoAtualizacao = (
            resultado_atualizacao_inicial
            or ResultadoAtualizacao(status=StatusAtualizacao.NAO_APLICAVEL)
        )
        self.instalacoes_solicitadas: list[ResultadoAtualizacao | None] = []
        self.identidades_configuradas: list[tuple[str, str, str]] = []
        self.janelas_barra_tarefas: list[tuple[int, str]] = []
        self.icones_aplicados: list[tuple[int, str]] = []

    def configurar_resultado_atualizacao(self, resultado: ResultadoAtualizacao) -> None:
        """Define o resultado retornado por verificar_atualizacoes_disponiveis."""
        self._resultado_atualizacao = resultado

    def configurar_ambiente_plataforma(self) -> None:
        """Operação sem efeito em ambiente de teste."""
        return None

    def configurar_presenca_barra_de_tarefas(
        self,
        identificador_janela: int,
        caminho_icone: Path | str | None = None,
    ) -> bool:
        self.janelas_barra_tarefas.append(
            (identificador_janela, str(caminho_icone) if caminho_icone else "")
        )
        return True

    def configurar_identidade_processo(
        self,
        identificador_app: str,
        nome_exibicao: str = "",
        caminho_icone: Path | str | None = None,
    ) -> bool:
        self.identidades_configuradas.append(
            (identificador_app, nome_exibicao, str(caminho_icone) if caminho_icone else "")
        )
        return True

    def aplicar_icone_janela_nativa(
        self,
        identificador_janela: int,
        caminho_icone: Path | str | None = None,
    ) -> bool:
        self.icones_aplicados.append(
            (identificador_janela, str(caminho_icone) if caminho_icone else "")
        )
        return True

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        _ = identificador_janela
        return True

    def obter_diretorio_dados_usuario(self) -> Path:
        return self._diretorio_dados

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        return self._resultado_atualizacao

    def solicitar_instalacao_atualizacao(
        self, resultado: ResultadoAtualizacao | None = None
    ) -> bool:
        self.instalacoes_solicitadas.append(resultado)
        return True

    def obter_nome_icone_preferencial(self) -> str:
        return "logo_app.png"

    def configurar_cofre_credenciais(self) -> bool:
        return True

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        if not caminho:
            return ""
        return str(Path(caminho).resolve())
