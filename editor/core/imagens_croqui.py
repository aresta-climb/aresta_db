# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from collections import Counter
from typing import Any, Dict, List, Optional


def extrair_caminhos_imagens(msg: Any) -> List[str]:
    """
    Extrai recursivamente todos os caminhos relativos de imagens presentes
    em uma mensagem Protobuf ou ReadOnlyProxy (como mapas e thumbnails).
    Retorna uma lista com os caminhos padronizados com barras normais '/'.
    """
    caminhos: List[str] = []
    if msg is None:
        return caminhos

    # Desembrulha caso seja ReadOnlyProxy
    msg_real = getattr(msg, "_obj", msg)

    # Campos de imagem conhecidos no schema do Croqui
    if hasattr(msg_real, "caminho_imagem_mapa") and msg_real.caminho_imagem_mapa:
        caminho_norm = str(msg_real.caminho_imagem_mapa).replace("\\", "/")
        caminhos.append(caminho_norm)

    if hasattr(msg_real, "caminho_thumbnail") and msg_real.caminho_thumbnail:
        caminho_norm = str(msg_real.caminho_thumbnail).replace("\\", "/")
        caminhos.append(caminho_norm)

    # Percorre recursivamente campos compostos e listas repeated
    if hasattr(msg_real, "ListFields"):
        for descriptor, valor in msg_real.ListFields():
            if descriptor.type == descriptor.TYPE_MESSAGE:
                if isinstance(valor, (list, tuple)) or hasattr(valor, "extend"):
                    for item in valor:
                        caminhos.extend(extrair_caminhos_imagens(item))
                else:
                    caminhos.extend(extrair_caminhos_imagens(valor))

    return caminhos


def obter_imagens_orfas_ao_remover(
    croqui_raiz: Any,
    item_removido: Any,
    imagens_em_ram: Dict[str, bytes],
) -> Dict[str, bytes]:
    """
    Calcula quais imagens armazenadas na memória RAM se tornarão órfãs caso
    o `item_removido` seja excluído de `croqui_raiz`.
    Retorna um dicionário {caminho_imagem: bytes} apenas das imagens cuja remoção
    deixará o croqui sem nenhuma outra referência ativa a elas.
    """
    if croqui_raiz is None or item_removido is None or not imagens_em_ram:
        return {}

    caminhos_removidos = extrair_caminhos_imagens(item_removido)
    if not caminhos_removidos:
        return {}

    # Filtra apenas caminhos que de fato existem no buffer em memória RAM
    caminhos_em_ram = [c for c in caminhos_removidos if c in imagens_em_ram]
    if not caminhos_em_ram:
        return {}

    # Contagem global de referências no croqui
    todos_caminhos_croqui = extrair_caminhos_imagens(croqui_raiz)
    contagem_croqui = Counter(todos_caminhos_croqui)
    contagem_removidos = Counter(caminhos_removidos)

    imagens_orfas: Dict[str, bytes] = {}
    for caminho in caminhos_em_ram:
        # Se todas as ocorrências do caminho pertencem ao item sendo removido
        if contagem_croqui[caminho] <= contagem_removidos[caminho]:
            imagens_orfas[caminho] = imagens_em_ram[caminho]

    return imagens_orfas
