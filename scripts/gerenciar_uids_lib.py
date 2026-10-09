# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Biblioteca pura de gerenciamento de UIDs universais e links canônicos aresta.cc.

Esta biblioteca é o ponto único da verdade para criação, validação e formatação
de identificadores imutáveis NanoID 14c em Base62 para todo o ecossistema Aresta Climb.
O uso da biblioteca externa 'nanoid' é estritamente encapsulado neste módulo.
"""

from typing import Optional, Dict, Any, Tuple, List, Union
import io
import re
import string
import urllib.parse
from pathlib import Path
from ruamel.yaml import YAML
import nanoid

# Alfabeto Base62 estritamente alfanumérico contínuo: [0-9a-zA-Z]
ALFABETO_BASE62: str = string.digits + string.ascii_letters
TAMANHO_UID: int = 14
DOMINIO_CURTO: str = "aresta.cc"
PREFIXO_URL: str = f"https://{DOMINIO_CURTO}/"

_REGEX_UID = re.compile(r"^[0-9a-zA-Z]{14}$")


def gerar_uid() -> str:
    """Gera um NanoID de 14 caracteres Base62 contínuo, seguro e sem viés estatístico.

    Utiliza o algoritmo oficial do nanoid com CSPRNG do sistema operacional
    e o alfabeto Base62 [0-9a-zA-Z].
    """
    return str(nanoid.generate(alphabet=ALFABETO_BASE62, size=TAMANHO_UID))


def validar_uid(uid: Optional[str]) -> bool:
    """Valida se o identificador possui exatamente 14 caracteres alfanuméricos Base62.

    Rejeita nulos, tamanhos diferentes de 14, caracteres especiais (incluindo
    hífens e underscores) e espaços.
    """
    if not isinstance(uid, str):
        return False
    return bool(_REGEX_UID.match(uid))


def formatar_url_aresta(uid: str) -> str:
    """Retorna a URL canônica encurtada correspondente ao UID informado.

    Formato: https://aresta.cc/<uid> (exatamente 32 caracteres).
    Levanta ValueError se o UID for inválido.
    """
    if not validar_uid(uid):
        raise ValueError(f"UID inválido: '{uid}'. Deve conter exatamente 14 caracteres Base62.")
    return f"{PREFIXO_URL}{uid}"


def extrair_uid_de_url(url: str) -> Optional[str]:
    """Extrai e valida o UID a partir de uma URL curta ou link escaneado.

    Aceita variações com http, https, com ou sem barra final, e parâmetros de consulta.
    Retorna None se a URL não pertencer ao domínio aresta.cc ou se o UID for inválido.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    texto = url.strip()
    if not texto.startswith(("http://", "https://")):
        texto = f"https://{texto}"

    try:
        parsed = urllib.parse.urlparse(texto)
    except Exception:
        return None

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if host != DOMINIO_CURTO:
        return None

    caminho = parsed.path.strip("/")
    if not caminho:
        return None

    segmentos = caminho.split("/")
    candidato = segmentos[0]

    if validar_uid(candidato):
        return candidato

    return None


def _inserir_ou_mover_para_posicao(mapa: Any, chave: str, valor: Any = None, pos: int = 0) -> None:
    """Insere ou move uma chave para uma posição específica (padrão 0 = início) preservando ruamel.yaml CommentedMap."""
    if hasattr(mapa, "insert"):
        if chave in mapa:
            val = mapa.pop(chave)
            mapa.insert(pos, chave, valor if valor is not None else val)
        elif valor is not None:
            mapa.insert(pos, chave, valor)
    elif isinstance(mapa, dict):
        if chave in mapa:
            val = mapa.pop(chave)
            novo_val = valor if valor is not None else val
        elif valor is not None:
            novo_val = valor
        else:
            return
        itens = list(mapa.items())
        itens.insert(pos, (chave, novo_val))
        mapa.clear()
        for k, v in itens:
            mapa[k] = v


def _obter_yaml() -> YAML:
    """Configura instância do ruamel.yaml com preservação estrita de comentários e formatação."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 120
    y.representer.ignore_aliases = lambda *data: True
    return y


def _carregar_md_ruamel(caminho: Path) -> Tuple[Optional[Any], str, Optional[YAML]]:
    """Lê um arquivo Markdown e faz o parse do Frontmatter preservando formatação e comentários."""
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except Exception:
        return None, "", None

    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n(.*))?$", conteudo, re.DOTALL)
    if not match:
        return None, conteudo, None

    y = _obter_yaml()
    try:
        dados = y.load(match.group(1)) or {}
    except Exception:
        return None, conteudo, None

    corpo = match.group(2) or ""
    return dados, corpo, y


def _salvar_md_ruamel(caminho: Path, dados: Any, corpo: str, y: YAML) -> None:
    """Salva o Frontmatter e o corpo preservando comentários originais."""
    stream = io.StringIO()
    y.dump(dados, stream)
    texto_yaml = stream.getvalue().strip()
    texto_corpo = corpo.strip()
    if texto_corpo:
        caminho.write_text(f"---\n{texto_yaml}\n---\n\n{texto_corpo}\n", encoding="utf-8")
    else:
        caminho.write_text(f"---\n{texto_yaml}\n---\n", encoding="utf-8")


def _extrair_nome_escalada(escalada: Dict[str, Any]) -> str:
    """Extrai o nome de uma escalada suportando modelo plano ou polimórfico."""
    if not isinstance(escalada, dict):
        return ""
    if "nome" in escalada and isinstance(escalada["nome"], str):
        return escalada["nome"].strip()
    for subtipo in (
        "via_esportiva",
        "via_movel",
        "via_tradicional",
        "boulder",
        "via_psicobloc",
        "via_artificial",
        "highline",
        "via_multiplas_enfiadas",
    ):
        conteudo_sub = escalada.get(subtipo)
        if isinstance(conteudo_sub, dict) and "nome" in conteudo_sub:
            return str(conteudo_sub.get("nome", "")).strip()
    return ""


def sanear_uids_croqui(pico_path: Union[str, Path]) -> bool:
    """Executa o saneamento contínuo e idempotente de UIDs e referências de mapas em um croqui.

    Garante que todas as entidades (Croqui, Grupo, Setor, Escalada, PontoDeInteresse e Botao)
    possuam NanoIDs 14c Base62 válidos, que labels legados sejam convertidos para rotulo,
    e que referências semânticas textuais (escalada/setor/grupo) sejam convertidas para alvo_uid/pontos_uids,
    preservando integralmente os UIDs pré-existentes.
    Retorna True se algum arquivo foi modificado no disco, False caso contrário.
    """
    pico_path = Path(pico_path)
    houve_modificacao = False

    # 1. Saneia croqui.yaml
    caminho_yaml = pico_path / "croqui.yaml"
    if caminho_yaml.exists():
        y = _obter_yaml()
        try:
            dados_croqui = y.load(caminho_yaml.read_text(encoding="utf-8")) or {}
        except Exception:
            dados_croqui = {}

        if dados_croqui:
            modificado_yaml = False
            croqui_uid = dados_croqui.get("uid")
            if croqui_uid is None or str(croqui_uid).strip() == "":
                croqui_uid = gerar_uid()
                _inserir_ou_mover_para_posicao(dados_croqui, "uid", croqui_uid, 0)
                modificado_yaml = True

            for botao in dados_croqui.get("botoes", []):
                if isinstance(botao, dict):
                    botao_uid = botao.get("uid")
                    if botao_uid is None or str(botao_uid).strip() == "":
                        botao_uid = gerar_uid()
                        _inserir_ou_mover_para_posicao(botao, "uid", botao_uid, 0)
                        modificado_yaml = True

            if modificado_yaml:
                stream = io.StringIO()
                y.dump(dados_croqui, stream)
                caminho_yaml.write_text(stream.getvalue(), encoding="utf-8")
                houve_modificacao = True

    # 2. Primeira passagem pelos arquivos .md: atribui UIDs a setores, grupos e escaladas,
    # e constrói o índice de resolução de nomes para referências
    arquivos_md: List[Path] = [p for p in pico_path.glob("*.md") if p.is_file()]
    dados_md_carregados: Dict[Path, Tuple[Any, str, YAML, bool]] = {}

    mapa_escaladas_com_setor: Dict[Tuple[str, str], str] = {}
    mapa_escaladas_simples: Dict[str, str] = {}
    mapa_setores: Dict[str, str] = {}
    mapa_grupos: Dict[str, str] = {}

    for md_path in arquivos_md:
        dados, corpo, inst_y = _carregar_md_ruamel(md_path)
        if dados is None or not isinstance(dados, dict) or inst_y is None:
            continue

        nome_lower = str(dados.get("nome", "")).lower()
        eh_setor = md_path.name.startswith("setor") or "escaladas" in dados or nome_lower.startswith("setor")
        eh_grupo = md_path.name.startswith("grupo") or "setores" in dados or "sub_setores" in dados or nome_lower.startswith("grupo")
        eh_mapa = md_path.name.startswith("mapas") or "mapas" in dados

        if not (eh_setor or eh_grupo or eh_mapa):
            # Arquivo auxiliar de texto (ex: capa.md, avisos.md):
            # Preserva comentários de licença e outros campos, mas garante que não possui UID nem ID no frontmatter
            if "uid" in dados or "id" in dados:
                dados.pop("uid", None)
                dados.pop("id", None)
                _salvar_md_ruamel(md_path, dados, corpo, inst_y)
                houve_modificacao = True
            continue

        modificado_md = False

        if eh_setor or eh_grupo:
            # Garante UID da entidade raiz (Setor ou Grupo) se ausente
            s_uid = dados.get("uid")
            if s_uid is None or str(s_uid).strip() == "":
                setor_ou_grupo_uid = gerar_uid()
                _inserir_ou_mover_para_posicao(dados, "uid", setor_ou_grupo_uid, 0)
                modificado_md = True
            else:
                setor_ou_grupo_uid = s_uid

            nome_entidade = str(dados.get("nome", "")).strip()
            if eh_setor:
                if nome_entidade:
                    mapa_setores[nome_entidade] = dados["uid"]
                    if nome_entidade.lower().startswith("setor "):
                        mapa_setores[nome_entidade[6:].strip()] = dados["uid"]
                    else:
                        mapa_setores[f"Setor {nome_entidade}"] = dados["uid"]
            else:
                if nome_entidade:
                    mapa_grupos[nome_entidade] = dados["uid"]
                    if nome_entidade.lower().startswith("grupo "):
                        mapa_grupos[nome_entidade[6:].strip()] = dados["uid"]
                    else:
                        mapa_grupos[f"Grupo {nome_entidade}"] = dados["uid"]

            # Garante UIDs de todas as escaladas se ausente
            for escalada in dados.get("escaladas", []):
                if isinstance(escalada, dict):
                    e_uid = escalada.get("uid")
                    if e_uid is None or str(e_uid).strip() == "":
                        esc_uid = gerar_uid()
                        _inserir_ou_mover_para_posicao(escalada, "uid", esc_uid, 0)
                        modificado_md = True
                    else:
                        esc_uid = e_uid

                    nome_via = _extrair_nome_escalada(escalada)
                    if nome_via:
                        if nome_entidade:
                            mapa_escaladas_com_setor[(nome_entidade, nome_via)] = escalada["uid"]
                        mapa_escaladas_simples[nome_via] = escalada["uid"]

        dados_md_carregados[md_path] = (dados, corpo, inst_y, modificado_md)

    # 3. Segunda passagem pelos arquivos .md: migra mapas (POIs e referências)
    for md_path, (dados, corpo, y, modificado_passagem1) in dados_md_carregados.items():
        modificado_md = modificado_passagem1
        nome_setor_atual = str(dados.get("nome", "")).strip()
        mapas = dados.get("mapas", [])
        if isinstance(mapas, list):
            for mapa in mapas:
                if not isinstance(mapa, dict):
                    continue

                # 3.1 Migra pontos de interesse: label -> rotulo e atribui UIDs, posicionando uid e rotulo no início
                poi_id_para_uid: Dict[str, str] = {}
                for poi in mapa.get("pontos_de_interesse", []):
                    if not isinstance(poi, dict):
                        continue

                    # Extrai / remove label legado
                    if "label" in poi:
                        label_legado = poi.pop("label")
                        rotulo = poi.get("rotulo") or label_legado
                        poi["rotulo"] = rotulo
                        modificado_md = True

                    # Atribui UID se ausente
                    p_uid = poi.get("uid")
                    if p_uid is None or str(p_uid).strip() == "":
                        poi_uid = gerar_uid()
                        _inserir_ou_mover_para_posicao(poi, "uid", poi_uid, 0)
                        modificado_md = True
                    else:
                        poi_uid = p_uid

                    if "id" in poi:
                        poi_id_para_uid[str(poi["id"])] = poi_uid
                        del poi["id"]
                        modificado_md = True

                    # Garante posicionamento canônico: uid na pos 0 e rotulo na pos 1
                    if "rotulo" in poi:
                        chaves = list(poi.keys())
                        if len(chaves) >= 2 and (chaves[0] != "uid" or chaves[1] != "rotulo"):
                            _inserir_ou_mover_para_posicao(poi, "rotulo", poi["rotulo"], 0)
                            _inserir_ou_mover_para_posicao(poi, "uid", poi_uid, 0)
                            modificado_md = True

                # 3.2 Migra referências: alvo_uid, pontos_uids e remove strings legadas
                for ref in mapa.get("referencias", []):
                    if not isinstance(ref, dict):
                        continue

                    # Converte alvo_uid se ausente
                    alvo_uid = ref.get("alvo_uid")
                    if alvo_uid is None or str(alvo_uid).strip() == "":
                        alvo_uid_encontrado: Optional[str] = None
                        if "escalada" in ref:
                            nome_via = str(ref.get("escalada", "")).strip()
                            nome_setor = str(ref.get("setor", "")).strip() or nome_setor_atual
                            alvo_uid_encontrado = mapa_escaladas_com_setor.get((nome_setor, nome_via)) or mapa_escaladas_simples.get(nome_via)
                        elif "setor" in ref:
                            nome_setor = str(ref.get("setor", "")).strip()
                            alvo_uid_encontrado = mapa_setores.get(nome_setor) or mapa_grupos.get(nome_setor)
                        elif "grupo" in ref:
                            nome_grupo = str(ref.get("grupo", "")).strip()
                            alvo_uid_encontrado = mapa_grupos.get(nome_grupo) or mapa_setores.get(nome_grupo)

                        if alvo_uid_encontrado:
                            alvo_uid = alvo_uid_encontrado
                            _inserir_ou_mover_para_posicao(ref, "alvo_uid", alvo_uid, 0)
                            modificado_md = True

                    # Converte pontos_uids se ausente
                    if "pontos_uids" not in ref or ref.get("pontos_uids") is None:
                        ids_locais = ref.get("ids", [])
                        if isinstance(ids_locais, list):
                            pontos_uids = [
                                poi_id_para_uid.get(str(pid), pid) for pid in ids_locais
                            ]
                            _inserir_ou_mover_para_posicao(ref, "pontos_uids", pontos_uids, 0)
                            modificado_md = True

                    # Remove campos legados ids e indice_mapa_alvo
                    if "ids" in ref:
                        del ref["ids"]
                        modificado_md = True
                    if "indice_mapa_alvo" in ref:
                        del ref["indice_mapa_alvo"]
                        modificado_md = True

                    # Remove obrigatoriamente campos textuais legados se alvo_uid foi resolvido
                    if validar_uid(str(ref.get("alvo_uid") or "")):
                        if "escalada" in ref:
                            del ref["escalada"]
                            modificado_md = True
                        if "setor" in ref:
                            del ref["setor"]
                            modificado_md = True
                        if "grupo" in ref:
                            del ref["grupo"]
                            modificado_md = True

                    # Garante posicionamento canônico: alvo_uid na pos 0 e pontos_uids na pos 1
                    if "alvo_uid" in ref and "pontos_uids" in ref:
                        chaves_ref = list(ref.keys())
                        if len(chaves_ref) >= 2 and (chaves_ref[0] != "alvo_uid" or chaves_ref[1] != "pontos_uids"):
                            _inserir_ou_mover_para_posicao(ref, "pontos_uids", ref["pontos_uids"], 0)
                            _inserir_ou_mover_para_posicao(ref, "alvo_uid", ref["alvo_uid"], 0)
                            modificado_md = True

        # Salva o arquivo apenas se houve modificações reais
        if modificado_md:
            _salvar_md_ruamel(md_path, dados, corpo, y)
            houve_modificacao = True

    return houve_modificacao

