# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
from editor.models.readonly_proxy import ReadOnlyProxy

def test_readonly_proxy_reads_primitive():
    croqui = Croqui(nome="Teste Inicial")
    proxy = ReadOnlyProxy(croqui)
    
    assert proxy.nome == "Teste Inicial", "Leitura de campo primitivo falhou"
    
def test_readonly_proxy_prevents_primitive_assignment():
    croqui = Croqui(nome="Teste Inicial")
    proxy = ReadOnlyProxy(croqui)
    
    with pytest.raises(RuntimeError, match="Proibido alterar o atributo"):
        proxy.nome = "Mutei!"

def test_readonly_proxy_reads_repeated_and_nested():
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    proxy = ReadOnlyProxy(croqui)
    
    assert len(proxy.picos) == 1, "Falha ao ler tamanho de lista"
    assert proxy.picos[0].nome == "Pico 1", "Falha ao ler sub-campo de item iterado"
    
    nomes = [p.nome for p in proxy.picos]
    assert nomes == ["Pico 1"], "Falha ao iterar em repeated proxy"

def test_readonly_proxy_prevents_nested_assignment():
    croqui = Croqui()
    croqui.picos.add(nome="Pico 1")
    proxy = ReadOnlyProxy(croqui)
    
    proxy_pico = proxy.picos[0]
    
    with pytest.raises(RuntimeError, match="Proibido alterar o atributo"):
        proxy_pico.nome = "Tentando Hackear"

def test_readonly_proxy_prevents_list_mutation_methods():
    croqui = Croqui()
    croqui.picos.add(nome="Pico Existente")
    proxy = ReadOnlyProxy(croqui)
    
    # Testar mutadores de RepeatedCompositeFieldContainer e de Python list
    methods = ['add', 'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'sort', 'reverse']
    
    for method in methods:
        with pytest.raises(RuntimeError, match="Proibido chamar"):
            func = getattr(proxy.picos, method)
            # Para métodos que precisam de argumentos, só o fato de chamar ou acessar já deveria estar bloqueado
            # Mas como implementamos o bloqueio no __getattr__ do ReadOnlyListProxy,
            # ele estoura erro no exato momento do getattr
            pass # getattr já levanta a exceção, então se passou da linha acima, a exception funcionou

def test_readonly_proxy_prevents_list_setitem():
    croqui = Croqui()
    croqui.picos.add(nome="Pico Original")
    proxy = ReadOnlyProxy(croqui)
    
    with pytest.raises(RuntimeError, match="Proibido atribuir itens"):
        proxy.picos[0] = Pico(nome="Substitui!")

def test_readonly_proxy_prevents_list_delitem():
    croqui = Croqui()
    croqui.picos.add(nome="Pico Original")
    proxy = ReadOnlyProxy(croqui)
    
    with pytest.raises(RuntimeError, match="Proibido deletar itens"):
        del proxy.picos[0]

def test_readonly_proxy_repeated_scalar():
    croqui = Croqui()
    croqui.creditos.append("Renato")
    
    proxy = ReadOnlyProxy(croqui)
    assert len(proxy.creditos) == 1
    assert proxy.creditos[0] == "Renato"
    
    # Acesso a getattr num método mutador
    with pytest.raises(RuntimeError, match="Proibido chamar 'append'"):
        _ = proxy.creditos.append
        
    with pytest.raises(RuntimeError, match="Proibido atribuir itens"):
        proxy.creditos[0] = "Hakcer"

def test_readonly_proxy_copia_segura():
    from editor.models.readonly_proxy import _copia_segura
    croqui = Croqui(nome="Teste Deep Copy")
    pico = croqui.picos.add(nome="Pico Original")
    proxy = ReadOnlyProxy(croqui)
    
    # 1. Faz a copia
    copia = _copia_segura(proxy)
    
    # 2. Assegura que é uma nova instância de Message (e não um proxy!)
    assert type(copia) == Croqui, "Cópia deve ser o tipo original da mensagem Protobuf"
    assert copia is not croqui, "A cópia deve ser um objeto diferente na memória"
    
    # 3. Assegura que os dados vieram junto
    assert copia.nome == "Teste Deep Copy"
    assert copia.picos[0].nome == "Pico Original"
    
    # 4. Modificar a cópia não deve afetar a original!
    copia.nome = "Alterado"
    copia.picos[0].nome = "Pico Alterado"
    
    assert croqui.nome == "Teste Deep Copy"
    assert croqui.picos[0].nome == "Pico Original"

def test_readonly_list_proxy_copia_segura():
    from editor.models.readonly_proxy import _copia_segura
    croqui = Croqui()
    croqui.picos.add(nome="Pico 1")
    croqui.picos.add(nome="Pico 2")
    
    proxy = ReadOnlyProxy(croqui)
    lista_proxy = proxy.picos
    
    # Faz copia profunda da lista inteira
    lista_copia = _copia_segura(lista_proxy)
    
    assert type(lista_copia) == list, "A cópia da lista deve ser uma lista python"
    assert lista_copia is not croqui.picos, "A cópia não pode ser a lista nativa referenciada em memória!"
    assert len(lista_copia) == 2
    assert type(lista_copia[0]) == Pico
    assert lista_copia[0] is not croqui.picos[0], "Os elementos internos da lista também devem ser instâncias diferentes (deep copy)"
    assert lista_copia[0].nome == "Pico 1"
    
    lista_copia[0].nome = "Hackeado"
    assert croqui.picos[0].nome == "Pico 1"

def test_readonly_proxy_prevents_extension_mutation():
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import ArquivoMarkdown
    md = ArquivoMarkdown(conteudo="# Texto")
    md.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_original = "original.md"
    
    proxy = ReadOnlyProxy(md)
    
    # Acesso de leitura deve funcionar
    assert proxy.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_original == "original.md"
    assert croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo in proxy.Extensions
    
    with pytest.raises(RuntimeError, match="Violação de Arquitetura MVC: Proibido alterar o atributo 'caminho_novo'"):
        proxy.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo = "hackeado.md"
        
    with pytest.raises(RuntimeError, match="Proibido deletar a extensão"):
        del proxy.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo]

