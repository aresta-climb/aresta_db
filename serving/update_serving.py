import os
import sys
import boto3
import requests
import subprocess
import glob
from pathlib import Path
from botocore.exceptions import ClientError
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

# Ajusta o sys.path para importar o protobuf gerado da raiz do projeto
sys.path.append(str(Path(__file__).resolve().parent.parent))
from aresta_api.proto.generated import serving_pb2

def get_db_version() -> str:
    base_dir = Path(__file__).resolve().parent.parent / "migracoes"
    max_num = 0
    if base_dir.exists():
        for m in base_dir.glob("*.py"):
            if m.name.endswith("_test.py"): continue
            num_str = "".join(filter(str.isdigit, m.name.split("_")[0]))
            if num_str:
                num = int(num_str)
                if num > max_num: max_num = num
    return f"v{max_num}"

class CloudflarePurger:
    def purge_manifests(self, db_version: str):
        zone_id = os.environ.get("CLOUDFLARE_ZONE_ID")
        api_token = os.environ.get("CLOUDFLARE_CACHE_PURGE_API_TOKEN")

        if not zone_id or not api_token:
            raise ValueError("Credenciais do Cloudflare ausentes (CLOUDFLARE_ZONE_ID ou CLOUDFLARE_CACHE_PURGE_API_TOKEN).")

        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "files": [
                f"https://cdn.aresta.app/{db_version}/indice.binarypb",
                f"https://cdn.aresta.app/{db_version}/arquivos_serving.binarypb"
            ]
        }
        
        print(f"Purgando cache do Cloudflare para os manifestos...")
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        print("Cache purgado com sucesso.")

class Deployer:
    def __init__(self, generated_dir: Path = None):
        self.generated_dir = generated_dir or (Path(__file__).resolve().parent.parent / "generated")
        self.db_version = get_db_version()
        self.bucket = os.environ.get("R2_BUCKET", "aresta")
        
        endpoint = os.environ.get("R2_ENDPOINT_URL")
        if endpoint:
            self.s3 = boto3.client("s3", endpoint_url=endpoint)
        else:
            self.s3 = boto3.client("s3")
            
        self.purger = CloudflarePurger()

    def _get_remote_manifest(self) -> serving_pb2.ArquivosServing:
        key = f"{self.db_version}/arquivos_serving.binarypb"
        try:
            resp = self.s3.get_object(Bucket=self.bucket, Key=key)
            data = resp['Body'].read()
            m = serving_pb2.ArquivosServing()
            m.ParseFromString(data)
            return m
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise e

    def _get_local_manifest(self) -> serving_pb2.ArquivosServing:
        path = self.generated_dir / "arquivos_serving.binarypb"
        # Em blobless clone, precisamos forçar o download primeiro
        try:
            subprocess.run(["git", "checkout", "HEAD", "--", "generated/arquivos_serving.binarypb"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass

        if not path.exists():
            raise FileNotFoundError(f"Manifesto local não encontrado: {path}")
        m = serving_pb2.ArquivosServing()
        m.ParseFromString(path.read_bytes())
        return m

    def _upload_file(self, rel_path: str):
        local_path = self.generated_dir / rel_path
        remote_key = f"{self.db_version}/{rel_path}"
        print(f"Uploading: {rel_path} -> s3://{self.bucket}/{remote_key}")
        
        content_type = "application/octet-stream"
        if rel_path.endswith(".webp"): content_type = "image/webp"
        elif rel_path.endswith(".jpg") or rel_path.endswith(".jpeg"): content_type = "image/jpeg"
        elif rel_path.endswith(".png"): content_type = "image/png"
        elif rel_path.endswith(".md"): content_type = "text/markdown; charset=utf-8"
        elif rel_path.endswith(".yaml") or rel_path.endswith(".yml"): content_type = "text/yaml; charset=utf-8"
            
        self.s3.upload_file(
            str(local_path), 
            self.bucket, 
            remote_key,
            ExtraArgs={'ContentType': content_type}
        )

    def _upload_files_parallel(self, files: list[str]):
        if not files: return
        with ThreadPoolExecutor(max_workers=10) as executor:
            # list() força a execução e levanta eventuais exceções
            list(executor.map(self._upload_file, files))

    def _delete_files_bulk(self, rel_paths: list[str]):
        if not rel_paths: return
        print(f"Deleting {len(rel_paths)} objects via bulk API...")
        objects = [{'Key': f"{self.db_version}/{p}"} for p in rel_paths]
        for i in range(0, len(objects), 1000):
            chunk = objects[i:i+1000]
            self.s3.delete_objects(Bucket=self.bucket, Delete={'Objects': chunk})

    def execute(self):
        remote_manifest = self._get_remote_manifest()
        local_manifest = self._get_local_manifest()

        if not remote_manifest:
            print("=== FALLBACK FULL DEPLOY ===")
            print(f"Manifesto remoto {self.db_version}/arquivos_serving.binarypb não encontrado.")
            print("Executando: git checkout HEAD -- generated/")
            subprocess.run(["git", "checkout", "HEAD", "--", "generated/"], check=True)
            
            paths = [a.caminho_relativo for a in local_manifest.arquivos]
            paths.append("arquivos_serving.binarypb")
            print(f"Enviando {len(paths)} arquivos para R2 em paralelo...")
            self._upload_files_parallel(paths)
        else:
            print("=== DELTA DEPLOY ===")
            remote_map = {a.caminho_relativo: a.checksum_sha256 for a in remote_manifest.arquivos}
            local_map = {a.caminho_relativo: a.checksum_sha256 for a in local_manifest.arquivos}
            
            added = []
            modified = []
            deleted = []
            
            for path, checksum in local_map.items():
                if path not in remote_map:
                    added.append(path)
                elif remote_map[path] != checksum:
                    modified.append(path)
                    
            for path in remote_map.keys():
                if path not in local_map:
                    deleted.append(path)
            
            to_upload = sorted(added + modified)
            if not to_upload and not deleted:
                print("Nenhum arquivo modificado. Deploy pulado.")
                return

            # Inclui o manifesto em to_upload
            if "arquivos_serving.binarypb" not in to_upload:
                to_upload.append("arquivos_serving.binarypb")

            print(f"Adicionados: {len(added)}")
            print(f"Modificados: {len(modified)}")
            print(f"Deletados  : {len(deleted)}")

            checkout_paths = [f"generated/{p}" for p in to_upload]
            if "generated/indice.binarypb" not in checkout_paths:
                checkout_paths.append("generated/indice.binarypb")
                
            checkout_paths.sort()
            print(f"Baixando {len(checkout_paths)} blobs pontuais via git checkout...")
            subprocess.run(["git", "checkout", "HEAD", "--"] + checkout_paths, check=True)
            
            self._upload_files_parallel(to_upload)
            self._delete_files_bulk(sorted(deleted))

        # Purge Cloudflare
        self.purger.purge_manifests(self.db_version)

if __name__ == "__main__":
    d = Deployer()
    d.execute()
