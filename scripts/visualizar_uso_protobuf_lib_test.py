import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, MagicMock

# Adiciona a raiz do projeto ao path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.visualizar_uso_protobuf_lib import DescriptorParser, FieldInfo, MessageInfo

def test_parse_simple_descriptor():
    # Mocking um descriptor simples
    mock_field1 = Mock()
    mock_field1.name = "nome"
    mock_field1.type = 9 # TYPE_STRING
    mock_field1.message_type = None
    
    mock_desc = Mock()
    mock_desc.name = "Simples"
    mock_desc.full_name = "pacote.Simples"
    mock_desc.fields = [mock_field1]
    
    parser = DescriptorParser()
    messages = parser.parse(mock_desc)
    
    assert len(messages) == 1
    assert "pacote.Simples" in messages
    msg_info = messages["pacote.Simples"]
    assert msg_info.name == "Simples"
    assert len(msg_info.fields) == 1
    assert msg_info.fields[0].name == "nome"
    assert msg_info.fields[0].is_message == False

def test_parse_nested_descriptor():
    # Mocking um descriptor aninhado (Ex: Croqui tem lista de Vias)
    mock_via_field = Mock()
    mock_via_field.name = "grau"
    mock_via_field.type = 9
    mock_via_field.message_type = None

    mock_via_desc = Mock()
    mock_via_desc.name = "Via"
    mock_via_desc.full_name = "pacote.Via"
    mock_via_desc.fields = [mock_via_field]

    mock_field_vias = Mock()
    mock_field_vias.name = "vias"
    mock_field_vias.type = 11 # TYPE_MESSAGE
    mock_field_vias.message_type = mock_via_desc

    mock_croqui_desc = Mock()
    mock_croqui_desc.name = "Croqui"
    mock_croqui_desc.full_name = "pacote.Croqui"
    mock_croqui_desc.fields = [mock_field_vias]

    parser = DescriptorParser()
    messages = parser.parse(mock_croqui_desc)

    assert len(messages) == 2
    assert "pacote.Croqui" in messages
    assert "pacote.Via" in messages

    croqui_info = messages["pacote.Croqui"]
    assert len(croqui_info.fields) == 1
    assert croqui_info.fields[0].name == "vias"
    assert croqui_info.fields[0].is_message == True
    assert croqui_info.fields[0].message_full_name == "pacote.Via"

    via_info = messages["pacote.Via"]
    assert len(via_info.fields) == 1
    assert via_info.fields[0].name == "grau"

def test_parse_prevents_infinite_recursion():
    # Estrutura cíclica: Node -> Node
    mock_node_desc = Mock()
    mock_node_desc.name = "Node"
    mock_node_desc.full_name = "pacote.Node"
    
    mock_child = Mock()
    mock_child.name = "child"
    mock_child.type = 11
    mock_child.message_type = mock_node_desc
    
    mock_node_desc.fields = [mock_child]

    parser = DescriptorParser()
    messages = parser.parse(mock_node_desc)

    assert len(messages) == 1
    assert "pacote.Node" in messages
    node_info = messages["pacote.Node"]
    assert len(node_info.fields) == 1
    assert node_info.fields[0].is_message == True
    assert node_info.fields[0].message_full_name == "pacote.Node"

def test_binary_pb_counter_simple():
    from scripts.visualizar_uso_protobuf_lib import BinaryPbCounter
    
    counter = BinaryPbCounter()
    
    mock_field = Mock()
    mock_field.name = "nome"
    mock_field.type = 9
    mock_field.label = 1
    
    mock_msg = Mock()
    mock_msg.DESCRIPTOR.full_name = "pacote.Simples"
    mock_msg.ListFields.return_value = [(mock_field, "valor")]
    
    counter.process_file_message(mock_msg, is_published=True)
    
    assert counter.total_all == 1
    assert counter.total_published == 1
    assert counter.counts["pacote.Simples"]["nome"]["all"] == 1
    assert counter.counts["pacote.Simples"]["nome"]["published"] == 1

def test_binary_pb_counter_nested_and_repeated():
    from scripts.visualizar_uso_protobuf_lib import BinaryPbCounter
    
    counter = BinaryPbCounter()
    
    # Via
    mock_grau_desc = Mock()
    mock_grau_desc.name = "grau"
    mock_grau_desc.type = 9
    mock_grau_desc.label = 1
    
    mock_via1 = Mock()
    mock_via1.DESCRIPTOR.full_name = "pacote.Via"
    mock_via1.ListFields.return_value = [(mock_grau_desc, "5sup")]
    
    mock_via2 = Mock()
    mock_via2.DESCRIPTOR.full_name = "pacote.Via"
    mock_via2.ListFields.return_value = [(mock_grau_desc, "6a")]

    # Croqui
    mock_vias_desc = Mock()
    mock_vias_desc.name = "vias"
    mock_vias_desc.type = 11
    mock_vias_desc.label = 3 # REPEATED
    
    mock_croqui = Mock()
    mock_croqui.DESCRIPTOR.full_name = "pacote.Croqui"
    mock_croqui.ListFields.return_value = [(mock_vias_desc, [mock_via1, mock_via2])]
    
    counter.process_file_message(mock_croqui, is_published=False)
    
    assert counter.total_all == 1
    assert counter.total_published == 0
    # Croqui.vias counted ONCE
    assert counter.counts["pacote.Croqui"]["vias"]["all"] == 1
    # Via.grau counted ONCE per file, even though there are 2 vias
    assert counter.counts["pacote.Via"]["grau"]["all"] == 1
    assert counter.counts["pacote.Via"]["grau"]["published"] == 0

    # Testando message_totals
    assert counter.message_totals["pacote.Croqui"]["all"] == 1
    assert counter.message_totals["pacote.Via"]["all"] == 1
    assert counter.message_totals["pacote.Via"]["published"] == 0
    
def test_heatmap_calculator():
    from scripts.visualizar_uso_protobuf_lib import HeatmapCalculator
    
    # ratio 0
    assert HeatmapCalculator.get_color(0, 10) == ("#cccccc", "black")
    # ratio 1
    assert HeatmapCalculator.get_color(10, 10) == ("#ff0000", "white")
    # ratio 0.5
    r, c = HeatmapCalculator.get_color(5, 10)
    assert r == "#7f007f" # ~ 127
    
def test_graphviz_renderer():
    from scripts.visualizar_uso_protobuf_lib import GraphvizRenderer, MessageInfo, FieldInfo, BinaryPbCounter
    
    msg_info = MessageInfo(name="Croqui", full_name="pacote.Croqui")
    msg_info.fields.append(FieldInfo(name="nome", is_message=False))
    msg_info.fields.append(FieldInfo(name="vias", is_message=True, message_full_name="pacote.Via"))
    
    messages = {
        "pacote.Croqui": msg_info,
        "pacote.Via": MessageInfo(name="Via", full_name="pacote.Via")
    }
    
    counter = BinaryPbCounter()
    counter.total_all = 10
    counter.total_published = 5
    counter.counts = {
        "pacote.Croqui": {
            "nome": {"all": 10, "published": 5},
            "vias": {"all": 2, "published": 0}
        }
    }
    custom_totals = {
        "pacote.Croqui": 10,
        "pacote.Via": 20
    }
    custom_comments = {
        ("Croqui", "__message__"): "Isto eh um croqui",
        ("Croqui", "vias"): "Lista de vias",
        ("Via", "__message__"): "Isto eh uma via"
    }
    
    renderer = GraphvizRenderer(messages, counter, custom_totals=custom_totals, comments=custom_comments)
    dot = renderer.render()
    
    assert "digraph" in dot
    assert "rankdir=LR" in dot
    assert "label=<" in dot
    assert "pacote.Croqui" in dot
    assert "<table" in dot
    assert "nome" in dot
    assert "bgcolor" in dot
    assert "color" in dot
    assert 'tooltip="Isto eh um croqui"' in dot
    assert 'tooltip="Lista de vias"' in dot
    assert 'tooltip="Isto eh uma via"' in dot
    assert "100%" in dot
    assert "20% (2/10)" in dot
    assert "0% (0/10)" in dot
    assert "\"pacote.Croqui\":\"vias\":e -> \"pacote.Via\":w;" in dot

def test_graphviz_renderer_filter_unused():
    from scripts.visualizar_uso_protobuf_lib import GraphvizRenderer, MessageInfo, FieldInfo, BinaryPbCounter
    
    msg_info = MessageInfo(name="Croqui", full_name="pacote.Croqui")
    msg_info.fields.append(FieldInfo(name="usado", is_message=False))
    msg_info.fields.append(FieldInfo(name="nao_usado", is_message=False))
    msg_info.fields.append(FieldInfo(name="vias", is_message=True, message_full_name="pacote.Via"))
    
    msg_via = MessageInfo(name="Via", full_name="pacote.Via")
    msg_via.fields.append(FieldInfo(name="nao_usado_via", is_message=False))
    
    msg_isolada = MessageInfo(name="Isolada", full_name="pacote.Isolada")
    msg_isolada.fields.append(FieldInfo(name="nao_usado_iso", is_message=False))
    
    messages = {
        "pacote.Croqui": msg_info,
        "pacote.Via": msg_via,
        "pacote.Isolada": msg_isolada
    }
    
    counter = BinaryPbCounter()
    counter.total_all = 10
    counter.total_published = 10
    counter.counts = {
        "pacote.Croqui": {
            "usado": {"all": 10, "published": 10},
            "nao_usado": {"all": 0, "published": 0},
            "vias": {"all": 5, "published": 5}
        },
        "pacote.Via": {
            "nao_usado_via": {"all": 0, "published": 0}
        },
        "pacote.Isolada": {
            "nao_usado_iso": {"all": 0, "published": 0}
        }
    }
    
    renderer = GraphvizRenderer(messages, counter, filter_unused=True)
    dot = renderer.render()
    
    # "usado" tem count > 0, "vias" tem count > 0
    assert "usado" in dot
    assert "vias" in dot
    assert "\"pacote.Croqui\":\"vias\":e -> \"pacote.Via\":w;" in dot
    
    # "nao_usado" e "nao_usado_via" e "Isolada" não devem aparecer
    assert "nao_usado" not in dot
    assert "nao_usado_via" not in dot
    assert "Isolada" not in dot
    
    # Como pacote.Via foi incluída mas sem campos, deve ter o placeholder
    assert "<i>Nenhum campo utilizado</i>" in dot
