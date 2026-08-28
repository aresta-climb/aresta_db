# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from unittest.mock import MagicMock
from PySide6.QtCore import QObject
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


def test_croqui_model_salva_setores_dentro_de_grupo(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    import yaml

    db_path = tmp_path / "database"
    db_path.mkdir()

    croqui = Croqui()
    p = croqui.picos.add()
    sg = p.setores_ou_grupos.add()
    
    sg.grupo.conteudo.nome = "Grupo Teste"
    sg.grupo.Extensions[croqui_pb2.ArquivoGrupo.ext_metadados_arquivo].caminho_original = "grupo_teste.md"
    sg.grupo.Extensions[croqui_pb2.ArquivoGrupo.ext_metadados_arquivo].caminho_novo = "grupo_teste.md"

    # Add a Setor inside the Grupo
    setor_interno = sg.grupo.conteudo.setores.add()
    setor_interno.conteudo.nome = "Setor Interno"
    setor_interno.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_interno.md"
    setor_interno.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_interno.md"

    model = CroquiModel(croqui)
    dict_salvo = model.extrair_arquivos_e_serializar(db_path)

    # 1. Verifica no grupo (retornado na raiz serializada)
    sg_salvo = dict_salvo['picos'][0]['setores_ou_grupos'][0]['grupo']
    assert 'caminho' in sg_salvo
    assert 'conteudo' not in sg_salvo

    # 2. Verifica os arquivos criados
    caminho_grupo = db_path / "grupo_teste.md"
    assert caminho_grupo.exists()
    
    caminho_setor = db_path / "setor_interno.md"
    assert caminho_setor.exists()

    # 3. Verifica o conteúdo do arquivo do grupo
    with open(caminho_grupo, "r", encoding="utf-8") as f:
        content = f.read()
        parts = content.split("---")
        yaml_grupo = yaml.safe_load(parts[1])
        
        # O grupo não deve ter o 'conteudo' do setor, apenas o 'caminho'
        assert "setores" in yaml_grupo
        setor_serializado = yaml_grupo["setores"][0]
        assert "caminho" in setor_serializado
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


def test_croqui_model_carrega_e_salva_arquivos_externos_shadow_state(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo
    from editor.models.croqui_model import CroquiModel
    import yaml

    db_path = tmp_path / "database"
    db_path.mkdir()
    
    # ... create dummy file ...
    caminho_setor = db_path / "setor_teste.md"
    caminho_setor.write_text("---\nnome: 'Setor Teste'\n---\nDescricao setor", encoding="utf-8")
    
    croqui = Croqui()
    p = croqui.picos.add()
    sg = p.setores_ou_grupos.add()
    sg.setor.caminho = "setor_teste.md"
    
    model = CroquiModel(croqui)
    model.carregar_arquivos_externos(db_path)
    
    # 1. Verifica se o shadow_state do Setor foi populado corretamente
    assert sg.setor.HasExtension(croqui_pb2.ArquivoSetor.ext_metadados_arquivo)
    ext = sg.setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo]
    assert ext.caminho_original == "setor_teste.md"
    assert ext.caminho_novo == "setor_teste.md"
    import json
    assert json.loads(ext.dados_json_originais) == {"nome": "Setor Teste"}
    
    # Muda o caminho e simula salvamento
    ext.caminho_novo = "setor_renomeado.md"
    dict_salvo = model.extrair_arquivos_e_serializar(db_path)
    
    # O arquivo antigo deve ter sido deletado
    assert not (db_path / "setor_teste.md").exists()
    assert (db_path / "setor_renomeado.md").exists()


def test_croqui_model_salva_setores_dentro_de_grupo(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    import yaml

    db_path = tmp_path / "database"
    db_path.mkdir()

    croqui = Croqui()
    p = croqui.picos.add()
    sg = p.setores_ou_grupos.add()
    
    sg.grupo.conteudo.nome = "Grupo Teste"
    sg.grupo.Extensions[croqui_pb2.ArquivoGrupo.ext_metadados_arquivo].caminho_original = "grupo_teste.md"
    sg.grupo.Extensions[croqui_pb2.ArquivoGrupo.ext_metadados_arquivo].caminho_novo = "grupo_teste.md"

    # Add a Setor inside the Grupo
    setor_interno = sg.grupo.conteudo.setores.add()
    setor_interno.conteudo.nome = "Setor Interno"
    setor_interno.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_original = "setor_interno.md"
    setor_interno.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo = "setor_interno.md"

    model = CroquiModel(croqui)
    dict_salvo = model.extrair_arquivos_e_serializar(db_path)

    # 1. Verifica no grupo (retornado na raiz serializada)
    sg_salvo = dict_salvo['picos'][0]['setores_ou_grupos'][0]['grupo']
    assert 'caminho' in sg_salvo
    assert 'conteudo' not in sg_salvo

    # 2. Verifica os arquivos criados
    caminho_grupo = db_path / "grupo_teste.md"
    assert caminho_grupo.exists()
    
    caminho_setor = db_path / "setor_interno.md"
    assert caminho_setor.exists()

    # 3. Verifica o conteúdo do arquivo do grupo
    with open(caminho_grupo, "r", encoding="utf-8") as f:
        content = f.read()
        parts = content.split("---")
        yaml_grupo = yaml.safe_load(parts[1])
        
        # O grupo não deve ter o 'conteudo' do setor, apenas o 'caminho'
        assert "setores" in yaml_grupo
        setor_serializado = yaml_grupo["setores"][0]
        assert "caminho" in setor_serializado
        assert setor_serializado["caminho"] == "setor_interno.md"
        assert "conteudo" not in setor_serializado
        assert "ext_metadados_arquivo" not in setor_serializado

    # 4. Verifica o conteúdo do arquivo do setor
    with open(caminho_setor, "r", encoding="utf-8") as f:
        content = f.read()
        parts = content.split("---")
        yaml_setor = yaml.safe_load(parts[1])
        
        assert yaml_setor["nome"] == "Setor Interno"
        assert "ext_metadados_arquivo" not in yaml_setor

def test_croqui_model_preserva_ordem_dos_campos(tmp_path):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo
    
    # DADO um arquivo YAML em disco com uma ordem peculiar de campos e dicionários aninhados (escaladas)
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    caminho_setor = db_path / "setor_ordem.md"
    caminho_setor.write_text("---\n"
                             "sinal_de_celular: true\n"
                             "nome: 'A Nome'\n"
                             "amigavel_a_bebes: false\n"
                             "escaladas:\n"
                             "  - boulder:\n"
                             "      nome: 'Meu Boulder'\n"
                             "---\n"
                             "Corpo markdown", encoding="utf-8")

    croqui = Croqui()
    pico = Pico(nome="Pico 1")
    sg = SetorOuGrupo()
    sg.setor.caminho = "setor_ordem.md"
    pico.setores_ou_grupos.append(sg)
    croqui.picos.append(pico)

    from editor.models.croqui_model import CroquiModel
    model = CroquiModel(croqui)
    model.carregar_arquivos_externos(db_path)

    # Injetamos um campo novo no meio da raiz e do boulder
    sg_real = croqui.picos[0].setores_ou_grupos[0]
    sg_real.setor.conteudo.amigavel_a_criancas = True
    sg_real.setor.conteudo.escaladas[0].boulder.data_abertura = "2024"

    # QUANDO salvamos de volta
    model.extrair_arquivos_e_serializar(db_path)

    texto_salvo = caminho_setor.read_text(encoding="utf-8")
    import yaml
    parts = texto_salvo.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])

    chaves = list(frontmatter.keys())
    # Os originais mantém a ordem. O novo campo vai pro fim.
    assert chaves[:3] == ["sinal_de_celular", "nome", "amigavel_a_bebes"]
    assert "amigavel_a_criancas" in chaves[3:]
    
    # A ordem aninhada das chaves de boulder deve ter sido mantida recursivamente
    boulder_keys = list(frontmatter["escaladas"][0]["boulder"].keys())
    assert boulder_keys[:1] == ["nome"]
    assert "data_abertura" in boulder_keys[1:]

def test_croqui_model_nao_vaza_extensoes_no_croqui_raiz(tmp_path):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico
    from editor.models.croqui_model import CroquiModel
    
    croqui = Croqui(id="meu-croqui", descricao="Teste")
    croqui.picos.append(Pico(nome="Pico Root"))
    
    # Injetamos a extensão no Root, fingindo que foi carregado com metadados do editor
    from aresta_api.proto.generated import croqui_pb2
    ext = croqui.Extensions[croqui_pb2.Croqui.ext_metadados_arquivo]
    ext.caminho_original = "teste"
    ext.dados_json_originais = '{"autor": "João", "id": "meu-croqui"}'
    
    model = CroquiModel(croqui)
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    
    resultado = model.extrair_arquivos_e_serializar(db_path)
    
    # A extensão NÂO pode vazar pro dicionário serializado
    assert "ext_metadados_arquivo" not in resultado
    assert "[aresta.MetadadosArquivoNoEditor]" not in resultado
    
    import yaml
    # Simula o dump que ocorreria no deploy
    yaml_dump = yaml.dump(resultado)
    assert "ext_metadados" not in yaml_dump

def test_croqui_model_preserva_ordem_croqui_raiz(tmp_path):
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    import json
    
    dict_original = {
        "id": "meu-croqui",
        "nome": "Meu Croqui",
        "botoes": [
            {
                "destino": {
                    "url": "http://google.com"
                },
                "texto": "Botao 1"
            }
        ],
        "picos": [
            {
                "url_google_maps": "http://maps.com",
                "nome": "Pico Root"
            }
        ]
    }
    
    from google.protobuf.json_format import ParseDict
    croqui_msg = ParseDict(dict_original, Croqui(), ignore_unknown_fields=True)
    
    from aresta_api.proto.generated import croqui_pb2
    ext = croqui_msg.Extensions[croqui_pb2.Croqui.ext_metadados_arquivo]
    ext.dados_json_originais = json.dumps(dict_original, ensure_ascii=False)
    
    model = CroquiModel(croqui_msg)
    
    croqui_msg.picos[0].descricao = "Adicionado pelo UI"
    
    # Serializa de volta simulando salvar
    db_path = tmp_path / "database"
    resultado = model.extrair_arquivos_e_serializar(db_path)
    
    chaves_raiz = list(resultado.keys())
    assert chaves_raiz[:4] == ["id", "nome", "botoes", "picos"]
    
    chaves_botao = list(resultado["botoes"][0].keys())
    assert chaves_botao == ["destino", "texto"]
    
    chaves_pico = list(resultado["picos"][0].keys())
    assert chaves_pico[:2] == ["url_google_maps", "nome"]
    assert "descricao" in chaves_pico[2:]

def test_croqui_model_preserva_ordem_grupo(tmp_path):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo
    
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    caminho_grupo = db_path / "grupo_ordem.md"
    caminho_grupo.write_text("---\n"
                             "nome: 'Grupo 1'\n"
                             "mapas:\n"
                             "  - largura_mapa: 100\n"
                             "    caminho_imagem_mapa: 'img.webp'\n"
                             "---\n"
                             "Corpo markdown", encoding="utf-8")

    croqui = Croqui()
    pico = Pico(nome="Pico 1")
    sg = SetorOuGrupo()
    sg.grupo.caminho = "grupo_ordem.md"
    pico.setores_ou_grupos.append(sg)
    croqui.picos.append(pico)

    from editor.models.croqui_model import CroquiModel
    model = CroquiModel(croqui)
    model.carregar_arquivos_externos(db_path)

    sg_real = croqui.picos[0].setores_ou_grupos[0]
    sg_real.grupo.conteudo.localizacao_escalada.latitude = -10
    sg_real.grupo.conteudo.localizacao_escalada.longitude = -20

    model.extrair_arquivos_e_serializar(db_path)

    import yaml
    texto_salvo = caminho_grupo.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(texto_salvo.split("---", 2)[1])

    chaves_grupo = list(frontmatter.keys())
    assert chaves_grupo[:2] == ["nome", "mapas"]
    assert "localizacao_escalada" in chaves_grupo[2:]
    
    chaves_mapa = list(frontmatter["mapas"][0].keys())
    assert chaves_mapa == ["largura_mapa", "caminho_imagem_mapa"]

def test_croqui_model_preserva_formatacao_corpo_markdown(tmp_path):
    from aresta_api.proto.generated.croqui_pb2 import Croqui, Pico, SetorOuGrupo
    
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    caminho_setor = db_path / "setor_corpo.md"
    
    # Arquivo original SEM linha em branco antes do corpo, e SEM linha em branco no final
    conteudo_original = "---\nnome: 'Setor 1'\n---\nMeu corpo markdown"
    caminho_setor.write_text(conteudo_original, encoding="utf-8")

    croqui = Croqui()
    pico = Pico(nome="Pico 1")
    sg = SetorOuGrupo()
    sg.setor.caminho = "setor_corpo.md"
    pico.setores_ou_grupos.append(sg)
    croqui.picos.append(pico)

    from editor.models.croqui_model import CroquiModel
    model = CroquiModel(croqui)
    model.carregar_arquivos_externos(db_path)

    # Modificamos o YAML apenas
    sg_real = croqui.picos[0].setores_ou_grupos[0]
    sg_real.setor.conteudo.sinal_de_celular = True

    model.extrair_arquivos_e_serializar(db_path)

    texto_salvo = caminho_setor.read_text(encoding="utf-8")
    
    # Não deve ter linha extra antes do corpo, nem linha extra no final
    assert "---" in texto_salvo
    partes = texto_salvo.split("---")
    corpo = partes[-1]
    
    assert corpo == "\nMeu corpo markdown"


def test_croqui_model_carrega_arquivo_mapas(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel

    db_path = tmp_path / "database"
    db_path.mkdir()
    
    caminho_mapas = db_path / "mapas_gerais.md"
    caminho_mapas.write_text("---\nmapas:\n  - caminho_imagem_mapa: 'mapa1.webp'\n---\n", encoding="utf-8")
    
    croqui = Croqui()
    p = croqui.picos.add()
    p.mapas_gerais.caminho = "mapas_gerais.md"
    
    model = CroquiModel(croqui)
    model.carregar_arquivos_externos(db_path)
    
    assert p.mapas_gerais.HasExtension(croqui_pb2.ArquivoMapas.ext_metadados_arquivo)
    ext = p.mapas_gerais.Extensions[croqui_pb2.ArquivoMapas.ext_metadados_arquivo]
    assert ext.caminho_original == "mapas_gerais.md"
    
    # Must have populated 'conteudo'
    assert not p.mapas_gerais.HasField("caminho")
    assert p.mapas_gerais.HasField("conteudo")
    assert len(p.mapas_gerais.conteudo.mapas) == 1
    assert p.mapas_gerais.conteudo.mapas[0].caminho_imagem_mapa == "mapa1.webp"


def test_croqui_model_extrai_arquivo_mapas(tmp_path):
    from aresta_api.proto.generated import croqui_pb2
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    from editor.models.croqui_model import CroquiModel
    import yaml

    db_path = tmp_path / "database"
    db_path.mkdir()

    croqui = Croqui()
    p = croqui.picos.add()
    
    p.mapas_gerais.conteudo.mapas.add().caminho_imagem_mapa = "mapa_salvo.webp"
    p.mapas_gerais.Extensions[croqui_pb2.ArquivoMapas.ext_metadados_arquivo].caminho_original = "mapas_gerais.md"
    p.mapas_gerais.Extensions[croqui_pb2.ArquivoMapas.ext_metadados_arquivo].caminho_novo = "mapas_gerais.md"

    model = CroquiModel(croqui)
    dict_salvo = model.extrair_arquivos_e_serializar(db_path)

    assert "mapas_gerais" in dict_salvo['picos'][0]
    assert dict_salvo['picos'][0]['mapas_gerais']['caminho'] == "mapas_gerais.md"

    # The file must have been created
    caminho_mapas = db_path / "mapas_gerais.md"
    assert caminho_mapas.exists()
    
    with open(caminho_mapas, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f.read().split("---")[1])
        assert len(dados["mapas"]) == 1
        assert dados["mapas"][0]["caminho_imagem_mapa"] == "mapa_salvo.webp"

def test_salvar_croqui_quotes_string_digits(tmp_path):
    croqui = Croqui()
    pico = croqui.picos.add(nome="Pico 1")
    sg = pico.setores_ou_grupos.add()
    mapa = sg.setor.conteudo.mapas.add(caminho_imagem_mapa="mapa.webp")
    poi = mapa.pontos_de_interesse.add()
    poi.id = "09"
    poi.label = "10"
    
    model = CroquiModel(croqui)
    model.extrair_arquivos_e_serializar(tmp_path)
    
    caminho_yaml = tmp_path / "setor_.md"
    with open(caminho_yaml, "r", encoding="utf-8") as f:
        conteudo = f.read()
        assert "id: '09'" in conteudo, "ID composto apenas por digitos deve ter aspas"
        assert "label: '10'" in conteudo, "Label composto apenas por digitos deve ter aspas"


def test_buffer_imagens_em_memoria_emite_sinal_imagem_alterada(tmp_path):
    croqui = Croqui()
    model = CroquiModel(croqui)
    model.definir_caminho_db(tmp_path)

    slot_alteracao = MagicMock()
    model.imagem_alterada.connect(slot_alteracao)

    # 1. Definir imagem emite sinal
    model.definir_imagem_memoria("imagens/mapa1.webp", b"bytes1")
    slot_alteracao.assert_called_once_with("imagens/mapa1.webp")

    # 2. Remover imagem emite sinal
    slot_alteracao.reset_mock()
    model.remover_imagem_memoria("imagens/mapa1.webp")
    slot_alteracao.assert_called_once_with("imagens/mapa1.webp")


def test_buffer_imagens_em_memoria(tmp_path):
    croqui = Croqui()
    model = CroquiModel(croqui)
    model.definir_caminho_db(tmp_path)

    # 1. Obter imagem inexistente retorna None
    assert model.obter_bytes_imagem("imagens/inexistente.webp") is None

    # 2. Gravar no buffer em RAM
    dados_ram = b"conteudo_ram"
    model.definir_imagem_memoria("imagens/foto.webp", dados_ram)
    assert model.obter_bytes_imagem("imagens/foto.webp") == dados_ram
    assert model.obter_imagens_em_memoria() == {"imagens/foto.webp": dados_ram}

    # 3. Remover do buffer em RAM
    model.remover_imagem_memoria("imagens/foto.webp")
    assert model.obter_bytes_imagem("imagens/foto.webp") is None

    # 4. Fallback para o disco
    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir(parents=True, exist_ok=True)
    (pasta_img / "disco.webp").write_bytes(b"conteudo_disco")

    assert model.obter_bytes_imagem("imagens/disco.webp") == b"conteudo_disco"

    # 5. Prioridade da RAM sobre o disco
    model.definir_imagem_memoria("imagens/disco.webp", b"sobreposicao_ram")
    assert model.obter_bytes_imagem("imagens/disco.webp") == b"sobreposicao_ram"

    # 6. Limpar buffer
    model.limpar_imagens_em_memoria()
    assert model.obter_bytes_imagem("imagens/disco.webp") == b"conteudo_disco"


def test_extrair_arquivos_e_serializar_grava_imagens_em_memoria(tmp_path):
    croqui = Croqui()
    croqui.caminho_thumbnail = "imagens/thumbnail.webp"
    model = CroquiModel(croqui)

    model.definir_imagem_memoria("imagens/thumbnail.webp", b"bytes_thumbnail_salvo")
    model.extrair_arquivos_e_serializar(tmp_path)

    arquivo_gravado = tmp_path / "imagens" / "thumbnail.webp"
    assert arquivo_gravado.exists()
    assert arquivo_gravado.read_bytes() == b"bytes_thumbnail_salvo"


def test_extrair_arquivos_e_serializar_salva_com_quebras_lf(tmp_path):
    croqui = Croqui(nome="Croqui Teste LF")
    pico = croqui.picos.add(nome="Pico Teste")
    sg = pico.setores_ou_grupos.add()
    sg.setor.conteudo.nome = "Setor A"
    sg.setor.conteudo.descricao = "Linha 1\r\nLinha 2\r\nLinha 3"

    botao = croqui.botoes.add(texto="Capa")
    botao.destino.secao_textual.conteudo = "# Titulo\r\n\r\nCorpo do texto\r\n"

    model = CroquiModel(croqui)
    model.extrair_arquivos_e_serializar(tmp_path)

    for arq in tmp_path.rglob("*.md"):
        bytes_conteudo = arq.read_bytes()
        assert b"\r\n" not in bytes_conteudo, f"Arquivo {arq.name} contém CRLF (\\r\\n), esperado apenas LF (\\n)"


