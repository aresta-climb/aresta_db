# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento para a fachada pública `editor.plataforma`,
utilizando `AdaptadorPlataformaFake` sem mocks internos.
"""

import sys
from pathlib import Path

import pytest

import editor.plataforma as mod_plataforma
from editor.plataforma import (
    StatusAtualizacao,
    _AdaptadorPadraoFallback,
    aplicar_icone_janela_nativa,
    configurar_ambiente_plataforma,
    configurar_cofre_credenciais,
    configurar_identidade_processo,
    configurar_presenca_barra_de_tarefas,
    normalizar_caminho_estendido,
    obter_adaptador_plataforma,
    obter_diretorio_dados_usuario,
    obter_nome_icone_preferencial,
    solicitar_instalacao_atualizacao,
    trazer_janela_para_frente,
    verificar_atualizacoes_disponiveis,
)
from editor.plataforma.adaptador_plataforma_fake import AdaptadorPlataformaFake
from editor.plataforma.contrato import ResultadoAtualizacao


def test_obter_adaptador_plataforma_despacho_e_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida a resolução e cache por plataforma (`win32`, `linux`, `darwin` e genérica)."""
    cache_original = dict(mod_plataforma._ADAPTADORES_POR_PLATAFORMA)
    try:
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.clear()
        for plat in ("win32", "linux", "darwin", "freebsd"):
            monkeypatch.setattr(sys, "platform", plat)
            primeiro = obter_adaptador_plataforma()
            segundo = obter_adaptador_plataforma()
            assert primeiro is segundo
    finally:
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.clear()
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.update(cache_original)


def test_funcoes_conveniencia_fachada_com_adaptador_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Garante que todas as funções públicas da fachada delegam para o adaptador ativo."""
    fake = AdaptadorPlataformaFake(
        diretorio_dados=tmp_path,
        resultado_atualizacao_inicial=ResultadoAtualizacao(
            status=StatusAtualizacao.SEM_ATUALIZACAO
        ),
    )
    cache_original = dict(mod_plataforma._ADAPTADORES_POR_PLATAFORMA)
    try:
        monkeypatch.setattr(sys, "platform", "win32")
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA["win32"] = fake

        configurar_ambiente_plataforma()
        icone = tmp_path / "logo.ico"
        assert configurar_presenca_barra_de_tarefas(42, caminho_icone=icone) is True
        assert fake.janelas_barra_tarefas == [(42, str(icone))]

        assert (
            configurar_identidade_processo(
                "aresta.app", nome_exibicao="Editor Aresta", caminho_icone=icone
            )
            is True
        )
        assert fake.identidades_configuradas == [("aresta.app", "Editor Aresta", str(icone))]

        assert aplicar_icone_janela_nativa(42, caminho_icone=icone) is True
        assert fake.icones_aplicados == [(42, str(icone))]

        assert trazer_janela_para_frente(42) is True
        assert obter_diretorio_dados_usuario() == tmp_path

        res = verificar_atualizacoes_disponiveis()
        assert res.status == StatusAtualizacao.SEM_ATUALIZACAO
        assert solicitar_instalacao_atualizacao(res) is True
        assert fake.instalacoes_solicitadas == [res]

        assert obter_nome_icone_preferencial() == "logo_app.png"
        assert configurar_cofre_credenciais() is True
        assert normalizar_caminho_estendido(tmp_path / "arq.yaml") == str(
            (tmp_path / "arq.yaml").resolve()
        )
    finally:
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.clear()
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.update(cache_original)


def test_adaptador_padrao_fallback_completo() -> None:
    """Garante que a implementação neutra de fallback atende a todos os métodos do protocolo."""
    adaptador = _AdaptadorPadraoFallback()

    adaptador.configurar_ambiente_plataforma()
    assert adaptador.configurar_presenca_barra_de_tarefas(1, "logo.png") is True
    assert adaptador.configurar_identidade_processo("app", "App", "logo.png") is True
    assert adaptador.aplicar_icone_janela_nativa(1, "logo.png") is True
    assert adaptador.trazer_janela_para_frente(1) is True
    assert isinstance(adaptador.obter_diretorio_dados_usuario(), Path)
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.NAO_APLICAVEL
    assert adaptador.solicitar_instalacao_atualizacao() is False
    assert adaptador.obter_nome_icone_preferencial() == "logo_app.png"
    assert adaptador.configurar_cofre_credenciais() is False
    assert adaptador.normalizar_caminho_estendido("") == ""
    assert isinstance(adaptador.normalizar_caminho_estendido("teste"), str)
