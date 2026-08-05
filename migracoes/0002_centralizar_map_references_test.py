# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

# Copyright (C) 2026 ARESTA
#
# Este arquivo é livre; você pode redistribuí-lo e/ou modificá-lo
# sob os termos da Licença Pública Geral GNU.

import importlib.util
from pathlib import Path

# Carrega a migração dinamicamente devido à restrição de nomes começando com números em imports Python
caminho_migracao = Path(__file__).resolve().parent / "0002_centralizar_map_references.py"
spec = importlib.util.spec_from_file_location("migracao_0002", str(caminho_migracao))
migracao_modulo = importlib.util.module_from_spec(spec)
# Nós só damos load do spec na hora do teste se o arquivo existir, mas como TDD pede o teste primeiro, 
# vamos colocar dentro de um try/except e mockar temporariamente para o pytest rodar e falhar, ou
# assumir que o arquivo vazio já existe.
# Para o TDD funcionar bem, o arquivo 0002_centralizar_map_references.py precisa ser criado.
# Mas a execução será feita dentro dos tests.
try:
    spec.loader.exec_module(migracao_modulo)
    migrar = migracao_modulo.migrar
except FileNotFoundError:
    def migrar(croqui_dir):
        raise NotImplementedError("Implemente a migração 0002")

def test_migrar_setor_com_escaladas(tmp_path):
    # DADO um arquivo de setor com escaladas usando id_no_mapa antigo
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    # Criamos o arquivo croqui.yaml
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    # Criamos um arquivo de setor
    setor_path = db_path / "setor_principal.md"
    setor_path.write_text("""---
nome: Setor Principal
mapas:
  - largura_mapa: 1000
    caminho_imagem_mapa: img.webp
    pontos_de_interesse:
      - id: "1"
      - id: "a"
      - id: "b"
      - id: "2"
escaladas:
  - via_esportiva:
      nome: Via 1
      id_no_mapa: "1"
      id_no_mapa_meio: "1a"
      id_no_mapa_fim: "1b"
  - boulder:
      nome: Boulder A
      id_no_mapa: "2"
---
Corpo markdown
""", encoding="utf-8")

    # QUANDO executamos a migração
    migrar(db_path)

    # ENTÃO os campos antigos devem ter sumido e a Referencia criada no mapa
    texto_migrado = setor_path.read_text(encoding="utf-8")
    import yaml
    frontmatter = yaml.safe_load(texto_migrado.split("---", 2)[1])

    # Verifica o mapa
    assert "referencias" in frontmatter["mapas"][0]
    refs = frontmatter["mapas"][0]["referencias"]
    assert len(refs) == 2
    
    # Verifica a referencia da Via 1
    assert refs[0]["escalada"] == "Via 1"
    assert refs[0]["ids"] == ["1", "a", "b"]

    # Verifica a referencia do Boulder A
    assert refs[1]["escalada"] == "Boulder A"
    assert refs[1]["ids"] == ["2"]

    # Verifica que os ids foram removidos das escaladas
    escaladas = frontmatter["escaladas"]
    assert "id_no_mapa" not in escaladas[0]["via_esportiva"]
    assert "id_no_mapa_meio" not in escaladas[0]["via_esportiva"]
    assert "id_no_mapa_fim" not in escaladas[0]["via_esportiva"]
    assert "id_no_mapa" not in escaladas[1]["boulder"]


def test_migrar_setor_com_id_no_proprio_setor(tmp_path):
    # DADO um setor que possui id_no_mapa (ele aparece num mapa do grupo)
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    # Arquivo de grupo com o mapa
    grupo_path = db_path / "grupo_geral.md"
    grupo_path.write_text("""---
nome: Grupo Geral
mapas:
  - largura_mapa: 1000
    caminho_imagem_mapa: img.webp
    pontos_de_interesse:
      - id: "S"
      - id: "1"
setores:
  - arquivo_setor:
      caminho: setor_a.md
---
""", encoding="utf-8")

    # Arquivo do setor com o id_no_mapa
    setor_path = db_path / "setor_a.md"
    setor_path.write_text("""---
nome: Setor A
id_no_mapa: "S1"
---
""", encoding="utf-8")

    # QUANDO executamos a migração
    migrar(db_path)

    # ENTÃO
    import yaml
    front_grupo = yaml.safe_load(grupo_path.read_text(encoding="utf-8").split("---", 2)[1])
    front_setor = yaml.safe_load(setor_path.read_text(encoding="utf-8").split("---", 2)[1])

    assert "id_no_mapa" not in front_setor

    refs = front_grupo["mapas"][0]["referencias"]
    assert len(refs) == 1
    assert refs[0]["setor"] == "Setor A"
    assert refs[0]["ids"] == ["S", "1"]
    
def test_preserva_comentarios_ruamel(tmp_path):
    # Teste para garantir a premissa de RoundTrip do ruamel.yaml
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor_comentado.md"
    setor_path.write_text("""---
nome: Comentado
# Comentario do mapa
mapas:
  - largura_mapa: 1000 # Inline
    caminho_imagem_mapa: img.webp
    pontos_de_interesse:
      - id: "1"
escaladas:
  # Via legal
  - via_esportiva:
      nome: Via
      id_no_mapa: "1"
---
""", encoding="utf-8")

    migrar(db_path)

    texto_migrado = setor_path.read_text(encoding="utf-8")
    assert "# Comentario do mapa" in texto_migrado
    assert "# Inline" in texto_migrado
    assert "# Via legal" in texto_migrado
    assert "referencias:" in texto_migrado
    assert "id_no_mapa" not in texto_migrado


def test_migrar_inline_escaladas_in_croqui_yaml(tmp_path):
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    (db_path / "croqui.yaml").write_text("""id: teste
ultima_migracao: 1
picos:
  - nome: Pico 1
    mapas:
      - largura_mapa: 1000
        pontos_de_interesse:
          - id: "1"
    setores_ou_grupos:
      - setor:
          conteudo:
            nome: Setor Inline
            escaladas:
              - via_esportiva:
                  nome: Via 1
                  id_no_mapa: "1"
""", encoding="utf-8")
    
    migrar(db_path)
    
    import yaml
    croqui_yaml = yaml.safe_load((db_path / "croqui.yaml").read_text(encoding="utf-8"))
    
    refs = croqui_yaml["picos"][0]["mapas"][0]["referencias"]
    assert len(refs) == 1
    assert refs[0]["escalada"] == "Via 1"
    assert refs[0]["ids"] == ["1"]
    
    escaladas = croqui_yaml["picos"][0]["setores_ou_grupos"][0]["setor"]["conteudo"]["escaladas"]
    assert "id_no_mapa" not in escaladas[0]["via_esportiva"]

def test_migrar_inline_setores_in_grupo_md(tmp_path):
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    grupo_path = db_path / "grupo_geral.md"
    grupo_path.write_text("""---
nome: Grupo Geral
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "A"
setores:
  - conteudo:
      nome: Setor Inline
      escaladas:
        - boulder:
            nome: Boulder A
            id_no_mapa: "A"
---
""", encoding="utf-8")

    migrar(db_path)
    
    import yaml
    front_grupo = yaml.safe_load(grupo_path.read_text(encoding="utf-8").split("---", 2)[1])
    
    refs = front_grupo["mapas"][0]["referencias"]
    assert len(refs) == 1
    assert refs[0]["escalada"] == "Boulder A"
    assert refs[0]["ids"] == ["A"]
    
    escaladas = front_grupo["setores"][0]["conteudo"]["escaladas"]
    assert "id_no_mapa" not in escaladas[0]["boulder"]

def test_migrar_setor_multiplos_mapas_simples(tmp_path):
    # DADO um setor com múltiplos mapas que contém os pontos da escalada
    # QUANDO o id_no_mapa não tem barra (/)
    # ENTÃO a referência deve ser copiada para TODOS os mapas que possuam os pontos
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor_multi.md"
    setor_path.write_text("""---
nome: Setor Multi
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "1"
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "1"
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "2"
escaladas:
  - via_esportiva:
      nome: Via 1
      id_no_mapa: "1"
---
""", encoding="utf-8")

    migrar(db_path)

    import yaml
    frontmatter = yaml.safe_load(setor_path.read_text(encoding="utf-8").split("---", 2)[1])
    
    # Mapa 0 deve ter a via 1
    assert "referencias" in frontmatter["mapas"][0]
    assert frontmatter["mapas"][0]["referencias"][0]["escalada"] == "Via 1"
    
    # Mapa 1 deve ter a via 1
    assert "referencias" in frontmatter["mapas"][1]
    assert frontmatter["mapas"][1]["referencias"][0]["escalada"] == "Via 1"
    
    # Mapa 2 NÃO deve ter a via 1 (pois não tem o ponto "1")
    assert "referencias" not in frontmatter["mapas"][2]


def test_migrar_setor_distribuicao_estrita_barra(tmp_path):
    # DADO um setor com múltiplos mapas e id_no_mapa contendo barra (/)
    # ENTÃO deve seguir a distribuição estrita pelo índice do mapa
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor_barra.md"
    setor_path.write_text("""---
nome: Setor Barra
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "A"
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "B"
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "C"
escaladas:
  - boulder:
      nome: Boulder Barra
      id_no_mapa: "A/C"
---
""", encoding="utf-8")

    migrar(db_path)

    import yaml
    frontmatter = yaml.safe_load(setor_path.read_text(encoding="utf-8").split("---", 2)[1])
    
    # Grupo 0 ("A") testa contra mapa 0 -> Sucesso
    assert "referencias" in frontmatter["mapas"][0]
    assert frontmatter["mapas"][0]["referencias"][0]["ids"] == ["A"]
    
    # Grupo 1 ("C") testa contra mapa 1 -> Falha (mapa 1 tem "B")
    assert "referencias" not in frontmatter["mapas"][1]
    
    # Mapa 2 tem "C", mas o grupo 1 já foi pro mapa 1. O array tinha tamanho 2.
    assert "referencias" not in frontmatter["mapas"][2]
    
    # Verifica que "C" foi pro nao encontrados
    nao_enc_path = db_path / "ids_no_mapa_nao_encontrados.yaml"
    assert nao_enc_path.exists()
    nao_enc = yaml.safe_load(nao_enc_path.read_text(encoding="utf-8"))
    assert any(x["escalada"] == "Boulder Barra" and x["ids_procurados"] == "C" for x in nao_enc)


def test_migrar_parse_alfanumerico(tmp_path):
    # DADO um id_no_mapa contendo letras e números misturados (ex: "2B")
    # ENTÃO ele deve ser quebrado em ["2", "B"]
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor_alfa.md"
    setor_path.write_text("""---
nome: Setor Alfa
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "2"
      - id: "B"
escaladas:
  - via_esportiva:
      nome: Via 2B
      id_no_mapa: "2B"
---
""", encoding="utf-8")

    migrar(db_path)

    import yaml
    frontmatter = yaml.safe_load(setor_path.read_text(encoding="utf-8").split("---", 2)[1])
    
    assert frontmatter["mapas"][0]["referencias"][0]["ids"] == ["2", "B"]


def test_migrar_geracao_nao_encontrados_yaml(tmp_path):
    # DADO um id que falha parcialmente ou totalmente
    # ENTÃO o id é removido da via e um YAML de erro é gerado
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor_falha.md"
    setor_path.write_text("""---
nome: Setor Falha
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "1"
escaladas:
  - via_esportiva:
      nome: Via Falha Parcial
      id_no_mapa: "1"
      id_no_mapa_fim: "A"
  - boulder:
      nome: Boulder Inexistente
      id_no_mapa: "99"
  - boulder:
      nome: Boulder Inexistente
      id_no_mapa: "99"
  - boulder:
      nome: Boulder Vazio
      id_no_mapa: ""
---
""", encoding="utf-8")

    migrar(db_path)

    import yaml
    frontmatter = yaml.safe_load(setor_path.read_text(encoding="utf-8").split("---", 2)[1])
    
    # Nenhuma referencia deve ser criada, pois uma falha parcialmente e outra totalmente
    assert "referencias" not in frontmatter["mapas"][0]
    
    nao_enc_path = db_path / "ids_no_mapa_nao_encontrados.yaml"
    assert nao_enc_path.exists()
    nao_enc = yaml.safe_load(nao_enc_path.read_text(encoding="utf-8"))
    
    assert len(nao_enc) == 3
    assert nao_enc[0]["escalada"] == "Via Falha Parcial"
    assert nao_enc[0]["ids_procurados"] == "1/A"
    
    assert nao_enc[1]["escalada"] == "Boulder Inexistente"
    assert nao_enc[1]["ids_procurados"] == "99"
    
    assert nao_enc[2]["escalada"] == "Boulder Vazio"
    assert nao_enc[2]["ids_procurados"] == ""

def test_migrar_edge_cases_cobertura(tmp_path):
    # DADO um yaml com múltiplos edge cases (enfiadas, setores profundos, mapas inline falhando)
    # ENTÃO a migração cobre todos os ramos
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    # croqui com mapas inline, mas que referenciam um ponto inexistente
    (db_path / "croqui.yaml").write_text("""id: teste
ultima_migracao: 1
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "EXISTE"
escaladas:
  - via_multiplas_enfiadas:
      nome: Via Multi
      id_no_mapa: "INEXISTENTE"
      enfiadas:
        - via_esportiva:
            nome: Enfiada 1
            id_no_mapa: "EXISTE"
setores:
  - conteudo:
      nome: Setor Profundo
      grupo:
        conteudo:
          nome: Grupo Profundo
          escaladas:
            - via_tradicional:
                nome: Trad
                id_no_mapa: "TAMBEM_NAO"
""", encoding="utf-8")

    # setor com id que também falha
    setor_path = db_path / "setor_maluco.md"
    setor_path.write_text("""---
nome: Setor Maluco
setores:
  - arquivo_setor:
      caminho: nada.md
---
""", encoding="utf-8")

    migrar(db_path)
    
    nao_enc_path = db_path / "ids_no_mapa_nao_encontrados.yaml"
    assert nao_enc_path.exists()
    import yaml
    nao_enc = yaml.safe_load(nao_enc_path.read_text(encoding="utf-8"))
    
    # "INEXISTENTE" and "TAMBEM_NAO" should fail inline.
    assert len(nao_enc) >= 2
    assert any(x["escalada"] == "Via Multi" for x in nao_enc)
    assert any(x["escalada"] == "Trad" for x in nao_enc)

def test_migrar_evita_aliasing_ruamel(tmp_path):
    # DADO um yaml com duas escaladas apontando para o mesmo id_no_mapa
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor_aliasing.md"
    setor_path.write_text("""---
nome: Setor Alias
mapas:
  - pontos_de_interesse:
      - id: '18'
escaladas:
  - via_esportiva:
      nome: Via 1
      id_no_mapa: '18'
  - via_esportiva:
      nome: Via 2
      id_no_mapa: '18'
---
""", encoding="utf-8")

    # QUANDO executamos a migração
    migrar(db_path)
    
    # ENTÃO não deve haver alias YAML (ex: &id001, *id001) na string salva
    texto_migrado = setor_path.read_text(encoding="utf-8")
    assert "*id" not in texto_migrado
    assert "&id" not in texto_migrado
    
def test_migrar_registra_contexto_setor_grupo(tmp_path):
    # DADO uma via aninhada num setor e grupo que não tem correspondência no mapa
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("""id: teste
ultima_migracao: 1
mapas:
  - pontos_de_interesse:
      - id: "EXISTE"
setores:
  - conteudo:
      nome: Setor Teste
      grupo:
        conteudo:
          nome: Grupo Teste
          escaladas:
            - via_esportiva:
                nome: Via Errada
                id_no_mapa: "INEXISTENTE"
""", encoding="utf-8")

    migrar(db_path)
    
    nao_enc_path = db_path / "ids_no_mapa_nao_encontrados.yaml"
    import yaml
    nao_enc = yaml.safe_load(nao_enc_path.read_text(encoding="utf-8"))
    
    item = next((x for x in nao_enc if x.get("escalada") == "Via Errada"), None)
    assert item is not None
    assert item["setor_contexto"] == "Setor Teste"
    assert item["grupo_contexto"] == "Grupo Teste"

def test_migrar_contexto_herdado_do_pai(tmp_path):
    # DADO um grupo que inclui um arquivo_setor (o setor não sabe qual é seu grupo)
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    grupo_path = db_path / "grupo_principal.md"
    grupo_path.write_text("""---
nome: O Grande Grupo
mapas:
  - pontos_de_interesse:
      - id: "EXISTE"
setores:
  - arquivo_setor:
      caminho: grupo_principal_setor_incluido.md
---
""", encoding="utf-8")

    setor_path = db_path / "grupo_principal_setor_incluido.md"
    setor_path.write_text("""---
nome: Setor Incluido
escaladas:
  - via_esportiva:
      nome: Via Orfa
      id_no_mapa: "INEXISTENTE"
---
""", encoding="utf-8")

    # QUANDO executamos a migração
    migrar(db_path)
    
    # ENTÃO a falha gerada deve conter o grupo_contexto herdado do arquivo pai
    nao_enc_path = db_path / "ids_no_mapa_nao_encontrados.yaml"
    import yaml
    nao_enc = yaml.safe_load(nao_enc_path.read_text(encoding="utf-8"))
    
    item = next((x for x in nao_enc if x.get("escalada") == "Via Orfa"), None)
    assert item is not None
    assert item["setor_contexto"] == "Setor Incluido"
    assert item["grupo_contexto"] == "O Grande Grupo"

def test_migrar_sempre_atualiza_ultima_migracao(tmp_path):
    # DADO um croqui que não sofre nenhuma alteração
    db_path = tmp_path / "database" / "croqui_vazio"
    db_path.mkdir(parents=True)
    croqui_path = db_path / "croqui.yaml"
    croqui_path.write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    # QUANDO executamos a migração
    migrar(db_path)
    
    # ENTÃO ultima_migracao deve ir para 2
    import yaml
    conteudo = yaml.safe_load(croqui_path.read_text(encoding="utf-8"))
    assert conteudo["ultima_migracao"] == 2

def test_migracao_converte_scalar_int(tmp_path):
    # DADO um mapa com ponto de interesse de ID numérico
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor.md"
    setor_path.write_text("""---
nome: Setor Int
mapas:
  - largura_mapa: 1000
    caminho_imagem_mapa: img.webp
    pontos_de_interesse:
      - id: 08
        label: 2
      - id: 9
escaladas:
  - via_esportiva:
      nome: Via 8
      id_no_mapa: "08"
---
""", encoding="utf-8")

    # QUANDO executamos a migração
    migrar(db_path)

    # ENTÃO os inteiros são convertidos para SingleQuotedScalarString e mantêm os zeros à esquerda
    texto = setor_path.read_text(encoding="utf-8")
    import yaml
    frontmatter = yaml.safe_load(texto.split("---", 2)[1])
    pts = frontmatter["mapas"][0]["pontos_de_interesse"]
    assert pts[0]["id"] == "08"
    assert pts[0]["label"] == "2"
    assert pts[1]["id"] == "9"
    assert "- id: '08'" in texto
    assert "label: '2'" in texto
    assert "- id: '9'" in texto

def test_parse_reference_groups_raw_match(tmp_path):
    # DADO um ponto de interesse que tem id "04_topo" exato
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    setor_path = db_path / "setor.md"
    setor_path.write_text("""---
nome: Setor
mapas:
  - largura_mapa: 1000
    caminho_imagem_mapa: img.webp
    pontos_de_interesse:
      - id: "04_topo"
      - id: "1_b"
escaladas:
  - via_esportiva:
      nome: Via 4
      id_no_mapa: "04_topo"
  - via_esportiva:
      nome: Via 1B
      id_no_mapa: "1_b"
---
""", encoding="utf-8")

    # QUANDO executamos a migração
    migrar(db_path)

    # ENTÃO as vias devem ser migradas corretamente, usando match exato do raw
    import yaml
    texto_migrado = setor_path.read_text(encoding="utf-8")
    frontmatter = yaml.safe_load(texto_migrado.split("---", 2)[1])
    
    assert "referencias" in frontmatter["mapas"][0]
    refs = frontmatter["mapas"][0]["referencias"]
    assert len(refs) == 2
    assert refs[0]["ids"] == ["04_topo"]
    assert refs[1]["ids"] == ["1_b"]

def test_migracao_preserva_strings_multilinhas(tmp_path):
    # DADO um yaml com string foldada com mais de 80 caracteres (e menos de 4096)
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    croqui_path = db_path / "croqui.yaml"
    croqui_path.write_text("""id: teste
ultima_migracao: 1
descricao: >
  Era uma vez uma string muito, muito longa. Ela tem mais de oitenta caracteres e antigamente, com o width infinito, ela era transformada em uma única linha no dump. Vamos ver agora.
""", encoding="utf-8")
    
    # QUANDO executamos a migração
    migrar(db_path)
    
    # ENTÃO a string deve ser preservada como foldada (com o >) e manter quebras
    texto = croqui_path.read_text(encoding="utf-8")
    assert "descricao: >" in texto
    assert "Era uma vez uma string muito" in texto

def test_migrar_falhas_herdam_contexto_do_pai(tmp_path):
    # DADO um grupo com mapa que inclui um setor
    # E o setor possui escaladas cujos IDs não dão match no mapa
    # QUANDO migramos a base
    db_path = tmp_path / "database" / "croqui_teste"
    db_path.mkdir(parents=True)
    
    (db_path / "croqui.yaml").write_text("id: teste\nultima_migracao: 1\n", encoding="utf-8")
    
    grupo_path = db_path / "grupo_principal.md"
    grupo_path.write_text("""---
nome: O Grande Grupo
mapas:
  - largura_mapa: 1000
    pontos_de_interesse:
      - id: "ABC"
setores:
  - arquivo_setor:
      caminho: a_setor_a.md
---
""", encoding="utf-8")

    setor_path = db_path / "a_setor_a.md"
    setor_path.write_text("""---
nome: Setor A
escaladas:
  - via_esportiva:
      nome: Via Falha
      id_no_mapa: "99"
---
""", encoding="utf-8")

    migrar(db_path)
    
    # ENTÃO a falha registrada DEVE ter o grupo_contexto correto, mesmo que o setor_a.md
    # seja processado de forma isolada primeiro.
    nao_enc_path = db_path / "ids_no_mapa_nao_encontrados.yaml"
    assert nao_enc_path.exists()
    
    import yaml
    falhas = yaml.safe_load(nao_enc_path.read_text(encoding="utf-8"))
    assert len(falhas) == 1
    assert falhas[0]["escalada"] == "Via Falha"
    assert falhas[0]["setor_contexto"] == "Setor A"
    assert falhas[0]["grupo_contexto"] == "O Grande Grupo"



