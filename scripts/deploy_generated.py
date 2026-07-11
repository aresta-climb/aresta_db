# Copyright (C) 2026 ARESTA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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

import sys
import io

# Força o uso de UTF-8 para stdout e stderr, especialmente importante no Windows
# Em executáveis --windowed do PyInstaller, sys.stdout e sys.stderr podem ser None.
if sys.stdout is not None and getattr(sys.stdout, 'encoding', None) != 'utf-8':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

if sys.stderr is not None and getattr(sys.stderr, 'encoding', None) != 'utf-8':
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import hashlib
import datetime
import shutil
import argparse
import yaml
import base64
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

sys.path.append(str(Path(__file__).resolve().parent.parent))

import build
from aresta_api.proto.generated import indice_pb2
from scripts.preparar_submissao_lib import (
    corrigir_database,
    compilar_croqui
)
from scripts.gerar_compilado_md import gerar_compilado_md

ROOT_DIR     = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT_DIR / "database"

# Pode ser substituído via --output-dir na linha de comando
GENERATED_DIR: Path  # definido em deploy()


# Subdiretórios dentro de imagens/ que são artefatos de processamento e
# NÃO devem ser exportados para o frontend.
IMAGENS_SUBDIRS_EXCLUIDOS = {"raw_mapas"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def force_rmtree(path: Path) -> None:
    """Versão robusta do shutil.rmtree para Windows, com retry e tratamento de read-only."""
    import time
    import os
    
    def remover_somente_leitura(func, p, _):
        os.chmod(p, 0o777)
        func(p)
        
    for i in range(5):
        try:
            if path.exists():
                shutil.rmtree(path, onerror=remover_somente_leitura)
            return
        except PermissionError:
            if i == 4:
                raise
            time.sleep(0.2)

def calcular_sha256(caminho: Path) -> str:
    """SHA-256 de um arquivo, lido em chunks de 4096 bytes."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def processar_thumbnail(croqui_dir: Path, generated_dir: Path, croqui_data: dict, force_thumbnails: bool = False) -> bool:
    """
    Converte a imagem apontada em caminho_thumbnail para generated/thumbnails/<id>.webp.
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

    # Se a thumbnail já existe no destino e não estamos forçando, pulamos.
    if not force_thumbnails and dest_path.exists():
        # Idealmente verificaríamos se o src mudou, mas por agora simplificamos.
        return False

    if not src_path.exists():
        raise FileNotFoundError(f"Thumbnail original não encontrada em {src_path}. Verifique o campo 'caminho_thumbnail' no croqui.yaml.")

    print(f"  Gerando thumbnail: {caminho_thumb_original} -> {dest_path.relative_to(GENERATED_DIR)} (600x600, WebP)")
    
    try:
        with Image.open(src_path) as img:
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
            mask = Image.new('L', foreground.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, foreground.width, foreground.height), radius=CORNER_RADIUS, fill=255)
            
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


def encontrar_croquis() -> list[tuple[Path, dict]]:
    """Retorna [(croqui_dir, croqui_data)] para todos os croquis válidos em database/."""
    if not DATABASE_DIR.exists():
        return []

    resultado = []
    for d in sorted(DATABASE_DIR.iterdir()):
        yaml_path = d / "croqui.yaml"
        if not d.is_dir() or not yaml_path.exists():
            continue
        with open(yaml_path, "r", encoding="utf-8") as f:
            croqui_data = yaml.safe_load(f)
        croqui_id = croqui_data.get("id")
        if not croqui_id:
            print(f"Aviso: {d.name}/croqui.yaml sem campo 'id', ignorando.")
            continue
        resultado.append((d, croqui_data))

    return resultado


def carregar_um_croqui(caminho: Path) -> dict | None:
    """Carrega dados de um croqui a partir de um diretório qualquer."""
    yaml_path = caminho / "croqui.yaml"
    if not caminho.is_dir() or not yaml_path.exists():
        return None
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            croqui_data = yaml.safe_load(f)
        if not croqui_data or not croqui_data.get("id"):
            return None
        return croqui_data
    except Exception:
        return None

def validar_sem_extensoes_vazadas(pico_dir: Path):
    """
    Verifica se o YAML ou qualquer Markdown referenciado contem vestígios do
    Shadow State (extensoes de caminho original/novo) que deveriam existir
    apenas em memoria durante a edicao na UI.
    """
    extensoes_vazadas = [
        "ext_metadados"
    ]
    for f in pico_dir.rglob("*"):
        if f.is_file() and f.suffix in [".yaml", ".md"]:
            try:
                content = f.read_text(encoding="utf-8")
                for ext in extensoes_vazadas:
                    if ext in content:
                        raise ValueError(f"Extensão de Shadow State '{ext}' vazada detectada no arquivo {f}")
            except UnicodeDecodeError:
                pass


def extrair_descricao(croqui_data: dict) -> str:
    """Descrição de alto nível do croqui; fallback em picos[0].descricao."""
    if croqui_data.get("descricao"):
        return croqui_data["descricao"]
    picos = croqui_data.get("picos", [])
    if picos and picos[0].get("descricao"):
        return picos[0]["descricao"].strip()
    return ""


def verificar_nomes_duplicados_de_escalada(croqui_id: str, compiled_data: dict) -> None:
    """Procura escaladas com o mesmo nome no mesmo croqui e emite um aviso."""
    nomes_vistos = set()
    duplicados = set()

    def _buscar_escaladas(obj):
        if isinstance(obj, dict):
            if "escaladas" in obj and isinstance(obj["escaladas"], list):
                for escalada in obj["escaladas"]:
                    if isinstance(escalada, dict):
                        for tipo_via, dados_via in escalada.items():
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
        print(f"\nAviso: A escalada '{nome}' aparece mais de uma vez no croqui '{croqui_id}'. Nomes duplicados podem causar confusão.")


def verificar_escaladas_sem_mapa(croqui_id: str, compiled_data: dict) -> None:
    """Avisa se há escaladas que não estão mapeadas, caso o croqui já possua mapas desenhados."""
    todas_escaladas = set()
    escaladas_referenciadas = set()
    tem_mapas_com_pontos = False

    def _buscar(obj):
        nonlocal tem_mapas_com_pontos
        if isinstance(obj, dict):
            if "escaladas" in obj and isinstance(obj["escaladas"], list):
                for esc in obj["escaladas"]:
                    if isinstance(esc, dict):
                        for tipo_via, dados_via in esc.items():
                            if isinstance(dados_via, dict) and "nome" in dados_via:
                                todas_escaladas.add(dados_via["nome"])
            
            if "pontos_de_interesse" in obj and isinstance(obj["pontos_de_interesse"], list) and len(obj["pontos_de_interesse"]) > 0:
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
        print(f"\nAviso: A escalada '{nome}' não está referenciada em nenhum mapa no croqui '{croqui_id}'.")



# ---------------------------------------------------------------------------
# Imagens: symlink ou cópia
# ---------------------------------------------------------------------------

def copiar_imagens(src_imagens: Path, dest_imagens: Path) -> None:
    """Copia a pasta de imagens para o destino, excluindo subdiretórios de processamento."""
    def ignorar(dir_, nomes):
        return [n for n in nomes
                if (Path(dir_) / n).is_dir() and n in IMAGENS_SUBDIRS_EXCLUIDOS]
    shutil.copytree(src_imagens, dest_imagens, ignore=ignorar, dirs_exist_ok=True)
    print(f"  Imagens copiadas: {dest_imagens}")



def listar_imagens_exportaveis(imagens_path: Path) -> list[Path]:
    """
    Lista todos os arquivos .webp na raiz de imagens/ (sem descer em raw_mapas/).
    Retorna lista de Path absolutos.
    """
    if not imagens_path.exists():
        return []
    return sorted([
        f for f in imagens_path.iterdir()
        if f.is_file() and f.suffix.lower() == ".webp"
    ])


def calcular_arquivos_externos(imagens_src: Path) -> list[dict]:
    """
    Retorna lista de dicts {caminho, checksum_sha256} para cada imagem exportável,
    com caminho relativo à raiz do croqui (ex: imagens/pagina_7_imagem_0.webp).
    """
    arquivos = []
    for img in listar_imagens_exportaveis(imagens_src):
        arquivos.append({
            "caminho": f"imagens/{img.name}",
            "checksum_sha256": calcular_sha256(img),
        })
    return arquivos


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def preparar_generated(limpar: bool = True) -> None:
    """Garante que o diretório generated/ existe. Limpa se limpar=True."""
    if limpar and GENERATED_DIR.exists():
        force_rmtree(GENERATED_DIR)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def passo_a_compilar_croquis(a_compilar: list[tuple[Path, dict]], force_thumbnails: bool = False, gerar_arquivos_de_debug: bool = True, verbose: bool = False) -> tuple[list[tuple[str, dict, Path]], list[str]]:
    """
    Passo A: Corrige cada croqui e compila para .binarypb (e .yaml/.md se gerar_arquivos_de_debug=True).
    """
    print("\n=== Passo A: Compilando croquis ===")
    compilados = []
    erros = []
    total = len(a_compilar)

    for i, (croqui_dir, croqui_data) in enumerate(a_compilar, 1):
        croqui_id = croqui_data["id"]
        print(f"\n[{croqui_id}] ({i}/{total})")
        dest_dir  = GENERATED_DIR / croqui_id
        
        # Se estivermos em um deploy parcial, a pasta pode já existir.
        # Precisamos limpá-la para garantir uma compilação fresca (especialmente para imagens).
        if dest_dir.exists():
            force_rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_pb   = dest_dir / "compilado.binarypb"
        dest_yaml = dest_dir / "compilado.yaml" if gerar_arquivos_de_debug else None

        # --- Fase 1: Correção do Database (Migração de Imagens e Thumbnails) ---
        try:
            corrigir_database(croqui_dir)
            # Gera a thumbnail na pasta generated/thumbnails/
            processar_thumbnail(croqui_dir, GENERATED_DIR, croqui_data, force_thumbnails=force_thumbnails)
        except Exception as e:
            import traceback
            traceback.print_exc()
            msg = f"Erro ao corrigir database de {croqui_id}: {e}"
            print(f"  {msg}")
            erros.append(msg)
            continue

        # --- Fase 2: Imagens ---
        src_imagens  = croqui_dir / "imagens"
        dest_imagens = dest_dir / "imagens"
        arquivos_externos = []

        if src_imagens.exists():
            copiar_imagens(src_imagens, dest_imagens)
            arquivos_externos = calcular_arquivos_externos(src_imagens)
            print(f"  {len(arquivos_externos)} imagem(ns) indexada(s) em arquivos_externos")
        else:
            print(f"  Sem pasta imagens/")

        # --- Fase 3: Compilação ---
        try:
            validar_sem_extensoes_vazadas(croqui_dir)
            compilar_croqui(
                croqui_dir,
                destino_yaml=dest_yaml,
                destino_binarypb=dest_pb,
                dados_extras={"arquivos_externos": arquivos_externos} if arquivos_externos else None,
            )
            
            if dest_yaml and dest_yaml.exists():
                import yaml
                with open(dest_yaml, "r", encoding="utf-8") as f:
                    compiled_data = yaml.safe_load(f)
                def _check_integer_ids(obj):
                    if isinstance(obj, dict):
                        if "pontos_de_interesse" in obj:
                            for ponto in obj.get("pontos_de_interesse", []):
                                if "id" in ponto and type(ponto["id"]) is int:
                                    print(f"\nAviso: O ID de mapa '{ponto['id']}' no croqui '{croqui_id}' foi parseado como INTEIRO. Recomenda-se adicionar aspas simples no ID (ex: '{ponto['id']}').")
                        for v in obj.values():
                            _check_integer_ids(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            _check_integer_ids(item)
                            
                _check_integer_ids(compiled_data)
                verificar_nomes_duplicados_de_escalada(croqui_id, compiled_data)
                verificar_escaladas_sem_mapa(croqui_id, compiled_data)
                
            # Gerar também o compilado.md (opcional)
            if gerar_arquivos_de_debug:
                dest_md = dest_dir / "compilado.md"
                gerar_compilado_md(croqui_dir, dest_yaml, dest_md)
                if verbose:
                    print(f"  [compilado.md] gerado com sucesso!")
        except Exception as e:
            msg = f"Erro ao compilar {croqui_id}: {e}"
            print(f"  {msg}")
            erros.append(msg)
            continue

        if not dest_pb.exists():
            print(f"  Erro: compilado.binarypb não foi gerado.")
            continue

        compilados.append((croqui_id, croqui_data, dest_pb))

    return compilados, erros


def passo_b_calcular_checksums(
    compilados: list[tuple[str, dict, Path]],
    verbose: bool = False
) -> dict[str, str]:
    """Passo B: SHA-256 de cada compilado.binarypb em generated/<id>/."""
    if verbose:
        print("\n=== Passo B: Calculando checksums SHA-256 ===")
    checksums = {}
    for croqui_id, _, pb_path in compilados:
        checksum = calcular_sha256(pb_path)
        checksums[croqui_id] = checksum
        if verbose:
            print(f"  {croqui_id}: {checksum[:16]}...")
    return checksums


def passo_c_gerar_indice(
    compilados: list[tuple[str, dict, Path]],
    checksums: dict[str, str],
    dados_anteriores: dict[str, indice_pb2.ResumoCroqui] = None,
    preservados: list[indice_pb2.ResumoCroqui] = None,
    is_producao: bool = True,
    verbose: bool = False,
) -> indice_pb2.Indice:
    """
    Passo C: Gera generated/indice.binarypb (e indice.yaml para debug).
    O indice.binarypb é escrito por último para garantir deploy atômico.
    """
    if verbose:
        print("\n=== Passo C: Gerando indice.binarypb + indice.yaml ===")
    agora = datetime.datetime.now(datetime.timezone.utc)
    dados_anteriores = dados_anteriores or {}
    preservados = preservados or []

    indice     = indice_pb2.Indice()
    
    indice_list = []  # para o YAML

    # Primeiro adicionamos os novos/atualizados
    compilados_filtrados = compilados
    if is_producao:
        compilados_filtrados = [
            c for c in compilados if c[1].get("publicar_croqui", False)
        ]

    for croqui_id, croqui_data, _ in compilados_filtrados:

        new_checksum = checksums.get(croqui_id, "")
        old_resumo = dados_anteriores.get(croqui_id)
        old_checksum = old_resumo.checksum_sha256_croqui if old_resumo else ""
        old_timestamp = old_resumo.timestamp_update if old_resumo and old_resumo.HasField("timestamp_update") else None
        
        resumo = indice.croquis.add()
        if old_checksum == new_checksum and old_timestamp:
            resumo.timestamp_update.CopyFrom(old_timestamp)
            ts_str = resumo.timestamp_update.ToDatetime().strftime('%Y-%m-%dT%H:%M:%SZ')
            if verbose:
                print(f"  {croqui_id}: checksum inalterado, mantendo timestamp_update={ts_str}")
        else:
            resumo.timestamp_update.FromDatetime(agora)
            ts_str = resumo.timestamp_update.ToDatetime().strftime('%Y-%m-%dT%H:%M:%SZ')
            if verbose:
                if old_checksum:
                    print(f"  {croqui_id}: checksum mudou ({old_checksum[:8]}... -> {new_checksum[:8]}...), timestamp_update={ts_str}")
                else:
                    print(f"  {croqui_id}: novo croqui, timestamp_update={ts_str}")

        resumo.id             = croqui_id
        resumo.nome           = croqui_data.get("nome", croqui_id)
        resumo.descricao      = extrair_descricao(croqui_data)
        resumo.caminho_relativo = f"{croqui_id}/compilado.binarypb"
        resumo.checksum_sha256_croqui = new_checksum

        picos = croqui_data.get("picos", [])
        if picos and "localizacao" in picos[0]:
            loc = picos[0]["localizacao"]
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
        # Evita duplicatas caso algum preservado tenha o mesmo ID de um compilado (não deveria ocorrer se a lógica no deploy estiver certa)
        if any(c[0] == resumo_preservado.id for c in compilados):
            continue
            
        resumo = indice.croquis.add()
        resumo.CopyFrom(resumo_preservado)
        if verbose:
            print(f"  Preservado: {resumo.id} (de deploy anterior)")

    # Ordenar croquis no índice por ID para consistência
    indice.croquis.sort(key=lambda x: x.id)

    # Gerar lista para o YAML a partir do índice final (ordenado)
    for resumo in indice.croquis:
        item_yaml = {
            "id":             resumo.id,
            "nome":           resumo.nome,
            "descricao":      resumo.descricao,
            "caminho_relativo": resumo.caminho_relativo,
            "checksum_sha256_croqui": resumo.checksum_sha256_croqui,
            "checksum_sha256_thumbnail": resumo.checksum_sha256_thumbnail,
            "timestamp_update": resumo.timestamp_update.ToDatetime().strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        if resumo.HasField("localizacao"):
            item_yaml["localizacao"] = {
                "latitude": resumo.localizacao.latitude,
                "longitude": resumo.localizacao.longitude,
            }
        indice_list.append(item_yaml)

    # indice.yaml — escrito antes do .binarypb para debug
    indice_yaml_path = GENERATED_DIR / "indice.yaml"
    with open(indice_yaml_path, "w", encoding="utf-8") as f:
        yaml_content = {"croquis": indice_list}
        yaml.dump(
            yaml_content,
            f, allow_unicode=True, sort_keys=False,
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


def deploy(output_dir: Path, target_path: str = None, force_thumbnails: bool = False, gerar_arquivos_de_debug: bool = True, is_producao: bool = True, verbose: bool = False) -> None:
    global GENERATED_DIR
    GENERATED_DIR = output_dir.resolve()

    print(f"Diretorio de saida : {GENERATED_DIR}")
    if target_path:
        print(f"Alvo específico    : {target_path}")
    
    print(f"Arquivos de debug (.md/.yaml) : {'Sim' if gerar_arquivos_de_debug else 'Não'}")
    print()

    # 1. Encontrar todos os croquis na database/
    todos_croquis = encontrar_croquis()

    # 2. Filtrar o que será compilado e o que será preservado
    a_compilar = []
    a_preservar = []

    if target_path:
        # Resolve o caminho do alvo para comparação
        target_abs = Path(target_path).resolve()
        # Se o caminho não existe como está, tenta prefixar com database/
        if not target_abs.exists() and not Path(target_path).is_absolute():
            target_abs = (ROOT_DIR / "database" / target_path).resolve()

        encontrado_no_db = False
        for d, data in todos_croquis:
            if d.resolve() == target_abs:
                a_compilar.append((d, data))
                encontrado_no_db = True
            else:
                a_preservar.append((d, data))
        
        if not encontrado_no_db:
            # Tenta carregar como croqui externo
            data = carregar_um_croqui(target_abs)
            if data:
                print(f"  Alvo externo identificado: {data['id']}")
                a_compilar.append((target_abs, data))
            else:
                raise RuntimeError(f"Alvo '{target_path}' não encontrado ou não é um croqui válido (falta croqui.yaml com 'id').")
    else:
        if not todos_croquis:
            print("Nenhum croqui encontrado em database/. Nada a fazer.")
            return
        a_compilar = todos_croquis

    # 3. Carregar dados do índice anterior antes de (opcionalmente) limpar a pasta
    dados_anteriores = carregar_dados_anteriores(GENERATED_DIR / "indice.binarypb")

    # 4. Preparar pasta gerada (limpa tudo se não houver alvo específico)
    preparar_generated(limpar=(target_path is None))

    # 5. Compilar os selecionados
    compilados_novos, erros = passo_a_compilar_croquis(a_compilar, force_thumbnails=force_thumbnails, gerar_arquivos_de_debug=gerar_arquivos_de_debug, verbose=verbose)

    if erros:
        print("\n" + "!" * 60)
        print("AVISO: O processamento de um ou mais croquis falhou.")
        for msg in erros:
            print(f"\n{msg}")
        print("\n" + "!" * 60 + "\n")
        # Não damos exit aqui para permitir que o índice seja gerado com os croquis que deram certo

    # 6. Identificar o que preservar do índice anterior (caso seja deploy seletivo)
    compilados_preservados = []
    preservados_metadados = []

    if target_path:
        # Em deploy seletivo, preservamos tudo que já estava no índice e não é o alvo novo
        ids_novos = {c[0] for c in compilados_novos}
        for croqui_id, resumo in dados_anteriores.items():
            if croqui_id not in ids_novos:
                # Verifica se os arquivos ainda existem na pasta de saída
                dest_pb = GENERATED_DIR / croqui_id / "compilado.binarypb"
                if dest_pb.exists():
                    preservados_metadados.append(resumo)
                else:
                    print(f"  Aviso: croqui '{croqui_id}' estava no indice anterior mas arquivos sumiram de {GENERATED_DIR}. Removendo do indice.")
    else:
        # No deploy total, o comportamento anterior era preservar o que já estava em generated
        # se viesse do database. Como limpar=True por padrão, isso geralmente é vazio.
        for d, data in a_preservar:
            croqui_id = data["id"]
            dest_pb = GENERATED_DIR / croqui_id / "compilado.binarypb"
            if dest_pb.exists():
                compilados_preservados.append((croqui_id, data, dest_pb))

    # 7. Checksums e Índice
    # Calculamos checksums apenas para o que foi compilado ou preservado via arquivo (não via metadado direto)
    compilados_finais_para_checksum = compilados_novos + compilados_preservados
    
    if not compilados_finais_para_checksum and not preservados_metadados:
        print("Aviso: Nenhum croqui encontrado para compilar ou preservar.")
        # Se for deploy total, talvez seja erro. Se for específico, avisamos.
        if not target_path:
            return
        else:
            raise RuntimeError(f"Nenhum croqui válido encontrado no alvo: {target_path}")

    checksums = passo_b_calcular_checksums(compilados_finais_para_checksum, verbose=verbose)
    indice = passo_c_gerar_indice(
        compilados_finais_para_checksum, 
        checksums, 
        dados_anteriores, 
        preservados=preservados_metadados,
        is_producao=is_producao,
        verbose=verbose
    )

    passo_d_gerar_manifesto_serving(indice, verbose=verbose)

    print(f"\nTotal compilados: {len(compilados_novos)} de {len(a_compilar)}")
    if erros:
        print(f"Total erros: {len(erros)}")
        import sys
        print(f"Ocorreram {len(erros)} erros durante o deploy. Veja os logs acima.")
        sys.exit(1)

def passo_d_gerar_manifesto_serving(indice: indice_pb2.Indice, verbose: bool = False) -> None:
    """
    Passo D: Gera um manifesto YAML (arquivos_serving.yaml) com a lista completa de todos os
    arquivos a serem cacheados pelo CDN e servidos, junto com seus checksums.
    """
    import yaml
    from google.protobuf.json_format import MessageToDict
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated import serving_pb2
    
    if verbose:
        print("\n=== Passo D: Gerando arquivos_serving.yaml ===")
    
    manifesto = serving_pb2.ArquivosServing()
    adicionados = set()
    
    def add_file(rel_path: str, checksum: str):
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
            
        # 2. Lê o compilado para pegar arquivos_externos
        compilado_path = GENERATED_DIR / base / "compilado.binarypb"
        if compilado_path.exists():
            c = croqui_pb2.Croqui()
            c.ParseFromString(compilado_path.read_bytes())
            for ext in c.arquivos_externos:
                add_file(f"{base}/{ext.caminho}", ext.checksum_sha256)
                
        # 3. Calcula para os arquivos de debug gerados, se existirem
        for debug_file in ["compilado.yaml", "compilado.md"]:
            p = GENERATED_DIR / base / debug_file
            if p.exists():
                add_file(f"{base}/{debug_file}", calcular_sha256(p))

    # 4. Calcula para os arquivos globais
    for global_file in ["indice.binarypb", "indice.yaml"]:
        p = GENERATED_DIR / global_file
        if p.exists():
            add_file(global_file, calcular_sha256(p))
            
    dados = MessageToDict(manifesto, preserving_proto_field_name=True)
    manifest_yaml = yaml.dump(dados, sort_keys=False, allow_unicode=True)
    with open(GENERATED_DIR / "arquivos_serving.yaml", "w", encoding="utf-8") as f:
        f.write(manifest_yaml)
    
    if verbose:
        print(f"Manifesto salvo com {len(manifesto.arquivos)} arquivos.")


def atualizar_saude_croquis():
    """Chama o script de saúde dos croquis para atualizar o STATUS_CROQUIS.md."""
    print("\n=== Atualizando saúde dos croquis (STATUS_CROQUIS.md) ===")
    import subprocess
    script_path = ROOT_DIR / "scripts" / "medir_saude_croquis.py"
    try:
        subprocess.run([sys.executable, str(script_path)], check=True)
    except Exception as e:
        print(f"Erro ao atualizar saúde dos croquis: {e}")

def create_parser():
    parser = argparse.ArgumentParser(
        description="Compila todos os croquis (ou um específico) e gera o indice."
    )
    parser.add_argument(
        "croqui_caminho",
        nargs="?",
        default=None,
        help="Caminho opcional para um croqui específico (ex: database/meu_croqui). Se omitido, processa todos.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(ROOT_DIR / "generated"),
        help="Diretorio de saida (padrao: generated/)",
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
        help="Gera arquivos auxiliares .yaml e .md para debug (padrao: True).",
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

    try:
        build.generate_protos()
    except Exception as e:
        print(f"Erro ao gerar protos: {e}")
        sys.exit(1)

    try:
        deploy(
            output_dir, 
            target_path=args.croqui_caminho, 
            force_thumbnails=args.force_thumbnails,
            gerar_arquivos_de_debug=args.arquivos_de_debug,
            is_producao=args.producao,
            verbose=args.verbose
        )
    except RuntimeError as e:
        print(f"\\nDeploy interrompido: {e}")
        sys.exit(1)
    
    if args.status:
        atualizar_saude_croquis()
