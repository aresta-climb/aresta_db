# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors


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
