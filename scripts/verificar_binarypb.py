# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import os
from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from typing import Union
import build
from aresta_api.proto.generated import croqui_pb2

def verify_pb(pb_file: Union[str, Path]) -> None:


    print(f"Lendo {pb_file}...")
    croqui = croqui_pb2.Croqui()
    
    with open(pb_file, "rb") as f:
        croqui.ParseFromString(f.read())
    
    print(f"ID: {croqui.id}")
    print(f"Nome: {croqui.nome}")
    print(f"Botões: {len(croqui.botoes)}")
    print(f"Picos: {len(croqui.picos)}")
    
    for pico in croqui.picos:
        print(f"  Pico: {pico.nome}")
        print(f"  Elementos: {len(pico.setores_ou_grupos)}")
        for i, elemento in enumerate(pico.setores_ou_grupos):
            if elemento.HasField("setor"):
                arq_setor = elemento.setor
                if arq_setor.HasField("conteudo"):
                    setor = arq_setor.conteudo
                    print(f"    Setor {i+1}: {setor.nome} ({len(setor.escaladas)} escaladas)")
                    if len(setor.escaladas) > 0:
                        first_v = setor.escaladas[0]
                        if first_v.HasField("via_esportiva"):
                            v = first_v.via_esportiva
                            print(f"      Primeira via: {v.nome} (Grau: {v.dificuldade})")
            elif elemento.HasField("grupo"):
                grupo = elemento.grupo.conteudo
                print(f"    Grupo {i+1}: {grupo.nome} ({len(grupo.setores)} setores)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python verify_binarypb.py <file.binarypb>")
        sys.exit(1)

    try:
        build.generate_protos()
    except Exception as e:
        print(f"Erro ao invocar build.py para protos: {e}")
        sys.exit(1)
    
    verify_pb(sys.argv[1])
