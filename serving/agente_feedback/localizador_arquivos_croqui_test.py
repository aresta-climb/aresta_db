# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento para o extrator de contexto de Issues/`/ai-fix`
e construtor do pacote Warm-Start sobre `SessaoEditorHeadless`.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from editor.mcp.sessao_headless import abrir_editor_headless
from serving.agente_feedback.localizador_arquivos_croqui import (
    ContextoFeedbackExtraido,
    PacoteWarmStartCroqui,
    construir_pacote_warm_start,
    extrair_contexto_issue_feedback,
    extrair_instrucao_comentario_ai_fix,
)


def _criar_croqui_exemplo_warm_start(pasta_database: Path) -> Path:
    pasta_croqui = pasta_database / "br_mg_araxa_bocaina_esportivas"
    (pasta_croqui / "imagens").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color="orange").save(pasta_croqui / "imagens" / "capa.webp", "WEBP")
    Image.new("RGB", (100, 100), color="white").save(
        pasta_croqui / "imagens" / "setor_bem_vindo_p1.webp", "WEBP"
    )

    (pasta_croqui / "croqui.yaml").write_text(
        """# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: Ygo9aN5g9LtcLo
id: br_mg_araxa_bocaina_esportivas
nome: Bocaina Park (Esportivas)
caminho_thumbnail: imagens/capa.webp
ultima_migracao: 5
botoes:
- uid: btnComoChegar01
  texto: Como Chegar
  destino:
    secao_textual:
      conteudo: Texto de acesso
picos:
- nome: Bocaina Park
  estado: MG
  cidade: Araxá
  setores_ou_grupos:
  - setor:
      caminho: setor_bem_vindo.md
  - grupo:
      caminho: grupo_garganta.md
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
  largura_mapa: 100
  altura_mapa: 100
  pontos_de_interesse:
  - uid: HnWMGgZrbhzWVB
    rotulo: '03'
    circulo:
      x: 48
      y: 62
      raio: 10
escaladas:
- uid: 4RV25nAblvsxNc
  via_esportiva:
    nome: Sainhaca
    dificuldade: BR_8A
    conquistadores:
    - João Escalador
- uid: 0u3XfCe434ygyF
  via_esportiva:
    nome: Excalibur
    dificuldade: BR_7C
---

Texto do setor Bem-vindo.
""",
        encoding="utf-8",
    )
    (pasta_croqui / "grupo_garganta.md").write_text(
        """---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
uid: grpGargantaUid1
nome: Grupo Garganta
setores:
- caminho: setor_garganta.md
---
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


def test_extrai_croqui_id_pelo_titulo_label_ou_arvore() -> None:
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
        labels=["outro:label", "pico:br_mg_lapinha"],
    )
    assert contexto_label.croqui_id == "br_mg_lapinha"
    assert contexto_label.descricao_usuario == "Texto na seção"

    contexto_arvore = extrair_contexto_issue_feedback(
        titulo_issue="[Croqui] Ajuste geral",
        corpo_issue="## Descrição\nTexto\n\n## Informações Gerais\n- **Árvore de Navegação:** `Início -> Pico (br_mg_cipo)`\n",
        labels=[],
    )
    assert contexto_arvore.croqui_id == "br_mg_cipo"

    contexto_sem_id = extrair_contexto_issue_feedback(
        titulo_issue="Sem croqui",
        corpo_issue="Texto solto",
        labels=["feedback:croqui"],
    )
    assert contexto_sem_id.croqui_id is None


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


def test_constroi_pacote_warm_start_com_foco_por_setor_via_texto_e_sem_foco(
    tmp_path: Path,
) -> None:
    pasta_croqui = _criar_croqui_exemplo_warm_start(tmp_path)

    with abrir_editor_headless(pasta_croqui) as sessao:
        # 1. Foco resolvido pelo nome_setor na árvore de navegação
        ctx_setor = ContextoFeedbackExtraido(
            croqui_id="br_mg_araxa_bocaina_esportivas",
            descricao_usuario="Excalibur é 7b",
            nome_grupo=None,
            nome_setor="Setor Bem-vindo",
            nome_via="Excalibur",
            url_screenshot=None,
        )
        pacote_setor: PacoteWarmStartCroqui = construir_pacote_warm_start(sessao, ctx_setor)
        assert "resolver_feedback_croqui" in pacote_setor.catalogo_skills
        assert "aresta_migrar_escalada" in pacote_setor.instrucoes_skill
        assert "dwuQyJozrODbgq" in pacote_setor.indice_estrutural
        assert "grpGargantaUid1" in pacote_setor.indice_estrutural
        assert "secGargantaUid1" in pacote_setor.indice_estrutural
        assert "0u3XfCe434ygyF" in pacote_setor.indice_estrutural
        assert "btnComoChegar01" in pacote_setor.indice_estrutural
        assert pacote_setor.uid_foco == "dwuQyJozrODbgq"
        assert "HnWMGgZrbhzWVB" in pacote_setor.subarvore_foco_json

        prompt_completo = pacote_setor.montar_prompt_inicial(instrucao_extra="Priorize esta via")
        assert "Priorize esta via" in prompt_completo
        assert "Excalibur é 7b" in prompt_completo

        # 2. Foco resolvido pelo nome_via quando nome_setor está ausente
        ctx_via = ContextoFeedbackExtraido(
            croqui_id="br_mg_araxa_bocaina_esportivas",
            descricao_usuario="Grau errado",
            nome_grupo=None,
            nome_setor=None,
            nome_via="Chaminé Sombria",
            url_screenshot=None,
        )
        pacote_via = construir_pacote_warm_start(sessao, ctx_via)
        assert pacote_via.uid_foco == "secGargantaUid1"

        # 3. Foco resolvido por menção textual na descrição/instrução extra
        ctx_texto = ContextoFeedbackExtraido(
            croqui_id="br_mg_araxa_bocaina_esportivas",
            descricao_usuario="Na via sainhaca faltou extensão",
            nome_grupo=None,
            nome_setor=None,
            nome_via=None,
            url_screenshot=None,
        )
        pacote_texto = construir_pacote_warm_start(sessao, ctx_texto)
        assert pacote_texto.uid_foco == "dwuQyJozrODbgq"

        # 4. Feedback genérico sem setor específico -> uid_foco vazio, índice completo presente
        ctx_geral = ContextoFeedbackExtraido(
            croqui_id="br_mg_araxa_bocaina_esportivas",
            descricao_usuario="Ajustar introdução geral do pico",
            nome_grupo=None,
            nome_setor=None,
            nome_via=None,
            url_screenshot=None,
        )
        pacote_geral = construir_pacote_warm_start(sessao, ctx_geral)
        assert pacote_geral.uid_foco == ""
        assert pacote_geral.subarvore_foco_json == ""
        prompt_sem_extra = pacote_geral.montar_prompt_inicial()
        assert "Ajustar introdução geral do pico" in prompt_sem_extra
