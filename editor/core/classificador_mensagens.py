# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para classificação e filtragem de mensagens de saída e logs de compilação.
Evita falsos positivos em nomes de localidades ou vias (como 'Ferros' ou 'Ferramenta')
utilizando limites estritos de palavras (word boundaries).
"""

import re

# Padrões com limites de palavras (\b) para evitar falsos positivos
PADRAO_ERRO = re.compile(
    r"(?i)\b(erro|erros|falhou|falha|falhas|failed|traceback)\b|\b\w*(error|exception)s?\b"
)
PADRAO_AVISO = re.compile(r"(?i)\b(aviso|avisos|warning|warnings)\b")


def eh_linha_de_erro(linha: str) -> bool:
    """Retorna True se a linha contiver palavra-chave de erro com limite de palavra."""
    return bool(PADRAO_ERRO.search(linha))


def eh_linha_de_aviso(linha: str) -> bool:
    """Retorna True se a linha contiver palavra-chave de aviso e não for erro."""
    return bool(PADRAO_AVISO.search(linha)) and not eh_linha_de_erro(linha)


def eh_linha_de_aviso_ou_erro(linha: str) -> bool:
    """Retorna True se a linha for categorizada como aviso ou erro."""
    return eh_linha_de_erro(linha) or bool(PADRAO_AVISO.search(linha))


def filtrar_mensagens_de_log(saida_str: str) -> list[str]:
    """
    Filtra a saída do processo de compilação, preservando blocos de erros ou avisos
    e descartando linhas informativas de sucesso normal.
    """
    mensagens = []
    linhas = saida_str.splitlines()

    em_bloco = False
    for linha in linhas:
        is_keyword = eh_linha_de_aviso_ou_erro(linha)

        if is_keyword:
            em_bloco = True
            mensagens.append(linha.rstrip())
        elif em_bloco and (linha.startswith(" ") or linha.startswith("\t")):
            mensagens.append(linha.rstrip())
        elif em_bloco and not linha.strip():
            em_bloco = False
            mensagens.append("")
        else:
            em_bloco = False

    while mensagens and not mensagens[-1].strip():
        mensagens.pop()

    return mensagens
