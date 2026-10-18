# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Script de deploy dos croquis compilados.

Estrutura gerada:
  <output_dir>/
    <id>/
      compilado.yaml
      compilado.binarypb   <- inclui arquivos_externos com checksums das imagens
      imagens/             <- symlink para ../../database/<id>/imagens (ou cópia)
    indice.binarypb
    indice.yaml            <- para debug

Pipeline:
  A) Para cada croqui em database/:
     1. Cria <output_dir>/<id>/
     2. Tenta criar symlink <output_dir>/<id>/imagens -> ../../database/<id>/imagens
        (fallback: copia a pasta)
     3. Calcula SHA-256 de cada imagem (.webp na raiz de imagens/)
     4. Compila croqui com arquivos_externos em <output_dir>/<id>/compilado.binarypb
  B) Calcula SHA-256 dos compilado.binarypb gerados
  C) Gera <output_dir>/indice.binarypb e <output_dir>/indice.yaml

Uso:
  python scripts/deploy_generated.py [--output-dir <DIR>]
"""

import io
import sys

# Força o uso de UTF-8 para stdout e stderr, especialmente importante no Windows
# Em executáveis --windowed do PyInstaller, sys.stdout e sys.stderr podem ser None.
if sys.stdout is not None and getattr(sys.stdout, "encoding", None) != "utf-8":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

if sys.stderr is not None and getattr(sys.stderr, "encoding", None) != "utf-8":
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import argparse
import contextlib
import copy
import datetime
import hashlib
import re
import shutil
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.append(str(Path(__file__).resolve().parent.parent))
from aresta_api.proto.generated import croqui_pb2, indice_pb2, serving_pb2
from editor.core.serializacao_util import (
    carregar_yaml,
    escrever_texto_se_modificado,
    serializar_yaml,
)
from editor.plataforma import normalizar_caminho_estendido
from scripts.calcular_tamanho_croqui_lib import calcular_tamanho_croqui_bytes
from scripts.preparar_submissao_lib import (
    CacheMd,
    compilar_croqui,
    corrigir_database,
    sincronizar_dimensoes_mapas_database,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT_DIR / "database"

# Pode ser substituído via --output-dir na linha de comando
GENERATED_DIR: Path  # definido em deploy()
_ULTIMOS_DADOS_MEMORIA_SAUDE: dict[str, tuple[dict[str, Any], CacheMd]] = {}
_CACHE_SNAPSHOT_DISCO: dict[Path, tuple[int, int, Any, str | None]] = {}


def _estruturas_identicas_com_ordem(a: Any, b: Any) -> bool:
    """Compara dois objetos recursivamente exigindo a mesma ordem de chaves em dicionários."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return len(a) == len(b) and all(
            k1 == k2 and _estruturas_identicas_com_ordem(v1, v2)
            for (k1, v1), (k2, v2) in zip(a.items(), b.items())
        )
    if isinstance(a, list):
        return len(a) == len(b) and all(
            _estruturas_identicas_com_ordem(x, y) for x, y in zip(a, b)
        )
    return bool(a == b)


def registrar_snapshot_disco_arquivo(
    caminho: Path,
    dados: Any,
    corpo_bruto: str | None = None,
) -> None:
    """Registra no cache em memória o snapshot estrutural associado ao stat() atual do arquivo."""
    caminho_res = Path(caminho).resolve()
    if caminho_res.is_file():
        st = caminho_res.stat()
        _CACHE_SNAPSHOT_DISCO[caminho_res] = (
            st.st_mtime_ns,
            st.st_size,
            copy.deepcopy(dados),
            corpo_bruto,
        )


def _arquivo_inalterado_no_snapshot(
    caminho: Path,
    dados: Any,
    corpo_bruto: str | None = None,
) -> bool:
    """Verifica se o arquivo no disco e os dados em memória permanecem idênticos ao último snapshot."""
    caminho_res = Path(caminho).resolve()
    entrada = _CACHE_SNAPSHOT_DISCO.get(caminho_res)
    if entrada is None or not caminho_res.is_file():
        return False
    mtime_ns, tamanho, dados_cache, corpo_cache = entrada
    st = caminho_res.stat()
    return (
        st.st_mtime_ns == mtime_ns
        and st.st_size == tamanho
        and corpo_bruto == corpo_cache
        and _estruturas_identicas_com_ordem(dados, dados_cache)
    )


@dataclass
class ContextoMemoriaDeploy:
    """Mantém os dados do croqui e seus arquivos Markdown em RAM para evitar releituras e escritas intermediárias."""

    croqui_data: dict[str, Any]
    cache_md: CacheMd = field(default_factory=dict)
    corpos_brutos_md: dict[str, str] = field(default_factory=dict)
    persistido_no_disco: bool = False


_CONTEXTOS_MEMORIA_DEPLOY: dict[Path, ContextoMemoriaDeploy] = {}


def obter_contexto_memoria_deploy(caminho: Path) -> ContextoMemoriaDeploy | None:
    """Retorna o contexto em memória registrado para `caminho` (resolvido), ou None."""
    return _CONTEXTOS_MEMORIA_DEPLOY.get(Path(caminho).resolve())


def persistir_contexto_memoria_no_disco(
    croqui_dir: Path,
    contexto: ContextoMemoriaDeploy,
) -> None:
    """
    Grava `croqui.yaml` e todos os `.md` do `contexto` em `croqui_dir` uma única vez,
    preservando as quebras de linha exatas do corpo quando não houve mutação e pulando
    a serialização YAML de arquivos cujo snapshot estrutural permanece inalterado.
    """
    from scripts.markdown_frontmatter_lib import parse_texto_md_com_frontmatter

    croqui_dir_path = Path(croqui_dir)
    caminho_yaml = croqui_dir_path / "croqui.yaml"
    if not _arquivo_inalterado_no_snapshot(caminho_yaml, contexto.croqui_data, None):
        escrever_texto_se_modificado(
            caminho_yaml,
            serializar_yaml(contexto.croqui_data, incluir_cabecalho_spdx=True),
        )
        registrar_snapshot_disco_arquivo(caminho_yaml, contexto.croqui_data, None)

    for chave_rel, (fm, corpo) in contexto.cache_md.items():
        caminho_md = croqui_dir_path / chave_rel
        bruto = contexto.corpos_brutos_md.get(chave_rel)
        if fm is not None:
            eh_bruto_preservado = bruto is not None and bruto.strip() == corpo.strip()
            corpo_snapshot = bruto if eh_bruto_preservado else corpo
            if not _arquivo_inalterado_no_snapshot(caminho_md, fm, corpo_snapshot):
                bloco_yaml = serializar_yaml(fm, incluir_cabecalho_spdx=True).replace("\r\n", "\n")
                if eh_bruto_preservado:
                    texto_md = f"---\n{bloco_yaml}---\n{bruto}"
                else:
                    texto_md = f"---\n{bloco_yaml}---\n\n{corpo}" if fm else corpo
                escrever_texto_se_modificado(caminho_md, texto_md)
                registrar_snapshot_disco_arquivo(caminho_md, fm, corpo_snapshot)
        else:
            if (
                bruto is not None
                and parse_texto_md_com_frontmatter(
                    bruto, caminho_origem=caminho_md, lancar_erro_yaml=False
                )[1]
                == corpo.strip()
            ):
                texto_md = bruto
            else:
                texto_md = corpo
            escrever_texto_se_modificado(caminho_md, texto_md)

    contexto.persistido_no_disco = True


@contextlib.contextmanager
def usar_contexto_memoria_deploy(
    caminhos: Sequence[Path],
    croqui_data: dict[str, Any],
    cache_md: CacheMd | None = None,
    corpos_brutos_md: dict[str, str] | None = None,
) -> Iterator[ContextoMemoriaDeploy]:
    """
    Registra temporariamente o estado em memória de um croqui para que `deploy()`
    processe correções, sincronização e compilação diretamente da RAM sem reler do disco.
    """
    ctx = ContextoMemoriaDeploy(
        croqui_data=croqui_data,
        cache_md=cache_md if cache_md is not None else {},
        corpos_brutos_md=corpos_brutos_md if corpos_brutos_md is not None else {},
    )
    chaves = [Path(c).resolve() for c in caminhos]
    for ch in chaves:
        _CONTEXTOS_MEMORIA_DEPLOY[ch] = ctx
    try:
        yield ctx
    finally:
        for ch in chaves:
            _CONTEXTOS_MEMORIA_DEPLOY.pop(ch, None)


# Subdiretórios dentro de imagens/ que são artefatos de processamento e
# NÃO devem ser exportados para o frontend.
IMAGENS_SUBDIRS_EXCLUIDOS = {"raw_mapas"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def force_rmtree(path: Path) -> None:
    """Versão robusta do shutil.rmtree para Windows, com retry e tratamento de read-only."""
    import os
    import time

    def remover_somente_leitura(func: Any, p: str, _: Any) -> None:
        os.chmod(p, 0o777)
        func(p)

    caminho_estendido = normalizar_caminho_estendido(path)
    for i in range(5):
        try:
            if Path(caminho_estendido).exists():
                shutil.rmtree(caminho_estendido, onerror=remover_somente_leitura)
            return
        except PermissionError:
            if i == 4:
                raise
            time.sleep(0.2)


def calcular_sha256(caminho: Path) -> str:
    """SHA-256 de um arquivo utilizando hashlib.file_digest."""
    with open(caminho, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def processar_thumbnail(
    croqui_dir: Path,
    generated_dir: Path,
    croqui_data: dict[str, Any],
    force_thumbnails: bool = False,
) -> bool:
    """
    Converte a imagem apontada em caminho_thumbnail para generated/thumbnails/<id>.webp
    sincronizando o timestamp de modificação (st_mtime_ns) com a imagem de origem.
    """
    caminho_thumb_original = croqui_data.get("caminho_thumbnail")
    if not caminho_thumb_original:
        return False

    croqui_id = croqui_data.get("id")
    if not croqui_id:
        return False

    DEST_REL = f"thumbnails/{croqui_id}.webp"
    dest_path = generated_dir / DEST_REL
    src_path = croqui_dir / caminho_thumb_original

    if not src_path.exists():
        raise FileNotFoundError(
            f"Thumbnail original não encontrada em {src_path}. Verifique o campo 'caminho_thumbnail' no croqui.yaml."
        )

    if not force_thumbnails and dest_path.exists():
        if dest_path.stat().st_mtime_ns == src_path.stat().st_mtime_ns:
            return False

    print(
        f"  Gerando thumbnail: {caminho_thumb_original} -> {dest_path.relative_to(GENERATED_DIR)} (600x600, WebP)"
    )

    try:
        with Image.open(src_path) as raw_img:
            img: Image.Image = raw_img
            # Converter para RGB se necessário (ex: de PNG com alpha)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Dimensões alvo
            TARGET_SIZE = 600
            # A imagem principal ocupará ~90% do espaço para deixar uma borda borrada visível em todos os lados
            FOREGROUND_SIZE = int(TARGET_SIZE * 0.9)
            # Raio dos cantos arredondados (estilo ícone de app)
            CORNER_RADIUS = int(FOREGROUND_SIZE * 0.08)

            width, height = img.size

            # 1. Criar o fundo (Blurred Background)
            # Sempre usamos um crop centralizado para preencher o fundo de forma harmoniosa
            crop_size = min(width, height)
            left = (width - crop_size) // 2
            top = (height - crop_size) // 2
            right = (width + crop_size) // 2
            bottom = (height + crop_size) // 2

            background = img.crop((left, top, right, bottom))
            background = background.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(radius=20))
            # Escurecemos um pouco mais o fundo para dar mais profundidade e destaque ao centro
            enhancer = ImageEnhance.Brightness(background)
            background = enhancer.enhance(0.7)

            # 2. Preparar a imagem principal (Foreground)
            foreground = img.copy()
            foreground.thumbnail((FOREGROUND_SIZE, FOREGROUND_SIZE), Image.Resampling.LANCZOS)

            # 3. Criar máscara para cantos arredondados
            mask = Image.new("L", foreground.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle(
                (0, 0, foreground.width, foreground.height), radius=CORNER_RADIUS, fill=255
            )

            # 4. Montar a imagem final
            final_img = Image.new("RGB", (TARGET_SIZE, TARGET_SIZE))
            final_img.paste(background, (0, 0))

            # Centralizar o foreground sobre o fundo borrado usando a máscara de arredondamento
            offset = ((TARGET_SIZE - foreground.width) // 2, (TARGET_SIZE - foreground.height) // 2)
            final_img.paste(foreground, offset, mask=mask)
            img = final_img

            # Garantir pasta imagens/
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Salvar
            img.save(dest_path, "WEBP", quality=80)

        shutil.copystat(src_path, dest_path)
        return True
    except Exception as e:
        print(f"  Erro ao processar thumbnail {src_path}: {e}")
        return False


def carregar_dados_anteriores(caminho_pb: Path) -> dict[str, indice_pb2.ResumoCroqui]:
    """
    Lê o indice.binarypb anterior e retorna {id: ResumoCroqui}.
    Retorna dicionário vazio se o arquivo não existir ou se houver erro na leitura.
    """
    if not caminho_pb.exists():
        return {}

    try:
        indice = indice_pb2.Indice()
        with open(caminho_pb, "rb") as f:
            indice.ParseFromString(f.read())

        return {resumo.id: resumo for resumo in indice.croquis}
    except Exception as e:
        print(f"Aviso: não foi possível ler o índice anterior em {caminho_pb}: {e}")
        return {}


def encontrar_croquis(
    database_dir: Path | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    """Retorna [(croqui_dir, croqui_data)] para todos os croquis válidos em database/."""
    db_dir = database_dir or DATABASE_DIR
    if not db_dir.exists():
        return []

    resultado: list[tuple[Path, dict[str, Any]]] = []
    for d in sorted(db_dir.iterdir()):
        yaml_path = d / "croqui.yaml"
        if not d.is_dir() or not yaml_path.exists():
            continue
        croqui_data = carregar_yaml(yaml_path.read_text(encoding="utf-8"))
        if not isinstance(croqui_data, dict):
            continue
        croqui_id = croqui_data.get("id")
        if not croqui_id:
            print(f"Aviso: {d.name}/croqui.yaml sem campo 'id', ignorando.")
            continue
        resultado.append((d, croqui_data))

    return resultado


def carregar_um_croqui(caminho: Path) -> dict[str, Any] | None:
    """Carrega dados de um croqui a partir de um diretório qualquer."""
    yaml_path = caminho / "croqui.yaml"
    if not caminho.is_dir() or not yaml_path.exists():
        return None
    try:
        croqui_data = carregar_yaml(yaml_path.read_text(encoding="utf-8"))
        if not isinstance(croqui_data, dict) or not croqui_data.get("id"):
            return None
        return croqui_data
    except Exception:
        return None


def _contem_chave_recursivo(obj: Any, chave_proibida: str) -> bool:
    if isinstance(obj, dict):
        if chave_proibida in obj:
            return True
        return any(_contem_chave_recursivo(v, chave_proibida) for v in obj.values())
    if isinstance(obj, list):
        return any(_contem_chave_recursivo(item, chave_proibida) for item in obj)
    return False


def validar_sem_extensoes_vazadas(
    pico_dir: Path,
    *,
    dados_croqui_memoria: dict[str, Any] | None = None,
    cache_md_memoria: CacheMd | None = None,
) -> None:
    """
    Verifica se o YAML ou qualquer Markdown referenciado contém vestígios do
    Shadow State (extensões de caminho original/novo) que deveriam existir
    apenas em memória durante a edição na UI.
    """
    extensoes_vazadas = ["ext_metadados"]
    if dados_croqui_memoria is not None and cache_md_memoria is not None:
        for ext in extensoes_vazadas:
            if _contem_chave_recursivo(dados_croqui_memoria, ext):
                raise ValueError(
                    f"Extensão de Shadow State '{ext}' vazada detectada no arquivo {pico_dir / 'croqui.yaml'}"
                )
            for rel_path, (fm, corpo) in cache_md_memoria.items():
                if _contem_chave_recursivo(fm, ext) or ext in corpo:
                    raise ValueError(
                        f"Extensão de Shadow State '{ext}' vazada detectada no arquivo {pico_dir / rel_path}"
                    )
        return

    for f in pico_dir.rglob("*"):
        if f.is_file() and f.suffix in [".yaml", ".md"]:
            try:
                content = f.read_text(encoding="utf-8")
                for ext in extensoes_vazadas:
                    if ext in content:
                        raise ValueError(
                            f"Extensão de Shadow State '{ext}' vazada detectada no arquivo {f}"
                        )
            except UnicodeDecodeError:
                pass


def extrair_descricao(croqui_data: dict[str, Any]) -> str:
    """Descrição de alto nível do croqui; fallback em picos[0].descricao."""
    if croqui_data.get("descricao"):
        return str(croqui_data["descricao"])
    picos = croqui_data.get("picos", [])
    if picos and isinstance(picos, list) and picos[0].get("descricao"):
        return str(picos[0]["descricao"]).strip()
    return ""


def verificar_nomes_duplicados_de_escalada(croqui_id: str, compiled_data: dict[str, Any]) -> None:
    """Procura escaladas com o mesmo nome no mesmo croqui e emite um aviso."""
    nomes_vistos: set[str] = set()
    duplicados: set[str] = set()

    def _buscar_escaladas(obj: Any) -> None:
        if isinstance(obj, dict):
            if "escaladas" in obj and isinstance(obj["escaladas"], list):
                for escalada in obj["escaladas"]:
                    if isinstance(escalada, dict):
                        for dados_via in escalada.values():
                            if isinstance(dados_via, dict) and "nome" in dados_via:
                                nome = dados_via["nome"]
                                if nome in nomes_vistos:
                                    duplicados.add(nome)
                                else:
                                    nomes_vistos.add(nome)
            for v in obj.values():
                _buscar_escaladas(v)
        elif isinstance(obj, list):
            for item in obj:
                _buscar_escaladas(item)

    _buscar_escaladas(compiled_data)

    for nome in sorted(duplicados):
        print(
            f"\nAviso: A escalada '{nome}' aparece mais de uma vez no croqui '{croqui_id}'. Nomes duplicados podem causar confusão."
        )


def verificar_escaladas_sem_mapa(croqui_id: str, compiled_data: dict[str, Any]) -> None:
    """Avisa se há escaladas que não estão mapeadas, caso o croqui já possua mapas desenhados."""
    todas_escaladas: set[str] = set()
    escaladas_referenciadas: set[str] = set()
    tem_mapas_com_pontos = False

    def _buscar(obj: Any) -> None:
        nonlocal tem_mapas_com_pontos
        if isinstance(obj, dict):
            if "escaladas" in obj and isinstance(obj["escaladas"], list):
                for esc in obj["escaladas"]:
                    if isinstance(esc, dict):
                        for dados_via in esc.values():
                            if isinstance(dados_via, dict) and "nome" in dados_via:
                                todas_escaladas.add(dados_via["nome"])

            if (
                "pontos_de_interesse" in obj
                and isinstance(obj["pontos_de_interesse"], list)
                and len(obj["pontos_de_interesse"]) > 0
            ):
                tem_mapas_com_pontos = True

            if "referencias" in obj and isinstance(obj["referencias"], list):
                for ref in obj["referencias"]:
                    if isinstance(ref, dict) and "escalada" in ref:
                        escaladas_referenciadas.add(ref["escalada"])

            for v in obj.values():
                _buscar(v)
        elif isinstance(obj, list):
            for item in obj:
                _buscar(item)

    _buscar(compiled_data)

    if not tem_mapas_com_pontos:
        return

    escaladas_sem_mapa = todas_escaladas - escaladas_referenciadas
    for nome in sorted(escaladas_sem_mapa):
        print(
            f"\nAviso: A escalada '{nome}' não está referenciada em nenhum mapa no croqui '{croqui_id}'."
        )


def verificar_imagens_inexistentes(
    croqui_dir: Path, croqui_id: str, compiled_data: dict[str, Any]
) -> None:
    """Verifica se imagens referenciadas em mapas, miniaturas e Markdown existem no disco."""
    imagens_para_checar: set[str] = set()
    regex_md_img = re.compile(r"!\[.*?\]\((.*?)\)")

    def _coletar_imagens(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in (
                    "caminho_imagem_mapa",
                    "caminho_thumbnail",
                    "caminho_imagem_capa",
                ) and isinstance(v, str):
                    caminho = v.strip()
                    if caminho and not (
                        caminho.startswith("http://") or caminho.startswith("https://")
                    ):
                        imagens_para_checar.add(caminho)
                elif isinstance(v, str):
                    for match in regex_md_img.findall(v):
                        caminho_md = match.strip()
                        if caminho_md and not (
                            caminho_md.startswith("http://") or caminho_md.startswith("https://")
                        ):
                            imagens_para_checar.add(caminho_md)
                _coletar_imagens(v)
        elif isinstance(obj, list):
            for item in obj:
                _coletar_imagens(item)

    _coletar_imagens(compiled_data)

    for caminho_rel in sorted(imagens_para_checar):
        caminho_completo = croqui_dir / caminho_rel
        if not caminho_completo.exists():
            print(
                f"\nAviso: A imagem '{caminho_rel}' referenciada no croqui '{croqui_id}' não foi encontrada no disco ({caminho_completo})."
            )


def verificar_mapas_duplicados(croqui_id: str, compiled_data: dict[str, Any]) -> None:
    """Procura imagens de mapa que estão sendo exibidas em mais de um local e emite um aviso."""
    locais_por_imagem: dict[str, list[str]] = defaultdict(list)

    def registrar_mapas(mapas: list[Any], contexto: str) -> None:
        if not isinstance(mapas, list):
            return
        for idx, mapa in enumerate(mapas):
            if isinstance(mapa, dict):
                caminho = mapa.get("caminho_imagem_mapa")
                if caminho and isinstance(caminho, str):
                    locais_por_imagem[caminho].append(f"{contexto} (Mapa {idx + 1})")

    for pico in compiled_data.get("picos", []):
        pico_nome = pico.get("nome", "Pico Sem Nome")
        registrar_mapas(pico.get("mapas", []), f"Pico '{pico_nome}'")

        if "mapas_gerais" in pico and isinstance(pico["mapas_gerais"], dict):
            conteudo_mg = pico["mapas_gerais"].get("conteudo", pico["mapas_gerais"])
            if isinstance(conteudo_mg, dict):
                registrar_mapas(conteudo_mg.get("mapas", []), f"Pico '{pico_nome}' (Mapas Gerais)")

        for obj_sg in pico.get("setores_ou_grupos", []):
            if "grupo" in obj_sg:
                grupo = obj_sg["grupo"].get("conteudo", obj_sg["grupo"])
                grupo_nome = grupo.get("nome", "Grupo Sem Nome")
                registrar_mapas(grupo.get("mapas", []), f"Grupo '{grupo_nome}'")
                for obj_s in grupo.get("setores", []):
                    setor = obj_s.get("conteudo", obj_s)
                    setor_nome = setor.get("nome", "Setor Sem Nome")
                    registrar_mapas(
                        setor.get("mapas", []), f"Setor '{setor_nome}' (no Grupo '{grupo_nome}')"
                    )
                    for esc in setor.get("escaladas", []):
                        if isinstance(esc, dict):
                            nome_esc = "Sem Nome"
                            for v in esc.values():
                                if isinstance(v, dict) and "nome" in v:
                                    nome_esc = v["nome"]
                                    break
                            registrar_mapas(
                                esc.get("mapas", []),
                                f"Escalada '{nome_esc}' (no Setor '{setor_nome}')",
                            )
            elif "setor" in obj_sg:
                setor = obj_sg["setor"].get("conteudo", obj_sg["setor"])
                setor_nome = setor.get("nome", "Setor Sem Nome")
                registrar_mapas(setor.get("mapas", []), f"Setor '{setor_nome}'")
                for esc in setor.get("escaladas", []):
                    if isinstance(esc, dict):
                        nome_esc = "Sem Nome"
                        for v in esc.values():
                            if isinstance(v, dict) and "nome" in v:
                                nome_esc = v["nome"]
                                break
                        registrar_mapas(
                            esc.get("mapas", []), f"Escalada '{nome_esc}' (no Setor '{setor_nome}')"
                        )

    for caminho, locais in sorted(locais_por_imagem.items()):
        if len(locais) > 1:
            locais_str = ", ".join(locais)
            print(
                f"\nAviso: O mapa '{caminho}' no croqui '{croqui_id}' está sendo exibido em mais de um local: {locais_str}. "
                f"No geral, se estiver em mais de um lugar indica duplicação indevida de informação."
            )


def verificar_titulos_em_descricao_setor_grupo(
    croqui_id: str, compiled_data: dict[str, Any]
) -> None:
    """Verifica se a descrição de algum setor ou grupo contém cabeçalhos H1 e emite aviso."""

    def _verificar_entidade(tipo: str, entidade: dict[str, Any]) -> None:
        nome = entidade.get("nome", "Sem Nome")
        descricao = entidade.get("descricao")
        if isinstance(descricao, str):
            for linha in descricao.splitlines():
                linha_limpa = linha.strip()
                if linha_limpa.startswith("# ") or linha_limpa == "#":
                    print(
                        f"\nAviso: A descrição do {tipo} '{nome}' no croqui '{croqui_id}' "
                        f"contém título Markdown H1 ('{linha_limpa}'). "
                        f"Como o aplicativo já exibe o nome do {tipo} no topo da tela, "
                        f"recomenda-se remover o título da descrição para evitar duplicação visual."
                    )
                    break

    def _percorrer_setores(setores: list[Any]) -> None:
        if not isinstance(setores, list):
            return
        for item in setores:
            if isinstance(item, dict):
                setor = item.get("conteudo", item)
                if isinstance(setor, dict):
                    _verificar_entidade("setor", setor)

    for pico in compiled_data.get("picos", []):
        if not isinstance(pico, dict):
            continue
        for obj_sg in pico.get("setores_ou_grupos", []):
            if not isinstance(obj_sg, dict):
                continue
            if "grupo" in obj_sg:
                grupo = obj_sg["grupo"].get("conteudo", obj_sg["grupo"])
                if isinstance(grupo, dict):
                    _verificar_entidade("grupo", grupo)
                    _percorrer_setores(grupo.get("setores", []))
            elif "setor" in obj_sg:
                setor = obj_sg["setor"].get("conteudo", obj_sg["setor"])
                if isinstance(setor, dict):
                    _verificar_entidade("setor", setor)


# ---------------------------------------------------------------------------
# Imagens e Anexos: cópia e sincronização incremental
# ---------------------------------------------------------------------------


def copiar_imagens(src_imagens: Path, dest_imagens: Path) -> None:
    """Copia a pasta de imagens para o destino, excluindo subdiretórios de processamento."""

    def ignorar(dir_: str, nomes: list[str]) -> list[str]:
        return [n for n in nomes if (Path(dir_) / n).is_dir() and n in IMAGENS_SUBDIRS_EXCLUIDOS]

    src_estendido = normalizar_caminho_estendido(src_imagens)
    dest_estendido = normalizar_caminho_estendido(dest_imagens)
    shutil.copytree(src_estendido, dest_estendido, ignore=ignorar, dirs_exist_ok=True)
    print(f"  Imagens copiadas: {dest_imagens}")


def listar_imagens_exportaveis(imagens_path: Path) -> list[Path]:
    """
    Lista todos os arquivos .webp na raiz de imagens/ (sem descer em raw_mapas/).
    Retorna lista de Path absolutos.
    """
    if not imagens_path.exists():
        return []
    return sorted(
        [f for f in imagens_path.iterdir() if f.is_file() and f.suffix.lower() == ".webp"]
    )


def calcular_arquivos_externos(imagens_src: Path) -> list[dict[str, str]]:
    """
    Retorna lista de dicts {caminho, checksum_sha256} para cada imagem exportável,
    com caminho relativo à raiz do croqui (ex: imagens/pagina_7_imagem_0.webp).
    """
    arquivos: list[dict[str, str]] = []
    for img in listar_imagens_exportaveis(imagens_src):
        arquivos.append(
            {
                "caminho": f"imagens/{img.name}",
                "checksum_sha256": calcular_sha256(img),
            }
        )
    return arquivos


def copiar_anexos(src_anexos: Path, dest_anexos: Path) -> None:
    """Copia a pasta de anexos para o destino."""
    src_estendido = normalizar_caminho_estendido(src_anexos)
    dest_estendido = normalizar_caminho_estendido(dest_anexos)
    shutil.copytree(src_estendido, dest_estendido, dirs_exist_ok=True)
    print(f"  Anexos copiados: {dest_anexos}")


def listar_anexos_exportaveis(anexos_path: Path) -> list[Path]:
    """
    Lista todos os arquivos dentro de anexos/ recursivamente.
    Retorna lista de Path absolutos.
    """
    if not anexos_path.exists():
        return []
    return sorted([f for f in anexos_path.rglob("*") if f.is_file()])


def calcular_anexos_externos(anexos_src: Path) -> list[dict[str, str]]:
    """
    Retorna lista de dicts {caminho, checksum_sha256} para cada anexo exportável,
    com caminho relativo à raiz do croqui (ex: anexos/ficha_autorizacao.pdf).
    """
    arquivos: list[dict[str, str]] = []
    for arq in listar_anexos_exportaveis(anexos_src):
        rel = arq.relative_to(anexos_src).as_posix()
        arquivos.append(
            {
                "caminho": f"anexos/{rel}",
                "checksum_sha256": calcular_sha256(arq),
            }
        )
    return arquivos


def carregar_hashes_externos_anteriores(dest_pb: Path) -> dict[str, str]:
    """Lê o compilado.binarypb anterior e retorna o mapa {caminho: checksum_sha256}."""
    if not dest_pb.is_file():
        return {}
    try:
        croqui_anterior = croqui_pb2.Croqui()
        croqui_anterior.ParseFromString(dest_pb.read_bytes())
        return {
            ext.caminho: ext.checksum_sha256
            for ext in croqui_anterior.arquivos_externos
            if ext.caminho and ext.checksum_sha256
        }
    except Exception:
        return {}


def _sincronizar_arquivo_individual(
    src_file: Path,
    dest_file: Path,
    caminho_rel: str,
    hashes_anteriores: dict[str, str],
    force: bool,
    *,
    arquivos_inalterados_out: set[str] | None = None,
) -> str:
    """
    Sincroniza um arquivo individual usando comparação de stat() (st_mtime_ns, st_size)
    e fallback de SHA-256, preservando metadados com shutil.copy2.
    Registra `caminho_rel` em `arquivos_inalterados_out` quando nenhuma cópia de conteúdo foi necessária.
    """
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    hash_anterior = hashes_anteriores.get(caminho_rel)

    if not force and dest_file.is_file() and hash_anterior:
        st_src = src_file.stat()
        st_dest = dest_file.stat()
        if st_src.st_mtime_ns == st_dest.st_mtime_ns and st_src.st_size == st_dest.st_size:
            if arquivos_inalterados_out is not None:
                arquivos_inalterados_out.add(caminho_rel)
            return hash_anterior

        checksum = calcular_sha256(src_file)
        if checksum != hash_anterior:
            shutil.copy2(
                normalizar_caminho_estendido(src_file),
                normalizar_caminho_estendido(dest_file),
            )
        else:
            shutil.copystat(
                normalizar_caminho_estendido(src_file),
                normalizar_caminho_estendido(dest_file),
            )
            if arquivos_inalterados_out is not None:
                arquivos_inalterados_out.add(caminho_rel)
        return checksum

    shutil.copy2(
        normalizar_caminho_estendido(src_file),
        normalizar_caminho_estendido(dest_file),
    )
    return calcular_sha256(src_file)


def sincronizar_imagens_exportaveis(
    src_imagens: Path,
    dest_imagens: Path,
    hashes_anteriores: dict[str, str],
    force: bool = False,
    *,
    imagens_inalteradas_out: set[str] | None = None,
) -> list[dict[str, str]]:
    """Sincroniza incrementalmente as imagens exportáveis e remove arquivos órfãos."""
    if not src_imagens.exists():
        if dest_imagens.exists():
            force_rmtree(dest_imagens)
        return []

    dest_imagens.mkdir(parents=True, exist_ok=True)
    imgs_src = listar_imagens_exportaveis(src_imagens)
    nomes_validos = {img.name for img in imgs_src}

    for item_dest in list(dest_imagens.iterdir()):
        if item_dest.is_dir():
            force_rmtree(item_dest)
        elif item_dest.name not in nomes_validos:
            item_dest.unlink(missing_ok=True)

    arquivos_externos: list[dict[str, str]] = []
    for img_src in imgs_src:
        caminho_rel = f"imagens/{img_src.name}"
        img_dest = dest_imagens / img_src.name
        checksum = _sincronizar_arquivo_individual(
            img_src,
            img_dest,
            caminho_rel,
            hashes_anteriores,
            force,
            arquivos_inalterados_out=imagens_inalteradas_out,
        )
        arquivos_externos.append({"caminho": caminho_rel, "checksum_sha256": checksum})

    return arquivos_externos


def sincronizar_anexos_exportaveis(
    src_anexos: Path,
    dest_anexos: Path,
    hashes_anteriores: dict[str, str],
    force: bool = False,
) -> list[dict[str, str]]:
    """Sincroniza incrementalmente os anexos exportáveis e remove arquivos órfãos."""
    if not src_anexos.exists():
        if dest_anexos.exists():
            force_rmtree(dest_anexos)
        return []

    dest_anexos.mkdir(parents=True, exist_ok=True)
    arqs_src = listar_anexos_exportaveis(src_anexos)
    rels_validos = {arq.relative_to(src_anexos).as_posix() for arq in arqs_src}

    for item_dest in listar_anexos_exportaveis(dest_anexos):
        rel_dest = item_dest.relative_to(dest_anexos).as_posix()
        if rel_dest not in rels_validos:
            item_dest.unlink(missing_ok=True)

    arquivos_externos: list[dict[str, str]] = []
    for arq_src in arqs_src:
        rel = arq_src.relative_to(src_anexos).as_posix()
        caminho_rel = f"anexos/{rel}"
        arq_dest = dest_anexos / rel
        checksum = _sincronizar_arquivo_individual(
            arq_src, arq_dest, caminho_rel, hashes_anteriores, force
        )
        arquivos_externos.append({"caminho": caminho_rel, "checksum_sha256": checksum})

    return arquivos_externos


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------


def preparar_generated(limpar: bool = True) -> None:
    """Garante que o diretório generated/ existe. Limpa se limpar=True."""
    if limpar and GENERATED_DIR.exists():
        force_rmtree(GENERATED_DIR)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def passo_a_compilar_croquis(
    a_compilar: list[tuple[Path, dict[str, Any]]],
    force_thumbnails: bool = False,
    gerar_arquivos_de_debug: bool = True,
    verbose: bool = False,
    *,
    force: bool = False,
) -> tuple[list[tuple[str, dict[str, Any], Path]], list[str], list[Exception], bool]:
    """
    Passo A: Corrige cada croqui em memória, sincroniza imagens/anexos incrementalmente
    e compila para .binarypb (e compilado.yaml se gerar_arquivos_de_debug=True) sem reler arquivos do disco.
    Retorna (compilados, erros, excecoes, database_modificado).
    """
    print("\n=== Passo A: Compilando croquis ===")
    compilados: list[tuple[str, dict[str, Any], Path]] = []
    erros: list[str] = []
    excecoes: list[Exception] = []
    database_modificado: bool = False
    total = len(a_compilar)

    for i, (croqui_dir, croqui_data) in enumerate(a_compilar, 1):
        croqui_id = croqui_data["id"]
        print(f"\n[{croqui_id}] ({i}/{total})")
        dest_dir = GENERATED_DIR / croqui_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_pb = dest_dir / "compilado.binarypb"
        dest_yaml = dest_dir / "compilado.yaml" if gerar_arquivos_de_debug else None
        hashes_anteriores = {} if force else carregar_hashes_externos_anteriores(dest_pb)

        if not gerar_arquivos_de_debug:
            (dest_dir / "compilado.yaml").unlink(missing_ok=True)
        (dest_dir / "compilado.md").unlink(missing_ok=True)

        ctx_memoria = obter_contexto_memoria_deploy(croqui_dir)
        em_modo_ram = ctx_memoria is not None
        cache_md: CacheMd = ctx_memoria.cache_md if ctx_memoria is not None else {}

        # --- Fase 1: Correção do Database em Memória (Migração de Imagens e Thumbnails) ---
        try:
            if corrigir_database(
                croqui_dir,
                dados_croqui_memoria=croqui_data,
                cache_md_memoria=cache_md,
                persistir_no_disco=not em_modo_ram,
            ):
                database_modificado = True
            processar_thumbnail(
                croqui_dir,
                GENERATED_DIR,
                croqui_data,
                force_thumbnails=(force or force_thumbnails),
            )
        except Exception as e:
            if ctx_memoria is not None and not ctx_memoria.persistido_no_disco:
                persistir_contexto_memoria_no_disco(croqui_dir, ctx_memoria)
            import traceback

            print(traceback.format_exc())
            msg = f"Erro ao corrigir database de {croqui_id}: {e}"
            print(f"  {msg}")
            erros.append(msg)
            excecoes.append(e)
            continue

        # --- Fase 2: Sincronização Incremental de Imagens e Anexos ---
        src_imagens = croqui_dir / "imagens"
        dest_imagens = dest_dir / "imagens"
        imagens_inalteradas: set[str] = set()
        arquivos_externos = sincronizar_imagens_exportaveis(
            src_imagens,
            dest_imagens,
            hashes_anteriores,
            force=force,
            imagens_inalteradas_out=imagens_inalteradas,
        )
        if arquivos_externos:
            print(f"  {len(arquivos_externos)} imagem(ns) indexada(s) em arquivos_externos")
        else:
            print("  Sem pasta imagens/")

        if sincronizar_dimensoes_mapas_database(
            croqui_dir,
            croqui_data,
            cache_md,
            imagens_inalteradas=imagens_inalteradas,
            persistir_no_disco=not em_modo_ram,
        ):
            database_modificado = True

        if ctx_memoria is not None and not ctx_memoria.persistido_no_disco:
            persistir_contexto_memoria_no_disco(croqui_dir, ctx_memoria)

        src_anexos = croqui_dir / "anexos"
        dest_anexos = dest_dir / "anexos"
        anexos_externos = sincronizar_anexos_exportaveis(
            src_anexos, dest_anexos, hashes_anteriores, force=force
        )
        if anexos_externos:
            arquivos_externos.extend(anexos_externos)
            print(f"  {len(anexos_externos)} anexo(s) indexado(s) em arquivos_externos")

        # --- Fase 3: Compilação em Memória ---
        try:
            validar_sem_extensoes_vazadas(
                croqui_dir,
                dados_croqui_memoria=croqui_data,
                cache_md_memoria=cache_md,
            )
            croqui_compilado = compilar_croqui(
                croqui_dir,
                destino_yaml=dest_yaml,
                destino_binarypb=dest_pb,
                dados_extras={"arquivos_externos": arquivos_externos}
                if arquivos_externos
                else None,
                dados_croqui_memoria=croqui_data,
                cache_md_memoria=cache_md,
                imagens_inalteradas=imagens_inalteradas,
            )

            def _check_integer_ids(obj: Any) -> None:
                if isinstance(obj, dict):
                    if "pontos_de_interesse" in obj:
                        for ponto in obj.get("pontos_de_interesse", []):
                            if "id" in ponto and type(ponto["id"]) is int:
                                print(
                                    f"\nAviso: O ID de mapa '{ponto['id']}' no croqui '{croqui_id}' foi parseado como INTEIRO. Recomenda-se adicionar aspas simples no ID (ex: '{ponto['id']}')."
                                )
                    for v in obj.values():
                        _check_integer_ids(v)
                elif isinstance(obj, list):
                    for item in obj:
                        _check_integer_ids(item)

            _check_integer_ids(croqui_compilado)
            verificar_nomes_duplicados_de_escalada(croqui_id, croqui_compilado)
            verificar_escaladas_sem_mapa(croqui_id, croqui_compilado)
            verificar_imagens_inexistentes(croqui_dir, croqui_id, croqui_compilado)
            verificar_mapas_duplicados(croqui_id, croqui_compilado)
            verificar_titulos_em_descricao_setor_grupo(croqui_id, croqui_compilado)
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            msg = f"Erro ao compilar {croqui_id}: {e}"
            print(f"  {msg}")
            erros.append(msg)
            excecoes.append(e)
            continue

        if not dest_pb.exists():
            print("  Erro: compilado.binarypb não foi gerado.")
            continue

        _ULTIMOS_DADOS_MEMORIA_SAUDE[croqui_dir.name] = (croqui_data, cache_md)
        compilados.append((croqui_id, croqui_compilado, dest_pb))

    return compilados, erros, excecoes, database_modificado


def passo_b_calcular_checksums(
    compilados: list[tuple[str, dict[str, Any], Path]], verbose: bool = False
) -> dict[str, str]:
    """Passo B: SHA-256 de cada compilado.binarypb em generated/<id>/."""
    if verbose:
        print("\n=== Passo B: Calculando checksums SHA-256 ===")
    checksums: dict[str, str] = {}
    for croqui_id, _, pb_path in compilados:
        checksum = calcular_sha256(pb_path)
        checksums[croqui_id] = checksum
        if verbose:
            print(f"  {croqui_id}: {checksum[:16]}...")
    return checksums


def passo_c_gerar_indice(
    compilados: list[tuple[str, dict[str, Any], Path]],
    checksums: dict[str, str],
    dados_anteriores: dict[str, indice_pb2.ResumoCroqui] | None = None,
    preservados: list[indice_pb2.ResumoCroqui] | None = None,
    is_producao: bool = True,
    verbose: bool = False,
) -> indice_pb2.Indice:
    """
    Passo C: Gera generated/indice.binarypb (e indice.yaml para debug).
    O indice.binarypb é escrito por último para garantir deploy atômico.
    """
    if verbose:
        print("\n=== Passo C: Gerando indice.binarypb + indice.yaml ===")
    agora = datetime.datetime.now(datetime.UTC)
    dados_anteriores = dados_anteriores or {}
    preservados = preservados or []

    indice = indice_pb2.Indice()

    indice_list: list[dict[str, Any]] = []  # para o YAML

    # Primeiro adicionamos os novos/atualizados
    compilados_filtrados = compilados
    if is_producao:
        compilados_filtrados = [c for c in compilados if c[1].get("publicar_croqui", False)]

    for croqui_id, croqui_data, caminho_compilado_pb in compilados_filtrados:
        new_checksum = checksums.get(croqui_id, "")
        old_resumo = dados_anteriores.get(croqui_id)
        old_checksum = old_resumo.checksum_sha256_croqui if old_resumo else ""
        old_timestamp = (
            old_resumo.timestamp_update
            if old_resumo and old_resumo.HasField("timestamp_update")
            else None
        )

        resumo = indice.croquis.add()
        if old_checksum == new_checksum and old_timestamp:
            resumo.timestamp_update.CopyFrom(old_timestamp)
            ts_str = resumo.timestamp_update.ToDatetime().strftime("%Y-%m-%dT%H:%M:%SZ")
            if verbose:
                print(f"  {croqui_id}: checksum inalterado, mantendo timestamp_update={ts_str}")
        else:
            resumo.timestamp_update.FromDatetime(agora)
            ts_str = resumo.timestamp_update.ToDatetime().strftime("%Y-%m-%dT%H:%M:%SZ")
            if verbose:
                if old_checksum:
                    print(
                        f"  {croqui_id}: checksum mudou ({old_checksum[:8]}... -> {new_checksum[:8]}...), timestamp_update={ts_str}"
                    )
                else:
                    print(f"  {croqui_id}: novo croqui, timestamp_update={ts_str}")

        resumo.id = croqui_id
        resumo.croqui_uid = croqui_data.get("uid", "")
        resumo.nome = croqui_data.get("nome", croqui_id)
        resumo.descricao = extrair_descricao(croqui_data)
        resumo.caminho_relativo = f"{croqui_id}/compilado.binarypb"
        resumo.checksum_sha256_croqui = new_checksum

        picos = croqui_data.get("picos", [])

        # Injeta estatísticas pré-computadas agregando todos os picos
        total_escaladas = 0
        total_setores = 0
        total_grupos = 0
        total_esportivas = 0
        total_moveis = 0
        total_boulders = 0
        total_multiplas_enfiadas = 0
        total_highlines = 0

        if isinstance(picos, list):
            for pico in picos:
                if isinstance(pico, dict):
                    pre = pico.get("precomputados", {})
                    if isinstance(pre, dict):
                        total_escaladas += pre.get("total_escaladas", 0)
                        total_setores += pre.get("total_setores", 0)
                        total_grupos += pre.get("total_grupos", 0)
                        total_esportivas += pre.get("total_esportivas", 0)
                        total_moveis += pre.get("total_moveis", 0)
                        total_boulders += pre.get("total_boulders", 0)
                        total_multiplas_enfiadas += pre.get("total_multiplas_enfiadas", 0)
                        total_highlines += pre.get("total_highlines", 0)

        resumo.precomputados.total_escaladas = total_escaladas
        resumo.precomputados.total_setores = total_setores
        resumo.precomputados.total_grupos = total_grupos
        resumo.precomputados.total_esportivas = total_esportivas
        resumo.precomputados.total_moveis = total_moveis
        resumo.precomputados.total_boulders = total_boulders
        resumo.precomputados.total_multiplas_enfiadas = total_multiplas_enfiadas
        resumo.precomputados.total_highlines = total_highlines

        # Injeta tamanho estimado de download para modo offline
        pasta_imagens = caminho_compilado_pb.parent / "imagens"
        pasta_anexos = caminho_compilado_pb.parent / "anexos"
        resumo.precomputados.tamanho_download_bytes = calcular_tamanho_croqui_bytes(
            caminho_compilado=caminho_compilado_pb,
            pasta_imagens=pasta_imagens,
            pastas_excluidas=IMAGENS_SUBDIRS_EXCLUIDOS,
            pasta_anexos=pasta_anexos,
        )

        if (
            isinstance(picos, list)
            and len(picos) > 0
            and isinstance(picos[0], dict)
            and "localizacao" in picos[0]
        ):
            loc = picos[0]["localizacao"]
            if isinstance(loc, dict):
                resumo.localizacao.latitude = loc.get("latitude", 0)
                resumo.localizacao.longitude = loc.get("longitude", 0)

        # Thumbnail Checksum
        thumb_path = GENERATED_DIR / "thumbnails" / f"{croqui_id}.webp"
        thumb_checksum = ""
        if thumb_path.exists():
            thumb_checksum = calcular_sha256(thumb_path)
            resumo.checksum_sha256_thumbnail = thumb_checksum

        if verbose:
            print(f"  Adicionado/Atualizado: {croqui_id}")

    # Depois adicionamos os preservados
    for resumo_preservado in preservados:
        if any(c[0] == resumo_preservado.id for c in compilados):
            continue

        resumo = indice.croquis.add()
        resumo.CopyFrom(resumo_preservado)

        if resumo.precomputados.tamanho_download_bytes == 0 and resumo.caminho_relativo:
            caminho_pb = GENERATED_DIR / resumo.caminho_relativo
            pasta_img = caminho_pb.parent / "imagens"
            resumo.precomputados.tamanho_download_bytes = calcular_tamanho_croqui_bytes(
                caminho_compilado=caminho_pb,
                pasta_imagens=pasta_img,
                pastas_excluidas=IMAGENS_SUBDIRS_EXCLUIDOS,
            )

        if verbose:
            print(f"  Preservado: {resumo.id} (de deploy anterior)")

    # Ordenar croquis no índice por ID para consistência
    indice.croquis.sort(key=lambda x: x.id)

    # Gerar lista para o YAML a partir do índice final (ordenado)
    for resumo in indice.croquis:
        item_yaml: dict[str, Any] = {
            "id": resumo.id,
            "croqui_uid": resumo.croqui_uid,
            "nome": resumo.nome,
            "descricao": resumo.descricao,
            "caminho_relativo": resumo.caminho_relativo,
            "checksum_sha256_croqui": resumo.checksum_sha256_croqui,
            "checksum_sha256_thumbnail": resumo.checksum_sha256_thumbnail,
            "timestamp_update": resumo.timestamp_update.ToDatetime().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if resumo.HasField("precomputados"):
            pre_yaml: dict[str, Any] = {
                "total_escaladas": resumo.precomputados.total_escaladas,
                "total_setores": resumo.precomputados.total_setores,
                "total_grupos": resumo.precomputados.total_grupos,
            }
            if resumo.precomputados.total_esportivas > 0:
                pre_yaml["total_esportivas"] = resumo.precomputados.total_esportivas
            if resumo.precomputados.total_moveis > 0:
                pre_yaml["total_moveis"] = resumo.precomputados.total_moveis
            if resumo.precomputados.total_boulders > 0:
                pre_yaml["total_boulders"] = resumo.precomputados.total_boulders
            if resumo.precomputados.total_multiplas_enfiadas > 0:
                pre_yaml["total_multiplas_enfiadas"] = resumo.precomputados.total_multiplas_enfiadas
            if resumo.precomputados.total_highlines > 0:
                pre_yaml["total_highlines"] = resumo.precomputados.total_highlines
            if resumo.precomputados.tamanho_download_bytes > 0:
                pre_yaml["tamanho_download_bytes"] = resumo.precomputados.tamanho_download_bytes

            item_yaml["precomputados"] = pre_yaml
        if resumo.HasField("localizacao"):
            item_yaml["localizacao"] = {
                "latitude": resumo.localizacao.latitude,
                "longitude": resumo.localizacao.longitude,
            }
        indice_list.append(item_yaml)

    # Preenche versao_catalogo se catalogo.db já estiver disponível
    caminho_catalogo_db = GENERATED_DIR / "catalogo.db"
    if caminho_catalogo_db.exists():
        from scripts.gerar_catalogo_sqlite_lib import obter_versao_catalogo

        versao_cat = obter_versao_catalogo(caminho_catalogo_db)
        if versao_cat:
            indice.versao_catalogo = versao_cat

    # indice.yaml — escrito antes do .binarypb para debug
    indice_yaml_path = GENERATED_DIR / "indice.yaml"
    yaml_content: dict[str, Any] = {}
    if indice.versao_catalogo:
        yaml_content["versao_catalogo"] = indice.versao_catalogo
    yaml_content["croquis"] = indice_list
    escrever_texto_se_modificado(
        indice_yaml_path,
        serializar_yaml(yaml_content, incluir_cabecalho_spdx=False),
    )
    if verbose:
        print(f"  indice.yaml escrito ({indice_yaml_path})")

    # indice.binarypb — sempre o último (deploy atômico)
    indice_bytes = indice.SerializeToString()
    indice_pb_path = GENERATED_DIR / "indice.binarypb"
    with open(indice_pb_path, "wb") as f:
        f.write(indice_bytes)

    total_dirs = len([d for d in GENERATED_DIR.iterdir() if d.is_dir()])
    print(f"\nDeploy concluido em: {GENERATED_DIR}")
    print(f"  {total_dirs} pastas de croqui + indice.binarypb + indice.yaml")

    return indice


def deploy(
    output_dir: Path,
    target_paths: Sequence[str | Path] | None = None,
    force_thumbnails: bool = False,
    gerar_arquivos_de_debug: bool = True,
    is_producao: bool = True,
    verbose: bool = False,
    sair_ao_falhar: bool = False,
    *,
    force: bool = False,
    database_dir: Path | None = None,
) -> bool:
    global GENERATED_DIR
    GENERATED_DIR = output_dir.resolve()
    db_dir = (database_dir or DATABASE_DIR).resolve()

    print(f"Diretorio de saida : {GENERATED_DIR}")
    if target_paths:
        print(f"Alvos específicos  : {target_paths}")
    print()

    a_compilar: list[tuple[Path, dict[str, Any]]] = []
    a_preservar: list[tuple[Path, dict[str, Any]]] = []

    if target_paths:
        # Carrega estritamente os croquis alvo sem varrer database/ inteiro
        vistos: set[Path] = set()
        for t in target_paths:
            t_path = Path(t)
            t_abs = t_path.resolve()
            if not t_abs.exists() and not t_path.is_absolute():
                candidato_db = (db_dir / t).resolve()
                if candidato_db.exists():
                    t_abs = candidato_db
            if t_abs in vistos:
                continue
            vistos.add(t_abs)
            ctx_memoria = obter_contexto_memoria_deploy(t_abs)
            if (
                ctx_memoria is not None
                and isinstance(ctx_memoria.croqui_data, dict)
                and ctx_memoria.croqui_data.get("id")
            ):
                a_compilar.append((t_abs, ctx_memoria.croqui_data))
                continue
            croqui_alvo_data = carregar_um_croqui(t_abs)
            if croqui_alvo_data is not None:
                a_compilar.append((t_abs, croqui_alvo_data))
            else:
                raise RuntimeError(
                    f"Alvo '{t_abs}' não encontrado ou não é um croqui válido (falta croqui.yaml com 'id')."
                )
    else:
        todos_croquis = encontrar_croquis(database_dir=db_dir)
        if not todos_croquis:
            print("Nenhum croqui encontrado em database/. Nada a fazer.")
            return False
        a_compilar = todos_croquis

    # Carregar dados do índice anterior antes de (opcionalmente) limpar a pasta
    dados_anteriores = carregar_dados_anteriores(GENERATED_DIR / "indice.binarypb")

    # Preparar pasta gerada (limpa tudo apenas se não houver alvo específico e force=True)
    preparar_generated(limpar=(not target_paths and force))

    # Compilar os selecionados
    compilados_novos, erros, excecoes, database_modificado = passo_a_compilar_croquis(
        a_compilar,
        force_thumbnails=force_thumbnails,
        gerar_arquivos_de_debug=gerar_arquivos_de_debug,
        verbose=verbose,
        force=force,
    )

    if erros:
        print("\n" + "!" * 60)
        print("AVISO: O processamento de um ou mais croquis falhou.")
        for msg in erros:
            print(f"\n{msg}")
        print("\n" + "!" * 60 + "\n")

    # Identificar o que preservar do índice anterior (caso seja deploy seletivo)
    compilados_preservados: list[tuple[str, dict[str, Any], Path]] = []
    preservados_metadados: list[indice_pb2.ResumoCroqui] = []

    if target_paths:
        ids_novos = {c[0] for c in compilados_novos}
        for croqui_id, resumo in dados_anteriores.items():
            if croqui_id not in ids_novos:
                dest_pb = GENERATED_DIR / croqui_id / "compilado.binarypb"
                if dest_pb.exists():
                    preservados_metadados.append(resumo)
                else:
                    print(
                        f"  Aviso: croqui '{croqui_id}' estava no indice anterior mas arquivos sumiram de {GENERATED_DIR}. Removendo do indice."
                    )
    else:
        for _d, data in a_preservar:
            croqui_id = str(data["id"])
            dest_pb = GENERATED_DIR / croqui_id / "compilado.binarypb"
            if dest_pb.exists():
                compilados_preservados.append((croqui_id, data, dest_pb))

    compilados_finais_para_checksum = compilados_novos + compilados_preservados

    if not compilados_finais_para_checksum and not preservados_metadados:
        print("Aviso: Nenhum croqui encontrado para compilar ou preservar.")
        if erros:
            if sair_ao_falhar:
                sys.exit(1)
            else:
                msg_erro = f"Ocorreram {len(erros)} erros durante o deploy:\n" + "\n".join(erros)
                if excecoes:
                    raise RuntimeError(msg_erro) from excecoes[0]
                else:
                    raise RuntimeError(msg_erro)
        if not target_paths:
            return False
        else:
            raise RuntimeError(f"Nenhum croqui válido encontrado no alvo: {target_paths}")

    checksums = passo_b_calcular_checksums(compilados_finais_para_checksum, verbose=verbose)
    alvos_catalogo = [c[0] for c in compilados_novos] if target_paths else None
    passo_e_gerar_catalogo_sqlite(alvos=alvos_catalogo, verbose=verbose)
    indice = passo_c_gerar_indice(
        compilados_finais_para_checksum,
        checksums,
        dados_anteriores,
        preservados=preservados_metadados,
        is_producao=is_producao,
        verbose=verbose,
    )
    passo_d_gerar_manifesto_serving(
        indice,
        verbose=verbose,
        compilados_novos=compilados_novos,
        alvos=set(alvos_catalogo) if alvos_catalogo is not None else None,
    )

    print(f"\nTotal compilados: {len(compilados_novos)} de {len(a_compilar)}")
    if erros:
        print(f"Total erros: {len(erros)}")
        print(f"Ocorreram {len(erros)} erros durante o deploy. Veja os logs acima.")
        if sair_ao_falhar:
            sys.exit(1)
        else:
            raise RuntimeError(
                f"Ocorreram {len(erros)} erros durante o deploy:\n" + "\n".join(erros)
            )

    return database_modificado


def passo_d_gerar_manifesto_serving(
    indice: indice_pb2.Indice,
    verbose: bool = False,
    *,
    compilados_novos: list[tuple[str, dict[str, Any], Path]] | None = None,
    alvos: set[str] | None = None,
) -> None:
    """
    Passo D: Gera ou atualiza incrementalmente o manifesto YAML (arquivos_serving.yaml)
    com a lista completa de todos os arquivos a serem cacheados pelo CDN e servidos.
    """
    from google.protobuf.json_format import MessageToDict

    if verbose:
        print("\n=== Passo D: Gerando arquivos_serving.yaml ===")

    caminho_manifesto = GENERATED_DIR / "arquivos_serving.yaml"
    entradas_anteriores_por_croqui: dict[str, list[tuple[str, str]]] = defaultdict(list)
    if alvos is not None and caminho_manifesto.is_file():
        try:
            dados_ant = carregar_yaml(caminho_manifesto.read_text(encoding="utf-8")) or {}
            for item in dados_ant.get("arquivos", []):
                if isinstance(item, dict):
                    rel = str(item.get("caminho_relativo", ""))
                    chk = str(item.get("checksum_sha256", ""))
                    if "/" in rel and not rel.startswith("thumbnails/"):
                        cid = rel.split("/", 1)[0]
                        entradas_anteriores_por_croqui[cid].append((rel, chk))
        except Exception:
            entradas_anteriores_por_croqui.clear()

    mapa_novos_memoria: dict[str, list[dict[str, str]]] = {}
    if compilados_novos:
        for cid, cdata, _ in compilados_novos:
            exts = cdata.get("arquivos_externos")
            if isinstance(exts, list):
                mapa_novos_memoria[cid] = exts

    manifesto = serving_pb2.ArquivosServing()
    adicionados: set[str] = set()

    def add_file(rel_path: str, checksum: str) -> None:
        if rel_path in adicionados:
            return
        arquivo = manifesto.arquivos.add()
        arquivo.caminho_relativo = rel_path
        arquivo.checksum_sha256 = checksum
        adicionados.add(rel_path)

    # 1. Adiciona os arquivos do Índice
    for croqui in indice.croquis:
        base = croqui.id
        add_file(f"{base}/compilado.binarypb", croqui.checksum_sha256_croqui)
        if croqui.checksum_sha256_thumbnail:
            add_file(f"thumbnails/{base}.webp", croqui.checksum_sha256_thumbnail)

        if base in mapa_novos_memoria:
            for ext_dict in mapa_novos_memoria[base]:
                add_file(f"{base}/{ext_dict['caminho']}", ext_dict["checksum_sha256"])
            p_yaml = GENERATED_DIR / base / "compilado.yaml"
            if p_yaml.exists():
                add_file(f"{base}/compilado.yaml", calcular_sha256(p_yaml))
        elif alvos is not None and base not in alvos and base in entradas_anteriores_por_croqui:
            for rel_ant, chk_ant in entradas_anteriores_por_croqui[base]:
                if rel_ant != f"{base}/compilado.binarypb":
                    add_file(rel_ant, chk_ant)
        else:
            compilado_path = GENERATED_DIR / base / "compilado.binarypb"
            if compilado_path.exists():
                c = croqui_pb2.Croqui()
                c.ParseFromString(compilado_path.read_bytes())
                for ext in c.arquivos_externos:
                    add_file(f"{base}/{ext.caminho}", ext.checksum_sha256)
            p_yaml = GENERATED_DIR / base / "compilado.yaml"
            if p_yaml.exists():
                add_file(f"{base}/compilado.yaml", calcular_sha256(p_yaml))

    # 2. Calcula para os arquivos globais
    for global_file in ["indice.binarypb", "indice.yaml", "catalogo.db"]:
        p = GENERATED_DIR / global_file
        if p.exists():
            add_file(global_file, calcular_sha256(p))

    dados = MessageToDict(manifesto, preserving_proto_field_name=True)
    escrever_texto_se_modificado(
        caminho_manifesto,
        serializar_yaml(dados, incluir_cabecalho_spdx=False),
    )

    if verbose:
        print(f"Manifesto salvo com {len(manifesto.arquivos)} arquivos.")


def passo_e_gerar_catalogo_sqlite(alvos: list[str] | None = None, verbose: bool = False) -> Path:
    """
    Passo E: Gera ou atualiza incrementalmente o catálogo SQLite descomprimido (catalogo.db).
    """
    from scripts.gerar_catalogo_sqlite_lib import gerar_catalogo_completo

    if verbose:
        print("\n=== Passo E: Gerando catálogo SQLite (catalogo.db) ===")

    caminho_db = GENERATED_DIR / "catalogo.db"
    gerar_catalogo_completo(GENERATED_DIR, caminho_db, alvos=alvos)

    if verbose:
        print(f"Catálogo SQLite gerado em {caminho_db}")

    return caminho_db


def atualizar_saude_croquis(
    alvos: Sequence[str | Path] | None = None,
    *,
    base_path: Path | None = None,
    output_path: Path | None = None,
    dados_em_memoria: dict[str, tuple[dict[str, Any], CacheMd]] | None = None,
) -> bool:
    """Atualiza o STATUS_CROQUIS.md em memória sem invocar subprocesso."""
    print("\n=== Atualizando saúde dos croquis (STATUS_CROQUIS.md) ===")
    from scripts.medir_saude_croquis import atualizar_relatorio_saude_croquis

    try:
        return atualizar_relatorio_saude_croquis(
            base_path=base_path or DATABASE_DIR,
            output_path=output_path or (ROOT_DIR / "STATUS_CROQUIS.md"),
            alvos=alvos,
            dados_em_memoria=dados_em_memoria
            if dados_em_memoria is not None
            else _ULTIMOS_DADOS_MEMORIA_SAUDE,
        )
    except Exception as e:
        print(f"Erro ao atualizar saúde dos croquis: {e}")
        return False


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compila todos os croquis (ou um específico) e gera o indice."
    )
    parser.add_argument(
        "croquis",
        nargs="*",
        default=[],
        help="Caminhos para croquis específicos (ex: database/meu_croqui).",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        default=None,
        help="Caminhos para croquis específicos (ex: database/meu_croqui). Se omitido, processa todos.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(ROOT_DIR / "generated"),
        help="Diretorio de saida (padrao: generated/)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Força recálculo integral de SHA-256, recópia de imagens/anexos e regeneração de thumbnails.",
    )
    parser.add_argument(
        "--force-thumbnails",
        action="store_true",
        help="Força a re-geração de todas as thumbnails.",
    )
    parser.add_argument(
        "--producao",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Se ativado, inclui no indice apenas croquis com publicar_croqui=true (padrao: True).",
    )
    parser.add_argument(
        "--status",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Atualiza o arquivo STATUS_CROQUIS.md ao final (padrao: True).",
    )
    parser.add_argument(
        "--arquivos-de-debug",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Gera arquivo auxiliar compilado.yaml para debug (padrao: True).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Habilita logs detalhados dos passos B, C e D.",
    )
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    alvos = (args.target or []) + (args.croquis or [])
    target_paths = alvos if alvos else None

    try:
        deploy(
            output_dir,
            target_paths=target_paths,
            force_thumbnails=(args.force or args.force_thumbnails),
            gerar_arquivos_de_debug=args.arquivos_de_debug,
            is_producao=args.producao,
            verbose=args.verbose,
            sair_ao_falhar=True,
            force=args.force,
        )
    except RuntimeError as e:
        print(f"\\nDeploy interrompido: {e}")
        sys.exit(1)

    if args.status:
        atualizar_saude_croquis(alvos=target_paths)
