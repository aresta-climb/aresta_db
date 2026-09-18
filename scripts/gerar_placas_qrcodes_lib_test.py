# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path
from typing import Any
import pytest
from PIL import Image

from scripts.gerar_placas_qrcodes_lib import (
    slugify,
    montar_url_deep_link,
    gerar_qrcode_com_logo,
    gerar_placa_png,
    gerar_placa_svg,
    carregar_imagem_topo,
    obter_logo_aresta_padrao,
    obter_logo_topo_padrao,
    recortar_bordas_vazias,
    extrair_itens_croqui,
    exportar_placas_pico,
    resolver_cor_borda_logo,
)


def test_slugify() -> None:
    assert slugify("Grupo Estacionamento") == "grupo_estacionamento"
    assert slugify("Savassinha") == "savassinha"
    assert slugify("Teto da Aresta") == "teto_da_aresta"
    assert slugify("Pé de Cabra - Setor 2!") == "pe_de_cabra_setor_2"
    assert slugify("") == ""
    assert slugify("   ") == ""


def test_montar_url_deep_link_niveis() -> None:
    # 1 nível (apenas pico)
    url_pico = montar_url_deep_link("br_mg_igarape_pedra_grande")
    assert url_pico == "https://app.arestaclimb.com/br_mg_igarape_pedra_grande"

    # 2 níveis (pico e setor)
    url_setor = montar_url_deep_link(
        "br_mg_igarape_pedra_grande", setor="savassinha"
    )
    assert (
        url_setor == "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"
    )

    # 3 níveis (pico, grupo e setor)
    url_grupo_setor = montar_url_deep_link(
        "br_mg_igarape_pedra_grande",
        grupo="grupo_estacionamento",
        setor="savassinha",
    )
    assert (
        url_grupo_setor
        == "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/grupo_estacionamento/savassinha"
    )

    # 4 níveis (pico, grupo, setor e via)
    url_via = montar_url_deep_link(
        "br_mg_igarape_pedra_grande",
        grupo="grupo_estacionamento",
        setor="savassinha",
        via="teto_da_aresta",
    )
    assert (
        url_via
        == "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/grupo_estacionamento/savassinha/teto_da_aresta"
    )


def test_montar_url_deep_link_host_customizado() -> None:
    url = montar_url_deep_link(
        "br_mg_igarape_pedra_grande",
        setor="savassinha",
        host="staging.arestaclimb.com",
    )
    assert (
        url
        == "https://staging.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"
    )


def test_montar_url_deep_link_pico_obrigatorio() -> None:
    with pytest.raises(ValueError, match="identificador do pico é obrigatório"):
        montar_url_deep_link("")


def test_montar_url_deep_link_com_parametros_utm() -> None:
    # Apenas utm_source e utm_medium
    url = montar_url_deep_link(
        "br_mg_igarape_pedra_grande",
        setor="setor_estacionamento",
        utm_source="setor_igarameca",
        utm_medium="qrcode",
    )
    assert (
        url
        == "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/setor_estacionamento?utm_source=setor_igarameca&utm_medium=qrcode"
    )

    # Com utm_campaign
    url_camp = montar_url_deep_link(
        "br_mg_igarape_pedra_grande",
        setor="setor_estacionamento",
        utm_source="setor_igarameca",
        utm_medium="qrcode",
        utm_campaign="placas_2026",
    )
    assert (
        url_camp
        == "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/setor_estacionamento?utm_source=setor_igarameca&utm_medium=qrcode&utm_campaign=placas_2026"
    )


def test_gerar_qrcode_com_logo(tmp_path: Path) -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"

    # Cria logo temporário para o teste
    caminho_logo = tmp_path / "logo_teste.png"
    img_logo = Image.new("RGBA", (100, 100), color=(217, 119, 6, 255))
    img_logo.save(caminho_logo)

    qr_img = gerar_qrcode_com_logo(
        url=url, caminho_logo=caminho_logo, tamanho_px=400
    )

    assert isinstance(qr_img, Image.Image)
    assert qr_img.size == (400, 400)


def test_gerar_qrcode_sem_logo() -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande"
    qr_img = gerar_qrcode_com_logo(url=url, caminho_logo=None, tamanho_px=300)

    assert isinstance(qr_img, Image.Image)
    assert qr_img.size == (300, 300)


def test_gerar_placa_png(tmp_path: Path) -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/grupo_estacionamento/savassinha"
    placa = gerar_placa_png(
        url=url,
        titulo="Setor Savassinha",
        subtitulo="Pedra Grande · Igarapé, MG",
        largura=800,
        altura=1000,
    )

    assert isinstance(placa, Image.Image)
    assert placa.size == (800, 1000)

    caminho_saida = tmp_path / "placa_savassinha.png"
    placa.save(caminho_saida)
    assert caminho_saida.exists()
    assert caminho_saida.stat().st_size > 1000


def test_gerar_placa_png_padrao_a4() -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"
    placa = gerar_placa_png(
        url=url,
        titulo="Savassinha",
        subtitulo="Pedra Grande",
    )
    assert placa.size == (4960, 7016)


def test_gerar_placa_svg() -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"
    svg = gerar_placa_svg(
        url=url,
        titulo="Setor Savassinha",
        subtitulo="Pedra Grande · Igarapé, MG",
        caminho_logo_aresta="",
    )

    assert isinstance(svg, str)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "SETOR" in svg
    assert "SAVASSINHA" in svg
    assert "Pedra Grande · Igarapé, MG" in svg
    assert "ARESTA CLIMB" in svg
    # Verifica que o link textual foi removido
    assert "app.arestaclimb.com" not in svg


def test_gerar_placa_svg_com_logo_customizado(tmp_path: Path) -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"
    caminho_logo = tmp_path / "logo.png"
    Image.new("RGBA", (50, 50), color=(255, 0, 0, 255)).save(caminho_logo)

    svg = gerar_placa_svg(
        url=url,
        titulo="Setor Savassinha",
        subtitulo="Pedra Grande · Igarapé, MG",
        caminho_logo=caminho_logo,
    )
    assert '<image href="data:image/png;base64,' in svg


def test_gerar_placa_svg_com_erro_leitura_logo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"
    caminho_logo = tmp_path / "logo_erro.png"
    caminho_logo.write_bytes(b"dummy")

    import builtins
    abrir_original = builtins.open

    def mock_open(*args: Any, **kwargs: Any) -> Any:
        if str(caminho_logo) in str(args[0]):
            raise OSError("Falha simulada de leitura")
        return abrir_original(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)
    svg = gerar_placa_svg(
        url=url,
        titulo="Setor Savassinha",
        subtitulo="Pedra Grande",
        caminho_logo=caminho_logo,
        caminho_logo_aresta="",
    )
    assert "<image href=" not in svg


def test_carregar_imagem_topo_casos_diversos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Caminho nulo
    assert carregar_imagem_topo(None) is None

    # 2. Caminho inexistente
    assert carregar_imagem_topo(tmp_path / "inexistente.pdf") is None

    # 3. Imagem comum válida (PNG)
    img_path = tmp_path / "topo.png"
    Image.new("RGBA", (100, 50), color=(0, 100, 200, 255)).save(img_path)
    img_carregada = carregar_imagem_topo(img_path)
    assert img_carregada is not None
    assert img_carregada.size == (100, 50)

    # 4. Imagem com erro de abertura
    img_corrompida = tmp_path / "corrompida.png"
    img_corrompida.write_bytes(b"dados_invalidos")
    assert carregar_imagem_topo(img_corrompida) is None

    # 5. PDF válido (se pymupdf disponível)
    raiz = Path(__file__).resolve().parent.parent
    caminho_pdf = raiz.parent / "aresta_data" / "logo_igarameca.pdf"
    if caminho_pdf.exists():
        img_pdf = carregar_imagem_topo(caminho_pdf)
        assert img_pdf is not None

    # 6. PDF vazio ou inválido
    pdf_corrompido = tmp_path / "teste_erro.pdf"
    pdf_corrompido.write_bytes(b"%PDF-1.4\n%%EOF")
    assert carregar_imagem_topo(pdf_corrompido) is None


def test_obter_logo_topo_padrao() -> None:
    assert obter_logo_topo_padrao(None) is None
    assert obter_logo_topo_padrao("pico_desconhecido") is None
    logo_igarape = obter_logo_topo_padrao("br_mg_igarape_pedra_grande")
    # Se existir em aresta_data, deve retornar o Path
    if logo_igarape is not None:
        assert logo_igarape.exists()


def test_recortar_bordas_vazias() -> None:
    # 1. Totalmente transparente
    img_vazia = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    assert recortar_bordas_vazias(img_vazia).size == (100, 100)

    # 2. Totalmente branca sólida (RGB)
    img_branca = Image.new("RGB", (100, 100), (255, 255, 255))
    assert recortar_bordas_vazias(img_branca).size == (100, 100)

    # 3. Transparente com elemento no centro
    img_com_elemento = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    img_com_elemento.putpixel((50, 50), (200, 50, 50, 255))
    cortada = recortar_bordas_vazias(img_com_elemento)
    assert cortada.size == (1, 1)


def test_obter_logo_aresta_padrao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    padrao = obter_logo_aresta_padrao()
    if padrao is not None:
        assert padrao.exists()

    # Simula quando raiz_projeto vazia é informada
    assert obter_logo_aresta_padrao(raiz_projeto=tmp_path) is None

    # Simula quando nenhum arquivo candidato existe
    real_exists = Path.exists

    def mock_exists(self: Path) -> bool:
        nome = self.name
        if nome in ("logo_splash.png", "logo_aresta_frontal.png"):
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)
    assert obter_logo_aresta_padrao() is None


def test_obter_logo_topo_padrao(tmp_path: Path) -> None:
    # Sem pico informado
    assert obter_logo_topo_padrao(None) is None
    # Pico sem mapeamento de logo institucional
    assert obter_logo_topo_padrao("pico_sem_logo", raiz_projeto=tmp_path) is None
    # Pico mapeado mas diretório sem os arquivos
    assert obter_logo_topo_padrao("br_mg_igarape_pedra_grande", raiz_projeto=tmp_path) is None



def test_gerar_placa_png_e_svg_combinacoes_logos(tmp_path: Path) -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/setor_estacionamento"
    logo_esq = tmp_path / "logo_esq.png"
    Image.new("RGBA", (200, 80), color=(10, 20, 30, 255)).save(logo_esq)

    logo_dir = tmp_path / "logo_dir.png"
    Image.new("RGBA", (150, 150), color=(200, 50, 50, 255)).save(logo_dir)

    # 1. Ambos os logos presentes (duplo)
    png_duplo = gerar_placa_png(
        url=url,
        titulo="Setor Duplo",
        caminho_logo_topo=logo_esq,
        caminho_logo_aresta=logo_dir,
        largura=800,
        altura=1000,
    )
    assert png_duplo.size == (800, 1000)

    svg_duplo = gerar_placa_svg(
        url=url,
        titulo="Setor Duplo",
        caminho_logo_topo=logo_esq,
        caminho_logo_aresta=logo_dir,
        largura=800,
        altura=1000,
    )
    assert "<image href=" in svg_duplo

    # 2. Apenas logo da esquerda (caminho_logo_aresta="")
    png_esq = gerar_placa_png(
        url=url,
        titulo="Setor Esquerdo",
        caminho_logo_topo=logo_esq,
        caminho_logo_aresta="",
        largura=800,
        altura=1000,
    )
    assert png_esq.size == (800, 1000)

    svg_esq = gerar_placa_svg(
        url=url,
        titulo="Setor Esquerdo",
        caminho_logo_topo=logo_esq,
        caminho_logo_aresta="",
        largura=800,
        altura=1000,
    )
    assert "<image href=" in svg_esq

    # 3. Apenas logo da direita (caminho_logo_topo=None)
    png_dir = gerar_placa_png(
        url=url,
        titulo="Setor Direito",
        caminho_logo_topo=None,
        caminho_logo_aresta=logo_dir,
        largura=800,
        altura=1000,
    )
    assert png_dir.size == (800, 1000)

    svg_dir = gerar_placa_svg(
        url=url,
        titulo="Setor Direito",
        caminho_logo_topo=None,
        caminho_logo_aresta=logo_dir,
        largura=800,
        altura=1000,
    )
    assert "<image href=" in svg_dir

    # 4. Nenhum logo (fallback textual puro)
    png_nenhum = gerar_placa_png(
        url=url,
        titulo="Setor Texto",
        subtitulo="Subtítulo Teste",
        caminho_logo_topo=None,
        caminho_logo_aresta="",
        largura=800,
        altura=1000,
    )
    assert png_nenhum.size == (800, 1000)



def criar_croqui_teste_pb(raiz: Path, pico_id: str = "pico_teste") -> Path:
    """Cria uma árvore hermética de teste com um compilado.binarypb válido."""
    from aresta_api.proto.generated import croqui_pb2

    pasta_compilado = raiz / "generated" / pico_id
    pasta_compilado.mkdir(parents=True, exist_ok=True)
    caminho_pb = pasta_compilado / "compilado.binarypb"

    croqui = croqui_pb2.Croqui()
    croqui.nome = "Pedra Grande de Teste"

    pico = croqui.picos.add()
    pico.nome = "Pedra Grande"

    elem_setor = pico.setores_ou_grupos.add()
    setor = elem_setor.setor.conteudo
    setor.nome = "Savassinha"

    via_esp = setor.escaladas.add()
    via_esp.via_esportiva.nome = "Dama de Ferro"
    via_esp.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_7A

    boulder = setor.escaladas.add()
    boulder.boulder.nome = "Boulder Teste"
    boulder.boulder.dificuldade = croqui_pb2.GrauBoulder.V3

    elem_grupo = pico.setores_ou_grupos.add()
    grupo = elem_grupo.grupo.conteudo
    grupo.nome = "Grupo Estacionamento"

    arq_setor = grupo.setores.add()
    setor_filho = arq_setor.conteudo
    setor_filho.nome = "Bloco Dengoso"

    via_filho = setor_filho.escaladas.add()
    via_filho.via_esportiva.nome = "Via Dengosa"
    via_filho.via_esportiva.dificuldade = croqui_pb2.GrauVia.BR_6SUP

    caminho_pb.write_bytes(croqui.SerializeToString())
    return caminho_pb


def test_extrair_itens_croqui_existente(tmp_path: Path) -> None:
    # Testa extração com um pico compilado em Protobuf hermético
    pico_id = "br_mg_igarape_pedra_grande"
    criar_croqui_teste_pb(tmp_path, pico_id=pico_id)
    itens = extrair_itens_croqui(pico_id, raiz_projeto=tmp_path)

    assert len(itens) > 0

    # Deve conter pelo menos o item do pico
    tipos = [item["tipo"] for item in itens]
    assert "pico" in tipos
    assert "setor" in tipos or "grupo" in tipos

    item_pico = next(item for item in itens if item["tipo"] == "pico")
    assert item_pico["pico"] == pico_id
    assert "Pedra Grande" in item_pico["titulo"]


def test_extrair_itens_croqui_nao_encontrado(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="não foi encontrado"):
        extrair_itens_croqui("pico_inexistente_123", raiz_projeto=tmp_path)


def test_exportar_placas_pico(tmp_path: Path) -> None:
    raiz = tmp_path / "projeto"
    criar_croqui_teste_pb(raiz, pico_id="br_mg_igarape_pedra_grande")
    saida = tmp_path / "saida_placas"

    # Por padrão gera PNG A4
    arquivos_gerados = exportar_placas_pico(
        pico_id="br_mg_igarape_pedra_grande",
        diretorio_saida=saida,
        raiz_projeto=raiz,
        limite_itens=2,
        largura=800,
        altura=1000,
    )

    assert len(arquivos_gerados) > 0
    for arq in arquivos_gerados:
        assert arq["png"].exists()
        assert "svg" not in arq


def test_exportar_placas_pico_com_svg(tmp_path: Path) -> None:
    raiz = tmp_path / "projeto"
    criar_croqui_teste_pb(raiz, pico_id="br_mg_igarape_pedra_grande")
    saida_svg = tmp_path / "com_svg"
    arqs_svg = exportar_placas_pico(
        pico_id="br_mg_igarape_pedra_grande",
        diretorio_saida=saida_svg,
        raiz_projeto=raiz,
        limite_itens=2,
        largura=800,
        altura=1000,
        gerar_svg=True,
    )
    assert len(arqs_svg) == 2
    assert "png" in arqs_svg[0]
    assert "svg" in arqs_svg[0]
    assert arqs_svg[0]["png"].exists()
    assert arqs_svg[0]["svg"].exists()


def test_formatar_grau() -> None:
    from scripts.gerar_placas_qrcodes_lib import (
        _formatar_grau_via,
        _formatar_grau_boulder,
    )
    from aresta_api.proto.generated import croqui_pb2

    assert _formatar_grau_via("") == ""
    assert _formatar_grau_via("7a") == "7a"
    assert _formatar_grau_via(None) == ""
    assert _formatar_grau_via(croqui_pb2.GrauVia.BR_7A) == "7a"
    assert _formatar_grau_via(croqui_pb2.GrauVia.BR_5_BARRA_5SUP) == "5/5sup"
    assert _formatar_grau_via(999999) == "999999"

    assert _formatar_grau_boulder("") == ""
    assert _formatar_grau_boulder("V5") == "V5"
    assert _formatar_grau_boulder(None) == ""
    assert _formatar_grau_boulder(croqui_pb2.GrauBoulder.V3) == "V3"
    assert _formatar_grau_boulder(croqui_pb2.GrauBoulder.V3_BARRA_V4) == "V3/V4"
    assert _formatar_grau_boulder(999999) == "999999"


def test_extrair_itens_croqui_com_vias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pico_id = "br_mg_igarape_pedra_grande"
    criar_croqui_teste_pb(tmp_path, pico_id=pico_id)
    # Testa chamada sem raiz_projeto explícito para exercitar o caminho padrão configurado
    import scripts.gerar_placas_qrcodes_lib as lib
    monkeypatch.setattr(lib, "DIRETORIO_RAIZ_PADRAO", tmp_path)

    itens = extrair_itens_croqui(pico_id, incluir_vias=True)
    assert len(itens) > 0
    vias = [item for item in itens if item["tipo"] == "via"]
    assert len(vias) > 0
    via_exemplo = vias[0]
    assert "via" in via_exemplo
    assert via_exemplo["via"] is not None



def test_extrair_itens_croqui_fallback_yaml(tmp_path: Path) -> None:
    # Cria estrutura com banco yaml mas sem compiled binarypb
    pico_id = "pico_teste_yaml"
    dir_banco = tmp_path / "database" / pico_id
    dir_banco.mkdir(parents=True)
    croqui_yaml = dir_banco / "croqui.yaml"
    croqui_yaml.write_text(
        """
nome: Pico Teste
picos:
  - setores_ou_grupos:
      - setor:
          caminho: setor_savassinha.md
      - grupo:
          caminho: grupo_central.md
""",
        encoding="utf-8",
    )

    itens = extrair_itens_croqui(pico_id, raiz_projeto=tmp_path)
    assert len(itens) == 3
    assert itens[0]["tipo"] == "pico"
    assert itens[1]["tipo"] == "setor"
    assert itens[1]["setor"] == "savassinha"
    assert itens[2]["tipo"] == "grupo"
    assert itens[2]["grupo"] == "grupo_central"


def test_obter_fonte_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from typing import Any, cast
    from PIL import ImageFont
    from scripts.gerar_placas_qrcodes_lib import _obter_fonte

    real_truetype = ImageFont.truetype

    def mock_truetype(*args: object, **kwargs: object) -> ImageFont.FreeTypeFont:
        if args and isinstance(args[0], str):
            raise OSError("Fonte não encontrada")
        return cast(ImageFont.FreeTypeFont, cast(Any, real_truetype)(*args, **kwargs))

    monkeypatch.setattr(ImageFont, "truetype", mock_truetype)
    fonte = _obter_fonte(20)
    assert fonte is not None


def test_gerar_qrcode_com_logo_corrompido(tmp_path: Path) -> None:
    corrompido = tmp_path / "corrompido.png"
    corrompido.write_bytes(b"conteudo invalido de imagem")
    qr = gerar_qrcode_com_logo(
        "https://app.arestaclimb.com/teste",
        caminho_logo=corrompido,
        tamanho_px=300,
    )
    assert qr.size == (300, 300)


def test_gerar_qrcode_sem_get_image(monkeypatch: pytest.MonkeyPatch) -> None:
    import qrcode
    from PIL import Image

    class MockImageSemGetImage:
        def __init__(self) -> None:
            self._img = Image.new("RGB", (200, 200), "white")

        def save(self, stream: object, format: str) -> None:
            self._img.save(stream, format=format)  # type: ignore[arg-type]

    real_make_image = qrcode.QRCode.make_image

    def mock_make_image(self: object, *args: object, **kwargs: object) -> object:
        return MockImageSemGetImage()

    monkeypatch.setattr(qrcode.QRCode, "make_image", mock_make_image)
    qr = gerar_qrcode_com_logo("https://app.arestaclimb.com/teste", tamanho_px=200)
    assert qr.size == (200, 200)


def test_resolver_cor_borda_logo() -> None:
    # Tupla RGB
    rgba, hex_code = resolver_cor_borda_logo((10, 20, 30))
    assert rgba == (10, 20, 30, 255)
    assert hex_code == "#0a141e"

    # Tupla RGBA
    rgba, hex_code = resolver_cor_borda_logo((10, 20, 30, 200))
    assert rgba == (10, 20, 30, 200)
    assert hex_code == "#0a141e"

    # Nome conhecido: laranja / orange / marca
    rgba, hex_code = resolver_cor_borda_logo("laranja")
    assert rgba == (234, 83, 65, 255)
    assert hex_code == "#ea5341"

    rgba, hex_code = resolver_cor_borda_logo("orange")
    assert hex_code == "#ea5341"

    # Nome conhecido: cinza / gray / grey
    rgba, hex_code = resolver_cor_borda_logo("cinza")
    assert rgba == (203, 213, 225, 255)
    assert hex_code == "#cbd5e1"

    # Hex 6 dígitos (#rrggbb)
    rgba, hex_code = resolver_cor_borda_logo("#3b82f6")
    assert rgba == (59, 130, 246, 255)
    assert hex_code == "#3b82f6"

    # Hex 3 dígitos (#rgb)
    rgba, hex_code = resolver_cor_borda_logo("#f00")
    assert rgba == (255, 0, 0, 255)
    assert hex_code == "#ff0000"

    # Padrão: preta ou qualquer valor não reconhecido
    rgba, hex_code = resolver_cor_borda_logo("preta")
    assert rgba == (17, 24, 39, 255)
    assert hex_code == "#111827"

    rgba, hex_code = resolver_cor_borda_logo("desconhecido")
    assert rgba == (17, 24, 39, 255)
    assert hex_code == "#111827"


def test_gerar_placas_com_cor_borda_customizada(tmp_path: Path) -> None:
    url = "https://app.arestaclimb.com/br_mg_igarape_pedra_grande/savassinha"

    # Gera PNG com borda laranja
    img = gerar_placa_png(
        url=url,
        titulo="Savassinha",
        subtitulo="Pedra Grande",
        largura=500,
        altura=700,
        cor_borda_logo="laranja",
    )
    assert isinstance(img, Image.Image)

    # Gera SVG com borda personalizada hex
    svg_conteudo = gerar_placa_svg(
        url=url,
        titulo="Savassinha",
        subtitulo="Pedra Grande",
        largura=500,
        altura=700,
        cor_borda_logo="#3b82f6",
    )
    assert 'stroke="#3b82f6"' in svg_conteudo

