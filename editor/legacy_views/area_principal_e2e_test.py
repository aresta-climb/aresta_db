import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from editor.legacy_views.area_principal import JanelaPrincipal
import yaml

def _get_id(obj):
    return obj.obter_id_nativo() if hasattr(obj, 'obter_id_nativo') else id(obj)

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_salvar_croqui_extrai_arquivos_wrapper(tmp_path, qapp):
    # Setup database dir and croqui.yaml
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    
    croqui_yaml = {
        "id": "test_croqui",
        "nome": "Test Croqui",
        "picos": [
            {
                "id": "pico_1",
                "nome": "Pico 1",
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "conteudo": {
                                "nome": "Setor Novo"
                            }
                        }
                    }
                ]
            }
        ]
    }
    with open(db_path / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump(croqui_yaml, f)
        
    from editor.core.workspace import ExperimentalWorkspace
    janela = JanelaPrincipal(workspace=ExperimentalWorkspace(tmp_path))
    
    # We must explicitly set the croqui_msg on the editor_dados mock 
    # to test the extraction logic, or trigger _extrair_arquivos_externos.
    from google.protobuf.json_format import ParseDict
    from aresta_api.proto.generated.croqui_pb2 import Croqui
    croqui_msg = ParseDict(croqui_yaml, Croqui(), ignore_unknown_fields=True)
    from editor.models.croqui_model import CroquiModel
    from editor.controllers.croqui_controller import CroquiController
    janela.croqui_model = CroquiModel(croqui_msg)
    janela.croqui_controller = CroquiController(janela.croqui_model, janela.historico.obter_pilha())
    janela.pagina_dados.carregar_dados(janela.croqui_model, janela.croqui_controller)
    
    from PyQt6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    janela.salvamento_finalizado.connect(loop.quit)
    janela.salvar_croqui()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    
    with open(db_path / "croqui.yaml", "r", encoding="utf-8") as f:
        saved_yaml = yaml.safe_load(f)
        
    setor_saved = saved_yaml['picos'][0]['setores_ou_grupos'][0]['setor']
    assert 'conteudo' not in setor_saved
    assert 'caminho' in setor_saved
    assert setor_saved['caminho'] == 'setor_setor_novo.md'
    
    assert (db_path / 'setor_setor_novo.md').exists()


def test_carregar_croqui_carrega_conteudos_externos(tmp_path, qapp):
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    
    # 1. Escreve arquivo do setor com frontmatter e corpo
    setor_content = """---
nome: Setor de Teste
localizacao_estacionamento:
  latitude: -200000000
  longitude: -400000000
---
Descrição detalhada do setor de teste.
"""
    with open(db_path / "setor_teste.md", "w", encoding="utf-8") as f:
        f.write(setor_content)
        
    # 2. Escreve arquivo de seção textual (doc_capa.md)
    capa_content = """# Capa Principal
Texto da capa do croqui.
"""
    with open(db_path / "doc_capa.md", "w", encoding="utf-8") as f:
        f.write(capa_content)
        
    # 3. Escreve croqui.yaml referenciando os caminhos
    croqui_yaml = {
        "id": "test_croqui",
        "nome": "Test Croqui",
        "botoes": [
            {
                "texto": "Capa Principal",
                "destino": {
                    "secao_textual": {
                        "caminho": "doc_capa.md"
                    }
                }
            }
        ],
        "picos": [
            {
                "id": "pico_1",
                "nome": "Pico 1",
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "caminho": "setor_teste.md"
                        }
                    }
                ]
            }
        ]
    }
    with open(db_path / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump(croqui_yaml, f)
        
    from editor.core.workspace import ExperimentalWorkspace
    janela = JanelaPrincipal(workspace=ExperimentalWorkspace(tmp_path))
    janela.carregar_croqui()
    
    croqui_msg = janela.pagina_dados.editor_dados.croqui
    
    # Verifica resolução em memória do Markdown
    assert "Capa Principal" in croqui_msg.botoes[0].destino.secao_textual.conteudo
    
    # Verifica resolução em memória do Setor
    setor_msg = croqui_msg.picos[0].setores_ou_grupos[0].setor.conteudo
    assert setor_msg.nome == "Setor de Teste"
    assert "Descrição detalhada" in setor_msg.descricao
        
    # Verifica que os mapeamentos de nomes de arquivo foram povoados usando as extensions
    from aresta_api.proto.generated import croqui_pb2
    assert croqui_msg.botoes[0].destino.secao_textual.Extensions[croqui_pb2.ArquivoMarkdown.ext_metadados_arquivo].caminho_novo == "doc_capa.md"
    
    assert croqui_msg.picos[0].setores_ou_grupos[0].setor.Extensions[croqui_pb2.ArquivoSetor.ext_metadados_arquivo].caminho_novo == "setor_teste.md"


def test_salvar_croqui_com_renomeacao_de_arquivos(tmp_path, qapp):
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    
    # Escreve arquivo original do setor
    setor_content = """---
nome: Setor de Teste
---
Corpo original.
"""
    with open(db_path / "setor_teste.md", "w", encoding="utf-8") as f:
        f.write(setor_content)
        
    croqui_yaml = {
        "id": "test_croqui",
        "nome": "Test Croqui",
        "picos": [
            {
                "id": "pico_1",
                "nome": "Pico 1",
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "caminho": "setor_teste.md"
                        }
                    }
                ]
            }
        ]
    }
    with open(db_path / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump(croqui_yaml, f)
        
    from editor.core.workspace import ExperimentalWorkspace
    janela = JanelaPrincipal(workspace=ExperimentalWorkspace(tmp_path))
    janela.carregar_croqui()
    
    croqui_msg = janela.pagina_dados.editor_dados.croqui
    setor_msg = croqui_msg.picos[0].setores_ou_grupos[0].setor.conteudo
    
    # Renomeia o arquivo na extension usando o CmdAlterarMetadadosCaminhoNovo
    from editor.commands.comandos_protobuf import CmdAlterarMetadadosCaminhoNovo
    from aresta_api.proto.generated import croqui_pb2
    wrapper = croqui_msg.picos[0].setores_ou_grupos[0].setor
    ext_desc = croqui_pb2.ArquivoSetor.ext_metadados_arquivo
    
    cmd = CmdAlterarMetadadosCaminhoNovo(janela.croqui_model, wrapper, ext_desc, wrapper.Extensions[ext_desc].caminho_novo, "setor_novo.md")
    janela.croqui_controller.undo_stack.push(cmd)
    
    # Salva
    from PyQt6.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    janela.salvamento_finalizado.connect(loop.quit)
    janela.salvar_croqui()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    
    # O arquivo antigo deve ter sido excluído e o novo deve ter sido criado
    assert not (db_path / "setor_teste.md").exists()
    assert (db_path / "setor_novo.md").exists()
    
    # O YAML do croqui deve estar apontando para o novo caminho
    with open(db_path / "croqui.yaml", "r", encoding="utf-8") as f:
        saved_yaml = yaml.safe_load(f)
    assert saved_yaml['picos'][0]['setores_ou_grupos'][0]['setor']['caminho'] == 'setor_novo.md'
    
    # Em memória, a mensagem ativa continua intacta
    assert croqui_msg.picos[0].setores_ou_grupos[0].setor.conteudo.nome == "Setor de Teste"


def test_carregamento_aplica_migracoes_automaticamente(tmp_path, qapp):
    db_path = tmp_path / "database"
    db_path.mkdir(parents=True)
    
    # 1. Escreve arquivo de seção textual (doc_capa.md)
    capa_content = """# Capa Principal
Texto da capa do croqui.
"""
    with open(db_path / "doc_capa.md", "w", encoding="utf-8") as f:
        f.write(capa_content)
        
    # 2. Escreve croqui.yaml legada (sem ultima_migracao, com secoes_textuais)
    croqui_yaml = {
        "id": "legacy_croqui",
        "nome": "Legacy Croqui",
        "secoes_textuais": [
            {
                "titulo": "Capa Principal",
                "caminho": "doc_capa.md"
            }
        ]
    }
    with open(db_path / "croqui.yaml", "w", encoding="utf-8") as f:
        yaml.dump(croqui_yaml, f)
        
    # 3. Abre a janela e carrega o croqui
    from editor.core.workspace import ExperimentalWorkspace
    janela = JanelaPrincipal(workspace=ExperimentalWorkspace(tmp_path))
    janela.carregar_croqui()
    
    # 4. Verifica se os dados em memória e no arquivo foram migrados com sucesso
    croqui_msg = janela.pagina_dados.editor_dados.croqui
    assert len(croqui_msg.botoes) == 1
    assert croqui_msg.botoes[0].texto == "Capa Principal"
    assert "Capa Principal" in croqui_msg.botoes[0].destino.secao_textual.conteudo

    with open(db_path / "croqui.yaml", "r", encoding="utf-8") as f:
        dados_yaml = yaml.safe_load(f)
    assert "secoes_textuais" not in dados_yaml
    assert "botoes" in dados_yaml
    assert dados_yaml["ultima_migracao"] >= 1




def test_e2e_selecao_mapa_por_node_path(tmp_path, qapp):
    from PyQt6.QtCore import Qt
    import yaml
    db_path = tmp_path / 'database'
    db_path.mkdir(parents=True)
    croqui_yaml = {'picos': [{'setores_ou_grupos': [{'setor': {'conteudo': {'mapas': [{'caminho_imagem_mapa': 'mapa_1.webp'}, {'caminho_imagem_mapa': 'mapa_2.webp'}]}}}]}]}
    with open(db_path / 'croqui.yaml', 'w', encoding='utf-8') as fw:
        yaml.dump(croqui_yaml, fw)
    from editor.core.workspace import ExperimentalWorkspace
    janela = JanelaPrincipal(workspace=ExperimentalWorkspace(tmp_path))
    janela.carregar_croqui()
    list_widget = janela.pagina_mapas.editor.list_widget
    uri = "page:mapas/node:Croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0/node:Setor/expando:mapas/item:1"
    
    janela.stack.setCurrentIndex(0)
    janela.croqui_model.notificar_foco_requisitado(uri)
    assert janela.stack.currentIndex() == 2
    item_selecionado = list_widget.currentItem()
    assert item_selecionado is not None
    assert item_selecionado.text() == 'mapa_2.webp'
    assert janela.pagina_mapas.editor.dados_atuais['mapa_idx'] == 1
