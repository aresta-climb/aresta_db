# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes de integração e comportamento para `serving/pr_db_validator.py`.
Segue estritamente os Princípios III, IV, V e VII do AGENTS.md (zero mocks para código interno,
utilizando arquivos reais em `tmp_path` e `ClienteR2Fake` para a fronteira externa R2).
"""

from pathlib import Path

from editor.core.serializacao_util import serializar_yaml
from scripts.gerenciar_uids_lib import gerar_uid
from scripts.migrador import obter_ultima_versao_migracao
from serving.cliente_r2_fake import ClienteR2Fake
from serving.pr_db_validator import (
    main,
    validar_cabecalhos_e_licencas,
    validar_pull_request,
    validar_versoes_migracao,
)
from serving.renderizador_resumo_pr_lib import ASSINATURA_COMENTARIO_PR


def _preparar_mini_repositorio(
    raiz: Path,
    *,
    cabecalho_py_valido: bool = True,
    ultima_migracao: int | None = None,
) -> Path:
    """Cria uma estrutura mínima de repositório real em `raiz` com cabeçalhos SPDX e um croqui."""
    raiz.mkdir(parents=True, exist_ok=True)
    if cabecalho_py_valido:
        (raiz / "modulo.py").write_text(
            "# SPDX-License-Identifier: MPL-2.0\n# Copyright (C) 2026 Aresta Climb Contributors\n",
            encoding="utf-8",
        )
    else:
        (raiz / "modulo.py").write_text("x = 1\n", encoding="utf-8")

    versao_mig = (
        obter_ultima_versao_migracao() if ultima_migracao is None else ultima_migracao
    )
    pasta_croqui = raiz / "database" / "cipo_teste"
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    dados_croqui = {
        "uid": gerar_uid(),
        "id": "cipo_teste",
        "nome": "Serra do Cipó Teste",
        "ultima_migracao": versao_mig,
        "publicar_croqui": False,
        "picos": [
            {
                "nome": "Serra do Cipó",
                "estado": "MG",
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "conteudo": {
                                "uid": "uidSetorFixo01",
                                "nome": "Setor Teste",
                                "escaladas": [
                                    {
                                        "uid": "uidViaFixa0001",
                                        "via_esportiva": {
                                            "nome": "Via Teste",
                                            "dificuldade": "BR_6",
                                            "extensao": 20,
                                        },
                                    }
                                ],
                            }
                        }
                    }
                ],
            }
        ],
    }
    conteudo_yaml = (
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n\n"
        + serializar_yaml(dados_croqui, incluir_cabecalho_spdx=False)
    )
    (pasta_croqui / "croqui.yaml").write_text(conteudo_yaml, encoding="utf-8")
    return pasta_croqui


def test_validar_cabecalhos_e_licencas_sucesso_e_falha(tmp_path: Path) -> None:
    """Deve retornar lista vazia quando cabeçalhos SPDX estão corretos e erros quando ausentes."""
    repo_ok = tmp_path / "repo_ok"
    _preparar_mini_repositorio(repo_ok, cabecalho_py_valido=True)
    assert validar_cabecalhos_e_licencas(raiz_repositorio=repo_ok) == []

    repo_ruim = tmp_path / "repo_ruim"
    _preparar_mini_repositorio(repo_ruim, cabecalho_py_valido=False)
    erros = validar_cabecalhos_e_licencas(raiz_repositorio=repo_ruim)
    assert len(erros) >= 1


def test_validar_versoes_migracao_cenarios(tmp_path: Path) -> None:
    """Deve validar versões de migração contra a versão esperada e tratar arquivos ausentes ou inválidos."""
    pasta_ok = tmp_path / "ok"
    pasta_ok.mkdir()
    (pasta_ok / "croqui.yaml").write_text("id: ok\nultima_migracao: 10\n", encoding="utf-8")
    assert validar_versoes_migracao([pasta_ok], versao_esperada=10) == []
    assert validar_versoes_migracao([pasta_ok], versao_esperada=0) == []

    pasta_vazia = tmp_path / "vazia"
    pasta_vazia.mkdir()
    assert validar_versoes_migracao([pasta_vazia], versao_esperada=10) == []

    pasta_lista = tmp_path / "lista"
    pasta_lista.mkdir()
    (pasta_lista / "croqui.yaml").write_text("- item1\n", encoding="utf-8")
    assert validar_versoes_migracao([pasta_lista], versao_esperada=10) == []

    pasta_defasada = tmp_path / "defasada"
    pasta_defasada.mkdir()
    (pasta_defasada / "croqui.yaml").write_text("id: v\nultima_migracao: 1\n", encoding="utf-8")
    erros_def = validar_versoes_migracao([pasta_defasada], versao_esperada=10)
    assert len(erros_def) == 1
    assert "desatualizada" in erros_def[0]

    pasta_corrompida = tmp_path / "corrompida"
    pasta_corrompida.mkdir()
    (pasta_corrompida / "croqui.yaml").write_text("chave: [invalido", encoding="utf-8")
    erros_corr = validar_versoes_migracao([pasta_corrompida], versao_esperada=10)
    assert len(erros_corr) == 1
    assert "Erro ao verificar versão de migração" in erros_corr[0]


def test_validar_pull_request_compila_gera_diff_resumo_html_e_publica_no_r2(
    tmp_path: Path,
) -> None:
    """Deve compilar a base e a PR, gerar resumo.html, publicar no R2 via Fake e salvar o comentário."""
    repo_base = tmp_path / "repo_base"
    _preparar_mini_repositorio(repo_base)

    repo_pr = tmp_path / "repo_pr"
    pasta_pr = _preparar_mini_repositorio(repo_pr)
    # Modifica o nome da via na PR mantendo o mesmo UID
    texto_pr = (pasta_pr / "croqui.yaml").read_text(encoding="utf-8").replace(
        "Via Teste", "Via Teste Modificada"
    )
    (pasta_pr / "croqui.yaml").write_text(texto_pr, encoding="utf-8")

    fake_r2 = ClienteR2Fake()
    arquivo_comentario = tmp_path / "pr_comment.txt"
    dir_saida = tmp_path / "saida_pr"

    erros = validar_pull_request(
        pastas_modificadas=[str(pasta_pr)],
        diretorio_saida=str(dir_saida),
        diretorio_base_database=str(repo_base / "database"),
        numero_pr=42,
        commit_sha="1234567890abcdef",
        caminho_comentario_saida=str(arquivo_comentario),
        cliente_r2=fake_r2,
        bucket_r2="aresta-serving",
        raiz_repositorio=repo_pr,
    )

    assert erros == []
    assert (dir_saida / "resumo.html").is_file()
    html_gerado = (dir_saida / "resumo.html").read_text(encoding="utf-8")
    assert "pr00-0042" in html_gerado
    assert "Via Teste Modificada" in html_gerado

    # Verifica objetos publicados no ClienteR2Fake
    chaves_r2 = fake_r2.listar_chaves("aresta-serving", prefixo="pr/42/")
    assert "pr/42/resumo.html" in chaves_r2
    assert "pr/42/indice.binarypb" in chaves_r2
    assert "pr/42/cipo_teste/compilado.binarypb" in chaves_r2

    # Verifica comentário gerado
    comentario = arquivo_comentario.read_text(encoding="utf-8")
    assert comentario.startswith(ASSINATURA_COMENTARIO_PR)
    assert "https://previa.arestaclimb.com/pr00-0042" in comentario
    assert "https://previa.arestaclimb.com/resumo/pr00-0042" in comentario


def test_validar_pull_request_sem_credenciais_r2_e_sem_diretorio_saida_explicito(
    tmp_path: Path,
) -> None:
    """Deve executar validação em diretório temporário e registrar aviso quando sem credenciais R2."""
    repo_pr = tmp_path / "repo_pr"
    pasta_pr = _preparar_mini_repositorio(repo_pr)
    arquivo_comentario = tmp_path / "comentario_sem_r2.txt"

    erros = validar_pull_request(
        pastas_modificadas=[str(pasta_pr)],
        numero_pr=7,
        caminho_comentario_saida=str(arquivo_comentario),
        ambiente={},
        raiz_repositorio=repo_pr,
    )
    assert erros == []
    comentario = arquivo_comentario.read_text(encoding="utf-8")
    assert "pr00-0007" in comentario
    assert "Credenciais do R2 ausentes" in comentario

    # Lista de pastas vazia retorna sem erros
    assert validar_pull_request([], raiz_repositorio=repo_pr) == []


def test_validar_pull_request_erros_cabecalho_pasta_migracao_e_compilacao(
    tmp_path: Path,
) -> None:
    """Deve reportar erros e gravar comentário de falha com assinatura invisível em cada etapa."""
    comentario_falha = tmp_path / "falha.txt"

    # 1. Falha de cabeçalho SPDX
    repo_sem_spdx = tmp_path / "repo_sem_spdx"
    pasta_1 = _preparar_mini_repositorio(repo_sem_spdx, cabecalho_py_valido=False)
    erros_1 = validar_pull_request(
        [str(pasta_1)],
        caminho_comentario_saida=str(comentario_falha),
        raiz_repositorio=repo_sem_spdx,
    )
    assert len(erros_1) >= 1
    assert comentario_falha.read_text(encoding="utf-8").startswith(ASSINATURA_COMENTARIO_PR)

    # 2. Pasta inexistente
    repo_ok = tmp_path / "repo_ok"
    _preparar_mini_repositorio(repo_ok)
    erros_2 = validar_pull_request(
        [str(tmp_path / "pasta_inexistente")],
        caminho_comentario_saida=str(comentario_falha),
        raiz_repositorio=repo_ok,
    )
    assert len(erros_2) == 1
    assert "Pasta não encontrada" in erros_2[0]

    # 3. Migração desatualizada
    repo_mig = tmp_path / "repo_mig"
    pasta_mig = _preparar_mini_repositorio(repo_mig, ultima_migracao=0)
    erros_3 = validar_pull_request(
        [str(pasta_mig)],
        caminho_comentario_saida=str(comentario_falha),
        raiz_repositorio=repo_mig,
    )
    assert len(erros_3) == 1
    assert "desatualizada" in erros_3[0]

    # 4. Erro de compilação no deploy (croqui.yaml sem id válido)
    repo_comp = tmp_path / "repo_comp"
    pasta_comp = _preparar_mini_repositorio(repo_comp)
    (pasta_comp / "croqui.yaml").write_text(
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        f"ultima_migracao: {obter_ultima_versao_migracao()}\n",
        encoding="utf-8",
    )
    erros_4 = validar_pull_request(
        [str(pasta_comp)],
        caminho_comentario_saida=str(comentario_falha),
        raiz_repositorio=repo_comp,
    )
    assert len(erros_4) == 1
    assert "Falha ao validar lote de croquis" in erros_4[0]


def test_main_cli_validacao_limpeza_pr_e_codigos_saida(tmp_path: Path) -> None:
    """Deve retornar códigos 0 (sucesso/limpeza), 1 (falha de validação) e 2 (argumentos inválidos)."""
    repo_pr = tmp_path / "repo_cli"
    pasta_pr = _preparar_mini_repositorio(repo_pr)
    fake_r2 = ClienteR2Fake()

    # Sucesso na validação (código 0)
    cod_ok = main(
        argv=[
            "--pastas",
            str(pasta_pr),
            "--numero-pr",
            "42",
        ],
        cliente_r2=fake_r2,
        raiz_repositorio=repo_pr,
    )
    assert cod_ok == 0
    assert "pr/42/resumo.html" in fake_r2.listar_chaves("aresta-serving", prefixo="pr/42/")

    # Limpeza da PR no fechamento (--limpar-pr)
    cod_limpar = main(
        argv=["--limpar-pr", "42"],
        cliente_r2=fake_r2,
        raiz_repositorio=repo_pr,
    )
    assert cod_limpar == 0
    assert fake_r2.listar_chaves("aresta-serving", prefixo="pr/42/") == []

    # Limpeza sem credenciais R2 no ambiente
    assert main(argv=["--limpar-pr", "42"], ambiente={}, raiz_repositorio=repo_pr) == 0

    # Falha legítima de validação (código 1)
    cod_falha = main(
        argv=["--pastas", str(tmp_path / "inexistente")],
        raiz_repositorio=repo_pr,
    )
    assert cod_falha == 1

    # Argumentos inválidos da CLI (código 2)
    assert main(argv=["--pastas"], raiz_repositorio=repo_pr) == 2
    assert main(argv=[], raiz_repositorio=repo_pr) == 2
