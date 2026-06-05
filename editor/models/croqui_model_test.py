from unittest.mock import MagicMock
from PyQt6.QtCore import QObject
from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
from editor.models.croqui_model import CroquiModel

def test_croqui_model_is_qobject(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    assert isinstance(model, QObject), "CroquiModel deve herdar de QObject para emitir sinais"

def test_croqui_model_obter_readonly_protege_mutacoes(qapp):
    croqui = Croqui(nome="Original")
    pico = croqui.picos.add(nome="Pico Original")
    
    model = CroquiModel(croqui)
    proxy = model.obter_croqui_readonly()
    
    # Leitura funciona
    assert proxy.nome == "Original"
    assert proxy.picos[0].nome == "Pico Original"
    
    import pytest
    with pytest.raises(RuntimeError):
        proxy.nome = "Mutei"
        
    with pytest.raises(RuntimeError):
        proxy.picos[0].nome = "Baguncei"

def test_croqui_model_readonly_reflete_mudancas(qapp):
    croqui = Croqui(nome="Inicial")
    croqui.picos.add(nome="Pico 1")
    
    model = CroquiModel(croqui)
    proxy = model.obter_croqui_readonly()
    
    assert proxy.nome == "Inicial"
    assert proxy.picos[0].nome == "Pico 1"
    
    # Vamos trocar a sub-mensagem por baixo dos panos e mudar dados do croqui
    model._set_primitivo(croqui, "nome", "Novo Nome Modificado")
    
    novo_pico = Pico(nome="Pico 2 (Novo Objeto)")
    model._alterar_repeated_item(croqui, "picos", 0, novo_pico)
    
    # O proxy original que cacheamos no início DEVE conseguir ler os novos dados perfeitamente
    # pois ele sempre busca a referência real no getattr
    assert proxy.nome == "Novo Nome Modificado"
    assert proxy.picos[0].nome == "Pico 2 (Novo Objeto)"

def test_croqui_model_emite_sinal_dado_alterado(qapp):
    croqui = Croqui()
    pico = croqui.picos.add()
    pico.nome = "Antigo"
    
    model = CroquiModel(croqui)
    
    # Mock do slot para ouvir o sinal
    slot_mock = MagicMock()
    model.dado_alterado.connect(slot_mock)
    
    # Executa a mutação encapsulada (acessível apenas via AST a commands/ e models/)
    model._set_primitivo(pico, "nome", "Novo")
    
    # Verifica a mutação no Protobuf
    assert pico.nome == "Novo"
    
    # Verifica a emissão do sinal
    slot_mock.assert_called_once_with(pico, "nome")

def test_croqui_model_adicionar_repeated(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.repeated_adicionado.connect(slot_mock)
    
    novo_pico = Pico(nome="Pico 1")
    model._adicionar_repeated(croqui, "picos", 0, novo_pico)
    
    assert len(croqui.picos) == 1
    assert croqui.picos[0].nome == "Pico 1"
    slot_mock.assert_called_once_with(croqui, "picos", 0)

def test_croqui_model_remover_repeated(qapp):
    croqui = Croqui()
    croqui.picos.add(nome="Pico A")
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.repeated_removido.connect(slot_mock)
    
    model._remover_repeated(croqui, "picos", 0)
    
    assert len(croqui.picos) == 0
    slot_mock.assert_called_once_with(croqui, "picos", 0)

def test_croqui_model_alterar_repeated_item(qapp):
    croqui = Croqui()
    croqui.picos.add(nome="Pico Antigo")
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.repeated_item_alterado.connect(slot_mock)
    
    novo_pico = Pico(nome="Pico Atualizado")
    model._alterar_repeated_item(croqui, "picos", 0, novo_pico)
    
    assert croqui.picos[0].nome == "Pico Atualizado"
    slot_mock.assert_called_once_with(croqui, "picos", 0)

def test_croqui_model_alterar_oneof(qapp):
    from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Antigo"
    
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.oneof_alterado.connect(slot_mock)
    
    grupo_arq = ArquivoGrupo()
    grupo_arq.conteudo.nome = "Grupo Novo"
    model._alterar_oneof(sg, "tipo", "setor", "grupo", grupo_arq)
    
    assert sg.WhichOneof("tipo") == "grupo"
    assert sg.grupo.conteudo.nome == "Grupo Novo"
    slot_mock.assert_called_once_with(sg, "tipo")

def test_croqui_model_carrega_e_salva_arquivos_externos_shadow_state(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    # Setup de arquivos simulados
    db_path = tmp_path / "database"
    db_path.mkdir()
    
    # Arquivo original existente
    (db_path / "setor_teste.md").write_text("---\nnome: 'Setor Teste'\n---\nDescricao setor", encoding="utf-8")
    
    # Cria o Croqui referenciando o arquivo via shadow state manual
    croqui = Croqui()
    p = croqui.picos.add()
    sg = p.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Modificado"
    
    # Simula as extensões preenchidas pelo Editor
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_teste.md"
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_renomeado.md"
    
    model = CroquiModel(croqui)
    
    # Extrai sem depender de dicionários externos
    dict_salvo = model.extrair_arquivos_e_serializar(db_path)
    
    # O dict resultante não deve ter 'conteudo', apenas 'caminho'
    sg_salvo = dict_salvo['picos'][0]['setores_ou_grupos'][0]['setor']
    assert 'caminho' in sg_salvo
    assert 'conteudo' not in sg_salvo
    
    # O caminho deve ser o novo
    assert sg_salvo['caminho'] == "setor_renomeado.md"
    
    # Verifica que o novo arquivo no disco foi criado e atualizado
    caminho_salvo = db_path / "setor_renomeado.md"
    assert caminho_salvo.exists(), "Novo arquivo deveria ter sido criado"
    conteudo_salvo = caminho_salvo.read_text(encoding='utf-8')
    assert "Setor Modificado" in conteudo_salvo
    
    # Verifica que o original foi deletado, afinal mudou de nome
    assert not (db_path / "setor_teste.md").exists(), "Arquivo antigo deveria ter sido deletado"
    
    # Verifica que as extensões do original (em memória) foram atualizadas para o novo caminho
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original == "setor_renomeado.md"
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_renomeado.md"


def test_croqui_model_alterar_repeated_item_message():
    croqui = Croqui()
    p1 = Pico(nome="P1")
    croqui.picos.extend([p1])
    
    model = CroquiModel(croqui)
    proxy = model.obter_croqui_readonly()
    
    p2_proxy = proxy.picos[0] # vamos fingir que p2_proxy é o valor_novo sendo passado
    # na verdade queremos passar um novo proxy de mensagem
    p2 = Pico(nome="P2")
    model2 = CroquiModel(p2) # Criamos um fake model só para pegar um proxy do p2
    p2_proxy_novo = model2.obter_croqui_readonly()
    
    model._alterar_repeated_item(proxy, "picos", 0, p2_proxy_novo)
    
    # Verifica se o nativo foi alterado
    assert croqui.picos[0].nome == "P2"
    # Garante que p2 não foi apenas referenciado, mas copiado (CopyFrom)
    p2.nome = "P2 Alterado"
    assert croqui.picos[0].nome == "P2"

def test_croqui_model_alterar_repeated_item_primitivo():
    croqui = Croqui()
    croqui.creditos.extend(["A"])
    
    model = CroquiModel(croqui)
    proxy = model.obter_croqui_readonly()
    
    # Primitivo não tem proxy, então é passado direto
    model._alterar_repeated_item(proxy, "creditos", 0, "B")
    
    assert croqui.creditos[0] == "B"

def test_croqui_model_alterar_oneof():
    croqui = Croqui()
    pico = Pico(nome="P1")
    croqui.picos.extend([pico])
    sg = croqui.picos[0].setores_ou_grupos.add()
    sg.setor.caminho = "S1.md"
        
    model = CroquiModel(croqui)
        
    # Crio proxy de sg
    proxy_sg = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0]
        
    # Criar um grupo para botar no oneof
    from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo
    grupo = ArquivoGrupo(caminho="G1.md")
    model2 = CroquiModel(grupo)
    grupo_proxy = model2.obter_croqui_readonly()
        
    model._alterar_oneof(proxy_sg, "tipo", "setor", "grupo", grupo_proxy)
        
    # Verifica no original
    assert sg.WhichOneof("tipo") == "grupo"
    assert sg.grupo.caminho == "G1.md"
        
    # Testa alterar pra None (limpar)
    model._alterar_oneof(proxy_sg, "tipo", "grupo", None, None)
    assert sg.WhichOneof("tipo") is None

def test_croqui_model_alterar_oneof_emite_campo_afetado_correto(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    setor = Setor()
    model = CroquiModel(setor)
    
    slot_mock = MagicMock()
    model.oneof_alterado.connect(slot_mock)
    
    # Adiciona campo opcional
    model._alterar_oneof(setor, None, None, "amigavel_a_criancas", True)
    slot_mock.assert_called_with(setor, "amigavel_a_criancas")
    model = CroquiModel(croqui)
    
    # Mock do slot para ouvir o sinal
    slot_mock = MagicMock()
    model.dado_alterado.connect(slot_mock)
    
    # Executa a mutação encapsulada (acessível apenas via AST a commands/ e models/)
    model._set_primitivo(pico, "nome", "Novo")
    
    # Verifica a mutação no Protobuf
    assert pico.nome == "Novo"
    
    # Verifica a emissão do sinal
    slot_mock.assert_called_once_with(pico, "nome")

def test_croqui_model_adicionar_repeated(qapp):
    croqui = Croqui()
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.repeated_adicionado.connect(slot_mock)
    
    novo_pico = Pico(nome="Pico 1")
    model._adicionar_repeated(croqui, "picos", 0, novo_pico)
    
    assert len(croqui.picos) == 1
    assert croqui.picos[0].nome == "Pico 1"
    slot_mock.assert_called_once_with(croqui, "picos", 0)

def test_croqui_model_remover_repeated(qapp):
    croqui = Croqui()
    croqui.picos.add(nome="Pico A")
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.repeated_removido.connect(slot_mock)
    
    model._remover_repeated(croqui, "picos", 0)
    
    assert len(croqui.picos) == 0
    slot_mock.assert_called_once_with(croqui, "picos", 0)

def test_croqui_model_alterar_repeated_item(qapp):
    croqui = Croqui()
    croqui.picos.add(nome="Pico Antigo")
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.repeated_item_alterado.connect(slot_mock)
    
    novo_pico = Pico(nome="Pico Atualizado")
    model._alterar_repeated_item(croqui, "picos", 0, novo_pico)
    
    assert croqui.picos[0].nome == "Pico Atualizado"
    slot_mock.assert_called_once_with(croqui, "picos", 0)

def test_croqui_model_alterar_oneof(qapp):
    from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Antigo"
    
    model = CroquiModel(croqui)
    
    slot_mock = MagicMock()
    model.oneof_alterado.connect(slot_mock)
    
    grupo_arq = ArquivoGrupo()
    grupo_arq.conteudo.nome = "Grupo Novo"
    model._alterar_oneof(sg, "tipo", "setor", "grupo", grupo_arq)
    
    assert sg.WhichOneof("tipo") == "grupo"
    assert sg.grupo.conteudo.nome == "Grupo Novo"
    slot_mock.assert_called_once_with(sg, "tipo")

def test_croqui_model_carrega_e_salva_arquivos_externos_shadow_state(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    # Setup de arquivos simulados
    db_path = tmp_path / "database"
    db_path.mkdir()
    
    # Arquivo original existente
    (db_path / "setor_teste.md").write_text("---\nnome: 'Setor Teste'\n---\nDescricao setor", encoding="utf-8")
    
    # Cria o Croqui referenciando o arquivo via shadow state manual
    croqui = Croqui()
    p = croqui.picos.add()
    sg = p.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor Modificado"
    
    # Simula as extensões preenchidas pelo Editor
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_teste.md"
    sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_renomeado.md"
    
    model = CroquiModel(croqui)
    
    # Extrai sem depender de dicionários externos
    dict_salvo = model.extrair_arquivos_e_serializar(db_path)
    
    # O dict resultante não deve ter 'conteudo', apenas 'caminho'
    sg_salvo = dict_salvo['picos'][0]['setores_ou_grupos'][0]['setor']
    assert 'caminho' in sg_salvo
    assert 'conteudo' not in sg_salvo
    
    # O caminho deve ser o novo
    assert sg_salvo['caminho'] == "setor_renomeado.md"
    
    # Verifica que o novo arquivo no disco foi criado e atualizado
    caminho_salvo = db_path / "setor_renomeado.md"
    assert caminho_salvo.exists(), "Novo arquivo deveria ter sido criado"
    conteudo_salvo = caminho_salvo.read_text(encoding='utf-8')
    assert "Setor Modificado" in conteudo_salvo
    
    # Verifica que o original foi deletado, afinal mudou de nome
    assert not (db_path / "setor_teste.md").exists(), "Arquivo antigo deveria ter sido deletado"
    
    # Verifica que as extensões do original (em memória) foram atualizadas para o novo caminho
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original == "setor_renomeado.md"
    assert sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_renomeado.md"


def test_croqui_model_alterar_repeated_item_message():
    croqui = Croqui()
    p1 = Pico(nome="P1")
    croqui.picos.extend([p1])
    
    model = CroquiModel(croqui)
    proxy = model.obter_croqui_readonly()
    
    p2_proxy = proxy.picos[0] # vamos fingir que p2_proxy é o valor_novo sendo passado
    # na verdade queremos passar um novo proxy de mensagem
    p2 = Pico(nome="P2")
    model2 = CroquiModel(p2) # Criamos um fake model só para pegar um proxy do p2
    p2_proxy_novo = model2.obter_croqui_readonly()
    
    model._alterar_repeated_item(proxy, "picos", 0, p2_proxy_novo)
    
    # Verifica se o nativo foi alterado
    assert croqui.picos[0].nome == "P2"
    # Garante que p2 não foi apenas referenciado, mas copiado (CopyFrom)
    p2.nome = "P2 Alterado"
    assert croqui.picos[0].nome == "P2"

def test_croqui_model_alterar_repeated_item_primitivo():
    croqui = Croqui()
    croqui.creditos.extend(["A"])
    
    model = CroquiModel(croqui)
    proxy = model.obter_croqui_readonly()
    
    # Primitivo não tem proxy, então é passado direto
    model._alterar_repeated_item(proxy, "creditos", 0, "B")
    
    assert croqui.creditos[0] == "B"

def test_croqui_model_alterar_oneof():
    croqui = Croqui()
    pico = Pico(nome="P1")
    croqui.picos.extend([pico])
    sg = croqui.picos[0].setores_ou_grupos.add()
    sg.setor.caminho = "S1.md"
        
    model = CroquiModel(croqui)
        
    # Crio proxy de sg
    proxy_sg = model.obter_croqui_readonly().picos[0].setores_ou_grupos[0]
        
    # Criar um grupo para botar no oneof
    from aresta_api.proto.generated.croqui_pb2 import ArquivoGrupo
    grupo = ArquivoGrupo(caminho="G1.md")
    model2 = CroquiModel(grupo)
    grupo_proxy = model2.obter_croqui_readonly()
        
    model._alterar_oneof(proxy_sg, "tipo", "setor", "grupo", grupo_proxy)
        
    # Verifica no original
    assert sg.WhichOneof("tipo") == "grupo"
    assert sg.grupo.caminho == "G1.md"
        
    # Testa alterar pra None (limpar)
    model._alterar_oneof(proxy_sg, "tipo", "grupo", None, None)
    assert sg.WhichOneof("tipo") is None

def test_croqui_model_alterar_oneof_emite_campo_afetado_correto(qapp):
    from aresta_api.proto.generated.croqui_pb2 import Setor, Croqui
    setor = Setor()
    model = CroquiModel(setor)
    
    slot_mock = MagicMock()
    model.oneof_alterado.connect(slot_mock)
    
    # Adiciona campo opcional
    model._alterar_oneof(setor, None, None, "amigavel_a_criancas", True)
    slot_mock.assert_called_with(setor, "amigavel_a_criancas")
    
    # Remove campo opcional
    model._alterar_oneof(setor, None, "amigavel_a_criancas", None, None)
    slot_mock.assert_called_with(setor, "amigavel_a_criancas")

    # Altera oneof normal
    croqui = Croqui()
    pico = croqui.picos.add()
    sg = pico.setores_ou_grupos.add()
    
    from aresta_api.proto.generated.croqui_pb2 import ArquivoSetor
    arq_setor = ArquivoSetor()
    model2 = CroquiModel(arq_setor)
    arq_setor_proxy = model2.obter_croqui_readonly()

    model._alterar_oneof(sg, "tipo", None, "setor", arq_setor_proxy)
    slot_mock.assert_called_with(sg, "tipo")


def test_croqui_model_mover_repeated(qapp):
    from unittest.mock import MagicMock
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel

    croqui = Croqui()
    croqui.creditos.extend(['A', 'B', 'C'])
    model = CroquiModel(croqui)
    mock_slot = MagicMock()
    model.repeated_movido.connect(mock_slot)

    model._mover_repeated(croqui, 'creditos', 0, 2)
    assert croqui.creditos == ['B', 'C', 'A']
    mock_slot.assert_called_once_with(croqui, 'creditos', 0, 2)

