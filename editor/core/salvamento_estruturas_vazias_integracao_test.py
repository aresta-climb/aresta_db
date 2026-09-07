# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from pathlib import Path
import yaml

from editor.core.storage import GerenciadorCaminhos
from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.core.workspace import ExperimentalWorkspace


@pytest.fixture
def storage_temporario(tmp_path: Path) -> GerenciadorCaminhos:
    storage = GerenciadorCaminhos()
    storage.obter_diretorio_base = lambda: tmp_path / "editor_aresta"
    storage.inicializar_diretorios()
    return storage


def test_salvamento_e_compilacao_com_pico_vazio_e_grupo_sem_setores(storage_temporario: GerenciadorCaminhos) -> None:
    """
    Teste de integração (Princípio V):
    Garante o contrato ponta a ponta de que salvar e compilar um croqui contendo
    um Pico sem setores (lista vazia) e um Grupo sem setores filhos (setores: [])
    ocorre com sucesso, gerando os artefatos de saída sem erros de tipo nulo ('NoneType').
    """
    gerenciador = GerenciadorCroquiExperimental(storage_temporario)
    
    # 1. Cria a estrutura do croqui experimental inicial
    caminho_croqui = gerenciador.criar_novo_croqui(
        id_croqui="br_mg_teste_vazio",
        pico="Pico do Teste",
        estado="MG",
        nome_usuario="Escalador Teste"
    )
    
    caminho_database = caminho_croqui / "database"
    
    # 2. Configura um grupo sem setores (grupo_boulders.md com lista vazia)
    arquivo_grupo = caminho_database / "grupo_boulders.md"
    conteudo_grupo = (
        "---\n"
        "nome: Setores Boulders\n"
        "setores: []\n"
        "---\n"
        "Descrição dos boulders em progresso.\n"
    )
    arquivo_grupo.write_text(conteudo_grupo, encoding="utf-8")
    
    # 3. Configura croqui.yaml contendo:
    #    - Pico 1 com um grupo que ainda não tem setores filhos
    #    - Pico 2 completamente novo e vazio (setores_ou_grupos vazio)
    dados_croqui = {
        "id": "br_mg_teste_vazio",
        "nome": "Croqui Teste Vazio",
        "descricao": "Croqui com estruturas em progresso para teste de integração",
        "picos": [
            {
                "nome": "Pico Principal",
                "estado": "MG",
                "setores_ou_grupos": [
                    {
                        "grupo": {
                            "caminho": "grupo_boulders.md"
                        }
                    }
                ]
            },
            {
                "nome": "Pico Secundário Vazio",
                "estado": "MG",
                "setores_ou_grupos": []
            }
        ]
    }
    
    caminho_yaml = caminho_database / "croqui.yaml"
    with open(caminho_yaml, "w", encoding="utf-8") as f:
        yaml.dump(dados_croqui, f, allow_unicode=True, sort_keys=False)
        
    # 4. Executa a compilação através do ExperimentalWorkspace
    workspace = ExperimentalWorkspace(caminho_croqui)
    
    # QUANDO processar a compilação de salvamento
    caminho_resultado, mensagens_erro = workspace.processar_renomeacao_e_compilacao(
        novo_id="br_mg_teste_vazio",
        id_atual="br_mg_teste_vazio",
        storage=storage_temporario
    )
    
    # ENTÃO a compilação deve ser concluída com sucesso
    assert caminho_resultado == caminho_croqui
    assert not any("erro" in m.lower() for m in mensagens_erro)
    
    # E os arquivos compilados finais devem existir
    caminho_compilado = caminho_croqui / "compilado" / "br_mg_teste_vazio"
    assert (caminho_compilado / "compilado.binarypb").is_file()
    assert (caminho_compilado / "compilado.yaml").is_file()
    assert (caminho_compilado / "compilado.md").is_file()
