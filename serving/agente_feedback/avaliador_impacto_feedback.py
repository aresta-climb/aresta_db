# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Avaliador determinístico de impacto semântico por UID para distinguir edições
seguras automáticas de "Mudanças Maiores" que exigem confirmação via `/ai-fix`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aresta_api.proto.generated import croqui_pb2
from serving.diff_croqui_pr_lib import calcular_diff_pull_request

LIMITE_SETORES_ADICIONADOS_AUTO = 1
LIMITE_ESCALADAS_ALTERADAS_OU_ADICIONADAS_AUTO = 5


@dataclass(frozen=True)
class AvaliacaoImpactoFeedback:
    """Resultado determinístico da avaliação de impacto de uma proposta de alteração."""

    eh_mudanca_maior: bool
    motivos: list[str]


def avaliar_impacto_alteracao_feedback(
    dir_compilado_base: Path,
    dir_compilado_novo: Path,
    croqui_base: croqui_pb2.Croqui,
    croqui_novo: croqui_pb2.Croqui,
) -> AvaliacaoImpactoFeedback:
    """
    Compara os estados compilados antes e depois da sessão Headless e sinaliza
    `eh_mudanca_maior=True` caso ocorra:
    1. Alteração de `id` do croqui ou `publicar_croqui`;
    2. Exclusão líquida de qualquer entidade (`Pico`, `Grupo`, `Setor`, `Escalada`, `Mapa` ou `Botao`);
    3. Adição de mais de `LIMITE_SETORES_ADICIONADOS_AUTO` setor(es);
    4. Adição ou modificação acumulada de mais de `LIMITE_ESCALADAS_ALTERADAS_OU_ADICIONADAS_AUTO` escaladas.
    """
    motivos: list[str] = []

    if croqui_base.id != croqui_novo.id:
        motivos.append(
            f"Alteração do identificador raiz (`id`) do croqui: '{croqui_base.id}' -> '{croqui_novo.id}'."
        )

    if bool(croqui_base.publicar_croqui) != bool(croqui_novo.publicar_croqui):
        motivos.append(
            f"Alteração de visibilidade (`publicar_croqui`): "
            f"{bool(croqui_base.publicar_croqui)} -> {bool(croqui_novo.publicar_croqui)}."
        )

    if len(croqui_novo.picos) < len(croqui_base.picos):
        motivos.append(
            f"Exclusão líquida de Pico ({len(croqui_base.picos)} -> {len(croqui_novo.picos)})."
        )

    uids_botoes_base = {str(b.uid) for b in croqui_base.botoes if b.uid}
    uids_botoes_novo = {str(b.uid) for b in croqui_novo.botoes if b.uid}
    botoes_removidos = sorted(uids_botoes_base - uids_botoes_novo)
    if botoes_removidos:
        motivos.append(
            f"Exclusão líquida de botão(ões) de navegação (UIDs: {', '.join(botoes_removidos)})."
        )

    if croqui_base.id == croqui_novo.id:
        resumo = calcular_diff_pull_request(
            dir_base=dir_compilado_base,
            dir_pr=dir_compilado_novo,
            ids_croquis=[croqui_novo.id],
        )
        for diff_croqui in resumo.croquis:
            for ent in diff_croqui.entidades:
                if ent.status == "removido":
                    motivos.append(
                        f"Exclusão líquida de {ent.tipo_entidade} '{ent.nome_antes}' (UID {ent.uid})."
                    )
            for mapa in diff_croqui.mapas:
                if mapa.status == "removido":
                    motivos.append(f"Exclusão líquida de mapa '{mapa.caminho_imagem}'.")

        if resumo.total_setores_adicionados > LIMITE_SETORES_ADICIONADOS_AUTO:
            motivos.append(
                f"Adição de {resumo.total_setores_adicionados} setores novos "
                f"(limite automático sem /ai-fix: {LIMITE_SETORES_ADICIONADOS_AUTO})."
            )

        total_escaladas_tocadas = (
            resumo.total_escaladas_adicionadas + resumo.total_escaladas_modificadas
        )
        if total_escaladas_tocadas > LIMITE_ESCALADAS_ALTERADAS_OU_ADICIONADAS_AUTO:
            motivos.append(
                f"Alteração/adição em massa de {total_escaladas_tocadas} escaladas "
                f"(limite automático sem /ai-fix: {LIMITE_ESCALADAS_ALTERADAS_OU_ADICIONADAS_AUTO})."
            )

    return AvaliacaoImpactoFeedback(
        eh_mudanca_maior=bool(motivos),
        motivos=motivos,
    )
