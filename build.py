# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent

# Adiciona o diretório raiz do projeto ao sys.path.
sys.path.append(str(ROOT_DIR))

def generate_protos(force=False):
    # Verifica que todos os arquivos proto existem
    if not (ROOT_DIR / "aresta_api" / "proto").exists():
        print(f"Error: aresta_api/proto not found. Did you clone the aresta_api submodule?")
        sys.exit(1)

    # Chama o build script em um subprocesso limpo para garantir isolamento total
    # e idêntica geração (evitando diferenças de CWD ou sys.path via import)
    argv = ['-f'] if force else []
    script = str(ROOT_DIR / "aresta_api" / "build.py")
    try:
        subprocess.run([sys.executable, script] + argv, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error compiling protos via aresta_api/build.py. Exit code: {e.returncode}")
        sys.exit(e.returncode)


# Benchmark de Performance dos Testes em Paralelo (rodando todos os 253 testes no Windows com 24 threads):
# | Workers | Tempo de Execução | Notas
# | ------- | ----------------- | -----------------------
# | N/A     | 34.17s            | Sequencial (no-parallel)
# | 2       | 22.33s            |
# | 4       | 19.74s            | Capped padrão (ótimo balanço de startup / execução com testmon)
# | 8       | 17.84s            | Sweet spot de velocidade máxima (mas demora mais no testmon)
# | 16      | 17.46s            | Ganho marginal com alta sobrecarga de RAM
# | 24      | 23.33s            | Lento devido ao overhead de spawn de processos no Windows.
def run_tests(testmon=False, parallel=False):
    print("Running all unit and integration tests (core, scripts, editor, migrations)...")
    # Adiciona as pastas de scripts, o submódulo aresta_api, o editor, as migrações, a coleta_de_betas e o teste do próprio build.py
    test_paths = ["scripts", "aresta_api", "editor", "migracoes", "coleta_de_betas", "build_test.py"]
    
    # Also run any tests in tests/ directory if it exists
    if (ROOT_DIR / "tests").exists():
        test_paths.append("tests")
        
    pytest_args = ["--import-mode=importlib"]
    if testmon:
        pytest_args.append("--testmon")
    if parallel:
        import os
        num_workers = min(4, os.cpu_count() or 1)
        pytest_args.extend(["-n", str(num_workers)])
        
    cmd = [sys.executable, "-m", "pytest"] + pytest_args + test_paths
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=False)
    
    # pytest returns 5 if no tests are collected, which is fine initially
    if result.returncode != 0 and result.returncode != 5:
        sys.exit(result.returncode)

def run_coverage():
    print("Running tests with coverage...")
    test_paths = ["scripts", "aresta_api", "editor", "migracoes", "build_test.py"]
    if (ROOT_DIR / "tests").exists():
        test_paths.append("tests")
        
    pytest_args = [
        "--import-mode=importlib",
        "--cov",
        "--cov-report=html:reports/coverage"
    ]
    cmd = [sys.executable, "-m", "pytest"] + pytest_args + test_paths
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=False)
    
    if result.returncode != 0 and result.returncode != 5:
        sys.exit(result.returncode)

def run_deploy():
    print("\nRunning deploy_generated...")
    script_path = ROOT_DIR / "scripts" / "deploy_generated.py"
    subprocess.run([sys.executable, str(script_path)], check=True)

def run_health_check():
    print("\nMeasuring health of croquis...")
    script_path = ROOT_DIR / "scripts" / "medir_saude_croquis.py"
    subprocess.run([sys.executable, str(script_path)], check=True)

def main():
    parser = argparse.ArgumentParser(description="Sistema de Build do Aresta DB.")
    parser.add_argument(
        "cmd", 
        nargs="?", 
        default="tudo",
        choices=["protos", "test", "coverage", "deploy", "saude", "tudo"],
        help="Comando a ser executado (padrão: tudo)"
    )
    parser.add_argument(
        "-f", "--force", 
        action="store_true", 
        help="Força a re-geração dos arquivos do Protobuf e limpa o cache do testmon."
    )
    parser.add_argument(
        "--no-testmon",
        dest="testmon",
        action="store_false",
        default=True,
        help="Desativa a execução incremental (pytest-testmon)."
    )
    parser.add_argument(
        "--parallel",
        dest="parallel",
        action="store_true",
        default=False,
        help="Ativa a paralelização com pytest-xdist."
    )
    parser.add_argument(
        "--drop-cache",
        action="store_true",
        help="Exclui o cache do pytest-testmon (.testmondata)."
    )
    
    args = parser.parse_args()

    # Gerenciamento de cache do pytest-testmon
    if args.force or args.drop_cache:
        testmon_db = ROOT_DIR / ".testmondata"
        if testmon_db.exists():
            print("Removing .testmondata cache...")
            try:
                testmon_db.unlink()
            except Exception as e:
                print(f"Error removing .testmondata: {e}")

    if args.cmd == "protos":
        generate_protos(force=args.force)
    elif args.cmd == "test":
        generate_protos(force=args.force)
        run_tests(testmon=args.testmon, parallel=args.parallel)
    elif args.cmd == "coverage":
        generate_protos(force=args.force)
        run_coverage()
    elif args.cmd == "deploy":
        generate_protos(force=args.force)
        run_deploy()
    elif args.cmd == "saude":
        run_health_check()
    elif args.cmd == "tudo":
        generate_protos(force=args.force)
        run_tests(testmon=args.testmon, parallel=args.parallel)
        run_deploy()


if __name__ == "__main__":
    main()
