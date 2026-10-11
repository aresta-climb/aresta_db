# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Teste de contrato de proibição de campos deprecados de Protobuf.

Inspeciona dinamicamente os descritores Protobuf para identificar campos marcados
com [deprecated = true] (ex: PontoDeInteresse.id, PontoDeInteresse.label,
Referencia.ids, Referencia.escalada, Referencia.setor, Referencia.grupo)
e audita a AST dos arquivos Python das pastas editor/, scripts/ e serving/,
garantindo que o código utilize exclusivamente os novos campos (uid, rotulo, alvo_uid, pontos_uids).
"""

import ast
from pathlib import Path
from typing import Any

from aresta_api.proto.generated import croqui_pb2

PASTA_RAIZ: Path = Path(__file__).resolve().parent.parent
PASTAS_AUDITADAS: list[Path] = [
    PASTA_RAIZ / "editor",
    PASTA_RAIZ / "scripts",
    PASTA_RAIZ / "serving",
]


def obter_campos_deprecados_por_mensagem() -> dict[str, set[str]]:
    """Extrai do descritor Protobuf todos os campos marcados como [deprecated = true]."""
    deprecados: dict[str, set[str]] = {}

    def _inspecionar_descriptor(msg_desc: Any) -> None:
        campos = {f.name for f in msg_desc.fields if f.GetOptions().deprecated}
        if campos:
            deprecados[msg_desc.name] = campos
        for nested in msg_desc.nested_types:
            _inspecionar_descriptor(nested)

    for msg_desc in croqui_pb2.DESCRIPTOR.message_types_by_name.values():
        _inspecionar_descriptor(msg_desc)
    return deprecados


class VisitanteASTCamposDeprecados(ast.NodeVisitor):
    """Analisa a AST de um módulo Python em busca de uso de campos Protobuf deprecados."""

    def __init__(self, caminho_arquivo: Path) -> None:
        self.caminho_arquivo: Path = caminho_arquivo
        self.violacoes: list[tuple[int, str, str]] = []  # (linha, campo, detalhe)

        # Nomes comuns de variáveis representando PontoDeInteresse ou Referencia
        self._nomes_var_poi = {
            "poi",
            "p",
            "ponto",
            "ponto_de_interesse",
            "p1",
            "p2",
            "p_orig",
            "p_hover",
            "p_novo",
            "poi_antigo",
            "poi_novo",
            "poi_dict",
            "linha_cand",
            "sub1",
            "sub2",
            "sub3",
            "linha_proto",
        }
        self._nomes_var_ref = {
            "ref",
            "referencia",
            "r",
            "ref_antiga",
            "ref_nova",
            "ref_editada",
            "ref_criada",
            "nova_ref",
            "ref_trav",
            "ref_setor",
            "ref_geral",
        }

    def visit_Call(self, node: ast.Call) -> None:
        """Verifica chamadas de instanciação de mensagens Protobuf com campos deprecados."""
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("PontoDeInteresse", "Referencia") or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "add"
            and hasattr(node.func.value, "attr")
            and node.func.value.attr in ("referencias", "pontos_de_interesse")
        ):
            # Se for teste legado específico de migração de croqui, permite
            if "croqui_model_test.py" not in str(self.caminho_arquivo):
                for keyword in node.keywords:
                    if keyword.arg:
                        if keyword.arg in ("id", "label") and (
                            func_name == "PontoDeInteresse"
                            or (
                                isinstance(node.func, ast.Attribute)
                                and getattr(node.func.value, "attr", "") == "pontos_de_interesse"
                            )
                        ):
                            self.violacoes.append(
                                (
                                    node.lineno,
                                    keyword.arg,
                                    f"Uso de campo deprecado '{keyword.arg}' em POI",
                                )
                            )
                        elif keyword.arg in ("ids", "escalada", "setor", "grupo") and (
                            func_name == "Referencia"
                            or (
                                isinstance(node.func, ast.Attribute)
                                and getattr(node.func.value, "attr", "") == "referencias"
                            )
                        ):
                            self.violacoes.append(
                                (
                                    node.lineno,
                                    keyword.arg,
                                    f"Uso de campo deprecado '{keyword.arg}' em Referência",
                                )
                            )

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Verifica acessos a atributos deprecados em variáveis de POI ou Referência."""
        nome_base = ""
        if isinstance(node.value, ast.Name):
            nome_base = node.value.id.lower()
        elif isinstance(node.value, ast.Attribute):
            nome_base = node.value.attr.lower()

        attr = node.attr

        # 1. Checagem de PontoDeInteresse: .label ou .id (quando nome_base é POI)
        if attr == "label" and (
            nome_base == "p"
            or any(
                p in nome_base
                for p in (
                    "poi",
                    "ponto",
                    "p1",
                    "p2",
                    "pt",
                    "p_orig",
                    "p_hover",
                    "p_novo",
                    "linha",
                    "geom",
                )
            )
        ):
            self.violacoes.append(
                (
                    node.lineno,
                    attr,
                    f"Acesso ao campo deprecado '{attr}' em POI (use 'rotulo')",
                )
            )
        elif attr == "id" and (
            nome_base == "p"
            or any(
                p in nome_base
                for p in ("poi", "ponto", "p1", "p2", "linha_cand", "sub1", "sub2", "sub3")
            )
        ):
            self.violacoes.append(
                (
                    node.lineno,
                    attr,
                    f"Acesso a '{nome_base}.id' deprecado em POI (use '{nome_base}.uid')",
                )
            )

        # 2. Checagem de Referencia: .ids, .escalada, .setor, .grupo
        elif attr == "ids" and (
            nome_base == "r" or any(r in nome_base for r in ("ref", "referencia"))
        ):
            self.violacoes.append(
                (
                    node.lineno,
                    attr,
                    f"Acesso ao campo deprecado '{nome_base}.ids' (use '{nome_base}.pontos_uids')",
                )
            )
        elif attr in ("escalada", "setor", "grupo") and (
            nome_base == "r" or any(r in nome_base for r in ("ref", "referencia"))
        ):
            # Descarta variáveis de SetorOuGrupo como sg_ref
            if not any(sg in nome_base for sg in ("sg", "setor_ou_grupo")):
                self.violacoes.append(
                    (
                        node.lineno,
                        attr,
                        f"Acesso ao campo deprecado '{nome_base}.{attr}' em Referência (use '{nome_base}.alvo_uid')",
                    )
                )

        self.generic_visit(node)


def test_proibicao_campos_deprecados_protobuf():
    """Garante que nenhum arquivo em editor/, scripts/ e serving/ utiliza campos deprecados do protobuf."""
    campos_deprecados = obter_campos_deprecados_por_mensagem()
    assert "PontoDeInteresse" in campos_deprecados, (
        "Descritor deve conter PontoDeInteresse com campos deprecados"
    )
    assert "Referencia" in campos_deprecados, (
        "Descritor deve conter Referencia com campos deprecados"
    )

    assert "id" in campos_deprecados["PontoDeInteresse"]
    assert "label" in campos_deprecados["PontoDeInteresse"]
    assert "ids" in campos_deprecados["Referencia"]
    assert "escalada" in campos_deprecados["Referencia"]
    assert "setor" in campos_deprecados["Referencia"]
    assert "grupo" in campos_deprecados["Referencia"]

    total_violacoes: list[str] = []

    for pasta in PASTAS_AUDITADAS:
        if not pasta.exists():
            continue
        for arq in sorted(pasta.rglob("*.py")):
            # Ignora migrações legadas se houver ou caches
            if "__pycache__" in arq.parts or ".pytest_cache" in arq.parts:
                continue

            try:
                conteudo = arq.read_text(encoding="utf-8")
                arvore = ast.parse(conteudo, filename=str(arq))
            except Exception as e:
                total_violacoes.append(f"{arq}: Erro ao fazer parse AST: {e}")
                continue

            visitante = VisitanteASTCamposDeprecados(arq)
            visitante.visit(arvore)

            for linha, campo, detalhe in visitante.violacoes:
                rel_path = arq.relative_to(PASTA_RAIZ)
                total_violacoes.append(f"{rel_path}:{linha} [{campo}] {detalhe}")

    assert not total_violacoes, (
        f"Foram encontrados {len(total_violacoes)} usos de campos deprecados de Protobuf em editor/, scripts/ ou serving/:\n"
        + "\n".join(total_violacoes[:30])
    )
