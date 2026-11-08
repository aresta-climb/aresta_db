# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SeletorAlvoQt:
    """Identificador semântico resiliente de um widget ou ação na interface Qt."""

    estrategia: str
    valor: str
    classe_widget: str = ""
    indice: int = 0

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "estrategia": self.estrategia,
            "valor": self.valor,
            "classe_widget": self.classe_widget,
            "indice": self.indice,
        }

    @classmethod
    def de_dicionario(cls, dados: dict[str, Any]) -> "SeletorAlvoQt":
        return cls(
            estrategia=str(dados.get("estrategia", "")),
            valor=str(dados.get("valor", "")),
            classe_widget=str(dados.get("classe_widget", "")),
            indice=int(dados.get("indice", 0)),
        )


@dataclass(frozen=True)
class PassoRobo:
    """Representa um passo sintético executado pelo Robô Caótico."""

    indice: int
    tipo_acao: str
    seletor: SeletorAlvoQt
    parametros: dict[str, Any] = field(default_factory=dict)
    mutou_estado: bool = True

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "indice": self.indice,
            "tipo_acao": self.tipo_acao,
            "seletor": self.seletor.para_dicionario(),
            "parametros": dict(self.parametros),
            "mutou_estado": self.mutou_estado,
        }

    @classmethod
    def de_dicionario(cls, dados: dict[str, Any]) -> "PassoRobo":
        return cls(
            indice=int(dados.get("indice", 0)),
            tipo_acao=str(dados.get("tipo_acao", "")),
            seletor=SeletorAlvoQt.de_dicionario(dados.get("seletor", {})),
            parametros=dict(dados.get("parametros", {})),
            mutou_estado=bool(dados.get("mutou_estado", True)),
        )


@dataclass(frozen=True)
class FalhaCapturadaRobo:
    """Detalhes da falha detectada por um dos oráculos do Robô Caótico."""

    oraculo: str
    tipo_excecao: str
    mensagem: str
    frame_principal: str
    stacktrace: str = ""

    def assinatura_deduplicacao(self) -> str:
        """Retorna chave única estável para deduplicar falhas e validar o shrinking."""
        return f"{self.oraculo}:{self.tipo_excecao}:{self.frame_principal}"

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "oraculo": self.oraculo,
            "tipo_excecao": self.tipo_excecao,
            "mensagem": self.mensagem,
            "frame_principal": self.frame_principal,
            "stacktrace": self.stacktrace,
        }

    @classmethod
    def de_dicionario(cls, dados: dict[str, Any]) -> "FalhaCapturadaRobo":
        return cls(
            oraculo=str(dados.get("oraculo", "")),
            tipo_excecao=str(dados.get("tipo_excecao", "")),
            mensagem=str(dados.get("mensagem", "")),
            frame_principal=str(dados.get("frame_principal", "")),
            stacktrace=str(dados.get("stacktrace", "")),
        )


@dataclass(frozen=True)
class ReceitaCrashRobo:
    """Receita determinística completa de um crash do Robô Caótico."""

    seed: int
    dataset: str
    escopo: str
    falha: FalhaCapturadaRobo
    passos_minimos: tuple[PassoRobo, ...]
    passos_originais: tuple[PassoRobo, ...]

    def assinatura_deduplicacao(self) -> str:
        return self.falha.assinatura_deduplicacao()

    def para_dicionario(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "dataset": self.dataset,
            "escopo": self.escopo,
            "falha": self.falha.para_dicionario(),
            "passos_minimos": [p.para_dicionario() for p in self.passos_minimos],
            "passos_originais": [p.para_dicionario() for p in self.passos_originais],
        }

    @classmethod
    def de_dicionario(cls, dados: dict[str, Any]) -> "ReceitaCrashRobo":
        return cls(
            seed=int(dados.get("seed", 0)),
            dataset=str(dados.get("dataset", "toxico")),
            escopo=str(dados.get("escopo", "aplicativo_completo")),
            falha=FalhaCapturadaRobo.de_dicionario(dados.get("falha", {})),
            passos_minimos=tuple(
                PassoRobo.de_dicionario(p) for p in dados.get("passos_minimos", [])
            ),
            passos_originais=tuple(
                PassoRobo.de_dicionario(p) for p in dados.get("passos_originais", [])
            ),
        )

    def salvar_json(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(self.para_dicionario(), ensure_ascii=False, indent=2)
        caminho.write_text(texto + "\n", encoding="utf-8")

    @classmethod
    def carregar_json(cls, caminho: Path) -> "ReceitaCrashRobo":
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return cls.de_dicionario(dados)
