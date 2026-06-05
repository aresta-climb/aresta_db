import os
import zipfile
import logging

logger = logging.getLogger(__name__)

def ofuscar_primeiro_byte(caminho_arquivo):
    """
    Inverte o primeiro byte do arquivo usando XOR 0xFF.
    Se o arquivo for um ZIP, isso quebra o magic number 'PK'.
    Esta operação é reversível (aplicar XOR duas vezes volta ao original).
    """
    if not os.path.exists(caminho_arquivo):
        return

    with open(caminho_arquivo, "r+b") as f:
        f.seek(0)
        primeiro_byte = f.read(1)
        if primeiro_byte:
            f.seek(0)
            byte_ofuscado = bytes([primeiro_byte[0] ^ 0xFF])
            f.write(byte_ofuscado)
            f.flush()

def empacotar_croqui(pasta_origem, caminho_destino):
    """
    Compacta uma pasta inteira em um arquivo ZIP e ofusca o magic number.
    """
    logger.info(f"Empacotando croqui de {pasta_origem} para {caminho_destino}")
    
    # 1. Criar o ZIP normalmente
    with zipfile.ZipFile(caminho_destino, 'w', zipfile.ZIP_DEFLATED) as zf:
        for raiz, dirs, arquivos in os.walk(pasta_origem):
            for arquivo in arquivos:
                caminho_completo = os.path.join(raiz, arquivo)
                caminho_relativo = os.path.relpath(caminho_completo, pasta_origem)
                zf.write(caminho_completo, arcname=caminho_relativo)
    
    # 2. Ofuscar o cabeçalho
    ofuscar_primeiro_byte(caminho_destino)
    logger.info("Empacotamento concluído com ofuscação.")

def ler_croqui(caminho_arquivo, pasta_destino):
    """
    Desofusca o arquivo temporariamente, extrai o conteúdo e re-ofusca.
    Também suporta arquivos ZIP normais (sem ofuscação) como fallback.
    """
    logger.info(f"Lendo croqui de {caminho_arquivo} para {pasta_destino}")
    
    with open(caminho_arquivo, "r+b") as f:
        f.seek(0)
        primeiro_byte = f.read(1)
        if not primeiro_byte:
            raise ValueError("Arquivo de croqui vazio.")

        # Tentar detectar se é um ZIP válido antes de mexer
        # Magic number ZIP: 0x50 0x4B (PK)
        e_zip_valido = primeiro_byte == b'P'
        
        try:
            if not e_zip_valido:
                # Se não parece um ZIP, tenta desofuscar
                logger.debug("Arquivo não parece um ZIP, tentando desofuscar.")
                f.seek(0)
                byte_consertado = bytes([primeiro_byte[0] ^ 0xFF])
                f.write(byte_consertado)
                f.flush()

            # Extrair o conteúdo
            # Usamos o próprio objeto de arquivo (f) que agora deve ser um ZIP válido
            f.seek(0)
            with zipfile.ZipFile(f) as zf:
                zf.extractall(pasta_destino)
                logger.info(f"Arquivos extraídos para {pasta_destino}")

        finally:
            if not e_zip_valido:
                # Re-ofuscar apenas se tivermos desofuscado
                logger.debug("Re-ofuscando o arquivo após extração.")
                f.seek(0)
                f.write(primeiro_byte)
                f.flush()
