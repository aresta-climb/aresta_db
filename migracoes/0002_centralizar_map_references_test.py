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
    assert refs[0]["ids"] == ["1", "1a", "1b"]

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
    assert refs[0]["ids"] == ["S1"]
    
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
