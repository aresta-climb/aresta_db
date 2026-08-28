# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para geração e empacotamento de croquis experimentais fora do ambiente gráfico (headless).
Segue estritamente os princípios do repositório (Tudo em Português).
"""

import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import pygit2
import yaml

from scripts.deploy_generated import deploy
from editor.core.croqui_format import empacotar_croqui

def _criar_croqui_experimental_yaml(id_croqui: str, yaml_path: Path) -> None:
    """
    Cria o arquivo croqui_experimental.yaml com os metadados necessários.
    
    Args:
        id_croqui: Identificador da montanha/croqui (nome da pasta original).
        yaml_path: Caminho de saída do arquivo yaml.
    """
    dados = {
        "id_original": id_croqui,
        "timestamp_criacao": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "autor": "Aresta CLI",
        "versao_formato": "1.0",
        "baseado_no_commit": "HEAD"
    }
    with open(yaml_path, "w", encoding="utf-8", newline="\n") as f:
        yaml_str = yaml.dump(dados, sort_keys=False, allow_unicode=True)
        f.write(yaml_str.replace("\r\n", "\n"))


def empacotar_databases_para_croqui(db_paths: list[Path], output_dir: Path) -> Path:
    """
    Dada uma lista de pastas database (ex: database/pico_do_lopo), compila os dados, 
    cria a estrutura temporária do formato croqui experimental (git, metadados),
    e empacota o resultado num zip ofuscado (com XOR 0xFF).
    
    Args:
        db_paths: Lista de caminhos para as pastas dos croquis no database.
        output_dir: Diretório de saída onde o arquivo .croqui será depositado.
        
    Returns:
        Caminho final para o arquivo .croqui gerado.
    """
    if not db_paths:
        raise ValueError("Nenhuma pasta fornecida para empacotar.")
        
    ids_croquis = []
    caminhos_resolvidos = []
    
    for db_path in db_paths:
        p = Path(db_path).resolve()
        if not p.exists() or not p.is_dir():
            raise FileNotFoundError(f"A pasta informada não existe: {p}")
        caminhos_resolvidos.append(p)
        ids_croquis.append(p.name)

    id_croqui = ",".join(ids_croquis)[:100] # Limita o tamanho caso sejam muitos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_pasta = f"{timestamp}_modificados"
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        raiz_croqui = tmp_path / nome_pasta
        raiz_croqui.mkdir()
        
        # 1. Cria croqui_experimental.yaml
        _criar_croqui_experimental_yaml(id_croqui, raiz_croqui / "croqui_experimental.yaml")
        
        # 2. Inicializa repositório Git
        pygit2.init_repository(str(raiz_croqui), False)
        
        # 3. Copia as bases de dados e monta lista de targets pro deploy
        targets = []
        for db_path in caminhos_resolvidos:
            destino_db = raiz_croqui / "database" / db_path.name
            shutil.copytree(db_path, destino_db)
            targets.append(str(destino_db))
        
        # 4. Executa o deploy_generated apontando o output para a pasta compilado
        pasta_compilado = raiz_croqui / "compilado"
        pasta_compilado.mkdir()
        
        deploy(
            output_dir=pasta_compilado,
            target_paths=targets,
            force_thumbnails=False,
            gerar_arquivos_de_debug=False,
            is_producao=False,
            verbose=False
        )
        
        # 5. Empacota com ofuscação usando a lib do editor
        output_dir.mkdir(parents=True, exist_ok=True)
        arquivo_final = output_dir / f"{nome_pasta}.croqui"
        
        empacotar_croqui(str(raiz_croqui), str(arquivo_final))
        
        return arquivo_final
