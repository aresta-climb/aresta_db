# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento para o localizador em cascata de arquivos de croqui
e extrator de contexto de Issues e Pull Requests de feedback.
"""

from __future__ import annotations

from pathlib import Path

from serving.agente_feedback.localizador_arquivos_croqui import (
    ContextoFeedbackExtraido,
    ResultadoLocalizacaoArquivos,
    extrair_contexto_issue_feedback,
    extrair_instrucao_comentario_ai_fix,
    gerar_indice_compacto_croqui,
    localizar_arquivos_candidatos_croqui,
)


def _criar_croqui_exemplo(pasta_database: Path) -> Path:
    pasta_croqui = pasta_database / "br_mg_araxa_bocaina_esportivas"
    pasta_croqui.mkdir(parents=True, exist_ok=True)
    (pasta_croqui / "croqui.yaml").write_text(
        """# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: Ygo9aN5g9LtcLo
id: br_mg_araxa_bocaina_esportivas
nome: Bocaina Park (Esportivas)
picos:
- nome: Bocaina Park
  setores_ou_grupos:
  - setor:
      caminho: setor_bem_vindo.md
  - setor:
      caminho: setor_garganta.md
ultima_migracao: 5
""",
        encoding="utf-8",
    )
    (pasta_croqui / "setor_bem_vindo.md").write_text(
        """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: dwuQyJozrODbgq
nome: Setor Bem-vindo
mapas:
- caminho_imagem_mapa: imagens/setor_bem_vindo_p1.webp
  largura_mapa: 1152
  altura_mapa: 1270
  pontos_de_interesse:
  - uid: HnWMGgZrbhzWVB
    rotulo: '03'
    circulo:
      x: 489
      y: 1219
      raio: 26
escaladas:
- uid: 4RV25nAblvsxNc
  via_esportiva:
    nome: Sainhaca
    dificuldade: BR_8A
- uid: 0u3XfCe434ygyF
  via_esportiva:
    nome: Excalibur
    dificuldade: BR_7C
---

Texto do setor Bem-vindo.
""",
        encoding="utf-8",
    )
    (pasta_croqui / "setor_garganta.md").write_text(
        """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: secGargantaUid1
nome: Setor Garganta
escaladas:
- uid: bldChamineUid01
  boulder:
    nome: Chaminé Sombria
    dificuldade: V4
- uid: tradFendaUid002
  via_tradicional:
    nome: Fenda do Vento
    dificuldade: BR_6SUP
---

Texto do setor Garganta.
""",
        encoding="utf-8",
    )
    return pasta_croqui


def test_extrai_metadados_completos_do_corpo_da_issue() -> None:
    corpo_issue = """## Descrição
O grau da Excalibur é 7b, não 7c!

### Captura de Tela
<a href="https://feedback.arestaclimb.com/anexos/123/screenshot.webp"><img src="https://feedback.arestaclimb.com/anexos/123/screenshot.webp" width="320" alt="Captura de Tela do Feedback" /></a>

## Informações Gerais
- **Categoria:** Sobre o Croqui
- **Pico / Croqui:** `br_mg_araxa_bocaina_esportivas`
- **Modo de Acesso:** 🌐 Online (Sob Demanda)
- **Árvore de Navegação:** `Início -> Pico (br_mg_araxa_bocaina_esportivas) -> Grupo (Principal) -> Setor (Setor Bem-vindo) -> Via (Excalibur)`
"""
    contexto: ContextoFeedbackExtraido = extrair_contexto_issue_feedback(
        titulo_issue="[Croqui | br_mg_araxa_bocaina_esportivas] O grau da Excalibur...",
        corpo_issue=corpo_issue,
        labels=["feedback:croqui", "pico:br_mg_araxa_bocaina_esportivas"],
    )

    assert contexto.croqui_id == "br_mg_araxa_bocaina_esportivas"
    assert contexto.descricao_usuario == "O grau da Excalibur é 7b, não 7c!"
    assert contexto.nome_grupo == "Principal"
    assert contexto.nome_setor == "Setor Bem-vindo"
    assert contexto.nome_via == "Excalibur"
    assert contexto.url_screenshot == "https://feedback.arestaclimb.com/anexos/123/screenshot.webp"


def test_extrai_croqui_id_pelo_titulo_ou_label_quando_ausente_no_corpo() -> None:
    contexto_titulo = extrair_contexto_issue_feedback(
        titulo_issue="[Croqui | br_mg_serra_do_cipo] Ajuste na capa",
        corpo_issue="Apenas um texto livre sem seção de informações.",
        labels=[],
    )
    assert contexto_titulo.croqui_id == "br_mg_serra_do_cipo"
    assert contexto_titulo.descricao_usuario == "Apenas um texto livre sem seção de informações."
    assert contexto_titulo.nome_setor is None
    assert contexto_titulo.nome_via is None
    assert contexto_titulo.url_screenshot is None

    contexto_label = extrair_contexto_issue_feedback(
        titulo_issue="[Croqui] Ajuste geral",
        corpo_issue="## Descrição\nTexto na seção\n\n## Informações Gerais\n- **Categoria:** Sobre o Croqui\n",
        labels=["pico:br_mg_lapinha"],
    )
    assert contexto_label.croqui_id == "br_mg_lapinha"
    assert contexto_label.descricao_usuario == "Texto na seção"

    contexto_arvore = extrair_contexto_issue_feedback(
        titulo_issue="[Croqui] Ajuste geral",
        corpo_issue="## Descrição\nTexto\n\n## Informações Gerais\n- **Árvore de Navegação:** `Início -> Pico (br_mg_cipo)`\n",
        labels=[],
    )
    assert contexto_arvore.croqui_id == "br_mg_cipo"


def test_extrai_instrucao_do_comentario_ai_fix() -> None:
    assert (
        extrair_instrucao_comentario_ai_fix("/ai-fix Muda o grau da Sainhaca para 7c")
        == "Muda o grau da Sainhaca para 7c"
    )
    assert (
        extrair_instrucao_comentario_ai_fix("Concordo!\n/ai-fix   Ajusta a extensão para 30m  ")
        == "Ajusta a extensão para 30m"
    )
    assert extrair_instrucao_comentario_ai_fix("/ai-fix") == ""
    assert extrair_instrucao_comentario_ai_fix("Comentário comum sem comando") is None


def test_localiza_arquivo_deterministicamente_pela_arvore_de_navegacao(tmp_path: Path) -> None:
    _criar_croqui_exemplo(tmp_path)
    contexto = ContextoFeedbackExtraido(
        croqui_id="br_mg_araxa_bocaina_esportivas",
        descricao_usuario="O grau está errado",
        nome_grupo=None,
        nome_setor="Setor Bem-vindo",
        nome_via="Excalibur",
        url_screenshot=None,
    )

    resultado: ResultadoLocalizacaoArquivos = localizar_arquivos_candidatos_croqui(
        diretorio_database=tmp_path,
        contexto=contexto,
    )

    assert resultado.estrategia == "deterministica"
    assert resultado.arquivos_relativos == ["setor_bem_vindo.md"]
    assert resultado.precisa_desambiguacao_ia is False


def test_localiza_arquivo_deterministicamente_pelo_nome_da_via_na_arvore(tmp_path: Path) -> None:
    _criar_croqui_exemplo(tmp_path)
    contexto = ContextoFeedbackExtraido(
        croqui_id="br_mg_araxa_bocaina_esportivas",
        descricao_usuario="É V5 na verdade",
        nome_grupo=None,
        nome_setor=None,
        nome_via="Chaminé Sombria",
        url_screenshot=None,
    )

    resultado = localizar_arquivos_candidatos_croqui(
        diretorio_database=tmp_path,
        contexto=contexto,
    )

    assert resultado.estrategia == "deterministica"
    assert resultado.arquivos_relativos == ["setor_garganta.md"]
    assert resultado.precisa_desambiguacao_ia is False


def test_localiza_arquivo_pelos_arquivos_modificados_na_pr(tmp_path: Path) -> None:
    _criar_croqui_exemplo(tmp_path)
    contexto = ContextoFeedbackExtraido(
        croqui_id="br_mg_araxa_bocaina_esportivas",
        descricao_usuario="Ajusta também a descrição",
        nome_grupo=None,
        nome_setor=None,
        nome_via=None,
        url_screenshot=None,
    )

    resultado = localizar_arquivos_candidatos_croqui(
        diretorio_database=tmp_path,
        contexto=contexto,
        arquivos_modificados_pr=[
            "database/br_mg_araxa_bocaina_esportivas/setor_garganta.md",
            "database/br_mg_araxa_bocaina_esportivas/imagens/foto.webp",
        ],
    )

    assert resultado.estrategia == "deterministica_pr"
    assert resultado.arquivos_relativos == ["setor_garganta.md"]
    assert resultado.precisa_desambiguacao_ia is False


def test_localiza_arquivo_por_busca_textual_local_quando_arvore_so_tem_pico(
    tmp_path: Path,
) -> None:
    _criar_croqui_exemplo(tmp_path)
    contexto = ContextoFeedbackExtraido(
        croqui_id="br_mg_araxa_bocaina_esportivas",
        descricao_usuario="Na via chamine sombria o grau correto é V5.",
        nome_grupo=None,
        nome_setor=None,
        nome_via=None,
        url_screenshot=None,
    )

    resultado = localizar_arquivos_candidatos_croqui(
        diretorio_database=tmp_path,
        contexto=contexto,
        instrucao_extra="Pode atualizar",
    )

    assert resultado.estrategia == "busca_textual"
    assert resultado.arquivos_relativos == ["setor_garganta.md"]
    assert resultado.precisa_desambiguacao_ia is False


def test_solicita_desambiguacao_com_indice_compacto_quando_texto_for_ambiguo(
    tmp_path: Path,
) -> None:
    pasta_croqui = _criar_croqui_exemplo(tmp_path)
    # Adiciona um arquivo .md sem frontmatter válido e um arquivo com YAML inválido para garantir resiliência
    (pasta_croqui / "capa.md").write_text("Texto de capa sem frontmatter.", encoding="utf-8")
    (pasta_croqui / "invalido.md").write_text("---\n: yaml_quebrado: [\n---\n", encoding="utf-8")

    contexto = ContextoFeedbackExtraido(
        croqui_id="br_mg_araxa_bocaina_esportivas",
        descricao_usuario="Essa via que circulei na foto é 7b!",
        nome_grupo=None,
        nome_setor=None,
        nome_via=None,
        url_screenshot="https://feedback.arestaclimb.com/anexos/123/screenshot.webp",
    )

    resultado = localizar_arquivos_candidatos_croqui(
        diretorio_database=tmp_path,
        contexto=contexto,
    )

    assert resultado.estrategia == "desambiguacao_ia"
    assert resultado.precisa_desambiguacao_ia is True
    assert "setor_bem_vindo.md" in resultado.indice_compacto
    assert "Setor Bem-vindo" in resultado.indice_compacto
    assert "Excalibur (BR_7C)" in resultado.indice_compacto
    assert "Chaminé Sombria (V4)" in resultado.indice_compacto
    assert "Fenda do Vento (BR_6SUP)" in resultado.indice_compacto
    assert "capa.md" in resultado.indice_compacto
    # Garante que coordenadas de círculos não poluem o índice compacto
    assert "1219" not in resultado.indice_compacto


def test_gera_indice_compacto_vazio_se_pasta_croqui_nao_existir(tmp_path: Path) -> None:
    assert gerar_indice_compacto_croqui(tmp_path / "inexistente") == ""
