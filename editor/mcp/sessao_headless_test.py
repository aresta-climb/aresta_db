# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
import json
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication

from editor.mcp.sessao_headless import (
    abrir_editor_headless,
    executar_servidor_stdio_headless,
    garantir_aplicacao_qt_headless,
)


def _criar_croqui_dr_gravata_fake(pasta_db: Path) -> None:
    pasta_db.mkdir(parents=True, exist_ok=True)
    pasta_img = pasta_db / "imagens"
    pasta_img.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 80), color="gray").save(pasta_img / "thumbnail.webp", "WEBP")

    (pasta_db / "croqui.yaml").write_text(
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        "uid: IueFHQqpIFT4cY\n"
        "id: br_mg_betim_pedreira_dr_gravata\n"
        "nome: Pedreira Dr. Gravatá\n"
        "ultima_migracao: 5\n"
        "caminho_thumbnail: imagens/thumbnail.webp\n"
        "publicar_croqui: true\n"
        "picos:\n"
        "- nome: Pedreira Dr. Gravatá\n"
        "  estado: MG\n"
        "  cidade: Betim\n"
        "  setores_ou_grupos:\n"
        "  - grupo:\n"
        "      caminho: grupo_setores.md\n",
        encoding="utf-8",
    )
    (pasta_db / "grupo_setores.md").write_text(
        "---\n"
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        "uid: QtxIGEyTkA9Q5c\n"
        "nome: Setores\n"
        "setores:\n"
        "- caminho: setor_das_treze.md\n"
        "---\n",
        encoding="utf-8",
    )
    (pasta_db / "setor_das_treze.md").write_text(
        "---\n"
        "# SPDX-License-Identifier: ODbL-1.0\n"
        "# Copyright (C) 2026 Aresta Climb Contributors\n"
        "uid: 8SUSM2sgVKSevu\n"
        "nome: Setor das Treze\n"
        "escaladas:\n"
        "- uid: TC8Wd0pa4YopiM\n"
        "  via_esportiva:\n"
        "    nome: CONFUSAO MENTAL\n"
        "    dificuldade: BR_7A\n"
        "    conquistadores:\n"
        "    - Macena, Samuel, Maceninha\n"
        "---\n",
        encoding="utf-8",
    )


def test_sessao_editor_headless_resolve_cenario_issue_108_sem_widgets(tmp_path: Path) -> None:
    """
    Valida que SessaoEditorHeadless abre croqui a partir de pasta ou croqui.yaml sem criar janelas,
    cria um novo setor ('Setor do Palanque'), migra 'CONFUSAO MENTAL' preservando o UID,
    ajusta conquistadores e salva com compilação real sem sujar fora de database/<id>.
    """
    app = garantir_aplicacao_qt_headless()
    assert app is not None

    raiz_repo = tmp_path / "repo"
    pasta_db = raiz_repo / "database" / "br_mg_betim_pedreira_dr_gravata"
    _criar_croqui_dr_gravata_fake(pasta_db)

    janelas_antes = len(QApplication.topLevelWidgets()) if isinstance(app, QApplication) else 0

    with abrir_editor_headless(pasta_db / "croqui.yaml") as sessao:
        janelas_durante = (
            len(QApplication.topLevelWidgets()) if isinstance(app, QApplication) else 0
        )
        assert janelas_durante == janelas_antes
        assert sessao.id_croqui == "br_mg_betim_pedreira_dr_gravata"
        assert sessao.caminho_database == pasta_db.resolve()
        assert any(f["name"] == "aresta_migrar_escalada" for f in sessao.listar_ferramentas())

        # 1. Criar o novo 'Setor do Palanque' dentro do grupo QtxIGEyTkA9Q5c
        res_novo_setor = sessao.chamar_ferramenta(
            "aresta_adicionar_repeated",
            {
                "alvo": "QtxIGEyTkA9Q5c",
                "campo": "setores",
                "valor": {"nome": "Setor do Palanque"},
            },
        )
        assert res_novo_setor["isError"] is False
        uid_palanque = res_novo_setor["structuredContent"]["uid"]
        assert uid_palanque

        # 2. Migrar a via CONFUSAO MENTAL (TC8Wd0pa4YopiM) preservando seu UID
        res_migrar = sessao.chamar_ferramenta(
            "aresta_migrar_escalada",
            {
                "alvo_escalada": "TC8Wd0pa4YopiM",
                "alvo_setor_destino": uid_palanque,
            },
        )
        assert res_migrar["isError"] is False
        assert res_migrar["structuredContent"]["uid"] == "TC8Wd0pa4YopiM"

        # 3. Ajustar conquistadores removendo Maceninha
        res_alt = sessao.chamar_ferramenta(
            "aresta_alterar_campo",
            {
                "alvo": "TC8Wd0pa4YopiM",
                "campo": "conquistadores",
                "valor": ["Macena, Samuel"],
            },
        )
        assert res_alt["isError"] is False

        # 4. Salvar e compilar no disco
        res_salvar = sessao.chamar_ferramenta("aresta_salvar", {})
        assert res_salvar["isError"] is False
        assert res_salvar["structuredContent"]["mensagens"] == []
        assert (sessao.obter_caminho_compilado() / "compilado.binarypb").is_file()

        # Ferramenta inexistente retorna isError=True estruturado
        res_inexistente = sessao.chamar_ferramenta("aresta_ferramenta_que_nao_existe", {})
        assert res_inexistente["isError"] is True
        assert "desconhecida" in res_inexistente["content"][0]["text"]

    # Novo arquivo de setor criado com SPDX ODbL-1.0, via migrada e sem sujar fora de database/
    arquivos_setor_novo = [
        p for p in pasta_db.glob("*.md") if p.name not in {"grupo_setores.md", "setor_das_treze.md"}
    ]
    assert len(arquivos_setor_novo) == 1
    texto_novo_setor = arquivos_setor_novo[0].read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: ODbL-1.0" in texto_novo_setor
    assert "Setor do Palanque" in texto_novo_setor
    assert "TC8Wd0pa4YopiM" in texto_novo_setor
    assert "Macena, Samuel" in texto_novo_setor
    assert "Maceninha" not in texto_novo_setor
    assert "CONFUSAO MENTAL" not in (pasta_db / "setor_das_treze.md").read_text(encoding="utf-8")
    assert not (raiz_repo / "generated").exists()
    assert not (raiz_repo / "STATUS_CROQUIS.md").exists()


def test_sessao_editor_headless_falha_caminho_invalido_e_loop_stdio(tmp_path: Path) -> None:
    """Valida erro explícito para caminho sem croqui.yaml e processamento completo do servidor stdio."""
    with pytest.raises(FileNotFoundError, match=r"croqui\.yaml"):
        abrir_editor_headless(tmp_path / "pasta_inexistente")

    pasta_db = tmp_path / "database" / "br_mg_betim_pedreira_dr_gravata"
    _criar_croqui_dr_gravata_fake(pasta_db)

    with abrir_editor_headless(pasta_db) as sessao:
        entrada = io.StringIO(
            "\n"
            "{json_invalido\n"
            + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
            + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {}})
            + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "tools/call",
                    "params": {"name": "aresta_status_workspace", "arguments": {}},
                }
            )
            + "\n"
        )
        saida = io.StringIO()
        codigo = executar_servidor_stdio_headless(sessao, entrada=entrada, saida=saida)
        assert codigo == 0

        respostas = [json.loads(linha) for linha in saida.getvalue().splitlines() if linha.strip()]
        assert len(respostas) == 3
        assert respostas[0]["error"]["code"] == -32700
        assert respostas[1]["id"] == 10
        assert respostas[1]["result"]["serverInfo"]["name"] == "editor-aresta"
        assert respostas[2]["id"] == 11
        assert (
            respostas[2]["result"]["structuredContent"]["id_croqui"]
            == "br_mg_betim_pedreira_dr_gravata"
        )
