# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca para configuração e importação segura de certificados Apple Developer ID no macOS Keychain.
Garante conversão de PKCS#12 modernos (OpenSSL 3 / AES-256 / SHA-256 MAC) para o formato compatível
com o Security.framework do macOS (PBE-SHA1-3DES / SHA-1 MAC), prevenindo a falha:
'security: SecKeychainItemImport: MAC verification failed during PKCS12 import (wrong password?)'.
"""

import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def decodificar_certificado_base64(conteudo_base64: str, destino: Path) -> Path:
    """
    Decodifica o conteúdo Base64 do certificado PKCS#12 (.p12), normalizando
    espaços e quebras de linha para prevenir truncamento de binários.
    """
    try:
        dados_limpos = conteudo_base64.strip().encode("ascii")
        binario = base64.b64decode(dados_limpos)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(binario)
        return destino
    except Exception as e:
        raise ValueError(f"Conteúdo Base64 do certificado PKCS#12 é inválido: {e}") from e


def converter_pkcs12_para_formato_compativel_macos(
    caminho_p12: Path, senha: str, destino: Path | None = None
) -> Path:
    """
    Converte um arquivo PKCS#12 potencialmente gerado por OpenSSL 3.x moderno
    para a cifragem tradicional/legada (PBES2 com 3DES e SHA-1 MAC) aceita
    nativamente pelo utilitário /usr/bin/security do macOS Keychain.
    """
    if destino is None:
        destino = caminho_p12.with_name(f"{caminho_p12.stem}_compat.p12")

    caminho_pem_temp = caminho_p12.with_name(f"{caminho_p12.stem}_temp_unencrypted.pem")

    try:
        # 1. Extrai chaves e certificados em texto claro para arquivo PEM intermediário
        cmd_extrair = [
            "openssl",
            "pkcs12",
            "-in",
            str(caminho_p12),
            "-passin",
            f"pass:{senha}",
            "-nodes",
            "-out",
            str(caminho_pem_temp),
        ]
        try:
            subprocess.run(cmd_extrair, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            msg_erro = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else str(e)
            raise RuntimeError(
                f"Falha ao ler certificado PKCS#12 com OpenSSL (senha incorreta ou arquivo corrompido): {msg_erro}"
            ) from e

        # 2. Reexporta para PKCS#12 usando a cifragem legada suportada pelo Security.framework
        cmd_legacy = [
            "openssl",
            "pkcs12",
            "-export",
            "-in",
            str(caminho_pem_temp),
            "-out",
            str(destino),
            "-passout",
            f"pass:{senha}",
            "-legacy",
            "-certpbe",
            "PBE-SHA1-3DES",
            "-keypbe",
            "PBE-SHA1-3DES",
            "-macalg",
            "sha1",
        ]
        try:
            subprocess.run(cmd_legacy, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Fallback para versões do OpenSSL / LibreSSL que não possuem o provider -legacy
            cmd_fallback = [
                "openssl",
                "pkcs12",
                "-export",
                "-in",
                str(caminho_pem_temp),
                "-out",
                str(destino),
                "-passout",
                f"pass:{senha}",
            ]
            subprocess.run(cmd_fallback, check=True, capture_output=True)

        return destino
    except FileNotFoundError:
        # Caso o binário openssl não esteja disponível no ambiente, utiliza o arquivo original
        return caminho_p12
    finally:
        if caminho_pem_temp.exists():
            try:
                caminho_pem_temp.unlink()
            except OSError:
                pass


def importar_certificado_na_keychain(
    caminho_p12: Path,
    senha_certificado: str,
    nome_keychain: str = "build.keychain",
    senha_keychain: str = "actions",
) -> None:
    """
    Cria e configura a Keychain do macOS, importando o certificado Developer ID
    e autorizando a ferramenta /usr/bin/codesign para assinatura sem prompts interativos.
    """
    # 1. Cria a Keychain dedicada do build
    subprocess.run(
        ["security", "create-keychain", "-p", senha_keychain, nome_keychain],
        check=True,
    )

    # 2. Define a Keychain como padrão do usuário atual
    subprocess.run(
        ["security", "default-keychain", "-s", nome_keychain],
        check=True,
    )

    # 3. Desbloqueia a Keychain para permitir operações
    subprocess.run(
        ["security", "unlock-keychain", "-p", senha_keychain, nome_keychain],
        check=True,
    )

    # 4. Desativa timeout de bloqueio da Keychain durante a execução do runner (6 horas)
    subprocess.run(
        ["security", "set-keychain-settings", "-lut", "21600", nome_keychain],
        check=True,
    )

    # 5. Importa o certificado na Keychain com permissões explícitas de codesign e security
    subprocess.run(
        [
            "security",
            "import",
            str(caminho_p12),
            "-k",
            nome_keychain,
            "-P",
            senha_certificado,
            "-A",
            "-T",
            "/usr/bin/codesign",
            "-T",
            "/usr/bin/security",
        ],
        check=True,
    )

    # 6. Atualiza a lista de partição para evitar janelas de diálogo solicitando senha de acesso à chave
    subprocess.run(
        [
            "security",
            "set-key-partition-list",
            "-S",
            "apple-tool:,apple:,codesign:",
            "-s",
            "-k",
            senha_keychain,
            nome_keychain,
        ],
        check=True,
    )


def configurar_keychain_e_certificado_macos(
    conteudo_p12_base64: str | None = None,
    senha_certificado: str | None = None,
    nome_keychain: str = "build.keychain",
    senha_keychain: str = "actions",
    diretorio_trabalho: Path | None = None,
) -> bool:
    """
    Orquestra a configuração completa da Keychain do macOS a partir das variáveis de ambiente
    ou parâmetros fornecidos, garantindo sanitização e compatibilidade de cifras criptográficas.
    """
    p12_b64 = conteudo_p12_base64 if conteudo_p12_base64 is not None else os.environ.get("APPLE_CERT_P12", "")
    senha_cert = senha_certificado if senha_certificado is not None else os.environ.get("APPLE_CERT_PASSWORD", "")

    if not p12_b64 or not p12_b64.strip():
        print("ℹ️ Certificado Apple Developer ID não configurado, pulando etapa.")
        return False

    with tempfile.TemporaryDirectory(dir=diretorio_trabalho) as temp_dir:
        pasta = Path(temp_dir)
        caminho_orig = pasta / "certificate.p12"
        caminho_compat = pasta / "certificate_compat.p12"

        print("🔑 Decodificando certificado Apple Developer ID...")
        decodificar_certificado_base64(p12_b64, caminho_orig)

        print("🔄 Assegurando formato compatível com Security.framework do macOS...")
        caminho_final = converter_pkcs12_para_formato_compativel_macos(
            caminho_p12=caminho_orig,
            senha=senha_cert,
            destino=caminho_compat,
        )

        print(f"📦 Importando certificado na Keychain '{nome_keychain}'...")
        importar_certificado_na_keychain(
            caminho_p12=caminho_final,
            senha_certificado=senha_cert,
            nome_keychain=nome_keychain,
            senha_keychain=senha_keychain,
        )

        print("✅ Keychain e certificado Apple Developer ID configurados com sucesso.")
        return True


def main() -> int:
    """Ponto de entrada de linha de comando para uso no GitHub Actions."""
    try:
        configurar_keychain_e_certificado_macos()
        return 0
    except Exception as e:
        print(f"❌ Erro fatal ao configurar certificado Apple Developer ID: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
