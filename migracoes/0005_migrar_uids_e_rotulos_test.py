# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários da migração 0005: Migração para UIDs universais e rótulos."""

import importlib.util
from pathlib import Path
import pytest
from scripts.helpers_migracao import (
    configurar_croqui_teste,
    carregar_yaml_migrado,
    carregar_markdown_migrado,
)
from scripts.gerenciar_uids_lib import validar_uid

caminho_script = Path(__file__).parent / "0005_migrar_uids_e_rotulos.py"
spec = importlib.util.spec_from_file_location("migracao_0005", str(caminho_script))
assert spec and spec.loader
migracao_0005 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migracao_0005)


def test_afeta_versao_serving() -> None:
    """Garante que a migração 0005 seja marcada como database-only."""
    assert hasattr(migracao_0005, "AFETA_VERSAO_SERVING")
    assert migracao_0005.AFETA_VERSAO_SERVING is False
    assert hasattr(migracao_0005, "MIGRATION_ID")
    assert migracao_0005.MIGRATION_ID == 5


def test_migracao_completa_uids_e_rotulos(tmp_path: Path) -> None:
    """Testa a migração de um croqui legado contendo entidades sem UIDs, labels e referências textuais."""
    croqui_yaml = """\
id: "br_mg_croqui_teste"
nome: "Croqui de Teste"
descricao: "Descrição do croqui"
botoes:
  - texto: "Capa"
    destino:
      secao_textual:
        caminho: "capa.md"
ultima_migracao: 4
"""

    capa_md = """\
---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
titulo: "Capa"
uid: "12345678901234"
id: "capa_legado"
---

# Imagem de Capa
"""

    setor_md = """\
---
nome: "Setor Principal"
escaladas:
  - via_esportiva:
      nome: "Sombra Fresca"
      dificuldade: "6sup"
  - boulder:
      nome: "Sol Ardente"
      dificuldade: "V4"
mapas:
  - caminho_imagem_mapa: "mapas/mapa1.webp"
    largura_mapa: 1920
    altura_mapa: 1080
    pontos_de_interesse:
      - id: "p1"
        label: "11"
        circulo:
          x: 100
          y: 200
          raio: 15
      - id: "p2"
        label: "11A"
        circulo:
          x: 150
          y: 250
          raio: 15
    referencias:
      - escalada: "Sombra Fresca"
        ids:
          - "p1"
          - "p2"
---

Texto descritivo do setor.
"""

    arquivos = {
        "setor_principal.md": setor_md,
        "capa.md": capa_md,
    }
    croqui_dir = configurar_croqui_teste(tmp_path, croqui_yaml, arquivos)

    # Executa a migração
    migracao_0005.migrar(croqui_dir)

    # 1. Valida croqui.yaml
    dados_croqui = carregar_yaml_migrado(croqui_dir)
    assert "uid" in dados_croqui
    assert validar_uid(dados_croqui["uid"]) is True
    assert list(dados_croqui.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo no croqui.yaml"
    assert list(dados_croqui.keys())[1] == "id", "O campo 'id' deve vir logo após o 'uid' no croqui.yaml"
    texto_croqui = (croqui_dir / "croqui.yaml").read_text(encoding="utf-8")
    assert texto_croqui.index("uid:") < texto_croqui.index("id:"), "uid deve preceder id no arquivo croqui.yaml"
    croqui_uid_original = dados_croqui["uid"]

    assert len(dados_croqui.get("botoes", [])) == 1
    botao_migrado = dados_croqui["botoes"][0]
    assert "uid" in botao_migrado
    assert validar_uid(botao_migrado["uid"]) is True
    assert list(botao_migrado.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo no botão"
    botao_uid_original = botao_migrado["uid"]

    # 1.1 Valida que arquivo auxiliar capa.md não possui uid nem id no frontmatter
    fm_capa, _ = carregar_markdown_migrado(croqui_dir, "capa.md")
    assert fm_capa is not None
    assert "uid" not in fm_capa, "Arquivo auxiliar não deve possuir UID"
    assert "id" not in fm_capa, "Arquivo auxiliar não deve possuir ID"
    assert fm_capa.get("titulo") == "Capa"

    # 2. Valida setor_principal.md
    fm, corpo = carregar_markdown_migrado(croqui_dir, "setor_principal.md")
    assert fm is not None
    assert "uid" in fm
    assert validar_uid(fm["uid"]) is True
    assert list(fm.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo no frontmatter do setor"

    # 3. Valida escaladas
    escaladas = fm.get("escaladas", [])
    assert len(escaladas) == 2
    via1 = escaladas[0]
    via2 = escaladas[1]
    assert via1["via_esportiva"]["nome"] == "Sombra Fresca"
    assert "uid" in via1
    assert validar_uid(via1["uid"]) is True
    assert list(via1.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo da escalada"
    via1_uid = via1["uid"]

    assert via2["boulder"]["nome"] == "Sol Ardente"
    assert "uid" in via2
    assert validar_uid(via2["uid"]) is True
    assert list(via2.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo da escalada"

    # 4. Valida pontos de interesse (renomeação de label para rotulo e inserção de uid)
    mapas = fm.get("mapas", [])
    assert len(mapas) == 1
    pois = mapas[0].get("pontos_de_interesse", [])
    assert len(pois) == 2
    poi1 = pois[0]
    poi2 = pois[1]

    assert "id" not in poi1, "O campo 'id' deve ser removido do POI na pasta database"
    assert poi1.get("rotulo") == "11"
    assert "label" not in poi1, "O campo 'label' deve ser removido e renomeado para 'rotulo'"
    assert "uid" in poi1
    assert validar_uid(poi1["uid"]) is True
    assert list(poi1.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo no POI"
    assert list(poi1.keys())[1] == "rotulo", "O campo 'rotulo' deve ser o segundo campo no POI"
    poi1_uid = poi1["uid"]

    assert "id" not in poi2, "O campo 'id' deve ser removido do POI na pasta database"
    assert poi2.get("rotulo") == "11A"
    assert "label" not in poi2
    assert "uid" in poi2
    assert validar_uid(poi2["uid"]) is True
    assert list(poi2.keys())[0] == "uid", "O campo 'uid' deve ser o primeiro campo no POI"
    assert list(poi2.keys())[1] == "rotulo", "O campo 'rotulo' deve ser o segundo campo no POI"
    poi2_uid = poi2["uid"]

    # 5. Valida referências (adoção de alvo_uid e pontos_uids, e deleção de escalada)
    refs = mapas[0].get("referencias", [])
    assert len(refs) == 1
    ref = refs[0]

    assert ref.get("alvo_uid") == via1_uid
    assert ref.get("pontos_uids") == [poi1_uid, poi2_uid]
    assert list(ref.keys())[0] == "alvo_uid", "O campo 'alvo_uid' deve ser o primeiro campo na referência"
    assert list(ref.keys())[1] == "pontos_uids", "O campo 'pontos_uids' deve ser o segundo campo na referência"
    assert "ids" not in ref, "Campo legado 'ids' deve ser removido da referência no Markdown"
    assert "indice_mapa_alvo" not in ref, "Campo legado 'indice_mapa_alvo' deve ser removido da referência"
    assert "escalada" not in ref, "Campo legado 'escalada' deve ser removido da referência no Markdown"
    assert "setor" not in ref
    assert "grupo" not in ref

    # 6. Validação de Idempotência: rodar novamente não altera os UIDs
    migracao_0005.migrar(croqui_dir)
    dados_croqui_2 = carregar_yaml_migrado(croqui_dir)
    assert dados_croqui_2["uid"] == croqui_uid_original
    assert dados_croqui_2["botoes"][0]["uid"] == botao_uid_original
    assert list(dados_croqui_2.keys())[0] == "uid"

    fm_2, _ = carregar_markdown_migrado(croqui_dir, "setor_principal.md")
    assert fm_2 is not None
    assert fm_2["escaladas"][0]["uid"] == via1_uid
    assert list(fm_2["escaladas"][0].keys())[0] == "uid"
    assert fm_2["mapas"][0]["pontos_de_interesse"][0]["uid"] == poi1_uid
    assert list(fm_2["mapas"][0]["pontos_de_interesse"][0].keys())[0] == "uid"
    assert fm_2["mapas"][0]["referencias"][0]["alvo_uid"] == via1_uid
    assert list(fm_2["mapas"][0]["referencias"][0].keys())[0] == "alvo_uid"


def test_migracao_grupos_setores_e_casos_de_borda(tmp_path: Path) -> None:
    """Testa referências apontando para grupos e setores, e casos de borda de serialização."""
    croqui_yaml = """\
id: "br_mg_croqui_grupos"
nome: "Croqui com Grupos"
"""
    # Arquivo de Grupo (sem escaladas)
    grupo_md = """\
---
nome: "Falésias"
mapas:
  - caminho_imagem_mapa: "mapas/geral.webp"
    largura_mapa: 1000
    altura_mapa: 800
    pontos_de_interesse:
      - id: "pg1"
        label: "G1"
        rotulo: "G1"
      - "elemento_invalido"
    referencias:
      - grupo: "Grupo Falésias"
        indice_mapa_alvo: 1
        ids: ["pg1"]
      - setor: "Setor Paredão Isolado"
        ids: ["pg1"]
      - "ref_invalida"
  - "mapa_invalido"
---
"""
    # Setor Isolado (sem corpo)
    setor_md = """\
---
nome: "Paredão Isolado"
escaladas: []
---
"""
    # Arquivo inválido sem frontmatter
    invalido_md = "Este arquivo não tem frontmatter delimitado."

    # Arquivo com frontmatter sintaticamente incorreto
    corrompido_md = """\
---
: invalido : : yaml
---
Corpo
"""

    grupo_dois_md = """\
---
nome: "Grupo Dois"
setores: []
---
"""

    arquivos = {
        "grupo.md": grupo_md,
        "grupo_dois.md": grupo_dois_md,
        "setor_isolado.md": setor_md,
        "invalido.md": invalido_md,
        "corrompido.md": corrompido_md,
    }
    croqui_dir = configurar_croqui_teste(tmp_path, croqui_yaml, arquivos)

    # Executa migração
    migracao_0005.migrar(croqui_dir)

    fm_grupo, _ = carregar_markdown_migrado(croqui_dir, "grupo.md")
    assert fm_grupo is not None
    assert validar_uid(fm_grupo["uid"]) is True
    grupo_uid = fm_grupo["uid"]

    fm_setor, _ = carregar_markdown_migrado(croqui_dir, "setor_isolado.md")
    assert fm_setor is not None
    assert validar_uid(fm_setor["uid"]) is True
    setor_uid = fm_setor["uid"]

    refs = fm_grupo["mapas"][0]["referencias"]
    assert refs[0]["alvo_uid"] == grupo_uid
    assert refs[1]["alvo_uid"] == setor_uid
    assert "grupo" not in refs[0]
    assert "setor" not in refs[1]
    assert "indice_mapa_alvo" not in refs[0]
    assert "ids" not in refs[0]
    assert "id" not in fm_grupo["mapas"][0]["pontos_de_interesse"][0]


def test_migracao_croqui_yaml_corrompido_e_falha_de_leitura(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa tratamento defensivo quando croqui.yaml está corrompido ou arquivo não pode ser lido."""
    croqui_dir = tmp_path / "croqui_quebrado"
    croqui_dir.mkdir()
    caminho_yaml = croqui_dir / "croqui.yaml"
    caminho_yaml.write_text("chave: [aberto sem fechar\noutra_chave: {invalido", encoding="utf-8")

    md_path = croqui_dir / "teste.md"
    md_path.write_text("---\nnome: Teste\n---\n", encoding="utf-8")

    # Força exceção em read_text em uma das chamadas para cobrir linhas de erro defensivo
    original_read_text = Path.read_text

    def falha_read_text(self: Path, *args, **kwargs):
        if self.name == "falha.md":
            raise PermissionError("Acesso negado de teste")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", falha_read_text)
    (croqui_dir / "falha.md").touch()

    # Não deve lançar exceção
    migracao_0005.migrar(croqui_dir)


def test_extrair_nome_escalada() -> None:
    """Testa a extração polimórfica de nomes de escaladas."""
    fn = migracao_0005._extrair_nome_escalada
    assert fn(None) == ""
    assert fn("invalido") == ""
    assert fn({"nome": "Via Plana"}) == "Via Plana"
    assert fn({"via_esportiva": {"nome": "Via Esp"}}) == "Via Esp"
    assert fn({"via_movel": {"nome": "Via Mov"}}) == "Via Mov"
    assert fn({"via_tradicional": {"nome": "Via Trad"}}) == "Via Trad"
    assert fn({"boulder": {"nome": "Meu Bloco"}}) == "Meu Bloco"
    assert fn({"via_psicobloc": {"nome": "Psico"}}) == "Psico"
    assert fn({"via_artificial": {"nome": "Artif"}}) == "Artif"
    assert fn({"highline": {"nome": "Fita Alta"}}) == "Fita Alta"
    assert fn({"via_multiplas_enfiadas": {"nome": "Big Wall"}}) == "Big Wall"
    assert fn({"via_esportiva": "invalido"}) == ""
    assert fn({"outra_coisa": 123}) == ""


def test_inserir_ou_mover_para_posicao() -> None:
    """Testa inserção e reposicionamento com CommentedMap e dict padrão."""
    fn = migracao_0005._inserir_ou_mover_para_posicao
    from ruamel.yaml.comments import CommentedMap

    # 1. CommentedMap: chave existente
    cmap = CommentedMap([("a", 1), ("b", 2), ("c", 3)])
    fn(cmap, "c", pos=0)
    assert list(cmap.keys()) == ["c", "a", "b"]
    assert cmap["c"] == 3

    # 2. CommentedMap: chave inexistente com valor
    fn(cmap, "z", valor=99, pos=0)
    assert list(cmap.keys()) == ["z", "c", "a", "b"]
    assert cmap["z"] == 99

    # 3. dict comum: chave existente
    d = {"x": 10, "y": 20, "z": 30}
    fn(d, "z", pos=0)
    assert list(d.keys()) == ["z", "x", "y"]
    assert d["z"] == 30

    # 4. dict comum: chave inexistente com valor
    fn(d, "w", valor=40, pos=0)
    assert list(d.keys()) == ["w", "z", "x", "y"]
    assert d["w"] == 40

    # 5. dict comum: chave inexistente sem valor (nenhuma mutação)
    d_clone = dict(d)
    fn(d, "inexistente", valor=None, pos=0)
    assert d == d_clone

    # 6. CommentedMap: chave inexistente sem valor (nenhuma mutação)
    cmap_clone = list(cmap.keys())
    fn(cmap, "inexistente", valor=None, pos=0)
    assert list(cmap.keys()) == cmap_clone



