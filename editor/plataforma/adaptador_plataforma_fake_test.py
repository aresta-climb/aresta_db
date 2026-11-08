# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from editor.plataforma.adaptador_plataforma_fake import AdaptadorPlataformaFake
from editor.plataforma.contrato import (
    AdaptadorPlataforma,
    ResultadoAtualizacao,
    StatusAtualizacao,
)


def test_adaptador_plataforma_fake_implementa_protocolo_e_simula_atualizacoes(
    tmp_path: Path,
) -> None:
    fake = AdaptadorPlataformaFake(diretorio_dados=tmp_path)
    assert isinstance(fake, AdaptadorPlataforma)

    fake.configurar_ambiente_plataforma()
    assert fake.configurar_presenca_barra_de_tarefas(100) is True
    assert fake.configurar_identidade_processo("Aresta.Editor") is True
    assert fake.trazer_janela_para_frente(100) is True
    assert fake.obter_diretorio_dados_usuario() == tmp_path
    assert fake.obter_nome_icone_preferencial() == "logo_app.png"
    assert fake.configurar_cofre_credenciais() is True
    assert fake.normalizar_caminho_estendido("") == ""
    assert fake.normalizar_caminho_estendido(tmp_path / "arq.txt") == str(
        (tmp_path / "arq.txt").resolve()
    )

    res_padrao = fake.verificar_atualizacoes_disponiveis()
    assert res_padrao.status == StatusAtualizacao.NAO_APLICAVEL

    res_disp = ResultadoAtualizacao(
        status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
        versao_disponivel="9.9.9",
    )
    fake.configurar_resultado_atualizacao(res_disp)
    assert fake.verificar_atualizacoes_disponiveis() == res_disp
    assert fake.solicitar_instalacao_atualizacao(res_disp) is True
    assert fake.instalacoes_solicitadas == [res_disp]
