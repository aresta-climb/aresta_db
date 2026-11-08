# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from editor.caos.receita_crash_robo import (
    FalhaCapturadaRobo,
    PassoRobo,
    ReceitaCrashRobo,
    SeletorAlvoQt,
)


def test_serializacao_e_desserializacao_receita_crash_robo_em_json(
    tmp_path: Path,
) -> None:
    seletor_arvore = SeletorAlvoQt(
        estrategia="caminho_no_arvore",
        valor="croqui/expando:picos/item:0",
        classe_widget="QTreeView",
        indice=0,
    )
    seletor_campo = SeletorAlvoQt(
        estrategia="campo_formulario",
        valor="Nome",
        classe_widget="QLineEdit",
        indice=0,
    )

    passo_1 = PassoRobo(
        indice=1,
        tipo_acao="selecionar_no_arvore",
        seletor=seletor_arvore,
        parametros={"expandir": True},
        mutou_estado=True,
    )
    passo_2 = PassoRobo(
        indice=2,
        tipo_acao="inserir_texto_fuzz",
        seletor=seletor_campo,
        parametros={"texto": "Pico Tóxico 🔥"},
        mutou_estado=True,
    )

    falha = FalhaCapturadaRobo(
        oraculo="excecao_nao_tratada",
        tipo_excecao="RuntimeError",
        mensagem="Internal C++ object (QLineEdit) already deleted.",
        frame_principal="editor/views/dados/form_builder.py:142",
        stacktrace="Traceback (most recent call last):\n  File 'form_builder.py', line 142\nRuntimeError",
    )

    receita = ReceitaCrashRobo(
        seed=987654,
        dataset="toxico",
        escopo="aplicativo_completo",
        falha=falha,
        passos_minimos=(passo_1, passo_2),
        passos_originais=(passo_1, passo_2),
    )

    assert (
        receita.assinatura_deduplicacao()
        == "excecao_nao_tratada:RuntimeError:editor/views/dados/form_builder.py:142"
    )
    hash_1 = receita.hash_deduplicacao()
    assert len(hash_1) == 8
    assert receita.nome_arquivo_padrao() == f"crash_seed_987654_runtimeerror_{hash_1}.json"

    falha_outro_stack = FalhaCapturadaRobo(
        oraculo="excecao_nao_tratada",
        tipo_excecao="RuntimeError",
        mensagem="Outro erro na mesma seed",
        frame_principal="editor/core/worker.py:446",
        stacktrace='Traceback (most recent call last):\n  File "editor/core/worker.py", line 446, in run\nRuntimeError',
    )
    assert falha_outro_stack.hash_deduplicacao() != hash_1

    caminho_json = tmp_path / receita.nome_arquivo_padrao()
    receita.salvar_json(caminho_json)
    assert caminho_json.is_file()

    carregada = ReceitaCrashRobo.carregar_json(caminho_json)
    assert carregada == receita
    assert carregada.para_dicionario() == receita.para_dicionario()
