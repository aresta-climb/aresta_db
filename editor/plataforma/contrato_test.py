# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o contrato e tipos da biblioteca de plataforma.
"""

from pathlib import Path
from typing import Optional
from editor.plataforma.contrato import (
    AdaptadorPlataforma,
    StatusAtualizacao,
    ResultadoAtualizacao,
)


class AdaptadorFalso(AdaptadorPlataforma):
    """Implementação concreta de teste do protocolo AdaptadorPlataforma."""

    def configurar_ambiente_plataforma(self) -> None:
        pass

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        return identificador_janela > 0

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        return bool(identificador_app)

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        return identificador_janela > 0

    def obter_diretorio_dados_usuario(self) -> Path:
        return Path("/tmp/editor_teste")

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

    def solicitar_instalacao_atualizacao(
        self, resultado: Optional[ResultadoAtualizacao] = None
    ) -> bool:
        return True

    def obter_nome_icone_preferencial(self) -> str:
        return "logo.png"

    def configurar_cofre_credenciais(self) -> None:
        pass

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        return str(caminho)


def test_resultado_atualizacao_propriedades() -> None:
    """Valida as propriedades utilitárias de ResultadoAtualizacao."""
    res_sem = ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)
    assert not res_sem.tem_atualizacao
    assert not res_sem.obrigatoria

    res_disp = ResultadoAtualizacao(
        status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
        versao_disponivel="1.0.0",
    )
    assert res_disp.tem_atualizacao
    assert not res_disp.obrigatoria

    res_obrig = ResultadoAtualizacao(
        status=StatusAtualizacao.ATUALIZACAO_OBRIGATORIA,
        versao_disponivel="2.0.0",
    )
    assert res_obrig.tem_atualizacao
    assert res_obrig.obrigatoria


def test_adaptador_falso_conforme_contrato() -> None:
    """Garante que a implementação de teste cumpre todas as assinaturas do protocolo."""
    adaptador: AdaptadorPlataforma = AdaptadorFalso()
    adaptador.configurar_ambiente_plataforma()
    assert adaptador.configurar_presenca_barra_de_tarefas(123) is True
    assert adaptador.configurar_identidade_processo("aresta.app") is True
    assert adaptador.trazer_janela_para_frente(123) is True
    assert isinstance(adaptador.obter_diretorio_dados_usuario(), Path)
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.SEM_ATUALIZACAO
    assert adaptador.solicitar_instalacao_atualizacao(res) is True
    assert adaptador.normalizar_caminho_estendido("foo/bar") == "foo/bar"
