# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Orquestrador de resolução automatizada e sob demanda (`/ai-fix`) de feedbacks de croqui.
Coordena localização em cascata de arquivos `.md`, renderização de régua cartesiana,
inferência multimodal com Gemini Flash, Hard Jail de escopo em `database/<croqui_id>/`,
validação local com autoretry e abertura/atualização de Pull Requests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from serving.agente_feedback.cliente_gemini_feedback import (
    AlteracaoArquivoProposta,
    InterfaceClienteGeminiFeedback,
)
from serving.agente_feedback.cliente_github_feedback import InterfaceClienteGithubFeedback
from serving.agente_feedback.localizador_arquivos_croqui import (
    ContextoFeedbackExtraido,
    extrair_contexto_issue_feedback,
    extrair_instrucao_comentario_ai_fix,
    localizar_arquivos_candidatos_croqui,
)
from serving.agente_feedback.renderizador_regua_mapa import (
    MapaAnotadoEmMemoria,
    extrair_e_renderizar_mapas_do_setor,
)

ASSOCIACOES_MANTENEDOR_AUTORIZADAS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
EXTENSOES_PERMITIDAS = (".md", ".yaml")


@dataclass(frozen=True)
class ResultadoProcessamentoFeedback:
    """Resultado final da execução do orquestrador para uma Issue ou Pull Request."""

    status: str
    numero_pr: int | None = None
    url_pr: str | None = None
    detalhe: str = ""


def validar_escopo_e_cabecalho_alteracao(
    pasta_croqui: Path,
    alteracao: AlteracaoArquivoProposta,
) -> str | None:
    """
    Aplica o Hard Jail de segurança:
    1. O arquivo relativo deve terminar em `.md` ou `.yaml`.
    2. O caminho resolvido deve pertencer estritamente ao diretório `pasta_croqui` (sem `../` ou subpastas).
    3. O novo conteúdo deve preservar `# SPDX-License-Identifier: ODbL-1.0` e `# Copyright (C)`.
    Retorna `None` se válido ou a mensagem de erro caso viole alguma invariante.
    """
    nome_rel = alteracao.arquivo_relativo.strip()
    if not nome_rel.endswith(EXTENSOES_PERMITIDAS):
        return (
            f"Extensão não permitida para o arquivo '{nome_rel}'. Apenas .md e .yaml são aceitos."
        )

    pasta_resolvida = pasta_croqui.resolve()
    destino_resolvido = (pasta_resolvida / nome_rel).resolve()
    if destino_resolvido.parent != pasta_resolvida:
        return f"Violação de escopo (Hard Jail): '{nome_rel}' aponta para fora de '{pasta_croqui.name}'."

    conteudo = alteracao.conteudo_novo
    if "SPDX-License-Identifier: ODbL-1.0" not in conteudo or "Copyright (C)" not in conteudo:
        return f"Cabeçalho obrigatório SPDX ODbL-1.0 ou Copyright ausente em '{nome_rel}'."

    return None


def _extrair_croqui_id_de_arquivos_pr(arquivos_pr: list[str]) -> str | None:
    """Extrai `<croqui_id>` a partir de caminhos `database/<croqui_id>/...` modificados na PR."""
    for arq in arquivos_pr:
        partes = arq.split("/")
        if len(partes) >= 3 and partes[0] == "database":
            return partes[1]
    return None


class OrquestradorResolucaoFeedback:
    """Orquestra o ciclo ponta a ponta de análise, validação com autoretry e abertura/atualização de PR."""

    def __init__(
        self,
        diretorio_database: Path,
        cliente_gemini: InterfaceClienteGeminiFeedback,
        cliente_github: InterfaceClienteGithubFeedback,
        executor_git: Callable[[str, str, list[Path]], None],
        validador_croqui: Callable[[Path], list[str]],
    ) -> None:
        self._diretorio_database = diretorio_database
        self._cliente_gemini = cliente_gemini
        self._cliente_github = cliente_github
        self._executor_git = executor_git
        self._validador_croqui = validador_croqui

    def processar_evento(
        self,
        numero_issue_ou_pr: int,
        corpo_comentario: str | None = None,
        associacao_autor: str = "",
    ) -> ResultadoProcessamentoFeedback:
        """Processa a abertura de uma Issue `feedback:croqui` ou um comentário `/ai-fix`."""
        instrucao_extra = ""
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

        if not croqui_id or not pasta_croqui.is_dir():
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

        loc = localizar_arquivos_candidatos_croqui(
            diretorio_database=self._diretorio_database,
            contexto=contexto_com_id,
            instrucao_extra=instrucao_extra,
            arquivos_modificados_pr=arquivos_pr,
        )
        arquivos_selecionados = list(loc.arquivos_relativos)
        if loc.precisa_desambiguacao_ia:
            sugeridos = self._cliente_gemini.desambiguar_arquivos_croqui(
                indice_compacto=loc.indice_compacto,
                descricao_feedback=contexto_com_id.descricao_usuario,
                instrucao_extra=instrucao_extra,
                screenshot_bytes=screenshot_bytes,
                screenshot_mime=screenshot_mime,
            )
            arquivos_selecionados = [arq for arq in sugeridos if (pasta_croqui / arq).is_file()]

        arquivos_atuais: dict[str, str] = {}
        mapas_anotados: list[MapaAnotadoEmMemoria] = []
        for arq_rel in arquivos_selecionados:
            caminho_arq = pasta_croqui / arq_rel
            arquivos_atuais[arq_rel] = caminho_arq.read_text(encoding="utf-8")
            if arq_rel.endswith(".md"):
                mapas_anotados.extend(extrair_e_renderizar_mapas_do_setor(pasta_croqui, arq_rel))

        snapshot_original = {
            p.name: p.read_text(encoding="utf-8")
            for p in pasta_croqui.iterdir()
            if p.is_file() and p.name.endswith(EXTENSOES_PERMITIDAS)
        }

        def restaurar_snapshot() -> None:
            for nome_arq, conteudo_orig in snapshot_original.items():
                (pasta_croqui / nome_arq).write_text(conteudo_orig, encoding="utf-8")

        erro_anterior = ""
        proposta_aprovada = None
        caminhos_modificados: list[Path] = []

        for _tentativa in range(2):
            proposta = self._cliente_gemini.gerar_proposta_alteracao(
                croqui_id=croqui_id,
                descricao_feedback=contexto_com_id.descricao_usuario,
                instrucao_extra=instrucao_extra,
                arquivos_atuais=arquivos_atuais,
                screenshot_bytes=screenshot_bytes,
                screenshot_mime=screenshot_mime,
                mapas_anotados=mapas_anotados,
                erro_validacao_anterior=erro_anterior,
            )

            if not proposta.acionavel or not proposta.alteracoes:
                restaurar_snapshot()
                self._cliente_github.publicar_comentario(
                    numero_issue_ou_pr,
                    f"🤖 Analisei o feedback, mas não gerei alteração automática pelo seguinte motivo:\n"
                    f"> {proposta.motivo_nao_acionavel or 'Informações insuficientes para edição segura.'}\n\n"
                    f"💡 Um mantenedor pode comentar `/ai-fix <instruções extras>` para orientar a correção.",
                )
                return ResultadoProcessamentoFeedback(
                    status="nao_acionavel",
                    detalhe=proposta.motivo_nao_acionavel,
                )

            caminhos_tentativa: list[Path] = []
            erros_tentativa: list[str] = []
            for alt in proposta.alteracoes:
                erro_escopo = validar_escopo_e_cabecalho_alteracao(pasta_croqui, alt)
                if erro_escopo:
                    erros_tentativa.append(erro_escopo)
                else:
                    caminho_dest = pasta_croqui / alt.arquivo_relativo.strip()
                    caminho_dest.write_text(alt.conteudo_novo, encoding="utf-8")
                    caminhos_tentativa.append(caminho_dest)

            if not erros_tentativa:
                erros_tentativa.extend(self._validador_croqui(pasta_croqui))

            if not erros_tentativa:
                proposta_aprovada = proposta
                caminhos_modificados = caminhos_tentativa
                break

            restaurar_snapshot()
            erro_anterior = "\n".join(erros_tentativa)

        if proposta_aprovada is None:
            self._cliente_github.publicar_comentario(
                numero_issue_ou_pr,
                "🤖 Não foi possível gerar uma alteração que passasse na validação automática do `aresta_db`:\n"
                f"```text\n{erro_anterior}\n```\n"
                "💡 Um mantenedor pode comentar `/ai-fix <instruções>` com mais detalhes.",
            )
            return ResultadoProcessamentoFeedback(
                status="falha_validacao",
                detalhe=erro_anterior,
            )

        branch_alvo = (
            dados_alvo.branch_head
            if (dados_alvo.eh_pull_request and dados_alvo.branch_head)
            else f"ai-fix/issue-{numero_issue_ou_pr}"
        )
        referencia_fechamento = (
            "" if dados_alvo.eh_pull_request else f"\n\nFixes #{numero_issue_ou_pr}"
        )
        mensagem_commit = (
            f"{proposta_aprovada.titulo_pr}\n\n"
            f"{proposta_aprovada.resumo_mudanca}{referencia_fechamento}"
        )
        self._executor_git(branch_alvo, mensagem_commit, caminhos_modificados)

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
                f"**Resumo:** {proposta_aprovada.resumo_mudanca}",
            )
            return ResultadoProcessamentoFeedback(
                status="pr_atualizada",
                numero_pr=num_pr,
                url_pr=url_pr,
            )

        corpo_pr = (
            f"## 🤖 Proposta Automática de Correção de Croqui\n\n"
            f"**Resumo:** {proposta_aprovada.resumo_mudanca}\n\n"
            f"Fixes #{numero_issue_ou_pr}\n"
        )
        nova_pr = self._cliente_github.criar_pull_request(
            branch_head=branch_alvo,
            titulo=proposta_aprovada.titulo_pr,
            corpo=corpo_pr,
        )
        self._cliente_github.publicar_comentario(
            numero_issue_ou_pr,
            f"🤖 Criei uma proposta de correção automática na **Pull Request #{nova_pr.numero}**: {nova_pr.url_html}\n\n"
            f"**Resumo da alteração:** {proposta_aprovada.resumo_mudanca}\n\n"
            f"💡 Para solicitar ajustes adicionais, comente `/ai-fix <instruções>` aqui ou diretamente na PR.",
        )
        return ResultadoProcessamentoFeedback(
            status="pr_criada",
            numero_pr=nova_pr.numero,
            url_pr=nova_pr.url_html,
        )
