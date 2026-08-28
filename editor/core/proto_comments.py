# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import re

_comments_cache = None

def get_proto_comments(proto_paths_override=None):
    """
    Carrega estaticamente os comentários dos arquivos .proto e retorna um cache de dicionário
    mapeando (msg_name, field_name) -> "Comentário". 
    Para comentários da própria mensagem, usa (msg_name, "__message__").
    """
    global _comments_cache
    if _comments_cache is not None and proto_paths_override is None:
        return _comments_cache
        
    _comments_cache = {}
    
    if proto_paths_override is not None:
        proto_paths = proto_paths_override
    else:
        # Procuramos croqui.proto e indice.proto em localizações conhecidas
        proto_paths = [
            "aresta_api/proto/croqui.proto",
            "../aresta_api/proto/croqui.proto",
            "proto/croqui.proto",
            "aresta_api/proto/indice.proto",
            "../aresta_api/proto/indice.proto",
            "proto/indice.proto"
        ]
    
    for proto_path in proto_paths:
        if not os.path.exists(proto_path):
            continue
            
        with open(proto_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        scope_stack = []
        pending_comments = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            if line_stripped == "}":
                if scope_stack:
                    scope_stack.pop()
                pending_comments = []
                continue
                
            if line_stripped.startswith("//"):
                content = line_stripped[2:].strip()
                if not any(content.startswith(x) for x in ("Copyright", "==", "--", "NEXT_ID", "TODO")):
                    pending_comments.append(content)
                continue
                
            if line_stripped.startswith("package "):
                pending_comments = []
                continue
                
            # Block start
            if "{" in line_stripped:
                match = re.search(r'(?:message|enum|oneof)\s+(\w+)', line_stripped)
                if match:
                    block_type = re.search(r'(message|enum|oneof)', line_stripped).group(1)
                    name = match.group(1)
                    
                    if block_type == "oneof":
                        parent = scope_stack[-1] if scope_stack else "IGNORE"
                        scope_stack.append(parent)
                    else:
                        scope_stack.append(name)
                        if pending_comments and block_type in ("message", "enum"):
                            _comments_cache[(name, "__message__")] = " ".join(pending_comments)
                else:
                    scope_stack.append("IGNORE")
                pending_comments = []
                continue
                
            # Field parsing
            if scope_stack:
                current_scope = scope_stack[-1]
                if current_scope != "IGNORE":
                    field_match = re.match(r"(?:repeated\s+)?(?:optional\s+)?([\w\.]+)\s+(\w+)\s*=", line_stripped)
                    if field_match:
                        field_name = field_match.group(2)
                        if pending_comments:
                            _comments_cache[(current_scope, field_name)] = " ".join(pending_comments)
                        pending_comments = []
                        
    return _comments_cache
