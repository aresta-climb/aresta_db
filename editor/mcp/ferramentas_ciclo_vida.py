# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aresta_api.proto.generated import croqui_pb2
from editor.controllers.croqui_controller import CroquiController
from editor.core.croqui_experimental import GerenciadorCroquiExperimental
from editor.core.formatacao import para_snake_case
from editor.core.instancia_unica import verificar_croqui_ja_aberto
from editor.core.serializacao_util import carregar_yaml
from editor.core.storage import GerenciadorCaminhos
from editor.mcp.resolvedor_alvo import resolver_alvo_mcp
from editor.mcp.servidor import ServidorMCP
from editor.mcp.sessao import listar_sessoes_mcp
from editor.models.croqui_model import CroquiModel
from scripts.deploy_generated import (
    persistir_contexto_memoria_no_disco,
    usar_contexto_memoria_deploy,
)
from scripts.gerenciar_uids_lib import gerar_uid
from scripts.repartir_pdf import repartir_pdf


def _obter_pilha_qt(undo_stack: Any) -> Any:
    if hasattr(undo_stack, "obter_pilha"):
        return undo_stack.obter_pilha()
    return undo_stack


def _executar_salvamento_e_compilacao(
    model: CroquiModel,
    undo_stack: Any,
    workspace: Any,
    storage: GerenciadorCaminhos | None = None,
) -> dict[str, Any]:
    """
    Executa a extração e serialização do CroquiModel em memória RAM, compila via
    workspace e persiste os arquivos finais no disco.
    """
    _exigir(
        workspace is not None,
        "Nenhum workspace configurado para salvar ou compilar o croqui.",
    )

    caminho_db = workspace.obter_caminho_database()
    cache_md: dict[str, tuple[dict[str, Any] | None, str]] = {}
    corpos_brutos_md: dict[str, str] = {}

    croqui_data = model.extrair_arquivos_e_serializar(
        caminho_db,
        cache_md_out=cache_md,
        corpos_brutos_md_out=corpos_brutos_md,
        persistir_no_disco=False,
    )

    novo_id = str(croqui_data.get("id", ""))
    nome_raiz = workspace.caminho_raiz.name
    partes = nome_raiz.split("_", 1)
    id_atual = partes[1] if len(partes) > 1 and partes[0].isdigit() else nome_raiz

    with usar_contexto_memoria_deploy(
        [caminho_db],
        croqui_data,
        cache_md=cache_md,
        corpos_brutos_md=corpos_brutos_md,
    ) as ctx_deploy:
        caminho_retornado, mensagens, database_modificado = (
            workspace.processar_renomeacao_e_compilacao(novo_id, id_atual, storage)
        )
        if not ctx_deploy.persistido_no_disco:
            persistir_contexto_memoria_no_disco(caminho_db, ctx_deploy)

    pilha = _obter_pilha_qt(undo_stack)
    pilha.setClean()

    return {
        "status": "ok",
        "caminho": str(caminho_retornado),
        "mensagens": list(mensagens),
        "database_modificado": bool(database_modificado),
    }


def _exigir(condicao: object, mensagem: str) -> None:
    if not condicao:
        raise ValueError(mensagem)


def _ler_metadados_croqui_yaml(caminho_yaml: Path, id_padrao: str) -> tuple[str, str]:
    dados = (
        (carregar_yaml(caminho_yaml.read_text(encoding="utf-8")) or {})
        if caminho_yaml.is_file()
        else {}
    )
    return (
        str(dados.get("id") or id_padrao),
        str(dados.get("nome") or id_padrao.replace("_", " ").title()),
    )


def _corresponde_filtro(filtro: str, *textos: str) -> bool:
    if not filtro:
        return True
    termo = filtro.lower()
    return any(termo in t.lower() for t in textos)


def _finalizar_abertura_croqui(
    status: str,
    id_croqui: str,
    caminho_exp: Path,
    callback_abrir_croqui: Callable[[Path], dict[str, Any] | None] | None,
) -> dict[str, Any]:
    caminho_db = (
        caminho_exp / "database" if (caminho_exp / "database").is_dir() else caminho_exp
    )
    resposta: dict[str, Any] = {
        "status": status,
        "id_croqui": id_croqui,
        "caminho": str(caminho_exp),
        "caminho_database": str(caminho_db),
    }
    if callback_abrir_croqui is not None:
        extra = callback_abrir_croqui(caminho_exp)
        if isinstance(extra, dict):
            resposta.update(extra)
    return resposta


def registrar_ferramentas_gestao_croquis(
    servidor: ServidorMCP,
    storage: Any | None = None,
    usuario: str = "Autor MCP",
    callback_abrir_croqui: Callable[[Path], dict[str, Any] | None] | None = None,
) -> None:
    """
    Registra no `ServidorMCP` as ferramentas globais de descoberta, criação, importação e
    abertura de croquis (`requer_croqui=False`), disponíveis inclusive na `TelaDeCarregamento`.
    """

    def _listar_croquis(args: dict[str, Any]) -> dict[str, Any]:
        filtro = str(args.get("filtro") or "").strip()
        sessoes = listar_sessoes_mcp(servidor.diretorio_sessao)
        abertos = [
            {
                "id_croqui": s.id_croqui,
                "porta": s.porta,
                "caminho_database": s.caminho_database,
            }
            for s in sessoes
            if s.id_croqui and _corresponde_filtro(filtro, s.id_croqui)
        ]

        experimentais: list[dict[str, Any]] = []
        oficiais: list[dict[str, Any]] = []

        if storage is not None:
            caminho_exp = storage.obter_caminho_croquis_experimentais()
            for pasta in sorted(p for p in caminho_exp.iterdir() if p.is_dir()) if caminho_exp.is_dir() else []:
                id_logico, nome = _ler_metadados_croqui_yaml(
                    pasta / "database" / "croqui.yaml", pasta.name
                )
                if _corresponde_filtro(filtro, pasta.name, id_logico, nome):
                    experimentais.append(
                        {
                            "pasta": pasta.name,
                            "id_croqui": id_logico,
                            "nome": nome,
                            "caminho": str(pasta),
                        }
                    )

            caminho_oficiais = storage.obter_caminho_base_repo() / "database"
            for pasta in sorted(p for p in caminho_oficiais.iterdir() if p.is_dir()) if caminho_oficiais.is_dir() else []:
                id_of, nome_of = _ler_metadados_croqui_yaml(pasta / "croqui.yaml", pasta.name)
                if _corresponde_filtro(filtro, pasta.name, id_of, nome_of):
                    oficiais.append(
                        {
                            "id_croqui": id_of,
                            "nome": nome_of,
                            "caminho": str(pasta),
                        }
                    )

        return {
            "abertos": abertos,
            "experimentais": experimentais,
            "oficiais": oficiais,
        }

    def _procurar_sessao_ja_aberta(id_alvo: str) -> dict[str, Any] | None:
        for s in listar_sessoes_mcp(servidor.diretorio_sessao):
            if s.id_croqui == id_alvo:
                verificar_croqui_ja_aberto(id_alvo)
                return {
                    "status": "ja_aberto",
                    "id_croqui": s.id_croqui,
                    "porta": s.porta,
                    "caminho_database": s.caminho_database,
                }
        return None

    def _abrir_croqui_existente(args: dict[str, Any]) -> dict[str, Any]:
        identificador = str(args.get("identificador") or "").strip()
        _exigir(identificador, "O parâmetro 'identificador' é obrigatório.")

        ja_aberto = _procurar_sessao_ja_aberta(identificador)
        if ja_aberto is not None:
            return ja_aberto

        _exigir(storage is not None, "Storage não configurado para localizar croquis experimentais.")

        caminho_exp_dir = storage.obter_caminho_croquis_experimentais()
        pasta_encontrada: Path | None = None
        id_logico_encontrado = identificador

        for pasta in sorted(p for p in caminho_exp_dir.iterdir() if p.is_dir()) if caminho_exp_dir.is_dir() else []:
            id_logico, _ = _ler_metadados_croqui_yaml(
                pasta / "database" / "croqui.yaml", pasta.name
            )
            if pasta.name == identificador or id_logico == identificador:
                pasta_encontrada = pasta
                id_logico_encontrado = id_logico
                break

        _exigir(pasta_encontrada is not None, f"Croqui experimental '{identificador}' não encontrado.")
        assert pasta_encontrada is not None

        GerenciadorCroquiExperimental(storage).abrir_croqui(pasta_encontrada, usuario)
        return _finalizar_abertura_croqui(
            "aberto", id_logico_encontrado, pasta_encontrada, callback_abrir_croqui
        )

    def _importar_croqui_oficial(args: dict[str, Any]) -> dict[str, Any]:
        id_oficial = str(args.get("id_oficial") or "").strip()
        resumo_edicao = str(args.get("resumo_edicao") or "").strip()
        _exigir(id_oficial, "O parâmetro 'id_oficial' é obrigatório.")

        ja_aberto = _procurar_sessao_ja_aberta(id_oficial)
        if ja_aberto is not None:
            return ja_aberto

        _exigir(storage is not None, "Storage não configurado para importar croqui oficial.")

        caminho_exp = GerenciadorCroquiExperimental(storage).criar_croqui_a_partir_de_oficial(
            id_oficial, usuario, resumo_edicao
        )
        return _finalizar_abertura_croqui(
            "importado", id_oficial, caminho_exp, callback_abrir_croqui
        )

    def _criar_novo_croqui(args: dict[str, Any]) -> dict[str, Any]:
        nome_pico = str(args.get("nome_pico") or "").strip()
        cidade = str(args.get("cidade") or "").strip()
        estado = str(args.get("estado") or "").strip().upper()
        pais = str(args.get("pais") or "BR").strip().upper()
        caminho_pdf = str(args.get("caminho_pdf_original") or "").strip()

        _exigir(
            all([nome_pico, cidade, estado, pais]),
            "Os parâmetros 'nome_pico', 'cidade', 'estado' e 'pais' são obrigatórios.",
        )
        _exigir(storage is not None, "Storage não configurado para criar novo croqui.")

        id_gerado = (
            f"{para_snake_case(pais)}_{para_snake_case(estado)}_"
            f"{para_snake_case(cidade)}_{para_snake_case(nome_pico)}"
        )[:100].rstrip("_")

        caminho_exp = GerenciadorCroquiExperimental(storage).criar_novo_croqui(
            id_gerado, nome_pico, estado, usuario
        )
        if caminho_pdf:
            origem_pdf = Path(caminho_pdf)
            _exigir(origem_pdf.is_file(), f"Arquivo PDF não encontrado em '{caminho_pdf}'.")
            destino_pdf = caminho_exp / "database" / "raw_original_pdf" / "croqui_original.pdf"
            destino_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem_pdf, destino_pdf)

        return _finalizar_abertura_croqui(
            "criado", id_gerado, caminho_exp, callback_abrir_croqui
        )

    servidor.registrar_ferramenta(
        nome="aresta_listar_croquis",
        descricao=(
            "Lista croquis atualmente abertos em janelas do Editor, croquis experimentais locais "
            "e croquis oficiais disponíveis no repositório para importação."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "filtro": {
                    "type": "string",
                    "description": "Termo opcional para filtrar croquis por ID ou nome.",
                }
            },
        },
        manipulador=_listar_croquis,
        requer_croqui=False,
    )
    servidor.registrar_ferramenta(
        nome="aresta_abrir_croqui_existente",
        descricao="Abre um croqui experimental já existente no histórico local por ID ou pasta.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "identificador": {
                    "type": "string",
                    "description": "ID lógico do croqui ou nome da pasta experimental.",
                }
            },
            "required": ["identificador"],
        },
        manipulador=_abrir_croqui_existente,
        requer_croqui=False,
    )
    servidor.registrar_ferramenta(
        nome="aresta_importar_croqui_oficial",
        descricao="Importa um croqui oficial do repositório para um novo workspace experimental e o abre.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "id_oficial": {
                    "type": "string",
                    "description": "ID do croqui oficial (ex: 'br_mg_serra_do_cipo_grupo_2').",
                },
                "resumo_edicao": {
                    "type": "string",
                    "description": "Resumo opcional descrevendo a edição planejada.",
                },
            },
            "required": ["id_oficial"],
        },
        manipulador=_importar_croqui_oficial,
        requer_croqui=False,
    )
    servidor.registrar_ferramenta(
        nome="aresta_criar_novo_croqui",
        descricao="Cria e compila inicialmente um novo croqui experimental (com cópia opcional do PDF original).",
        esquema_entrada={
            "type": "object",
            "properties": {
                "nome_pico": {"type": "string", "description": "Nome do pico principal."},
                "cidade": {"type": "string", "description": "Nome da cidade."},
                "estado": {"type": "string", "description": "Sigla da UF (ex: 'MG', 'SP')."},
                "pais": {"type": "string", "description": "Sigla do país (padrão 'BR')."},
                "caminho_pdf_original": {
                    "type": "string",
                    "description": "Caminho opcional do arquivo PDF original para copiar ao croqui.",
                },
            },
            "required": ["nome_pico", "cidade", "estado"],
        },
        manipulador=_criar_novo_croqui,
        requer_croqui=False,
    )


def _humanizar_nome_parte(nome_parte: str) -> str:
    sem_prefixo = re.sub(r"^\d+_", "", nome_parte)
    return sem_prefixo.replace("_", " ").strip().title() or nome_parte


def _inferir_tipo_parte(nome_parte: str, tipos_partes: dict[str, Any]) -> str:
    if nome_parte in tipos_partes:
        return str(tipos_partes[nome_parte]).strip().lower()
    lower = nome_parte.lower()
    if "mapa" in lower:
        return "mapas_gerais"
    if lower.startswith("00_") or "intro" in lower:
        return "botao"
    return "setor"


def _alocar_ou_obter_uid_parte(
    model: CroquiModel,
    controller: CroquiController,
    nome_parte: str,
    tipo_parte: str,
) -> str:
    titulo = _humanizar_nome_parte(nome_parte)
    raiz = model.obter_croqui_readonly()

    if tipo_parte == "botao":
        for botao in raiz.botoes:
            if botao.texto == titulo:
                return str(botao.uid)
        novo_botao = croqui_pb2.Botao(
            uid=gerar_uid(),
            texto=titulo,
        )
        controller.adicionar_repeated(
            raiz,
            "botoes",
            len(raiz.botoes),
            novo_botao,
        )
        return str(novo_botao.uid)

    if len(raiz.picos) == 0:
        novo_pico = croqui_pb2.Pico(nome=str(raiz.nome or "Pico Principal"))
        controller.adicionar_repeated(raiz, "picos", 0, novo_pico)
    pico = model.obter_croqui_readonly().picos[0]

    if tipo_parte == "mapas_gerais":
        if not pico.mapas_gerais.HasField("conteudo"):
            controller.alterar_campo(
                pico,
                campo_nome="mapas_gerais",
                valor_novo=croqui_pb2.ArquivoMapas(conteudo=croqui_pb2.ColecaoDeMapas()),
            )
        return "picos[0].mapas_gerais.conteudo"

    if tipo_parte == "grupo":
        for sg in pico.setores_ou_grupos:
            if sg.HasField("grupo") and sg.grupo.conteudo.nome == titulo:
                return str(sg.grupo.conteudo.uid)
        novo_sg_grupo = croqui_pb2.SetorOuGrupo()
        novo_sg_grupo.grupo.conteudo.uid = gerar_uid()
        novo_sg_grupo.grupo.conteudo.nome = titulo
        controller.adicionar_repeated(
            pico,
            "setores_ou_grupos",
            len(pico.setores_ou_grupos),
            novo_sg_grupo,
        )
        return str(novo_sg_grupo.grupo.conteudo.uid)

    for sg in pico.setores_ou_grupos:
        if sg.HasField("setor") and sg.setor.conteudo.nome == titulo:
            return str(sg.setor.conteudo.uid)
    novo_sg_setor = croqui_pb2.SetorOuGrupo()
    novo_sg_setor.setor.conteudo.uid = gerar_uid()
    novo_sg_setor.setor.conteudo.nome = titulo
    controller.adicionar_repeated(
        pico,
        "setores_ou_grupos",
        len(pico.setores_ou_grupos),
        novo_sg_setor,
    )
    return str(novo_sg_setor.setor.conteudo.uid)


def registrar_ferramentas_ciclo_vida(
    servidor: ServidorMCP,
    model: CroquiModel,
    undo_stack: Any,
    workspace: Any | None = None,
    storage: Any | None = None,
    callback_foco: Callable[[str, str], None] | None = None,
    callback_abrir_croqui: Callable[[Path], dict[str, Any] | None] | None = None,
) -> None:
    """
    Registra no `ServidorMCP` as ferramentas de ciclo de vida, gestão de croquis e PDF:
    `aresta_compilar`, `aresta_salvar`, `aresta_focar_elemento`, `aresta_status_workspace`,
    `aresta_particionar_pdf_croqui` e as ferramentas globais de gestão de croquis.
    """
    registrar_ferramentas_gestao_croquis(
        servidor=servidor,
        storage=storage,
        callback_abrir_croqui=callback_abrir_croqui,
    )
    controller = CroquiController(model, undo_stack)

    def _focar_elemento(args: dict[str, Any]) -> dict[str, Any]:
        alvo = str(args.get("alvo") or "")
        pagina = str(args.get("pagina") or "dados")
        _, caminho = resolver_alvo_mcp(model, alvo) if alvo else (None, "")
        uri = f"page:{pagina}/{caminho}" if caminho else f"page:{pagina}"
        model.notificar_foco_requisitado(uri)
        if callback_foco is not None:
            callback_foco(caminho, pagina)
        return {
            "status": "ok",
            "caminho": caminho,
            "pagina": pagina,
            "uri": uri,
        }

    def _status_workspace(_args: dict[str, Any]) -> dict[str, Any]:
        raiz = model.obter_croqui_readonly()
        pilha = _obter_pilha_qt(undo_stack)
        caminho_db = str(workspace.obter_caminho_database()) if workspace is not None else ""
        return {
            "id_croqui": str(getattr(raiz, "id", "")),
            "nome_croqui": str(getattr(raiz, "nome", "")),
            "uid_croqui": str(getattr(raiz, "uid", "")),
            "caminho_database": caminho_db,
            "modificado": not bool(pilha.isClean()),
            "indice_historico": int(pilha.index()),
            "total_comandos": int(pilha.count()),
            "pode_desfazer": bool(pilha.canUndo()),
            "pode_refazer": bool(pilha.canRedo()),
        }

    def _salvar_ou_compilar(_args: dict[str, Any]) -> dict[str, Any]:
        return _executar_salvamento_e_compilacao(model, undo_stack, workspace, storage)

    def _particionar_pdf_croqui(args: dict[str, Any]) -> dict[str, Any]:
        _exigir(
            workspace is not None,
            "Nenhum workspace configurado para particionar o PDF do croqui.",
        )
        assert workspace is not None
        partes_raw = args.get("partes")
        _exigir(
            isinstance(partes_raw, dict) and bool(partes_raw),
            "O parâmetro 'partes' deve ser um dicionário não vazio (ex: {'01_setor': [0, 1]}).",
        )
        assert isinstance(partes_raw, dict)
        partes: dict[str, list[int]] = {
            str(k): [int(p) for p in v] for k, v in partes_raw.items()
        }
        tipos_partes = args.get("tipos_partes") or {}
        caminho_pdf_arg = str(args.get("caminho_pdf") or "").strip()
        incluir_paginas = bool(args.get("incluir_paginas", False))
        apenas_extrair = bool(args.get("apenas_extrair", False))

        caminho_db = workspace.obter_caminho_database()
        pdf_padrao = caminho_db / "raw_original_pdf" / "croqui_original.pdf"
        if caminho_pdf_arg:
            origem_pdf = Path(caminho_pdf_arg)
            _exigir(
                origem_pdf.is_file(),
                f"Arquivo PDF informado não encontrado: '{caminho_pdf_arg}'.",
            )
            pdf_padrao.parent.mkdir(parents=True, exist_ok=True)
            if origem_pdf.resolve() != pdf_padrao.resolve():
                shutil.copy2(origem_pdf, pdf_padrao)
        else:
            _exigir(
                pdf_padrao.is_file(),
                f"PDF original não encontrado em '{pdf_padrao}'. Informe 'caminho_pdf'.",
            )

        (caminho_db / "partes.json").write_text(
            json.dumps(partes, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        pasta_saida = caminho_db / "raw_pdf_contents"
        if pasta_saida.exists():
            shutil.rmtree(pasta_saida, ignore_errors=True)
        pasta_saida.mkdir(parents=True, exist_ok=True)

        list(
            repartir_pdf(
                pdf_padrao,
                partes,
                pasta_saida,
                include_pages=incluir_paginas,
                apenas_extrair=apenas_extrair,
            )
        )

        pasta_imagens_db = caminho_db / "imagens"
        pasta_imagens_db.mkdir(parents=True, exist_ok=True)
        partes_processadas: dict[str, dict[str, Any]] = {}

        for nome_parte, paginas in partes.items():
            tipo_parte = _inferir_tipo_parte(nome_parte, tipos_partes)
            uid_parte = _alocar_ou_obter_uid_parte(model, controller, nome_parte, tipo_parte)
            pasta_imgs_parte = pasta_saida / "imagens" / nome_parte
            imagens_extraidas: list[str] = []
            if pasta_imgs_parte.is_dir():
                for arq_webp in sorted(pasta_imgs_parte.glob("*.webp")):
                    nome_final = f"{nome_parte}_{arq_webp.name}"
                    destino_img = pasta_imagens_db / nome_final
                    shutil.copy2(arq_webp, destino_img)
                    model.definir_imagem_memoria(f"imagens/{nome_final}", arq_webp.read_bytes())
                    imagens_extraidas.append(nome_final)

            partes_processadas[nome_parte] = {
                "tipo": tipo_parte,
                "uid": uid_parte,
                "paginas": paginas,
                "caminho_pdf": str(pasta_saida / f"{nome_parte}.pdf"),
                "imagens_extraidas": imagens_extraidas,
            }

        return {
            "status": "ok",
            "partes_processadas": partes_processadas,
        }

    servidor.registrar_ferramenta(
        nome="aresta_salvar",
        descricao="Salva as alterações em memória para o disco e compila o croqui no workspace ativo.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_salvar_ou_compilar,
    )
    servidor.registrar_ferramenta(
        nome="aresta_compilar",
        descricao="Executa o pipeline de validação e compilação do croqui e retorna a lista de erros ou avisos.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_salvar_ou_compilar,
    )
    servidor.registrar_ferramenta(
        nome="aresta_focar_elemento",
        descricao="Foca e seleciona visualmente um elemento na interface gráfica por UID ou caminho.",
        esquema_entrada={
            "type": "object",
            "properties": {
                "alvo": {"type": "string", "description": "UID ou caminho do elemento."},
                "pagina": {
                    "type": "string",
                    "description": "Página da interface: 'dados', 'imagens', 'mapas' ou 'historico'.",
                },
            },
        },
        manipulador=_focar_elemento,
    )
    servidor.registrar_ferramenta(
        nome="aresta_status_workspace",
        descricao="Retorna metadados do workspace ativo, estado de modificação e contadores da pilha de histórico.",
        esquema_entrada={"type": "object", "properties": {}},
        manipulador=_status_workspace,
    )
    servidor.registrar_ferramenta(
        nome="aresta_particionar_pdf_croqui",
        descricao=(
            "Divide o PDF original do croqui em sub-PDFs por parte lógica, extrai imagens WebP "
            "e metadados vetoriais, e pré-aloca/reconcilia os UIDs (Botao, Setor, Grupo, "
            "ColecaoDeMapas) na árvore do croqui."
        ),
        esquema_entrada={
            "type": "object",
            "properties": {
                "partes": {
                    "type": "object",
                    "description": "Mapa de nome da parte para lista de índices de páginas 0-based.",
                },
                "tipos_partes": {
                    "type": "object",
                    "description": (
                        "Mapa opcional de nome da parte para tipo ('botao', 'setor', "
                        "'grupo' ou 'mapas_gerais')."
                    ),
                },
                "caminho_pdf": {
                    "type": "string",
                    "description": "Caminho opcional do arquivo PDF original.",
                },
                "incluir_paginas": {
                    "type": "boolean",
                    "description": "Extrair também páginas inteiras como imagem.",
                },
                "apenas_extrair": {
                    "type": "boolean",
                    "description": "Extrair componentes de imagem sem agrupar tiles.",
                },
            },
            "required": ["partes"],
        },
        manipulador=_particionar_pdf_croqui,
    )
