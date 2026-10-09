# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Migração 0005: Migração para UIDs universais (Pure NanoID 14c) e rótulos.

Esta migração delega o saneamento contínuo e a injeção de UIDs estáveis
para a biblioteca pura gerenciar_uids_lib.
"""

from pathlib import Path
from scripts.gerenciar_uids_lib import (
    sanear_uids_croqui,
    _extrair_nome_escalada,
    _inserir_ou_mover_para_posicao,
)

# Migração com escopo restrito aos arquivos de dados internos (database/ e croquis).
# Não incrementa a versão pública de serving consumida pelo aplicativo móvel (mantém v4).
AFETA_VERSAO_SERVING: bool = False
MIGRATION_ID: int = 5


def migrar(pico_path: Path) -> None:
    """Ponto de entrada da migração 0005 invocado pelo motor de migrações."""
    sanear_uids_croqui(pico_path)
