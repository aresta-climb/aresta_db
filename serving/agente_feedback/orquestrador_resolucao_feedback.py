# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Orquestrador de resolução automatizada e sob demanda (`/ai-fix`) de feedbacks de croqui
acoplado em processo à `SessaoEditorHeadless` (3ª porta oficial do Editor Aresta),
com pacote *Warm-Start* (1 turno em casos diretos), *Circuit Breaker* de turnos,
desistência voluntária, guarda determinística de Mudança Maior e Hard Jail em `database/<id>/`.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aresta_api.proto.generated import croqui_pb2
from editor.core.classificador_mensagens import eh_linha_de_erro
from editor.mcp.sessao_headless import SessaoEditorHeadless, abrir_editor_headless
from scripts.deploy_generated import deploy
from serving.agente_feedback.avaliador_impacto_feedback import avaliar_impacto_alteracao_feedback
from serving.agente_feedback.cliente_gemini_feedback import (
    NOME_FERRAMENTA_FINALIZAR,
    InterfaceClienteGeminiFeedback,
    ResultadoFerramentaExecutada,
    construir_declaracoes_ferramentas_gemini,
    montar_turno_inicial_usuario,
    montar_turno_respostas_ferramentas,
)
from serving.agente_feedback.cliente_github_feedback import InterfaceClienteGithubFeedback
from serving.agente_feedback.localizador_arquivos_croqui import (
    ContextoFeedbackExtraido,
    construir_pacote_warm_start,
    extrair_contexto_issue_feedback,
    extrair_instrucao_comentario_ai_fix,
)

ASSOCIACOES_MANTENEDOR_AUTORIZADAS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
EXTENSOES_RAIZ_PERMITIDAS = (".md", ".yaml")
MAX_TURNOS_PADRAO = 5


@dataclass(frozen=True)
class ResultadoProcessamentoFeedback:
    """Resultado final da execução do orquestrador para uma Issue ou Pull Request."""

    status: str
    numero_pr: int | None = None
    url_pr: str | None = None
    detalhe: str = ""


def _capturar_snapshot_diretorio(pasta: Path) -> dict[str, bytes]:
    """Captura em memória todos os arquivos relativos de `pasta` para verificação e rollback atômico."""
    return {
        p.relative_to(pasta).as_posix(): p.read_bytes()
        for p in sorted(pasta.rglob("*"))
        if p.is_file()
    }


def _restaurar_snapshot_diretorio(
    pasta_original: Path,
    caminho_atual_sessao: Path,
    snapshot: dict[str, bytes],
) -> None:
    """Restaura integralmente `pasta_original` ao estado exato de `snapshot`, revertendo criações, edições, deleções ou renomeação."""
    if caminho_atual_sessao.resolve() != pasta_original.resolve() and caminho_atual_sessao.exists():
        shutil.rmtree(caminho_atual_sessao)

    pasta_original.mkdir(parents=True, exist_ok=True)
    for arq_existente in list(pasta_original.rglob("*")):
        if arq_existente.is_file():
            rel = arq_existente.relative_to(pasta_original).as_posix()
            if rel not in snapshot:
                arq_existente.unlink()

    for rel, conteudo in snapshot.items():
        destino = pasta_original / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)


def _exige_cabecalho_spdx(rel_posix: str, texto: str, snapshot_original: dict[str, bytes]) -> bool:
    if rel_posix.endswith(".yaml") or texto.startswith("---\n"):
        return True
    bytes_antigos = snapshot_original.get(rel_posix)
    if bytes_antigos is not None:
        texto_antigo = bytes_antigos.decode("utf-8", errors="replace")
        return "SPDX-License-Identifier: ODbL-1.0" in texto_antigo
    return False


def validar_diretorio_croqui_pos_edicao(
    pasta_croqui: Path,
    snapshot_original: dict[str, bytes],
) -> list[str]:
    """
    Aplica o Hard Jail de segurança sobre o estado persistido em `pasta_croqui`:
    1. Na raiz do croqui, apenas arquivos `.md` e `.yaml` são permitidos;
    2. Em subpastas, apenas `imagens/` (ou arquivos já existentes no snapshot original) são aceitos;
    3. Todo arquivo `.yaml` ou `.md` com frontmatter YAML deve preservar SPDX `ODbL-1.0` e `Copyright (C)`.
    """
    erros: list[str] = []
    for caminho in sorted(pasta_croqui.rglob("*")):
        if not caminho.is_file():
            continue
        rel_parts = caminho.relative_to(pasta_croqui).parts
        rel_posix = "/".join(rel_parts)

        if len(rel_parts) == 1:
            if not rel_posix.endswith(EXTENSOES_RAIZ_PERMITIDAS):
                erros.append(
                    f"Extensão não permitida na raiz do croqui: '{rel_posix}'. "
                    "Apenas .md e .yaml são aceitos."
                )
                continue
            texto = caminho.read_text(encoding="utf-8")
            if _exige_cabecalho_spdx(rel_posix, texto, snapshot_original) and (
                "SPDX-License-Identifier: ODbL-1.0" not in texto or "Copyright (C)" not in texto
            ):
                erros.append(
                    f"Cabeçalho obrigatório SPDX ODbL-1.0 ou Copyright ausente em '{rel_posix}'."
                )
        elif rel_parts[0] != "imagens" and rel_posix not in snapshot_original:
            erros.append(
                f"Subdiretório não permitido pelo Hard Jail dentro do croqui: '{rel_posix}'."
            )

    return erros


def _extrair_croqui_id_de_arquivos_pr(arquivos_pr: list[str]) -> str | None:
    """Extrai `<croqui_id>` a partir de caminhos `database/<croqui_id>/...` modificados na PR."""
    for arq in arquivos_pr:
        partes = arq.split("/")
        if len(partes) >= 3 and partes[0] == "database":
            return partes[1]
    return None


def _converter_resultado_mcp(
    nome_ferramenta: str,
    res_mcp: dict[str, Any],
) -> ResultadoFerramentaExecutada:
    blocos_conteudo = res_mcp.get("content") or []
    imagens = [
        (str(b.get("mimeType", "image/png")), str(b["data"]))
        for b in blocos_conteudo
        if isinstance(b, dict) and b.get("type") == "image" and b.get("data")
    ]
    if res_mcp.get("isError"):
        texto_erro = (
            str(blocos_conteudo[0].get("text", "Erro na ferramenta."))
            if blocos_conteudo
            else "Erro na ferramenta."
        )
        return ResultadoFerramentaExecutada(
            nome=nome_ferramenta,
            resposta_json={"isError": True, "erro": texto_erro},
            imagens_inline=imagens,
        )
    if "structuredContent" in res_mcp:
        return ResultadoFerramentaExecutada(
            nome=nome_ferramenta,
            resposta_json={"isError": False, "structuredContent": res_mcp["structuredContent"]},
            imagens_inline=imagens,
        )
    textos = [
        str(b.get("text", ""))
        for b in blocos_conteudo
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    return ResultadoFerramentaExecutada(
        nome=nome_ferramenta,
        resposta_json={"isError": False, "textos": textos},
        imagens_inline=imagens,
    )


def _compilar_estado_base_referencia(
    pasta_croqui: Path,
    dir_saida_base: Path,
) -> croqui_pb2.Croqui:
    deploy(
        output_dir=dir_saida_base,
        target_paths=[pasta_croqui],
        database_dir=pasta_croqui.resolve().parent,
        force_thumbnails=False,
        gerar_arquivos_de_debug=False,
        is_producao=False,
        verbose=False,
        sair_ao_falhar=False,
    )
    pb_base = dir_saida_base / pasta_croqui.name / "compilado.binarypb"
    croqui_msg = croqui_pb2.Croqui()
    croqui_msg.ParseFromString(pb_base.read_bytes())
    return croqui_msg


class OrquestradorResolucaoFeedback:
    """Orquestra o ciclo ponta a ponta de análise, edição via Editor Headless, guardas e abertura/atualização de PR."""

    def __init__(
        self,
        diretorio_database: Path,
        cliente_gemini: InterfaceClienteGeminiFeedback,
        cliente_github: InterfaceClienteGithubFeedback,
        executor_git: Callable[[str, str, Path], None],
        max_turnos: int = MAX_TURNOS_PADRAO,
    ) -> None:
        self._diretorio_database = diretorio_database
        self._cliente_gemini = cliente_gemini
        self._cliente_github = cliente_github
        self._executor_git = executor_git
        self._max_turnos = max_turnos

    def _executar_loop_sessao(
        self,
        *,
        sessao: SessaoEditorHeadless,
        pasta_croqui_original: Path,
        snapshot_original: dict[str, bytes],
        dir_comp_base: Path,
        croqui_base: croqui_pb2.Croqui,
        contexto: ContextoFeedbackExtraido,
        instrucao_extra: str,
        autorizado_por_mantenedor: bool,
        screenshot_bytes: bytes | None,
        screenshot_mime: str,
        numero_issue_ou_pr: int,
    ) -> tuple[ResultadoProcessamentoFeedback | None, tuple[str, str] | None]:
        pacote = construir_pacote_warm_start(sessao, contexto)
        prompt_inicial = pacote.montar_prompt_inicial(instrucao_extra=instrucao_extra)
        declaracoes = construir_declaracoes_ferramentas_gemini(sessao.listar_ferramentas())
        historico: list[dict[str, Any]] = [
            montar_turno_inicial_usuario(
                prompt_texto=prompt_inicial,
                screenshot_bytes=screenshot_bytes,
                screenshot_mime=screenshot_mime,
            )
        ]

        ultimo_erro = "Limite máximo de turnos atingido sem finalizar compilação limpa."

        for _turno in range(self._max_turnos):
            resp_turno = self._cliente_gemini.executar_turno_agente(historico, declaracoes)
            historico.append(resp_turno.conteudo_modelo_bruto)

            resultados_turno: list[ResultadoFerramentaExecutada] = []
            erro_ferramenta_no_turno = ""

            for chamada in resp_turno.chamadas:
                if chamada.nome != NOME_FERRAMENTA_FINALIZAR:
                    res_mcp = sessao.chamar_ferramenta(chamada.nome, chamada.argumentos)
                    conv = _converter_resultado_mcp(chamada.nome, res_mcp)
                    if conv.resposta_json.get("isError") and not erro_ferramenta_no_turno:
                        erro_ferramenta_no_turno = str(conv.resposta_json.get("erro", ""))
                    resultados_turno.append(conv)
                    continue

                acao = str(chamada.argumentos.get("acao") or "nao_acionavel")
                if acao != "abrir_pr":
                    motivo = str(
                        chamada.argumentos.get("motivo")
                        or "Informações insuficientes para edição automática segura."
                    )
                    _restaurar_snapshot_diretorio(
                        pasta_croqui_original, sessao.caminho_database, snapshot_original
                    )
                    self._cliente_github.publicar_comentario(
                        numero_issue_ou_pr,
                        f"🤖 Analisei o feedback, mas não gerei alteração automática pelo seguinte motivo:\n"
                        f"> {motivo}\n\n"
                        f"💡 Um mantenedor pode comentar `/ai-fix <instruções extras>` para orientar a correção.",
                    )
                    return (
                        ResultadoProcessamentoFeedback(status="nao_acionavel", detalhe=motivo),
                        None,
                    )

                if erro_ferramenta_no_turno:
                    ultimo_erro = erro_ferramenta_no_turno
                    resultados_turno.append(
                        ResultadoFerramentaExecutada(
                            nome=NOME_FERRAMENTA_FINALIZAR,
                            resposta_json={
                                "isError": True,
                                "erro": (
                                    "Finalização cancelada neste turno porque uma ferramenta anterior "
                                    f"falhou: {erro_ferramenta_no_turno}"
                                ),
                            },
                        )
                    )
                    continue

                res_salvar = sessao.chamar_ferramenta("aresta_salvar", {})
                mensagens_brutas = res_salvar.get("structuredContent", {}).get("mensagens", [])
                erros_salvar = [str(m) for m in mensagens_brutas if eh_linha_de_erro(str(m))]
                if not (sessao.obter_caminho_compilado() / "compilado.binarypb").is_file():
                    erros_salvar.append("Falha ao gerar compilado.binarypb na validação.")
                erros_jail = validar_diretorio_croqui_pos_edicao(
                    sessao.caminho_database, snapshot_original
                )
                todos_erros = [*erros_salvar, *erros_jail]

                if todos_erros:
                    ultimo_erro = "\n".join(todos_erros)
                    _restaurar_snapshot_diretorio(
                        pasta_croqui_original, sessao.caminho_database, snapshot_original
                    )
                    resultados_turno.append(
                        ResultadoFerramentaExecutada(
                            nome=NOME_FERRAMENTA_FINALIZAR,
                            resposta_json={"isError": True, "erros_validacao": todos_erros},
                        )
                    )
                    continue

                snapshot_atual = _capturar_snapshot_diretorio(sessao.caminho_database)
                if (
                    sessao.caminho_database.resolve() == pasta_croqui_original.resolve()
                    and snapshot_atual == snapshot_original
                ):
                    detalhe_vazio = (
                        "Nenhuma alteração efetiva foi produzida nos arquivos do croqui."
                    )
                    self._cliente_github.publicar_comentario(
                        numero_issue_ou_pr,
                        f"🤖 Analisei o feedback, mas não gerei alteração automática pelo seguinte motivo:\n"
                        f"> {detalhe_vazio}\n\n"
                        f"💡 Um mantenedor pode comentar `/ai-fix <instruções extras>` para orientar a correção.",
                    )
                    return (
                        ResultadoProcessamentoFeedback(
                            status="nao_acionavel", detalhe=detalhe_vazio
                        ),
                        None,
                    )

                titulo_pr = str(
                    chamada.argumentos.get("titulo_pr")
                    or f"fix({sessao.id_croqui}): aplicar ajuste de feedback"
                )
                resumo_mudanca = str(
                    chamada.argumentos.get("resumo_mudanca")
                    or "Aplicado ajuste automático solicitado no feedback."
                )

                if not autorizado_por_mantenedor:
                    pb_novo = sessao.obter_caminho_compilado() / "compilado.binarypb"
                    croqui_novo = croqui_pb2.Croqui()
                    croqui_novo.ParseFromString(pb_novo.read_bytes())
                    aval = avaliar_impacto_alteracao_feedback(
                        dir_compilado_base=dir_comp_base,
                        dir_compilado_novo=sessao.workspace.obter_pasta_servidor_celular(),
                        croqui_base=croqui_base,
                        croqui_novo=croqui_novo,
                    )
                    if aval.eh_mudanca_maior:
                        _restaurar_snapshot_diretorio(
                            pasta_croqui_original, sessao.caminho_database, snapshot_original
                        )
                        lista_motivos = "\n".join(f"- {m}" for m in aval.motivos)
                        self._cliente_github.publicar_comentario(
                            numero_issue_ou_pr,
                            "🤖 Identifiquei a alteração solicitada, mas ela foi classificada como **Mudança Maior** "
                            "e requer confirmação humana antes de abrir Pull Request:\n\n"
                            f"**Plano preparado:** {resumo_mudanca}\n\n"
                            f"**Motivos da guarda de segurança:**\n{lista_motivos}\n\n"
                            "💡 Um mantenedor pode autorizar a aplicação comentando `/ai-fix Pode aplicar`.",
                        )
                        return (
                            ResultadoProcessamentoFeedback(
                                status="confirmacao_necessaria",
                                detalhe="; ".join(aval.motivos),
                            ),
                            None,
                        )

                return None, (titulo_pr, resumo_mudanca)

            historico.append(montar_turno_respostas_ferramentas(resultados_turno))

        _restaurar_snapshot_diretorio(
            pasta_croqui_original, sessao.caminho_database, snapshot_original
        )
        self._cliente_github.publicar_comentario(
            numero_issue_ou_pr,
            "🤖 Não foi possível concluir uma alteração válida dentro do limite seguro de turnos:\n"
            f"```text\n{ultimo_erro}\n```\n"
            "💡 Um mantenedor pode comentar `/ai-fix <instruções>` com mais detalhes.",
        )
        return (
            ResultadoProcessamentoFeedback(status="falha_validacao", detalhe=ultimo_erro),
            None,
        )

    def processar_evento(
        self,
        numero_issue_ou_pr: int,
        corpo_comentario: str | None = None,
        associacao_autor: str = "",
    ) -> ResultadoProcessamentoFeedback:
        """Processa a rotulagem de uma Issue `feedback:croqui` ou um comentário `/ai-fix`."""
        instrucao_extra = ""
        autorizado_por_mantenedor = False
        if corpo_comentario is not None:
            if associacao_autor not in ASSOCIACOES_MANTENEDOR_AUTORIZADAS:
                return ResultadoProcessamentoFeedback(
                    status="ignorado",
                    detalhe="Autor do comentário não possui permissão de mantenedor.",
                )
            instrucao = extrair_instrucao_comentario_ai_fix(corpo_comentario)
            if instrucao is None:
                return ResultadoProcessamentoFeedback(
                    status="ignorado",
                    detalhe="Comentário não contém o comando /ai-fix.",
                )
            instrucao_extra = instrucao
            autorizado_por_mantenedor = True

        dados_alvo = self._cliente_github.obter_issue_ou_pr(numero_issue_ou_pr)
        arquivos_pr: list[str] = []
        if dados_alvo.eh_pull_request:
            arquivos_pr = self._cliente_github.obter_arquivos_modificados_pr(numero_issue_ou_pr)

        contexto = extrair_contexto_issue_feedback(
            titulo_issue=dados_alvo.titulo,
            corpo_issue=dados_alvo.corpo,
            labels=dados_alvo.labels,
        )
        croqui_id = contexto.croqui_id or _extrair_croqui_id_de_arquivos_pr(arquivos_pr)
        pasta_croqui = self._diretorio_database / (croqui_id or "__inexistente__")

        if not croqui_id or not (pasta_croqui / "croqui.yaml").is_file():
            self._cliente_github.publicar_comentario(
                numero_issue_ou_pr,
                "🤖 Não foi possível identificar um `croqui_id` válido em `database/` para este feedback. "
                "Um mantenedor pode responder com `/ai-fix <instruções>` informando o croqui e setor.",
            )
            return ResultadoProcessamentoFeedback(
                status="croqui_nao_identificado",
                detalhe="Croqui não encontrado.",
            )

        contexto_com_id = ContextoFeedbackExtraido(
            croqui_id=croqui_id,
            descricao_usuario=contexto.descricao_usuario,
            nome_grupo=contexto.nome_grupo,
            nome_setor=contexto.nome_setor,
            nome_via=contexto.nome_via,
            url_screenshot=contexto.url_screenshot,
        )

        screenshot_bytes: bytes | None = None
        screenshot_mime = "image/webp"
        if contexto_com_id.url_screenshot:
            anexo = self._cliente_github.baixar_imagem_anexo(contexto_com_id.url_screenshot)
            if anexo is not None:
                screenshot_bytes, screenshot_mime = anexo

        snapshot_original = _capturar_snapshot_diretorio(pasta_croqui)
        with tempfile.TemporaryDirectory(prefix=f"aresta_base_{croqui_id}_") as tmp_base:
            dir_comp_base = Path(tmp_base)
            croqui_base = _compilar_estado_base_referencia(pasta_croqui, dir_comp_base)
            with abrir_editor_headless(pasta_croqui) as sessao:
                resultado_parada, proposta = self._executar_loop_sessao(
                    sessao=sessao,
                    pasta_croqui_original=pasta_croqui,
                    snapshot_original=snapshot_original,
                    dir_comp_base=dir_comp_base,
                    croqui_base=croqui_base,
                    contexto=contexto_com_id,
                    instrucao_extra=instrucao_extra,
                    autorizado_por_mantenedor=autorizado_por_mantenedor,
                    screenshot_bytes=screenshot_bytes,
                    screenshot_mime=screenshot_mime,
                    numero_issue_ou_pr=numero_issue_ou_pr,
                )
                pasta_final = sessao.caminho_database

        if resultado_parada is not None:
            return resultado_parada

        assert proposta is not None
        titulo_pr, resumo_mudanca = proposta

        branch_alvo = (
            dados_alvo.branch_head
            if (dados_alvo.eh_pull_request and dados_alvo.branch_head)
            else f"ai-fix/issue-{numero_issue_ou_pr}"
        )
        referencia_fechamento = (
            "" if dados_alvo.eh_pull_request else f"\n\nFixes #{numero_issue_ou_pr}"
        )
        mensagem_commit = f"{titulo_pr}\n\n{resumo_mudanca}{referencia_fechamento}"
        self._executor_git(branch_alvo, mensagem_commit, pasta_final)

        pr_existente = (
            self._cliente_github.buscar_pr_aberta_por_branch(branch_alvo)
            if not dados_alvo.eh_pull_request
            else None
        )
        if dados_alvo.eh_pull_request or pr_existente is not None:
            num_pr = numero_issue_ou_pr if dados_alvo.eh_pull_request else pr_existente.numero  # type: ignore[union-attr]
            url_pr = "" if dados_alvo.eh_pull_request else pr_existente.url_html  # type: ignore[union-attr]
            self._cliente_github.publicar_comentario(
                numero_issue_ou_pr,
                f"🤖 Pull Request #{num_pr} atualizada com sucesso na branch `{branch_alvo}`!\n\n"
                f"**Resumo:** {resumo_mudanca}",
            )
            return ResultadoProcessamentoFeedback(
                status="pr_atualizada",
                numero_pr=num_pr,
                url_pr=url_pr,
            )

        corpo_pr = (
            f"## 🤖 Proposta Automática de Correção de Croqui\n\n"
            f"**Resumo:** {resumo_mudanca}\n\n"
            f"Fixes #{numero_issue_ou_pr}\n"
        )
        nova_pr = self._cliente_github.criar_pull_request(
            branch_head=branch_alvo,
            titulo=titulo_pr,
            corpo=corpo_pr,
        )
        self._cliente_github.publicar_comentario(
            numero_issue_ou_pr,
            f"🤖 Criei uma proposta de correção automática na **Pull Request #{nova_pr.numero}**: {nova_pr.url_html}\n\n"
            f"**Resumo da alteração:** {resumo_mudanca}\n\n"
            f"💡 Para solicitar ajustes adicionais, comente `/ai-fix <instruções>` aqui ou diretamente na PR.",
        )
        return ResultadoProcessamentoFeedback(
            status="pr_criada",
            numero_pr=nova_pr.numero,
            url_pr=nova_pr.url_html,
        )
