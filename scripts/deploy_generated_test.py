import os
import sys
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.append(str(Path(__file__).resolve().parent.parent))

import scripts.deploy_generated as deploy_module
from aresta_api.proto.generated import indice_pb2
from scripts.deploy_generated import (
    calcular_sha256,
    carregar_dados_anteriores,
    extrair_descricao,
    copiar_imagens,
    listar_imagens_exportaveis,
    calcular_arquivos_externos,
    encontrar_croquis,
    passo_a_compilar_croquis,
    passo_b_calcular_checksums,
    passo_c_gerar_indice,
    passo_d_gerar_manifesto_serving,
    processar_thumbnail,
)

def test_calcular_sha256(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")
    
    # SHA-256 of "hello world"
    expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert calcular_sha256(test_file) == expected_hash

def test_carregar_dados_anteriores(tmp_path):
    pb_file = tmp_path / "indice.binarypb"
    
    # Caso 1: arquivo não existe
    assert carregar_dados_anteriores(pb_file) == {}
    
    # Caso 2: arquivo válido
    indice = indice_pb2.Indice()
    resumo = indice.croquis.add()
    resumo.id = "pico1"
    resumo.checksum_sha256_croqui = "hash123"
    resumo.timestamp_update.FromSeconds(1714905040)  # 2024-05-05T10:30:40Z
    
    pb_file.write_bytes(indice.SerializeToString())
    dados = carregar_dados_anteriores(pb_file)
    
    assert "pico1" in dados
    assert dados["pico1"].checksum_sha256_croqui == "hash123"
    assert dados["pico1"].timestamp_update.ToSeconds() == 1714905040
    
    # Caso 3: arquivo corrompido
    pb_file.write_bytes(b"not a proto")
    assert carregar_dados_anteriores(pb_file) == {}

def test_passo_a_compilar_croquis_id_int(tmp_path):
    # DADO um croqui compilado com id inteiro
    croqui_dir = tmp_path / "croqui_teste"
    croqui_dir.mkdir()
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    deploy_module.GENERATED_DIR.mkdir()
    
    # Criamos um mock para validar_sem_extensoes_vazadas e compilar_croqui
    with patch("scripts.deploy_generated.validar_sem_extensoes_vazadas"), \
         patch("scripts.deploy_generated.compilar_croqui") as mock_compilar, \
         patch("scripts.deploy_generated.gerar_compilado_md"), \
         patch("scripts.deploy_generated.corrigir_database"), \
         patch("scripts.deploy_generated.processar_thumbnail"):
         
        def fake_compilar(cdir, destino_yaml, destino_binarypb, dados_extras):
            import ruamel.yaml
            yaml = ruamel.yaml.YAML()
            with open(destino_yaml, "w", encoding="utf-8") as f:
                yaml.dump({"mapas": [{"pontos_de_interesse": [{"id": 8}]}]}, f)
        
        mock_compilar.side_effect = fake_compilar
        
        # QUANDO executamos passo_a_compilar_croquis com esse croqui
        with pytest.raises(SystemExit):
            passo_a_compilar_croquis([(croqui_dir, {"id": "croqui_teste"})], gerar_arquivos_de_debug=True)

def test_extrair_descricao():
    # Caso 1: descricao na raiz
    data1 = {"id": "1", "descricao": "Descricao raiz"}
    assert extrair_descricao(data1) == "Descricao raiz"
    
    # Caso 2: descricao no primeiro pico
    data2 = {"id": "2", "picos": [{"nome": "Pico 1", "descricao": "Descricao pico"}]}
    assert extrair_descricao(data2) == "Descricao pico"
    
    # Caso 3: sem descricao
    data3 = {"id": "3"}
    assert extrair_descricao(data3) == ""

def test_copiar_imagens(tmp_path):
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    
    src_dir.mkdir()
    (src_dir / "imagem1.webp").write_text("fake img")
    (src_dir / "raw_mapas").mkdir()
    (src_dir / "raw_mapas" / "mapa.png").write_text("fake mapa")
    
    copiar_imagens(src_dir, dest_dir)
    
    assert (dest_dir / "imagem1.webp").exists()
    assert not (dest_dir / "raw_mapas").exists()
    assert not (dest_dir / "raw_mapas" / "mapa.png").exists()

def test_listar_imagens_exportaveis(tmp_path):
    imagens_dir = tmp_path / "imagens"
    imagens_dir.mkdir()
    
    (imagens_dir / "img1.webp").write_text("data")
    (imagens_dir / "img2.webp").write_text("data")
    (imagens_dir / "not_image.txt").write_text("data")
    
    raw_mapas_dir = imagens_dir / "raw_mapas"
    raw_mapas_dir.mkdir()
    (raw_mapas_dir / "img3.webp").write_text("data")
    
    imagens = listar_imagens_exportaveis(imagens_dir)
    
    assert len(imagens) == 2
    nomes = [p.name for p in imagens]
    assert "img1.webp" in nomes
    assert "img2.webp" in nomes
    assert "not_image.txt" not in nomes
    assert "img3.webp" not in nomes

def test_calcular_arquivos_externos(tmp_path):
    imagens_dir = tmp_path / "imagens"
    imagens_dir.mkdir()
    
    (imagens_dir / "img1.webp").write_bytes(b"data1")
    
    with patch("scripts.deploy_generated.calcular_sha256", return_value="fake_hash"):
        arquivos = calcular_arquivos_externos(imagens_dir)
        
    assert len(arquivos) == 1
    assert arquivos[0]["caminho"] == "imagens/img1.webp"
    assert arquivos[0]["checksum_sha256"] == "fake_hash"

@patch("scripts.deploy_generated.DATABASE_DIR")
def test_encontrar_croquis(mock_db_dir, tmp_path):
    mock_db_dir.exists.return_value = True
    
    pico1 = tmp_path / "pico1"
    pico1.mkdir()
    (pico1 / "croqui.yaml").write_text('id: "pico_1"\nnome: "Pico 1"')
    
    pico2 = tmp_path / "pico2"
    pico2.mkdir()
    (pico2 / "croqui.yaml").write_text('nome: "Pico sem ID"')
    
    mock_db_dir.iterdir.return_value = [pico1, pico2]
    
    resultados = encontrar_croquis()
    
    assert len(resultados) == 1
    assert resultados[0][0] == pico1
    assert resultados[0][1]["id"] == "pico_1"

@patch("scripts.deploy_generated.compilar_croqui")
@patch("scripts.deploy_generated.corrigir_database")
@patch("scripts.deploy_generated.copiar_imagens")
@patch("scripts.deploy_generated.gerar_compilado_md")
def test_passo_a_compilar_croquis(mock_md, mock_copiar, mock_corrigir, mock_compilar, tmp_path):
    croquis = [
        (tmp_path / "database" / "pico1", {"id": "pico1", "nome": "Pico 1"})
    ]
    
    dest_dir = tmp_path / "generated" / "pico1"
    dest_dir.mkdir(parents=True)
    dest_pb = dest_dir / "compilado.binarypb"
    
    def side_effect_compilar(*args, **kwargs):
        dest_pb.write_text("binary data")
        # Also create dest_yaml as it might be needed by subsequent steps if not mocked
        if "destino_yaml" in kwargs and kwargs["destino_yaml"]:
            kwargs["destino_yaml"].write_text("mapas: []\n")
        
    mock_compilar.side_effect = side_effect_compilar
    
    # Set GENERATED_DIR
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    deploy_module.GENERATED_DIR.mkdir(exist_ok=True)
    
    compilados, erros = passo_a_compilar_croquis(croquis, force_thumbnails=False)
    
    assert len(compilados) == 1
    assert compilados[0][0] == "pico1"
    assert compilados[0][2] == dest_pb
    
    mock_corrigir.assert_called_once()
    mock_compilar.assert_called_once()
    mock_md.assert_called_once()

def test_passo_b_calcular_checksums(tmp_path):
    pb_file = tmp_path / "compilado.binarypb"
    pb_file.write_bytes(b"binary data")
    
    compilados = [
        ("pico1", {}, pb_file)
    ]
    
    with patch("scripts.deploy_generated.calcular_sha256", return_value="hash_pico1"):
        checksums = passo_b_calcular_checksums(compilados)
        
    assert len(checksums) == 1
    assert checksums["pico1"] == "hash_pico1"

def test_passo_c_gerar_indice(tmp_path):
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    deploy_module.GENERATED_DIR.mkdir()
    
    compilados = [
        ("pico1", {"nome": "Pico 1", "descricao": "Desc", "publicar_croqui": True, "picos": [{"localizacao": {"latitude": -123000000, "longitude": -456000000}}]}, tmp_path / "pico1.binarypb"),
        ("pico2", {"nome": "Pico 2", "descricao": "Desc", "publicar_croqui": True}, tmp_path / "pico2.binarypb")
    ]
    checksums = {
        "pico1": "hash123", # mesmo checksum
        "pico2": "hashNEW"  # checksum diferente
    }
    
    r1 = indice_pb2.ResumoCroqui(id="pico1", checksum_sha256_croqui="hash123")
    r1.timestamp_update.FromSeconds(1714905040)
    r2 = indice_pb2.ResumoCroqui(id="pico2", checksum_sha256_croqui="hashOLD")
    r2.timestamp_update.FromSeconds(1714905040)
    dados_anteriores = {
        "pico1": r1,
        "pico2": r2
    }
    
    passo_c_gerar_indice(compilados, checksums, dados_anteriores)
    
    # Verifica se os arquivos foram criados
    assert (deploy_module.GENERATED_DIR / "indice.yaml").exists()
    assert (deploy_module.GENERATED_DIR / "indice.binarypb").exists()
    
    with open(deploy_module.GENERATED_DIR / "indice.yaml", "r") as f:
        indice = yaml.safe_load(f)
        
    assert "url_base" not in indice
    assert len(indice["croquis"]) == 2

    
    croquis_dict = {c["id"]: c for c in indice["croquis"]}
    
    # pico1 deve manter a data
    assert croquis_dict["pico1"]["checksum_sha256_croqui"] == "hash123"
    assert "2024-05-05" in croquis_dict["pico1"]["timestamp_update"]
    assert croquis_dict["pico1"]["localizacao"]["latitude"] == -123000000
    assert croquis_dict["pico1"]["localizacao"]["longitude"] == -456000000
    
    # pico2 deve atualizar a data para hoje (formato ISO 8601 UTC)
    assert croquis_dict["pico2"]["checksum_sha256_croqui"] == "hashNEW"
    assert "localizacao" not in croquis_dict["pico2"]
    val = croquis_dict["pico2"]["timestamp_update"]
    assert "T" in val and val.endswith("Z")

def test_passo_c_gerar_indice_com_producao(tmp_path):
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    deploy_module.GENERATED_DIR.mkdir()
    
    compilados = [
        ("pico_pub", {"nome": "Pico 1", "descricao": "Desc", "publicar_croqui": True}, tmp_path / "p1.binarypb"),
        ("pico_rascunho", {"nome": "Pico 2", "descricao": "Desc", "publicar_croqui": False}, tmp_path / "p2.binarypb"),
        ("pico_legacy", {"nome": "Pico 3", "descricao": "Desc"}, tmp_path / "p3.binarypb") # Sem flag -> False
    ]
    checksums = {"pico_pub": "1", "pico_rascunho": "2", "pico_legacy": "3"}
    
    # Executa COM is_producao=True (padrão)
    passo_c_gerar_indice(compilados, checksums, {}, is_producao=True)
    
    with open(deploy_module.GENERATED_DIR / "indice.yaml", "r") as f:
        indice_prod = yaml.safe_load(f)
        
    ids_prod = [c["id"] for c in indice_prod["croquis"]]
    assert len(ids_prod) == 1
    assert "pico_pub" in ids_prod
    
    # Executa COM is_producao=False
    passo_c_gerar_indice(compilados, checksums, {}, is_producao=False)
    
    with open(deploy_module.GENERATED_DIR / "indice.yaml", "r") as f:
        indice_dev = yaml.safe_load(f)
        
    ids_dev = [c["id"] for c in indice_dev["croquis"]]
    assert len(ids_dev) == 3
    assert "pico_pub" in ids_dev
    assert "pico_rascunho" in ids_dev
    assert "pico_legacy" in ids_dev



@patch("scripts.deploy_generated.encontrar_croquis")
@patch("scripts.deploy_generated.passo_a_compilar_croquis")
@patch("scripts.deploy_generated.passo_b_calcular_checksums")
@patch("scripts.deploy_generated.passo_c_gerar_indice")
@patch("scripts.deploy_generated.carregar_dados_anteriores")
@patch("scripts.deploy_generated.preparar_generated")
@patch("scripts.deploy_generated.ROOT_DIR")
def test_deploy_seletivo(
    mock_root, mock_preparar, mock_anteriores, mock_passo_c, mock_passo_b, mock_passo_a, mock_encontrar, tmp_path
):
    # Setup
    mock_root.__truediv__.return_value = tmp_path
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    
    pico1_dir = tmp_path / "database" / "pico1"
    pico1_dir.mkdir(parents=True)
    pico2_dir = tmp_path / "database" / "pico2"
    pico2_dir.mkdir(parents=True)
    
    croqui1 = (pico1_dir, {"id": "p1", "nome": "Pico 1"})
    croqui2 = (pico2_dir, {"id": "p2", "nome": "Pico 2"})
    
    mock_encontrar.return_value = [croqui1, croqui2]
    mock_passo_a.return_value = ([("p1", croqui1[1], tmp_path / "p1.pb")], [])
    mock_anteriores.return_value = {"p2": indice_pb2.ResumoCroqui(id="p2", nome="Pico 2")}
    
    # Simular que o pico2 já existe em generated/
    p2_gen_dir = deploy_module.GENERATED_DIR / "p2"
    p2_gen_dir.mkdir(parents=True)
    p2_pb = p2_gen_dir / "compilado.binarypb"
    p2_pb.write_text("existing data")
    
    # Mocking Path.resolve() to avoid real filesystem issues during test if necessary
    # but since we are using tmp_path it should be fine.
    
    from scripts.deploy_generated import deploy
    # Passamos o caminho como string
    deploy(tmp_path / "generated", target_path=str(pico1_dir))
    
    # Verificar se preparar_generated foi chamado com limpar=False
    mock_preparar.assert_called_with(limpar=False)
    
    # Verificar se o Passo A foi chamado apenas para o pico1
    mock_passo_a.assert_called_once()
    assert mock_passo_a.call_args[0][0] == [croqui1]
    
    # Verificar se o Passo C recebeu p1 em compilados e p2 em preservados
    mock_passo_c.assert_called_once()
    compilados_finais = mock_passo_c.call_args[0][0]
    preservados_finais = mock_passo_c.call_args[1].get("preservados", [])
    
    assert len(compilados_finais) == 1
    assert compilados_finais[0][0] == "p1"
    
    assert len(preservados_finais) == 1
    assert preservados_finais[0].id == "p2"



@patch("scripts.deploy_generated.compilar_croqui")
@patch("scripts.deploy_generated.corrigir_database")
@patch("scripts.deploy_generated.copiar_imagens")
@patch("scripts.deploy_generated.gerar_compilado_md")
def test_passo_a_directory_cleanup(mock_md, mock_copiar, mock_corrigir, mock_compilar, tmp_path):
    # Simula que a pasta de destino já existe (caso do deploy seletivo)
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    dest_dir = deploy_module.GENERATED_DIR / "pico1"
    dest_dir.mkdir(parents=True)
    (dest_dir / "old_file.txt").write_text("should be deleted")
    
    croquis = [
        (tmp_path / "database" / "pico1", {"id": "pico1", "nome": "Pico 1"})
    ]
    
    # Mock para compilar que cria o binarypb
    def side_effect_compilar(*args, **kwargs):
        (dest_dir / "compilado.binarypb").write_text("new data")
        
    mock_compilar.side_effect = side_effect_compilar
    
    passo_a_compilar_croquis(croquis, force_thumbnails=False)
    
    # Verifica se a pasta existe e se o arquivo antigo foi deletado (re-criada do zero)
    assert dest_dir.exists()
    assert not (dest_dir / "old_file.txt").exists()
    assert (dest_dir / "compilado.binarypb").exists()

@patch("subprocess.run")
def test_atualizar_saude_croquis(mock_run):
    from scripts.deploy_generated import atualizar_saude_croquis
    atualizar_saude_croquis()
    mock_run.assert_called_once()
    # Verifica se chamou o script correto (o segundo argumento deve ser o caminho do script)
    args = mock_run.call_args[0][0]
    assert "medir_saude_croquis.py" in str(args[1])

def test_processar_thumbnail(tmp_path):
    from PIL import Image
    croqui_dir = tmp_path / "croqui"
    croqui_dir.mkdir()
    dest_dir = tmp_path / "generated" / "pico1"
    dest_dir.mkdir(parents=True)
    
    img_dir = croqui_dir / "imagens"
    img_dir.mkdir()
    src_img = img_dir / "capa.webp"
    
    # Criar uma imagem real de teste (vertical para testar o fundo borrado)
    test_img = Image.new('RGB', (100, 200), color='red')
    test_img.save(src_img, "WEBP")
    
    croqui_data = {"id": "pico1", "caminho_thumbnail": "imagens/capa.webp"}
    
    # Mockando o GENERATED_DIR que é usado para log (relative_to)
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    
    success = processar_thumbnail(croqui_dir, dest_dir, croqui_data)
    
    assert success
    thumb_path = dest_dir / "imagens" / "thumbnail.webp"
    assert thumb_path.exists()
    
    # Verificar dimensões
    with Image.open(thumb_path) as thumb:
        assert thumb.size == (600, 600)
        # O modo deve ser RGB (convertido de qualquer outro se necessário)
        assert thumb.mode == "RGB"

def test_processar_thumbnail_missing_file(tmp_path):
    croqui_dir = tmp_path / "croqui"
    croqui_dir.mkdir()
    dest_dir = tmp_path / "generated" / "pico1"
    
    croqui_data = {"id": "pico1", "caminho_thumbnail": "imagens/nao_existe.webp"}
    
    # Mockando o GENERATED_DIR que é usado para log (relative_to)
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    
    with pytest.raises(FileNotFoundError, match="Thumbnail original não encontrada"):
        processar_thumbnail(croqui_dir, dest_dir, croqui_data)

def test_create_parser_output_dir():
    from scripts.deploy_generated import create_parser, ROOT_DIR
    parser = create_parser()
    
    # Caso padrão
    args = parser.parse_args([])
    assert Path(args.output_dir) == ROOT_DIR / "generated"
    assert args.status is True
    
    # Usando --output-dir
    args = parser.parse_args(["--output-dir", "custom/output"])
    assert args.output_dir == "custom/output"
    
    # Usando -o
    args = parser.parse_args(["-o", "short/output"])
    assert args.output_dir == "short/output"
    
    # Testando --no-status
    args = parser.parse_args(["--no-status"])
    assert args.status is False
    
    # Testando --status (para sobrescrever se necessário, embora default seja True)
    args = parser.parse_args(["--status"])
    assert args.status is True
    
    # Testando --producao
    args = parser.parse_args([])
    assert args.producao is True  # Padrão é True
    args = parser.parse_args(["--producao"])
    assert args.producao is True
    args = parser.parse_args(["--no-producao"])
    assert args.producao is False
    
    # Testando --arquivos-de-debug
    args = parser.parse_args(["--arquivos-de-debug"])
    assert args.arquivos_de_debug is True
    
    # Testando --no-arquivos-de-debug
    args = parser.parse_args(["--no-arquivos-de-debug"])
    assert args.arquivos_de_debug is False





def test_carregar_um_croqui(tmp_path):
    from scripts.deploy_generated import carregar_um_croqui
    
    # Caso 1: Válido
    croqui_dir = tmp_path / "meu_pico"
    croqui_dir.mkdir()
    (croqui_dir / "croqui.yaml").write_text("id: 'pico_xyz'\nnome: 'Pico XYZ'")
    
    data = carregar_um_croqui(croqui_dir)
    assert data is not None
    assert data["id"] == "pico_xyz"
    
    # Caso 2: Sem ID
    croqui_dir2 = tmp_path / "pico_ruim"
    croqui_dir2.mkdir()
    (croqui_dir2 / "croqui.yaml").write_text("nome: 'Pico Sem ID'")
    assert carregar_um_croqui(croqui_dir2) is None
    
    # Caso 3: Pasta sem croqui.yaml
    assert carregar_um_croqui(tmp_path / "vazia") is None


@patch("scripts.deploy_generated.passo_d_gerar_manifesto_serving")
@patch("scripts.deploy_generated.encontrar_croquis")
@patch("scripts.deploy_generated.passo_a_compilar_croquis")
@patch("scripts.deploy_generated.passo_b_calcular_checksums")
@patch("scripts.deploy_generated.passo_c_gerar_indice")
@patch("scripts.deploy_generated.carregar_dados_anteriores")
@patch("scripts.deploy_generated.preparar_generated")
@patch("scripts.deploy_generated.ROOT_DIR")
def test_deploy_resilience_to_failures(
    mock_root, mock_preparar, mock_anteriores, mock_passo_c, mock_passo_b, mock_passo_a, mock_encontrar, mock_passo_d, tmp_path
):
    """Garante que o índice seja gerado mesmo se alguns croquis falharem na compilação."""
    # Setup
    mock_root.__truediv__.return_value = tmp_path
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    
    pico1_dir = tmp_path / "database" / "pico1"
    pico1_dir.mkdir(parents=True)
    pico2_dir = tmp_path / "database" / "pico2"
    pico2_dir.mkdir(parents=True)
    
    croqui1 = (pico1_dir, {"id": "p1", "nome": "Pico 1"})
    croqui2 = (pico2_dir, {"id": "p2", "nome": "Pico 2"})
    
    mock_encontrar.return_value = [croqui1, croqui2]
    
    # pico1 compila com sucesso, pico2 falha
    mock_passo_a.return_value = (
        [("p1", croqui1[1], tmp_path / "p1.pb")],  # Sucessos
        ["Erro no pico2"]                          # Erros
    )
    
    mock_anteriores.return_value = {}
    mock_passo_b.return_value = {"p1": "hash1"}
    mock_passo_c.return_value = "indice_mock"

    from scripts.deploy_generated import deploy
    
    # O deploy deve lançar SystemExit devido ao erro no pico2, mas apenas ao final
    with pytest.raises(SystemExit):
        deploy(tmp_path / "generated")
    
    # Verifica que os arquivos da compilação bem-sucedida (pico1) estão lá
    
    # O Passo C DEVE ter sido chamado mesmo com o erro no pico2
    mock_passo_c.assert_called_once()
    assert mock_passo_d.called
    compilados_finais = mock_passo_c.call_args[0][0]
    assert len(compilados_finais) == 1
    assert compilados_finais[0][0] == "p1"


def test_validacao_extensoes_vazadas(tmp_path):
    from scripts.deploy_generated import validar_sem_extensoes_vazadas
    
    # 1. Tudo limpo (nenhuma menção às extensões)
    pico_limpo = tmp_path / "limpo"
    pico_limpo.mkdir()
    (pico_limpo / "croqui.yaml").write_text("id: 123\nnome: 'Teste'")
    
    # Não deve lançar exceção
    validar_sem_extensoes_vazadas(pico_limpo)
    
    # 2. YAML com extensão vazada
    pico_yaml_sujo = tmp_path / "yaml_sujo"
    pico_yaml_sujo.mkdir()
    (pico_yaml_sujo / "croqui.yaml").write_text("id: 456\n[aresta.ext_metadados_arquivo]:\n  caminho_original: 'abc'")
    
    with pytest.raises(ValueError, match="Extensão de Shadow State .*vazada"):
        validar_sem_extensoes_vazadas(pico_yaml_sujo)
        
    # 3. MD com extensão vazada
    pico_md_sujo = tmp_path / "md_sujo"
    pico_md_sujo.mkdir()
    (pico_md_sujo / "croqui.yaml").write_text("id: 789")
    (pico_md_sujo / "meu_texto.md").write_text("---\next_metadados_arquivo:\n  caminho_novo: 'teste'\n---\n# Oi")
    
    with pytest.raises(ValueError, match="Extensão de Shadow State .*vazada"):
        validar_sem_extensoes_vazadas(pico_md_sujo)

def test_passo_d_gerar_manifesto_serving(tmp_path):
    from aresta_api.proto.generated import serving_pb2
    from aresta_api.proto.generated import indice_pb2
    deploy_module.GENERATED_DIR = tmp_path / "generated"
    deploy_module.GENERATED_DIR.mkdir()

    # Cria alguns arquivos dummy
    (deploy_module.GENERATED_DIR / "indice.binarypb").write_bytes(b"123")
    croqui_dir = deploy_module.GENERATED_DIR / "pico1"
    croqui_dir.mkdir()
    from aresta_api.proto.generated import croqui_pb2
    (croqui_dir / "compilado.binarypb").write_bytes(croqui_pb2.Croqui().SerializeToString())
    
    indice = indice_pb2.Indice()
    rc = indice.croquis.add()
    rc.id = "pico1"
    rc.checksum_sha256_croqui = "hash_c"

    deploy_module.passo_d_gerar_manifesto_serving(indice)
    
    manifest_file = deploy_module.GENERATED_DIR / "arquivos_serving.yaml"
    assert manifest_file.exists()
    
    import yaml
    from google.protobuf import json_format
    
    manifest_dict = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    manifest = serving_pb2.ArquivosServing()
    json_format.ParseDict(manifest_dict, manifest, ignore_unknown_fields=True)
    
    paths = [a.caminho_relativo for a in manifest.arquivos]
    assert "indice.binarypb" in paths
    assert "pico1/compilado.binarypb" in paths
    
    # Valida checksums reais
    for a in manifest.arquivos:
        if a.caminho_relativo == "indice.binarypb":
            assert a.checksum_sha256 == calcular_sha256(deploy_module.GENERATED_DIR / "indice.binarypb")
        elif a.caminho_relativo == "pico1/compilado.binarypb":
            assert a.checksum_sha256 == "hash_c"


def test_verbose_flag_passo_b(capsys):
    from scripts.deploy_generated import passo_b_calcular_checksums
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as d:
        pb_path = Path(d) / 'test.pb'
        pb_path.write_bytes(b'test')
        compilados = [('pico_test', {}, pb_path)]
        
        # verbose=False
        passo_b_calcular_checksums(compilados, verbose=False)
        captured = capsys.readouterr()
        assert 'Passo B' not in captured.out
        
        # verbose=True
        passo_b_calcular_checksums(compilados, verbose=True)
        captured = capsys.readouterr()
        assert 'Passo B' in captured.out
        assert 'pico_test' in captured.out
