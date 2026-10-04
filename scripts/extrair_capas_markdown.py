# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Script e biblioteca utilitária para extração de fotos de capa em arquivos Markdown
de setores e grupos.

Promove a primeira imagem encontrada no corpo Markdown para a propriedade
'caminho_imagem_capa' no Frontmatter YAML, remove a tag original do corpo
para evitar duplicação visual e otimiza a imagem em disco se exceder 1 Megapixel.
"""

from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import re
import sys
from PIL import Image

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from editor.core.processamento_imagem_campo import (
    AREA_MAXIMA_ESCALADA,
    QUALIDADE_WEBP_ESCALADA,
    comprimir_imagem_para_bytes_webp,
)
from scripts.preparar_submissao_lib import (
    parse_md_com_frontmatter,
    salvar_md_com_frontmatter,
)

PADRAO_IMAGEM_MARKDOWN = re.compile(r"!\[(.*?)\]\((.*?)\)")


def extrair_primeira_imagem_markdown(corpo: str) -> Optional[Tuple[str, str, int, int]]:
    """
    Encontra a primeira ocorrência de uma tag de imagem Markdown no corpo do texto.
    Retorna uma tupla (alt_text, caminho_imagem, start_pos, end_pos) ou None.
    """
    match = PADRAO_IMAGEM_MARKDOWN.search(corpo)
    if not match:
        return None
    alt = match.group(1).strip()
    caminho = match.group(2).strip()
    start, end = match.span()
    return alt, caminho, start, end


def remover_tag_imagem_do_corpo(corpo: str, start: int, end: int) -> str:
    """
    Remove o trecho correspondente à tag da imagem do corpo Markdown
    e normaliza quebras de linha excessivas.
    """
    novo_corpo = corpo[:start] + corpo[end:]
    novo_corpo = re.sub(r"\n{3,}", "\n\n", novo_corpo)
    return novo_corpo.strip()


def encontrar_diretorio_pico(caminho_arquivo: Path) -> Path:
    """
    Navega para cima na hierarquia de diretórios até encontrar o arquivo 'croqui.yaml',
    identificando a raiz do pico. Caso não encontre, retorna o diretório pai do arquivo.
    """
    atual = caminho_arquivo.parent.resolve()
    while atual != atual.parent:
        if (atual / "croqui.yaml").exists():
            return atual
        atual = atual.parent
    return caminho_arquivo.parent.resolve()


def otimizar_imagem_se_necessario(
    caminho_imagem: Path,
    max_area: int = AREA_MAXIMA_ESCALADA,
    qualidade: int = QUALIDADE_WEBP_ESCALADA,
) -> bool:
    """
    Verifica se a imagem em disco excede a área máxima permitida (padrão 1 MP).
    Se exceder, redimensiona preservando o aspecto e re-comprime para WebP Q85.
    Retorna True se o arquivo foi modificado/otimizado, False caso contrário.
    """
    if not caminho_imagem.exists() or not caminho_imagem.is_file():
        return False

    try:
        with Image.open(caminho_imagem) as img:
            w, h = img.size
            area = w * h

        if area > max_area:
            bytes_webp, _, _ = comprimir_imagem_para_bytes_webp(
                caminho_imagem,
                quality=qualidade,
                max_area=max_area,
            )
            caminho_imagem.write_bytes(bytes_webp)
            return True
    except Exception as e:
        print(f"    Aviso: Falha ao processar imagem {caminho_imagem}: {e}")

    return False


def promover_capa_arquivo_md(
    caminho_md: Path,
    max_area: int = AREA_MAXIMA_ESCALADA,
) -> bool:
    """
    Processa um arquivo Markdown de Setor ou Grupo:
    - Lê o frontmatter e o corpo
    - Se já tiver caminho_imagem_capa, ignora (idempotência)
    - Extrai a primeira imagem do corpo
    - Remove a tag da imagem do corpo
    - Insere caminho_imagem_capa no topo do frontmatter
    - Salva o arquivo atualizado
    - Otimiza a imagem em disco caso exceda o limite de área
    Retorna True se o arquivo foi promovido, False caso contrário.
    """
    try:
        frontmatter, corpo = parse_md_com_frontmatter(caminho_md)
    except Exception as e:
        print(f"    Aviso: Erro ao ler frontmatter de {caminho_md}: {e}")
        return False

    if frontmatter is None:
        return False

    if frontmatter.get("caminho_imagem_capa"):
        return False

    imagem_info = extrair_primeira_imagem_markdown(corpo)
    if not imagem_info:
        return False

    _, caminho_imagem, start, end = imagem_info
    novo_corpo = remover_tag_imagem_do_corpo(corpo, start, end)

    novo_frontmatter = {"caminho_imagem_capa": caminho_imagem}
    for k, v in frontmatter.items():
        if k != "caminho_imagem_capa":
            novo_frontmatter[k] = v

    salvar_md_com_frontmatter(caminho_md, novo_frontmatter, novo_corpo)

    # Inspeciona e otimiza a imagem em disco caso exista
    pico_dir = encontrar_diretorio_pico(caminho_md)
    caminho_imagem_disco = pico_dir / caminho_imagem
    otimizar_imagem_se_necessario(caminho_imagem_disco, max_area=max_area)

    return True


def processar_diretorio(
    diretorio: Path,
    max_area: int = AREA_MAXIMA_ESCALADA,
) -> Dict[str, Any]:
    """
    Percorre o diretório informado procurando arquivos 'setor_*.md' e 'grupo_*.md'
    e promove as capas identificadas.
    """
    arquivos = []
    for caminho in diretorio.rglob("*.md"):
        nome = caminho.name
        if nome.startswith("setor_") or nome.startswith("grupo_"):
            arquivos.append(caminho)

    arquivos.sort()
    total = len(arquivos)
    promovidos = 0
    ignorados = 0

    for arq in arquivos:
        if promover_capa_arquivo_md(arq, max_area=max_area):
            promovidos += 1
        else:
            ignorados += 1

    return {
        "total_verificados": total,
        "promovidos": promovidos,
        "ignorados": ignorados,
    }


def main() -> None:
    """Execução via linha de comando."""
    raiz = Path(__file__).resolve().parent.parent
    alvo = raiz / "database"

    if len(sys.argv) > 1:
        alvo = Path(sys.argv[1]).resolve()

    print(f"Iniciando extração de capas em: {alvo}")
    if alvo.is_file():
        modificado = promover_capa_arquivo_md(alvo)
        print(f"Arquivo processado. Promovido: {modificado}")
    else:
        stats = processar_diretorio(alvo)
        print("Concluído!")
        print(f"  Total verificados: {stats['total_verificados']}")
        print(f"  Promovidos: {stats['promovidos']}")
        print(f"  Ignorados: {stats['ignorados']}")


if __name__ == "__main__":  # pragma: no cover
    main()
