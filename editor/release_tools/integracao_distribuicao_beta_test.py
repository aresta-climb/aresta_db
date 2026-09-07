# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
from unittest.mock import MagicMock, patch
from pathlib import Path

from editor.release_tools.gerador_appinstaller import gerar_conteudo_appinstaller
from editor.release_tools.gerador_instalador_bat import gerar_script_instalador_bat
from editor.release_tools.publicador_r2_beta import PublicadorR2Beta


def test_integracao_contrato_ponta_a_ponta_distribuicao_beta(tmp_path: Path) -> None:
    """
    Testa o contrato de integração de ponta a ponta do pipeline de distribuição:
    1. Geração do XML .appinstaller com parâmetros de versão e URI do R2.
    2. Geração do script .bat auto-contido com certificado X.509 embutido.
    3. Upload dos artefatos estáticos para o bucket R2 mockado.
    4. Purgação de cache das URLs correspondentes na Cloudflare via API mockada.
    """
    versao = "1.2.0.0"
    uri_base = "https://serving.arestaclimb.com/editor-beta"
    url_sucesso = "https://arestaclimb.com/editor/beta/certificado-instalado"
    certificado_falso_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIBtestecertificadofalsobase64==\n"
        "-----END CERTIFICATE-----"
    )

    # 1. Geração do .appinstaller
    conteudo_appinstaller = gerar_conteudo_appinstaller(versao, uri_base)
    assert f'Version="{versao}"' in conteudo_appinstaller
    assert f'Uri="{uri_base}/EditorArestaBeta.msix"' in conteudo_appinstaller
    assert 'HoursBetweenUpdateChecks="0"' in conteudo_appinstaller

    # 2. Geração do .bat auto-contido
    conteudo_bat = gerar_script_instalador_bat(certificado_falso_pem, url_sucesso)
    assert "-WindowStyle Hidden" in conteudo_bat
    assert 'certutil -decode "%~f0"' in conteudo_bat
    assert 'certutil -addstore -f "TrustedPeople"' in conteudo_bat
    assert 'start "" "https://arestaclimb.com/editor/beta/certificado-instalado?origem=instalador&thumbprint=' in conteudo_bat
    assert certificado_falso_pem in conteudo_bat

    # 3 & 4. Simulação de upload no R2 e purgação de cache
    caminho_appinstaller = tmp_path / "EditorAresta.appinstaller"
    caminho_appinstaller.write_text(conteudo_appinstaller, encoding="utf-8")

    caminho_msix = tmp_path / "EditorArestaBeta.msix"
    caminho_msix.write_bytes(b"PK\x03\x04conteudo_msix_falso")

    caminho_bat = tmp_path / "InstalarCertificadoEditorArestaBeta.bat"
    caminho_bat.write_text(conteudo_bat, encoding="utf-8")

    mock_cliente_s3 = MagicMock()
    mock_resposta_purge = MagicMock()
    mock_resposta_purge.__enter__.return_value.status = 200

    publicador = PublicadorR2Beta(
        cliente_s3=mock_cliente_s3,
        bucket="aresta-serving",
        zone_id="zona_teste_123",
        api_token="token_teste_abc",
        uri_base=uri_base,
    )

    with patch("urllib.request.urlopen", return_value=mock_resposta_purge) as mock_urlopen:
        resultado = publicador.publicar_e_purgar(
            caminho_appinstaller=caminho_appinstaller,
            caminho_msix=caminho_msix,
            caminho_bat=caminho_bat,
        )

        assert resultado is True

        # Verifica uploads no S3
        assert mock_cliente_s3.upload_file.call_count == 3
        chamadas_upload = [chamada[0] for chamada in mock_cliente_s3.upload_file.call_args_list]
        chaves_remotas = [args[2] for args in chamadas_upload]
        assert "editor-beta/EditorAresta.appinstaller" in chaves_remotas
        assert "editor-beta/EditorArestaBeta.msix" in chaves_remotas
        assert "editor-beta/InstalarCertificadoEditorArestaBeta.bat" in chaves_remotas

        # Verifica chamada de purgação de cache na Cloudflare
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert "https://api.cloudflare.com/client/v4/zones/zona_teste_123/purge_cache" in req.full_url
        dados_purge = json.loads(req.data.decode("utf-8"))
        assert f"{uri_base}/EditorAresta.appinstaller" in dados_purge["files"]
        assert f"{uri_base}/EditorArestaBeta.msix" in dados_purge["files"]
