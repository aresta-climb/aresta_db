# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

"""
Script para exportar croquis compilados (.binarypb) do Aresta para o formato CSV exigido pelo aplicativo Anchor Ledge.
"""
import argparse
import csv
import os
import re
import sys

# Adiciona o diretório gerado ao PYTHONPATH para conseguir importar o croqui_pb2
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GENERATED_PROTO_DIR = os.path.join(PROJECT_ROOT, 'aresta_api', 'proto', 'generated')
if GENERATED_PROTO_DIR not in sys.path:
    sys.path.insert(0, GENERATED_PROTO_DIR)

try:
    import croqui_pb2
except ImportError as e:
    print(f"Erro ao importar croqui_pb2. Certifique-se de que o protobuf foi compilado. Erro: {e}")
    sys.exit(1)

def converter_graduacao(valor_inteiro, enum_descriptor):
    """
    Converte o valor inteiro do enum GrauVia para a representação em string brasileira formatada.
    
    Args:
        valor_inteiro (int): O valor armazenado no protobuf.
        enum_descriptor: O descritor do enum GrauVia (ex: Croqui.DESCRIPTOR.enum_types_by_name['GrauVia']).
        
    Returns:
        str: A string formatada (ex: '6sup'), ou vazio se não encontrado.
    """
    if valor_inteiro not in enum_descriptor.values_by_number:
        return ''
        
    valor = enum_descriptor.values_by_number[valor_inteiro]
    nome = valor.name
    
    if not nome.startswith('BR_'):
        return ''
        
    # Remove prefixo BR_
    nome = nome[3:]
    # Troca _BARRA_ por /
    nome = nome.replace('_BARRA_', '/')
    # Para minúsculas
    nome = nome.lower()
    
    return nome

def extrair_ano_abertura(data_abertura):
    """
    Extrai o ano da data de abertura. A data de abertura deve vir no formato YYYY ou YYYY-MM ou YYYY-MM-DD.
    Essa função tenta identificar o ano (4 dígitos) utilizando regex, flexibilizando
    a possibilidade de ser no formato DD/MM/YYYY caso o usuário insira errado.
    
    Args:
        data_abertura (str): String contendo a data.
        
    Returns:
        str: String contendo apenas os 4 dígitos do ano, ou vazio se não encontrar.
    """
    if not data_abertura:
        return ''
        
    # Tenta padrão YYYY... (ex: 1994, 1994-06)
    match_yyyy = re.match(r'^(\d{4})', data_abertura)
    if match_yyyy:
        return match_yyyy.group(1)
        
    # Tenta padrão DD/MM/YYYY
    match_dd_mm = re.search(r'(\d{4})$', data_abertura)
    if match_dd_mm:
        return match_dd_mm.group(1)
        
    return ''

def extrair_ano_manutencao(data_manutencao):
    """
    Extrai o ano da data de manutenção. A data de manutenção deve vir no formato DD/MM/YYYY.
    Essa função tenta identificar o ano (4 dígitos) utilizando regex, flexibilizando
    a possibilidade de ser no formato YYYY-MM-DD.
    
    Args:
        data_manutencao (str): String contendo a data.
        
    Returns:
        str: String contendo apenas os 4 dígitos do ano, ou vazio se não encontrar.
    """
    if not data_manutencao:
        return ''
        
    # Tenta padrão DD/MM/YYYY (pega os 4 dígitos do final)
    match_dd_mm = re.search(r'(\d{4})$', data_manutencao)
    if match_dd_mm:
        return match_dd_mm.group(1)
        
    # Tenta padrão YYYY... (pega os 4 primeiros dígitos)
    match_yyyy = re.match(r'^(\d{4})', data_manutencao)
    if match_yyyy:
        return match_yyyy.group(1)
        
    return ''

def mapear_estrelas(destaque):
    """
    Mapeia a flag de destaque para a quantidade de estrelas (3 se True, 0 se False).
    
    Args:
        destaque (bool): Flag indicando se é destaque.
        
    Returns:
        str: '3' ou '0'.
    """
    return '3' if destaque else '0'

def determinar_status_e_material(tipo_via):
    """
    Determina o status e material baseado na string do oneof `tipo`.
    
    Args:
        tipo_via (str): A string representando qual oneof está preenchido (ex: 'via_esportiva', 'via_movel', 'projeto').
        
    Returns:
        tuple: (status, boltMaterial)
    """
    status = 'OPEN'
    bolt_material = ''
    
    if tipo_via == 'projeto':
        status = 'CLOSED'
    elif tipo_via == 'via_esportiva':
        bolt_material = 'UNKNOWN'
    elif tipo_via == 'via_movel':
        bolt_material = 'TRAD'
        
    return status, bolt_material


def processar_croqui(croqui_id, database_dir='generated'):
    """
    Lê um compilado.binarypb, extrai todas as vias e exporta para CSV no formato Anchor Ledge.
    
    Args:
        croqui_id (str): O ID do croqui (ex: br_mg_lagoa_santa_gruta_da_lapinha).
        database_dir (str): O diretório base onde os gerados ficam.
    """
    proto_path = os.path.join(PROJECT_ROOT, database_dir, croqui_id, 'compilado.binarypb')
    
    if not os.path.exists(proto_path):
        print(f"Erro: Arquivo compilado não encontrado em {proto_path}")
        return
        
    croqui = croqui_pb2.Croqui()
    with open(proto_path, 'rb') as f:
        croqui.ParseFromString(f.read())
        
    enum_grau = croqui_pb2.GrauVia.DESCRIPTOR.enum_types_by_name.get('GrauVia')
    if not enum_grau:
        print("Erro: Enum GrauVia não encontrado no proto.")
    
    routes = []
    
    # 1. Pré-processar os IDs dos mapas
    map_ids_por_escalada = {}
    for pico in croqui.picos:
        if pico.HasField('mapas_gerais') and pico.mapas_gerais.HasField('conteudo'):
            for mapa in pico.mapas_gerais.conteudo.mapas:
                for ref in mapa.referencias:
                    if getattr(ref, 'escalada', '') and getattr(ref, 'ids', []):
                        map_ids_por_escalada[ref.escalada] = ref.ids[0]
                        
        for setor_grupo in pico.setores_ou_grupos:
            if setor_grupo.HasField('setor'):
                setor_arq = setor_grupo.setor
                if not setor_arq.HasField('conteudo'):
                    continue
                setor = setor_arq.conteudo
                for mapa in setor.mapas:
                    for ref in mapa.referencias:
                        if getattr(ref, 'escalada', '') and getattr(ref, 'ids', []):
                            map_ids_por_escalada[ref.escalada] = ref.ids[0]
                            
    # 2. Processar vias
    for pico in croqui.picos:
        for setor_grupo in pico.setores_ou_grupos:
            if setor_grupo.HasField('setor'):
                setor_arq = setor_grupo.setor
                if not setor_arq.HasField('conteudo'):
                    continue
                setor = setor_arq.conteudo
                sector_name = setor.nome
                
                for escalada in setor.escaladas:
                    tipo_via = escalada.WhichOneof('tipo')
                    if not tipo_via:
                        continue
                        
                    dados_via = getattr(escalada, tipo_via)
                    
                    name = dados_via.nome
                    route_id = map_ids_por_escalada.get(name, '')
                    
                    # Graduação
                    grade = ''
                    if hasattr(dados_via, 'dificuldade') and enum_grau:
                        grade = converter_graduacao(dados_via.dificuldade, enum_grau)
                        
                    height = str(dados_via.extensao) if getattr(dados_via, 'extensao', 0) > 0 else ''
                    bolts = str(dados_via.quantidade_protecoes_intermediarias) if getattr(dados_via, 'quantidade_protecoes_intermediarias', 0) > 0 else ''
                    
                    first_ascent = ", ".join(dados_via.conquistadores) if getattr(dados_via, 'conquistadores', None) else ""
                    
                    fa_year = extrair_ano_abertura(getattr(dados_via, 'data_abertura', ''))
                    rebolted = extrair_ano_manutencao(getattr(dados_via, 'data_manutencao', ''))
                    
                    stars = mapear_estrelas(getattr(dados_via, 'destaque', False))
                    
                    status, bolt_material = determinar_status_e_material(tipo_via)
                    
                    description = getattr(dados_via, 'descricao', '')
                    
                    routes.append({
                        'id': route_id,
                        'name': name,
                        'grade': grade,
                        'height': height,
                        'bolts': bolts,
                        'stars': stars,
                        'firstAscent': first_ascent,
                        'faYear': fa_year,
                        'boltMaterial': bolt_material,
                        'anchorMaterial': '',
                        'rebolted': rebolted,
                        'safeUntil': '',
                        'status': status,
                        'description': description,
                        'latitude': '',
                        'longitude': '',
                        'areaId': croqui_id,
                        'sectorId': sector_name,
                        'subsectorId': ''
                    })
                    
    output_file = f"export_{croqui_id}.csv"
    fieldnames = [
        'id', 'name', 'grade', 'height', 'bolts', 'stars', 'firstAscent', 'faYear', 
        'boltMaterial', 'anchorMaterial', 'rebolted', 'safeUntil', 'status', 
        'description', 'latitude', 'longitude', 'areaId', 'sectorId', 'subsectorId'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for route in routes:
            writer.writerow(route)
            
    print(f"Exportadas {len(routes)} vias para {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Exporta Croqui Aresta para CSV Anchor Ledge')
    parser.add_argument('croqui_id', help='ID do croqui (ex: br_mg_lagoa_santa_gruta_da_lapinha)')
    args = parser.parse_args()
    processar_croqui(args.croqui_id)
