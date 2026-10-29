# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário e biblioteca para validação, geração de resumo visual (`resumo.html`),
publicação e limpeza de instâncias de prévia para Pull Requests que modificam croquis.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Garante que a raiz do repositório esteja no sys.path para resolução de módulos
_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from editor.core.serializacao_util import carregar_yaml
from scripts.deploy_generated import deploy
from scripts.migrador import obter_ultima_versao_migracao
from scripts.validador_cabecalhos import validar_todos_cabecalhos_e_licencas
from serving.diff_croqui_pr_lib import calcular_diff_pull_request
from serving.publicador_pr_r2_lib import (
    criar_cliente_r2_do_ambiente,
    limpar_pasta_pr_no_r2,
    publicar_diretorio_pr_no_r2,
)
from serving.renderizador_resumo_pr_lib import (
    renderizar_comentario_falha_pr_markdown,
    renderizar_comentario_pr_markdown,
    renderizar_resumo_html,
)


def validar_cabecalhos_e_licencas(
    raiz_repositorio: Path = _RAIZ_REPOSITORIO,
) -> list[str]:
    """
    Executa a validação de cabeçalhos e licenças utilizando a biblioteca nativa validador_cabecalhos.
    """
    erros = validar_todos_cabecalhos_e_licencas(raiz_repositorio)
    if erros:
        for erro in erros:
            print(f"ERRO: {erro}")
    else:
        print("Sucesso: Cabeçalhos e licenças SPDX/Copyright validados com êxito.")
    return erros


def validar_versoes_migracao(
    pastas: list[Path],
    versao_esperada: int | None = None,
) -> list[str]:
    """
    Valida se todos os croquis contidos nas pastas modificadas possuem
    o campo 'ultima_migracao' atualizado com a versão mais recente das migrações.
    """
    erros: list[str] = []
    esperada = obter_ultima_versao_migracao() if versao_esperada is None else versao_esperada
    if esperada == 0:
        return erros

    for pasta in pastas:
        caminho_yaml = pasta / "croqui.yaml"
        if not caminho_yaml.is_file():
            continue

        try:
            with open(caminho_yaml, encoding="utf-8") as f:
                dados = carregar_yaml(f)
            if not isinstance(dados, dict):
                continue
            versao_croqui = dados.get("ultima_migracao", 0)
            if versao_croqui < esperada:
                msg = (
                    f"[{pasta.name}] O croqui está com a versão de migração desatualizada: {versao_croqui}. "
                    f"A versão mais recente esperada é {esperada}. "
                    f"Execute a rotina de migração/correção do database antes de submeter o PR."
                )
                print(f"ERRO: {msg}")
                erros.append(msg)
        except Exception as e:
            msg = f"[{pasta.name}] Erro ao verificar versão de migração em {caminho_yaml}: {e}"
            print(f"ERRO: {msg}")
            erros.append(msg)

    return erros


def _salvar_comentario_se_configurado(caminho_comentario: str | None, conteudo: str) -> None:
    if caminho_comentario:
        caminho = Path(caminho_comentario)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")


def _compilar_base_e_publicar_previa(
    *,
    out_dir: Path,
    db_paths: list[Path],
    diretorio_base_database: str | None,
    numero_pr: int,
    commit_sha: str,
    caminho_comentario_saida: str | None,
    cliente_r2: Any,
    bucket_r2: str,
    ambiente: Mapping[str, str] | None,
) -> None:
    with tempfile.TemporaryDirectory() as temp_base_compilado:
        dir_base_comp = Path(temp_base_compilado)
        if diretorio_base_database:
            raiz_base_db = Path(diretorio_base_database)
            alvos_base = [
                raiz_base_db / p.name
                for p in db_paths
                if (raiz_base_db / p.name / "croqui.yaml").is_file()
            ]
            if alvos_base:
                deploy(
                    output_dir=dir_base_comp,
                    target_paths=alvos_base,
                    database_dir=raiz_base_db,
                    force_thumbnails=False,
                    gerar_arquivos_de_debug=False,
                    is_producao=False,
                    verbose=False,
                    sair_ao_falhar=False,
                )

        resumo_diff = calcular_diff_pull_request(
            dir_base=dir_base_comp,
            dir_pr=out_dir,
        )
        html_resumo = renderizar_resumo_html(
            resumo=resumo_diff,
            numero_pr=numero_pr,
            commit_sha=commit_sha,
        )
        (out_dir / "resumo.html").write_text(html_resumo, encoding="utf-8")

        par_r2 = (
            (cliente_r2, bucket_r2)
            if cliente_r2 is not None
            else criar_cliente_r2_do_ambiente(ambiente)
        )
        publicado = False
        if par_r2 is not None:
            cli_s3, bkt = par_r2
            res_pub = publicar_diretorio_pr_no_r2(
                diretorio_compilado=out_dir,
                numero_pr=numero_pr,
                cliente_r2=cli_s3,
                bucket=bkt,
            )
            publicado = True
            print(
                f"Prévia publicada em s3://{bkt}/{res_pub.prefixo} "
                f"({len(res_pub.arquivos_enviados)} arquivos enviados, "
                f"{len(res_pub.arquivos_orfaos_removidos)} órfãos removidos)."
            )

        comentario_md = renderizar_comentario_pr_markdown(
            resumo=resumo_diff,
            numero_pr=numero_pr,
            publicado_no_r2=publicado,
        )
        _salvar_comentario_se_configurado(caminho_comentario_saida, comentario_md)


def validar_pull_request(
    pastas_modificadas: list[str],
    diretorio_saida: str | None = None,
    *,
    diretorio_base_database: str | None = None,
    numero_pr: int | None = None,
    commit_sha: str = "",
    caminho_comentario_saida: str | None = None,
    cliente_r2: Any = None,
    bucket_r2: str = "aresta-serving",
    ambiente: Mapping[str, str] | None = None,
    raiz_repositorio: Path = _RAIZ_REPOSITORIO,
) -> list[str]:
    """
    Valida uma Pull Request e, quando `numero_pr` é informado, calcula o diff semântico/visual,
    gera `resumo.html` e publica a instância de prévia no R2.
    """
    erros: list[str] = []

    erros.extend(validar_cabecalhos_e_licencas(raiz_repositorio))
    if erros:
        _salvar_comentario_se_configurado(
            caminho_comentario_saida, renderizar_comentario_falha_pr_markdown(erros)
        )
        return erros

    if not pastas_modificadas:
        return erros

    db_paths: list[Path] = []
    for p in pastas_modificadas:
        caminho = Path(p)
        if not caminho.exists():
            erros.append(f"Pasta não encontrada ou inválida: {p}")
        else:
            db_paths.append(caminho)

    if erros:
        _salvar_comentario_se_configurado(
            caminho_comentario_saida, renderizar_comentario_falha_pr_markdown(erros)
        )
        return erros

    erros.extend(validar_versoes_migracao(db_paths))
    if erros:
        _salvar_comentario_se_configurado(
            caminho_comentario_saida, renderizar_comentario_falha_pr_markdown(erros)
        )
        return erros

    def _executar_validacao(out_dir: Path) -> None:
        try:
            deploy(
                output_dir=out_dir,
                target_paths=db_paths,
                database_dir=db_paths[0].resolve().parent,
                force_thumbnails=False,
                gerar_arquivos_de_debug=False,
                is_producao=False,
                verbose=False,
                sair_ao_falhar=False,
            )
            print(f"Sucesso: {len(db_paths)} croqui(s) validados com êxito")
        except Exception as e:
            msg_erro = f"Falha ao validar lote de croquis: {e!s}"
            print(f"ERRO: {msg_erro}")
            erros.append(msg_erro)
            _salvar_comentario_se_configurado(
                caminho_comentario_saida, renderizar_comentario_falha_pr_markdown(erros)
            )
            return

        if numero_pr is not None:
            _compilar_base_e_publicar_previa(
                out_dir=out_dir,
                db_paths=db_paths,
                diretorio_base_database=diretorio_base_database,
                numero_pr=numero_pr,
                commit_sha=commit_sha,
                caminho_comentario_saida=caminho_comentario_saida,
                cliente_r2=cliente_r2,
                bucket_r2=bucket_r2,
                ambiente=ambiente,
            )

    if diretorio_saida:
        out_dir = Path(diretorio_saida)
        out_dir.mkdir(parents=True, exist_ok=True)
        _executar_validacao(out_dir)
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            _executar_validacao(Path(temp_dir))

    return erros


def main(
    argv: list[str] | None = None,
    *,
    cliente_r2: Any = None,
    ambiente: Mapping[str, str] | None = None,
    raiz_repositorio: Path = _RAIZ_REPOSITORIO,
) -> int:
    """
    Ponto de entrada CLI do validador de Pull Requests do database.

    Convenção de códigos de saída:
    - `0`: Validação ou limpeza concluída com sucesso.
    - `1`: Recusa legítima de validação do PR (erros de dados, migração ou licenças SPDX).
    - `2`: Invocação inválida da CLI no workflow.
    """
    parser = argparse.ArgumentParser(description="Valida e publica prévia de PRs do database/")
    parser.add_argument("--pastas", nargs="+", default=None, help="Lista de pastas modificadas")
    parser.add_argument(
        "--saida", default=None, help="Diretório de saída opcional para os artefatos"
    )
    parser.add_argument(
        "--base-database",
        default=None,
        help="Diretório opcional contendo os croquis na branch base para diff",
    )
    parser.add_argument(
        "--numero-pr",
        type=int,
        default=None,
        help="Número da Pull Request para geração de resumo.html e upload no R2",
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help="Hash SHA do commit atual da Pull Request",
    )
    parser.add_argument(
        "--comentario-saida",
        default=None,
        help="Caminho do arquivo Markdown de comentário da PR a ser gerado",
    )
    parser.add_argument(
        "--limpar-pr",
        type=int,
        default=None,
        help="Remove a pasta pr/<numero_pr>/ do bucket R2 quando a PR é fechada",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    if args.limpar_pr is not None:
        par = (
            (cliente_r2, "aresta-serving")
            if cliente_r2 is not None
            else criar_cliente_r2_do_ambiente(ambiente)
        )
        if par is not None:
            cli_s3, bkt = par
            removidos = limpar_pasta_pr_no_r2(
                numero_pr=args.limpar_pr,
                cliente_r2=cli_s3,
                bucket=bkt,
            )
            print(
                f"Limpeza da PR #{args.limpar_pr} concluída ({len(removidos)} objetos removidos)."
            )
        return 0

    if not args.pastas:
        return 2

    erros = validar_pull_request(
        args.pastas,
        args.saida,
        diretorio_base_database=args.base_database,
        numero_pr=args.numero_pr,
        commit_sha=args.commit_sha,
        caminho_comentario_saida=args.comentario_saida,
        cliente_r2=cliente_r2,
        ambiente=ambiente,
        raiz_repositorio=raiz_repositorio,
    )

    if erros:
        print(f"\nValidação concluída com {len(erros)} erro(s).")
        return 1

    print("\nValidação concluída com sucesso.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
