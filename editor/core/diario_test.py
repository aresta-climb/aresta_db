# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pickle
import pytest
from pathlib import Path
from editor.core.diario import GerenciadorDiario


def test_gerenciador_diario_gravar_e_ler_pendente(tmp_path):
    # DADO um diretório de croqui
    diario = GerenciadorDiario(tmp_path)
    assert not diario.tem_alteracoes_pendentes()
    
    # QUANDO gravar comandos no diário pendente
    cmd1 = {"classe": "CmdAlterarPrimitivo", "campo": "nome", "valor": "A"}
    cmd2 = {"classe": "CmdAlterarPrimitivo", "campo": "nome", "valor": "B"}
    
    diario.gravar_comando_pendente(cmd1)
    diario.gravar_comando_pendente(cmd2)
    
    # ENTÃO deve acusar alterações pendentes
    assert diario.tem_alteracoes_pendentes()
    
    # E a leitura deve retornar os comandos na mesma ordem
    comandos = diario.ler_diario_pendente()
    assert len(comandos) == 2
    assert comandos[0] == cmd1
    assert comandos[1] == cmd2


def test_gerenciador_diario_consolidar_salvamento(tmp_path):
    diario = GerenciadorDiario(tmp_path)
    
    # Grava 2 comandos pendentes
    cmd1 = {"classe": "Cmd1"}
    cmd2 = {"classe": "Cmd2"}
    diario.gravar_comando_pendente(cmd1)
    diario.gravar_comando_pendente(cmd2)
    
    # QUANDO consolidar salvamento
    diario.consolidar_salvamento()
    
    # ENTÃO o pendente deve ser esvaziado
    assert not diario.tem_alteracoes_pendentes()
    assert len(diario.ler_diario_pendente()) == 0
    
    # E o diário salvo deve conter os comandos
    salvos = diario.ler_diario_salvo()
    assert len(salvos) == 2
    assert salvos[0] == cmd1
    assert salvos[1] == cmd2
    
    # Ao adicionar mais um e consolidar novamente, deve concatenar no salvo
    cmd3 = {"classe": "Cmd3"}
    diario.gravar_comando_pendente(cmd3)
    diario.consolidar_salvamento()
    
    salvos_apos = diario.ler_diario_salvo()
    assert len(salvos_apos) == 3
    assert salvos_apos[2] == cmd3


def test_gerenciador_diario_descartar_pendente(tmp_path):
    diario = GerenciadorDiario(tmp_path)
    
    diario.gravar_comando_pendente({"classe": "CmdX"})
    assert diario.tem_alteracoes_pendentes()
    
    # QUANDO descartar
    diario.descartar_pendente()
    
    # ENTÃO não deve mais ter alterações pendentes
    assert not diario.tem_alteracoes_pendentes()
    assert len(diario.ler_diario_pendente()) == 0


def test_gerenciador_diario_leitura_resiliente_arquivo_corrompido(tmp_path):
    diario = GerenciadorDiario(tmp_path)
    
    cmd1 = {"classe": "CmdValido1"}
    cmd2 = {"classe": "CmdValido2"}
    diario.gravar_comando_pendente(cmd1)
    diario.gravar_comando_pendente(cmd2)
    
    # Simula corte de energia corrompendo o final do arquivo
    caminho_pendente = tmp_path / "diario_pendente.bin"
    with open(caminho_pendente, "ab") as f:
        f.write(b"lixo_binario_corrompido_incompleto")
        
    # QUANDO ler o arquivo com final corrompido
    comandos = diario.ler_diario_pendente()
    
    # ENTÃO os comandos válidos anteriores devem ser recuperados sem lançar exceção
    assert len(comandos) == 2
    assert comandos[0] == cmd1
    assert comandos[1] == cmd2


def test_gerenciador_diario_exportar_anonimizado(tmp_path):
    diario = GerenciadorDiario(tmp_path)
    
    from PIL import Image
    import io
    img = Image.new("RGB", (200, 150), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    
    cmd_com_imagem = {
        "classe": "CmdAlterarCampoImagem",
        "campo_nome": "caminho_thumbnail",
        "bytes_novo": img_bytes,
        "caminho_novo": "thumb.webp"
    }
    diario.gravar_comando_pendente(cmd_com_imagem)
    
    # QUANDO exportar versão anonimizada
    exportados = diario.exportar_diario_anonimizado()
    
    # ENTÃO a imagem deve ser substituída por dummy WebP reduzido
    assert len(exportados) == 1
    bytes_anon = exportados[0]["bytes_novo"]
    assert bytes_anon != img_bytes
    assert len(bytes_anon) < 1024
    
    with Image.open(io.BytesIO(bytes_anon)) as img_out:
        assert img_out.format == "WEBP"
        assert img_out.size == (200, 150)


def test_gerenciador_diario_apenas_pendente(tmp_path):
    diario = GerenciadorDiario(tmp_path, apenas_pendente=True)
    diario.gravar_comando_pendente({"classe": "CmdLocal"})
    assert diario.tem_alteracoes_pendentes()

    diario.consolidar_salvamento()
    assert not diario.tem_alteracoes_pendentes()
    # No modo apenas_pendente, diario_salvo.bin não deve ser criado
    assert not diario.caminho_salvo.exists()
    assert len(diario.ler_diario_salvo()) == 0
