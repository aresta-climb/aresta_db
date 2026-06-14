import pytest
import sys
from pathlib import Path

# Garante que a raiz do projeto está no PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from editor.core.proto_comments import get_proto_comments

def test_proto_comments_with_nested_blocks(tmp_path, monkeypatch):
    proto_file = tmp_path / "test.proto"
    proto_content = """
    message Croqui {
        // Comment field A
        int32 field_a = 1;
        
        message Inner {
            // Comment inner field
            int32 inner_field = 1;
        }
        
        // Comment field B defined after inner block ends
        int32 field_b = 2;
        
        oneof my_oneof {
            // Comment inside oneof
            int32 field_c = 3;
        }
        
        // Comment field D defined after oneof
        int32 field_d = 4;
        
        // Comment for Enum
        enum Status {
            VALOR_UM = 1;
        }
    }
    """
    proto_file.write_text(proto_content, encoding='utf-8')
    
    # Pass the proto_file directly
    comments = get_proto_comments(proto_paths_override=[str(proto_file)])
    
    assert comments.get(("Croqui", "field_a")) == "Comment field A"
    assert comments.get(("Inner", "inner_field")) == "Comment inner field"
    assert comments.get(("Croqui", "field_b")) == "Comment field B defined after inner block ends"
    assert comments.get(("Croqui", "field_c")) == "Comment inside oneof"
    assert comments.get(("Croqui", "field_d")) == "Comment field D defined after oneof"
    assert comments.get(("Status", "__message__")) == "Comment for Enum"
