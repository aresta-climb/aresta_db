import os
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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

def load_arquivos_serving(content: str) -> dict:
    """
    Faz o parse simplificado do arquivos_serving.yaml usando apenas Python nativo.
    Desse jeito não precisamos de instalar dependências pra rodar o script de deploy.
    """
    res = {}
    current_path = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- caminho_relativo:"):
            current_path = line.split(":", 1)[1].strip()
        elif line.startswith("checksum_sha256:") and current_path:
            res[current_path] = line.split(":", 1)[1].strip()
            current_path = None
    return {"arquivos": [{"caminho_relativo": k, "checksum_sha256": v} for k, v in res.items()]}

class CloudflarePurger:
    def purge_manifests(self, db_version: str):
        zone_id = os.environ.get("CLOUDFLARE_ZONE_ID")
        api_token = os.environ.get("CLOUDFLARE_CACHE_PURGE_API_TOKEN")

        if not zone_id or not api_token:
            raise ValueError("Credenciais do Cloudflare ausentes (CLOUDFLARE_ZONE_ID ou CLOUDFLARE_CACHE_PURGE_API_TOKEN).")

        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
        payload = json.dumps({
            "files": [
                f"https://serving.arestaclimb.com/{db_version}/indice.binarypb",
                f"https://serving.arestaclimb.com/{db_version}/indice.yaml",
                f"https://serving.arestaclimb.com/{db_version}/arquivos_serving.yaml"
            ]
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }, method="POST")
        
        print(f"Purgando cache do Cloudflare para os manifestos...")
        try:
            with urllib.request.urlopen(req) as response:
                print(f"Cache purgado com sucesso. Status: {response.status}")
        except urllib.error.HTTPError as e:
            print(f"Erro ao purgar cache: {e.code} {e.reason}")
            raise

class Deployer:
    def __init__(self, generated_dir: Path = None):
        self.generated_dir = generated_dir or (Path(__file__).resolve().parent.parent / "generated")
        self.db_version = get_db_version()
        self.bucket = os.environ.get("R2_BUCKET")
        self.endpoint = os.environ.get("R2_ENDPOINT_URL")
        self.purger = CloudflarePurger()

    def _aws_cmd(self, *args):
        cmd = ["aws", "s3"] + list(args)
        if self.endpoint:
            cmd.extend(["--endpoint-url", self.endpoint])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)

    def _get_remote_manifest(self) -> dict:
        key = f"{self.db_version}/arquivos_serving.yaml"
        temp_file = "temp_remote_manifest.yaml"
        try:
            self._aws_cmd("cp", f"s3://{self.bucket}/{key}", temp_file)
            with open(temp_file, "r", encoding="utf-8") as f:
                data = f.read()
            os.remove(temp_file)
            return load_arquivos_serving(data)
        except subprocess.CalledProcessError:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return None

    def _get_local_manifest(self) -> dict:
        path = self.generated_dir / "arquivos_serving.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Manifesto local não encontrado: {path}")
        return load_arquivos_serving(path.read_text(encoding="utf-8"))

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
            
        args = ["cp", str(local_path), f"s3://{self.bucket}/{remote_key}", "--content-type", content_type]
        self._aws_cmd(*args)

    def _upload_files_parallel(self, files: list[str]):
        if not files: return
        with ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(self._upload_file, files))

    def _delete_file(self, rel_path: str):
        remote_key = f"{self.db_version}/{rel_path}"
        print(f"Deleting: s3://{self.bucket}/{remote_key}")
        self._aws_cmd("rm", f"s3://{self.bucket}/{remote_key}")

    def _delete_files_bulk(self, files: list[str]):
        if not files: return
        with ThreadPoolExecutor(max_workers=50) as executor:
            list(executor.map(self._delete_file, files))

    def execute(self):
        print(f"Iniciando deploy para banco de dados {self.db_version}")
        
        remote_manifest = self._get_remote_manifest()
        local_manifest = self._get_local_manifest()

        if not remote_manifest:
            print("=== FALLBACK FULL DEPLOY ===")
            print(f"Manifesto remoto {self.db_version}/arquivos_serving.yaml não encontrado.")
            print("Executando: git checkout HEAD -- generated/")
            subprocess.run(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--", "generated/"], check=True)
            
            paths = [item["caminho_relativo"] for item in local_manifest.get("arquivos", [])]
            if "arquivos_serving.yaml" not in paths:
                paths.append("arquivos_serving.yaml")
                
            print(f"Enviando {len(paths)} arquivos para R2 em paralelo...")
            self._upload_files_parallel(paths)
        else:
            print("=== DELTA DEPLOY ===")
            remote_map = {item["caminho_relativo"]: item["checksum_sha256"] for item in remote_manifest.get("arquivos", [])}
            local_map = {item["caminho_relativo"]: item["checksum_sha256"] for item in local_manifest.get("arquivos", [])}

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

            if "arquivos_serving.yaml" not in to_upload:
                to_upload.append("arquivos_serving.yaml")

            print(f"Adicionados: {len(added)}")
            print(f"Modificados: {len(modified)}")
            print(f"Deletados  : {len(deleted)}")

            checkout_paths = [f"generated/{p}" for p in to_upload]
            if "generated/indice.binarypb" not in checkout_paths:
                checkout_paths.append("generated/indice.binarypb")
            checkout_paths.sort()
            
            print(f"Baixando {len(checkout_paths)} blobs pontuais via git checkout...")
            subprocess.run(["git", "checkout", "HEAD", "--ignore-skip-worktree-bits", "--"] + checkout_paths, check=True)
            
            self._upload_files_parallel(to_upload)
            self._delete_files_bulk(sorted(deleted))

        # Purge cached manifest in Cloudflare
        self.purger.purge_manifests(self.db_version)

if __name__ == "__main__":
    d = Deployer()
    d.execute()
