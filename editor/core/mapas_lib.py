# Copyright (C) 2026 ARESTA
#
# Este arquivo faz parte do Aresta Editor.
# A lógica de manipulação de dados de mapas e POIs.

import os
import io
import ruamel.yaml

def converter_box_para_circulo(pt_dict):
    """
    Calcula a conversão de um dicionário de box para circular.
    
    Args:
        pt_dict (dict): Dicionário contendo as chaves 'box', 'id' e 'label'.
        
    Returns:
        dict: Novo dicionário no formato circular, ou None se 'box' não estiver presente.
    """
    if 'box' not in pt_dict:
        return None
        
    box = pt_dict['box']
    # Média entre comprimento e largura para o diâmetro, raio é metade disso
    r = (box['comprimento'] + box['largura']) / 4.0
    
    return {
        'id': pt_dict.get('id', ''),
        'label': pt_dict.get('label', ''),
        'circular': {
            'x': box['x'],
            'y': box['y'],
            'raio': int(round(r))
        }
    }

class GerenciadorArquivosMapa:
    """
    Gerencia a leitura e escrita de arquivos de mapa (Markdown com YAML Frontmatter).
    """
    
    def __init__(self):
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True

    def ler_arquivo(self, caminho_arquivo):
        """
        Lê um arquivo markdown e separa o YAML do corpo.
        
        Returns:
            tuple: (dados_yaml, corpo_markdown) ou (None, None) se falhar.
        """
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
            partes = conteudo.split('---\n', 2)
            if len(partes) < 3:
                return None, None
                
            dados_yaml = self.yaml.load(partes[1])
            corpo_markdown = partes[2]
            
            return dados_yaml, corpo_markdown
        except Exception:
            return None, None

    def salvar_arquivo(self, caminho_arquivo, dados_yaml, corpo_markdown):
        """
        Salva os dados no formato Markdown com YAML Frontmatter.
        """
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write('---\n')
            buf = io.StringIO()
            self.yaml.dump(dados_yaml, buf)
            f.write(buf.getvalue())
            f.write('---\n' + corpo_markdown)
