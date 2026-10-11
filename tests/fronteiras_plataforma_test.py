# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de integração e fronteiras de plataforma.
Valida estaticamente via AST que:
1. Nenhum módulo fora de editor/plataforma importa APIs ou subsistemas nativos específicos de sistema operacional.
2. Nenhum módulo fora da camada autorizada faz checagens diretas de plataforma (sys.platform, platform.system()).
3. Nenhum arquivo fora de editor/plataforma acessa submódulos internos (ex: editor.plataforma.windows).
4. Todos os adaptadores de plataforma concretos implementam integralmente os contratos definidos.
"""

import ast
from pathlib import Path

import pytest

from editor.plataforma.contrato import AdaptadorPlataforma

PASTA_RAIZ_REPOSITORIO: Path = Path(__file__).resolve().parent.parent
PASTA_EDITOR: Path = PASTA_RAIZ_REPOSITORIO / "editor"
PASTA_PLATAFORMA: Path = PASTA_EDITOR / "plataforma"

# Módulos ou símbolos nativos de SO restritos exclusivamente a editor/plataforma/
IMPORTACOES_NATIVAS_PROIBIDAS: set[str] = {
    # Windows
    "winrt",
    "winreg",
    "msilib",
    "winsound",
    "win32api",
    "win32gui",
    "win32con",
    "win32com",
    "win32process",
    "pywintypes",
    # macOS
    "objc",
    "AppKit",
    "Foundation",
    "Cocoa",
    "Quartz",
    # Unix / Linux específicos
    "posix",
    "fcntl",
    "pwd",
    "grp",
    "spwd",
    "termios",
    "syslog",
}

SUBMODULOS_PLATAFORMA_INTERNOS_PROIBIDOS: set[str] = {
    "editor.plataforma.windows",
    "editor.plataforma.linux",
    "editor.plataforma.macos",
    "editor.platform",
}

# Arquivos permitidos para checagens de compilação ou empacotamento externo
ARQUIVOS_PERMITIDOS_CHECAGEM_SO: set[str] = {
    "build.py",
}


class VisitanteASTFronteirasPlataforma(ast.NodeVisitor):
    """Varre a árvore sintática buscando importações e acessos a APIs de SO não permitidos fora da biblioteca de plataforma."""

    def __init__(self, caminho_arquivo: Path, checar_acesso_plataforma: bool = False) -> None:
        self.caminho_arquivo: Path = caminho_arquivo
        self.checar_acesso_plataforma: bool = checar_acesso_plataforma
        self.violacoes: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            nome_modulo = alias.name
            if nome_modulo in IMPORTACOES_NATIVAS_PROIBIDAS or any(
                nome_modulo.startswith(f"{m}.") for m in IMPORTACOES_NATIVAS_PROIBIDAS
            ):
                self.violacoes.append(
                    f"Linha {node.lineno}: importação direta proibida do módulo de SO '{nome_modulo}'"
                )
            for proibido in SUBMODULOS_PLATAFORMA_INTERNOS_PROIBIDOS:
                if nome_modulo == proibido or nome_modulo.startswith(f"{proibido}."):
                    self.violacoes.append(
                        f"Linha {node.lineno}: importação proibida do submódulo interno '{nome_modulo}' (use apenas 'editor.plataforma')"
                    )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            modulo_origem = node.module
            if modulo_origem in IMPORTACOES_NATIVAS_PROIBIDAS or any(
                modulo_origem.startswith(f"{m}.") for m in IMPORTACOES_NATIVAS_PROIBIDAS
            ):
                self.violacoes.append(
                    f"Linha {node.lineno}: importação 'from {modulo_origem}' proibida"
                )
            for proibido in SUBMODULOS_PLATAFORMA_INTERNOS_PROIBIDOS:
                if modulo_origem == proibido or modulo_origem.startswith(f"{proibido}."):
                    self.violacoes.append(
                        f"Linha {node.lineno}: importação direta de '{modulo_origem}' proibida (use apenas 'editor.plataforma')"
                    )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Detecta uso de ctypes.windll ou ctypes.oledll fora de editor/plataforma
        if node.attr in ("windll", "oledll"):
            if isinstance(node.value, ast.Name) and node.value.id == "ctypes":
                self.violacoes.append(
                    f"Linha {node.lineno}: acesso direto proibido a 'ctypes.{node.attr}'"
                )

        # Detecta checagens diretas de sys.platform fora dos arquivos permitidos
        if self.checar_acesso_plataforma:
            if (
                node.attr == "platform"
                and isinstance(node.value, ast.Name)
                and node.value.id == "sys"
            ):
                self.violacoes.append(
                    f"Linha {node.lineno}: checagem direta proibida de 'sys.platform' (delegue para 'editor.plataforma')"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Detecta chamadas a platform.system() fora da camada de plataforma
        if self.checar_acesso_plataforma:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "system":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "platform":
                    self.violacoes.append(
                        f"Linha {node.lineno}: chamada proibida a 'platform.system()' (delegue para 'editor.plataforma')"
                    )
        self.generic_visit(node)


def coletar_arquivos_python_editor(ignorar_testes: bool = False) -> list[Path]:
    """Retorna todos os arquivos .py dentro de editor/ excluindo a pasta editor/plataforma/."""
    arquivos: list[Path] = []
    for caminho in PASTA_EDITOR.rglob("*.py"):
        # Ignora arquivos sob editor/plataforma/
        try:
            caminho.relative_to(PASTA_PLATAFORMA)
            continue
        except ValueError:
            pass

        # Ignora arquivos de compilação de release / tools de release externos
        if "release_tools" in caminho.parts:
            continue

        if ignorar_testes and (caminho.stem.endswith("_test") or caminho.name.startswith("test_")):
            continue

        arquivos.append(caminho)
    return arquivos


def test_fronteiras_plataforma_sem_vazamento_de_apis_nativas() -> None:
    """
    Garante que nenhum arquivo fora de editor/plataforma acesse APIs de SO
    ou importe módulos nativos diretamente.
    """
    arquivos = coletar_arquivos_python_editor()
    assert len(arquivos) > 0, "Nenhum arquivo python encontrado em editor/"

    todas_violacoes: list[tuple[Path, list[str]]] = []

    for arq in arquivos:
        conteudo = arq.read_text(encoding="utf-8")
        try:
            arvore = ast.parse(conteudo, filename=str(arq))
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe em {arq}: {e}")

        visitante = VisitanteASTFronteirasPlataforma(arq, checar_acesso_plataforma=False)
        visitante.visit(arvore)
        if visitante.violacoes:
            todas_violacoes.append((arq, visitante.violacoes))

    if todas_violacoes:
        mensagens: list[str] = ["Violações de fronteira de plataforma encontradas:"]
        for arq, erros in todas_violacoes:
            rel = arq.relative_to(PASTA_RAIZ_REPOSITORIO)
            mensagens.append(f"\nNo arquivo {rel}:")
            for e in erros:
                mensagens.append(f"  - {e}")
        pytest.fail("\n".join(mensagens))


def test_fronteiras_plataforma_sem_checagens_diretas_de_sistema_operacional() -> None:
    """
    Garante que nenhum arquivo de produção fora das exceções permitidas
    faça verificações diretas de sistema operacional (sys.platform, platform.system()).
    Toda lógica condicional de plataforma deve residir estritamente em editor/plataforma/.
    """
    arquivos_producao = coletar_arquivos_python_editor(ignorar_testes=True)
    todas_violacoes: list[tuple[Path, list[str]]] = []

    for arq in arquivos_producao:
        if arq.name in ARQUIVOS_PERMITIDOS_CHECAGEM_SO:
            continue

        conteudo = arq.read_text(encoding="utf-8")
        try:
            arvore = ast.parse(conteudo, filename=str(arq))
        except SyntaxError as e:
            pytest.fail(f"Erro de sintaxe em {arq}: {e}")

        visitante = VisitanteASTFronteirasPlataforma(arq, checar_acesso_plataforma=True)
        visitante.visit(arvore)
        if visitante.violacoes:
            todas_violacoes.append((arq, visitante.violacoes))

    if todas_violacoes:
        mensagens: list[str] = [
            "Checagens diretas de sistema operacional encontradas fora de editor/plataforma/:"
        ]
        for arq, erros in todas_violacoes:
            rel = arq.relative_to(PASTA_RAIZ_REPOSITORIO)
            mensagens.append(f"\nNo arquivo {rel}:")
            for e in erros:
                mensagens.append(f"  - {e}")
        pytest.fail("\n".join(mensagens))


def test_adaptadores_de_plataforma_implementam_contrato_integralmente() -> None:
    """
    Garante que os adaptadores de todas as plataformas suportadas
    implementem integralmente o protocolo AdaptadorPlataforma com todos os métodos exigidos.
    """
    from editor.plataforma.linux.integracao import AdaptadorLinux
    from editor.plataforma.macos.integracao import AdaptadorMacOS
    from editor.plataforma.windows.integracao import AdaptadorWindows

    adaptadores = [AdaptadorWindows, AdaptadorLinux, AdaptadorMacOS]

    metodos_obrigatorios = [
        "configurar_ambiente_plataforma",
        "configurar_presenca_barra_de_tarefas",
        "configurar_identidade_processo",
        "trazer_janela_para_frente",
        "obter_diretorio_dados_usuario",
        "verificar_atualizacoes_disponiveis",
        "solicitar_instalacao_atualizacao",
    ]

    for cls in adaptadores:
        instancia = cls()
        assert isinstance(instancia, AdaptadorPlataforma), (
            f"{cls.__name__} deve cumprir o protocolo AdaptadorPlataforma"
        )
        for metodo in metodos_obrigatorios:
            assert hasattr(instancia, metodo), (
                f"{cls.__name__} deve implementar o método '{metodo}'"
            )
            assert callable(getattr(instancia, metodo)), (
                f"'{metodo}' em {cls.__name__} deve ser invocável"
            )


def test_visitante_ast_detecta_violacoes_corretamente(tmp_path: Path) -> None:
    """Valida se o VisitanteASTFronteirasPlataforma captura todas as categorias de violação."""
    codigo_infrator = """
import winreg
from objc import NSString
from editor.plataforma.windows.integracao import IntegracaoWindows
import ctypes
ctypes.windll.user32.ShowWindow()
import sys
if sys.platform == 'win32':
    pass
import platform
platform.system()
"""
    arvore = ast.parse(codigo_infrator)
    visitante = VisitanteASTFronteirasPlataforma(
        tmp_path / "infrator.py", checar_acesso_plataforma=True
    )
    visitante.visit(arvore)

    violacoes = "\n".join(visitante.violacoes)
    assert "winreg" in violacoes
    assert "objc" in violacoes
    assert "editor.plataforma.windows" in violacoes
    assert "ctypes.windll" in violacoes
    assert "sys.platform" in violacoes
    assert "platform.system" in violacoes
