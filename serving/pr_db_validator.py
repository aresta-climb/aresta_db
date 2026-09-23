# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Utilitário e biblioteca para validação de pull requests que modificam croquis.
"""

import sys
import tempfile
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path para resolução de módulos
_RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent
if str(_RAIZ_REPOSITORIO) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(_RAIZ_REPOSITORIO))

from scripts.deploy_generated import deploy
from scripts.validador_cabecalhos import validar_todos_cabecalhos_e_licencas


def validar_cabecalhos_e_licencas() -> list[str]:
    """
    Executa a validação de cabeçalhos e licenças utilizando a biblioteca nativa validador_cabecalhos.
    """
    erros = validar_todos_cabecalhos_e_licencas(_RAIZ_REPOSITORIO)
    if erros:
        for erro in erros:
            print(f"ERRO: {erro}")
    else:
        print("Sucesso: Cabeçalhos e licenças SPDX/Copyright validados com êxito.")
    return erros


def validar_pull_request(pastas_modificadas: list[str], diretorio_saida: str | None = None) -> list[str]:
    """
    Valida um pull request:
    1. Executa a validação de conformidade de cabeçalhos e licenças.
    2. Valida se os caminhos existem.
    3. Executa a rotina de deploy em modo verificação (sem salvar artefatos definitivos).
    
    Args:
        pastas_modificadas: Lista de caminhos relativos para pastas dentro de database/.
        diretorio_saida: Diretório opcional para geração transitória. Se omitido, usa diretório temporário.
        
    Returns:
        Uma lista de mensagens de erro. Se estiver vazia, significa sucesso total.
    """
    erros: list[str] = []
    
    # 1. Validação de cabeçalhos e licenças
    erros.extend(validar_cabecalhos_e_licencas())
    if erros:
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
            
    if erros or not db_paths:
        return erros

    def _executar_validacao(out_dir: Path) -> None:
        try:
            deploy(
                output_dir=out_dir,
                target_paths=db_paths,
                force_thumbnails=False,
                gerar_arquivos_de_debug=False,
                is_producao=False,
                verbose=False,
                sair_ao_falhar=False,
            )
            print(f"Sucesso: {len(db_paths)} croqui(s) validados com êxito")
        except Exception as e:
            msg_erro = f"Falha ao validar lote de croquis: {str(e)}"
            print(f"ERRO: {msg_erro}")
            erros.append(msg_erro)

    if diretorio_saida:
        out_dir = Path(diretorio_saida)
        out_dir.mkdir(parents=True, exist_ok=True)
        _executar_validacao(out_dir)
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            _executar_validacao(Path(temp_dir))
            
    return erros


def main() -> int:
    import argparse
    
    parser = argparse.ArgumentParser(description="Valida pastas modificadas do database/")
    parser.add_argument("--pastas", nargs="+", required=True, help="Lista de pastas modificadas")
    parser.add_argument("--saida", default=None, help="Diretório de saída opcional para os artefatos")
    
    args = parser.parse_args()
    erros = validar_pull_request(args.pastas, args.saida)
    
    if erros:
        print(f"\nValidação concluída com {len(erros)} erro(s).")
        return 1
    else:
        print("\nValidação concluída com sucesso.")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
