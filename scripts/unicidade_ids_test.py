# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import re
from pathlib import Path
from collections import Counter

def test_unicidade_dos_ids_de_migracao():
    """
    Garante que nenhum script de migração na pasta /migracoes/ possua o mesmo ID sequencial.
    """
    caminho_migracoes = Path(__file__).resolve().parent.parent / "migracoes"
    expressao_id = re.compile(r"^(\d{4})_.*\.py$")
    
    ids_encontrados = []
    
    for item in caminho_migracoes.iterdir():
        if item.is_file() and item.suffix == ".py" and not item.name.endswith("_test.py"):
            match = expressao_id.match(item.name)
            if match:
                ids_encontrados.append(match.group(1))
                
    contagem = Counter(ids_encontrados)
    duplicados = [versao for versao, qtd in contagem.items() if qtd > 1]
    
    assert not duplicados, f"Encontradas migrações com IDs duplicados: {duplicados}"
