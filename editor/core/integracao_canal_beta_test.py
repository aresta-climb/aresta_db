# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import importlib
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

import editor.plataforma as mod_plataforma
from editor.core.configuracao_canal import CANAL_BETA, obter_configuracao_canal
from editor.plataforma.adaptador_plataforma_fake import AdaptadorPlataformaFake


def test_integracao_contrato_canal_beta_variaveis_e_titulos(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Testa a integração entre a configuração de canal sob ARESTA_CANAL=beta
    e a criação da TelaDeAbertura, assegurando que o título e a identidade visual
    reflitam o canal Beta.
    """
    _ = qapp
    monkeypatch.setenv("ARESTA_CANAL", CANAL_BETA)
    config = obter_configuracao_canal()
    assert config.eh_beta is True
    assert config.nome_aplicativo == "Editor Aresta (Beta)"
    assert config.app_user_model_id == "aresta.editor.beta"
    assert config.titulo_janela("1.2.0") == "Editor Aresta (Beta) v1.2.0"
    assert config.subdiretorio_recursos == "recursos_beta"

    from editor.views.tela_de_abertura import TelaDeAbertura

    tela = TelaDeAbertura()
    try:
        tela.show()
        assert tela.windowTitle() == "Editor Aresta (Beta)"
        assert not tela.windowIcon().isNull()
    finally:
        tela.close()


def test_integracao_contrato_canal_producao_padrao(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Testa a integração no canal padrão de produção (quando ARESTA_CANAL não está definido),
    assegurando a compatibilidade total com o comportamento existente.
    """
    _ = qapp
    monkeypatch.delenv("ARESTA_CANAL", raising=False)

    config = obter_configuracao_canal()
    assert config.eh_beta is False
    assert config.nome_aplicativo == "Editor Aresta"
    assert config.app_user_model_id == "aresta.editor.v1"
    assert config.titulo_janela("1.2.0") == "Editor Aresta v1.2.0"
    assert config.subdiretorio_recursos == "recursos"

    from editor.views.tela_de_abertura import TelaDeAbertura

    tela = TelaDeAbertura()
    try:
        assert tela.windowTitle() == "Editor Aresta"
        assert not tela.windowIcon().isNull()
    finally:
        tela.close()


def test_import_main_e_headless_nao_chamam_identidade_mas_modo_grafico_chama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Garante que importar `editor.main` ou executar `--headless` não polui o AppUserModelID
    do Windows, enquanto o arranque gráfico real registra identidade, nome e ícone.
    """
    import editor.main as mod_main

    fake = AdaptadorPlataformaFake(diretorio_dados=tmp_path)
    chave_plat = (
        "win32"
        if sys.platform.startswith("win")
        else ("linux" if sys.platform.startswith("linux") else "darwin")
    )
    cache_orig = dict(mod_plataforma._ADAPTADORES_POR_PLATAFORMA)
    try:
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA[chave_plat] = fake
        monkeypatch.setenv("ARESTA_CANAL", CANAL_BETA)
        monkeypatch.setenv("ARESTA_PREFIXO_IPC", f"TesteIcone_{tmp_path.name}_")

        # 1. Reload/import não deve invocar configurar_identidade_processo
        importlib.reload(mod_main)
        assert fake.identidades_configuradas == []

        # 2. --headless com caminho inexistente sai antes de qualquer identidade gráfica
        with pytest.raises(SystemExit):
            mod_main.main(["--headless", str(tmp_path / "inexistente")])
        assert fake.identidades_configuradas == []

        # 3. Modo gráfico real invoca configurar_identidade_processo com AUMID, nome e ícone
        class _ControladorStub:
            def __init__(self, **_kwargs: object) -> None:
                pass

            def executar(self) -> int:
                return 0

        with pytest.raises(SystemExit) as exc:
            mod_main.main([], fabrica_controlador=_ControladorStub)
        assert exc.value.code == 0
        assert len(fake.identidades_configuradas) == 1
        app_id, nome_exibicao, caminho_icone = fake.identidades_configuradas[0]
        assert app_id == "aresta.editor.beta"
        assert nome_exibicao == "Editor Aresta (Beta)"
        assert Path(caminho_icone).is_file()
    finally:
        app = QApplication.instance()
        srv = getattr(app, "servidor_local", None)
        if srv is not None:
            from editor.core.instancia_unica import encerrar_servidor_local

            encerrar_servidor_local(srv)
            setattr(app, "servidor_local", None)
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.clear()
        mod_plataforma._ADAPTADORES_POR_PLATAFORMA.update(cache_orig)
