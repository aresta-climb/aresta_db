# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
from pathlib import Path
import yaml
from aresta_api.proto.generated import beta_pb2
from coleta_de_betas.extrator_vias import extrair_vias_de_croqui, executar_cli_extrair_vias


def criar_croqui_de_teste(diretorio: Path) -> Path:
    """Cria uma estrutura realista de croqui com croqui.yaml e arquivos .md para testes."""
    pico_dir = diretorio / "br_mg_ouro_preto_ouroboulder"
    pico_dir.mkdir(parents=True, exist_ok=True)

    # 1. Arquivo de setor 1 (Boulder)
    md_setor1 = pico_dir / "grupo_1_setor_1.md"
    conteudo_setor1 = """---
# SPDX-License-Identifier: ODbL-1.0
nome: Geriatria
escaladas:
  - boulder:
      nome: Fusca Azul
      grau: V4
  - boulder:
      nome: Prato Feito
      grau: V3
---
Descrição do setor Geriatria.
"""
    md_setor1.write_text(conteudo_setor1, encoding="utf-8")

    # 2. Arquivo de setor 2 (Via Esportiva sem grupo)
    md_setor2 = pico_dir / "setor_avulso.md"
    conteudo_setor2 = """---
# SPDX-License-Identifier: ODbL-1.0
nome: Falésia dos Ventos
escaladas:
  - via_esportiva:
      nome: Brisa Suave
      grau: 7a
---
Descrição da falésia.
"""
    md_setor2.write_text(conteudo_setor2, encoding="utf-8")

    # 3. Arquivo croqui.yaml
    croqui_yaml = pico_dir / "croqui.yaml"
    dados_croqui = {
        "nome": "Ouroboulder",
        "cidade": "Ouro Preto",
        "estado": "MG",
        "pais": "Brasil",
        "picos": [
            {
                "nome": "Pico de São Sebastião",
                "setores_ou_grupos": [
                    {
                        "grupo": {
                            "nome": "Setor Principal",
                            "setores": [
                                {"caminho": "grupo_1_setor_1.md"}
                            ]
                        }
                    },
                    {
                        "setor": {
                            "caminho": "setor_avulso.md"
                        }
                    }
                ]
            }
        ]
    }
    with open(croqui_yaml, "w", encoding="utf-8") as f:
        yaml.dump(dados_croqui, f)

    return pico_dir


def test_extrair_vias_de_croqui(tmp_path: Path):
    """
    Testa a extração completa de vias com metadados geográficos e de escalada.
    """
    pico_dir = criar_croqui_de_teste(tmp_path)

    vias_extraidas = extrair_vias_de_croqui(pico_dir)

    assert vias_extraidas.id_croqui == "br_mg_ouro_preto_ouroboulder"
    assert vias_extraidas.nome_croqui == "Ouroboulder"
    assert vias_extraidas.cidade == "Ouro Preto"
    assert vias_extraidas.estado == "MG"
    assert vias_extraidas.pais == "Brasil"
    assert len(vias_extraidas.escaladas) == 3

    # Valida via 1 (Fusca Azul)
    v1 = vias_extraidas.escaladas[0]
    assert v1.nome == "Fusca Azul"
    assert v1.grau == "V4"
    assert v1.tipo == "boulder"
    assert v1.nome_setor == "Geriatria"
    assert v1.nome_grupo == "Setor Principal"
    assert v1.nome_pico == "Pico de São Sebastião"
    assert v1.cidade == "Ouro Preto"
    assert v1.estado == "MG"
    assert v1.arquivo_origem == "grupo_1_setor_1.md"

    # Valida via 2 (Prato Feito)
    v2 = vias_extraidas.escaladas[1]
    assert v2.nome == "Prato Feito"
    assert v2.grau == "V3"
    assert v2.tipo == "boulder"

    # Valida via 3 (Brisa Suave - sem grupo)
    v3 = vias_extraidas.escaladas[2]
    assert v3.nome == "Brisa Suave"
    assert v3.grau == "7a"
    assert v3.tipo == "via_esportiva"
    assert v3.nome_setor == "Falésia dos Ventos"
    assert v3.nome_grupo == ""
    assert v3.arquivo_origem == "setor_avulso.md"


def test_executar_cli_extrair_vias(tmp_path: Path):
    """
    Testa o comando CLI de extração de vias gerando o arquivo vias_extraidas.yaml no disco.
    """
    pico_dir = criar_croqui_de_teste(tmp_path)
    destino_saida = pico_dir / "vias_extraidas.yaml"

    codigo_retorno = executar_cli_extrair_vias([str(pico_dir)])
    assert codigo_retorno == 0
    assert destino_saida.exists()

    conteudo = destino_saida.read_text(encoding="utf-8")
    assert "Fusca Azul" in conteudo
    assert "Brisa Suave" in conteudo
