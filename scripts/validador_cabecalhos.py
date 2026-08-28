# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para validação de cabeçalhos SPDX e direitos autorais (Copyright) no repositório.
Executa validações diretas em Python sem necessidade do pytest ou subprocessos.
"""

import re
from pathlib import Path

# Padrões regex para SPDX e Copyright
PADRAO_SPDX_MPL = re.compile(r"^#\s*SPDX-License-Identifier:\s*MPL-2\.0\s*$", re.MULTILINE)
PADRAO_SPDX_ODBL = re.compile(r"^#\s*SPDX-License-Identifier:\s*ODbL-1\.0\s*$", re.MULTILINE)
PADRAO_COPYRIGHT = re.compile(
    r"^#\s*(SPDX-FileCopyrightText:\s*)?Copyright\s*\([Cc]\)\s*\d{4}\s*Aresta\s+(Climb\s+)?Contributors\s*$",
    re.MULTILINE,
)

DIRETORIOS_IGNORADOS = {".git", "generated", "database", ".pytest_cache", "__pycache__", "venv", ".venv"}
DIRETORIOS_IGNORADOS_GPL = {".git", "generated", "database", ".pytest_cache", "__pycache__", "venv", ".venv", "openspec"}
ARQUIVOS_IGNORADOS_GPL = {"codebase_headers_test.py", "validador_cabecalhos.py", "validador_cabecalhos_test.py"}


def obter_raiz_repositorio(raiz: Path | None = None) -> Path:
    """Retorna o caminho raiz do repositório."""
    if raiz is not None:
        return raiz.resolve()
    return Path(__file__).resolve().parent.parent


def verificar_spdx_e_copyright_py(raiz: Path | None = None) -> list[str]:
    """
    Verifica se todos os arquivos .py contêm cabeçalho MPL-2.0 e Copyright válido.
    """
    root = obter_raiz_repositorio(raiz)
    erros = []
    arquivos_sem_spdx = []
    arquivos_sem_copyright = []
    total = 0

    for filepath in root.rglob("*.py"):
        if any(part in DIRETORIOS_IGNORADOS for part in filepath.parts):
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        total += 1
        rel_path = filepath.relative_to(root)

        if not PADRAO_SPDX_MPL.search(content):
            arquivos_sem_spdx.append(f"{rel_path} (Faltou MPL-2.0)")

        if not PADRAO_COPYRIGHT.search(content):
            arquivos_sem_copyright.append(str(rel_path))

    if total == 0:
        erros.append("Nenhum arquivo .py encontrado! Caminho base pode estar incorreto.")
    if arquivos_sem_spdx:
        erros.append(f"Arquivos .py com SPDX incorreto: {', '.join(arquivos_sem_spdx)}")
    if arquivos_sem_copyright:
        erros.append(f"Arquivos .py sem Copyright exato: {', '.join(arquivos_sem_copyright)}")

    return erros


def verificar_gpl_residual_py(
    raiz: Path | None = None,
    arquivos_a_ignorar: set[str] | None = None,
) -> list[str]:
    """
    Verifica se nenhum arquivo .py ativo contém menções residuais à licença GPL.
    """
    root = obter_raiz_repositorio(raiz)
    ignorar_nomes = ARQUIVOS_IGNORADOS_GPL if arquivos_a_ignorar is None else arquivos_a_ignorar
    erros = []
    arquivos_com_gpl = []

    for filepath in root.rglob("*.py"):
        if any(part in DIRETORIOS_IGNORADOS_GPL for part in filepath.parts):
            continue
        if filepath.name in ignorar_nomes:
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if "GPL-3.0" in content or "GPLv3" in content:
            arquivos_com_gpl.append(str(filepath.relative_to(root)))

    if arquivos_com_gpl:
        erros.append(f"Arquivos com menção residual a GPL: {', '.join(arquivos_com_gpl)}")

    return erros


def verificar_odbl_e_copyright_database(raiz: Path | None = None) -> list[str]:
    """
    Verifica se todos os arquivos .yaml e .md com frontmatter dentro de database/
    possuem cabeçalho ODbL-1.0 e Copyright válido.
    """
    root = obter_raiz_repositorio(raiz)
    database_dir = root / "database"

    if not database_dir.exists() or not database_dir.is_dir():
        return ["Diretório database/ não encontrado na raiz informada."]

    erros = []
    arquivos_sem_odbl = []
    arquivos_sem_copyright = []
    total = 0

    for filepath in database_dir.rglob("*"):
        if filepath.is_dir() or filepath.suffix not in {".yaml", ".md"}:
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if filepath.suffix == ".md" and not content.startswith("---"):
            continue

        total += 1
        rel_path = str(filepath.relative_to(root))

        if not PADRAO_SPDX_ODBL.search(content):
            arquivos_sem_odbl.append(rel_path)

        if not PADRAO_COPYRIGHT.search(content):
            arquivos_sem_copyright.append(rel_path)

    if total == 0:
        erros.append("Nenhum arquivo de database encontrado!")
    if arquivos_sem_odbl:
        erros.append(
            f"Arquivos na database sem ODbL-1.0: {len(arquivos_sem_odbl)} arquivos (ex: {', '.join(arquivos_sem_odbl[:5])})"
        )
    if arquivos_sem_copyright:
        erros.append(
            f"Arquivos na database sem Copyright correto: {len(arquivos_sem_copyright)} arquivos (ex: {', '.join(arquivos_sem_copyright[:5])})"
        )

    return erros


def validar_todos_cabecalhos_e_licencas(raiz: Path | None = None) -> list[str]:
    """
    Executa todas as validações de cabeçalhos e licenças do repositório.
    Retorna uma lista consolidada de erros (vazia se tudo estiver em conformidade).
    """
    root = obter_raiz_repositorio(raiz)
    erros = []
    erros.extend(verificar_spdx_e_copyright_py(root))
    erros.extend(verificar_gpl_residual_py(root))
    erros.extend(verificar_odbl_e_copyright_database(root))
    return erros
