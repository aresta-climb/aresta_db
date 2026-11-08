# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários para scripts/cliente_overpass_fake.py."""

from __future__ import annotations

import pytest

from scripts.cliente_overpass_fake import ClienteOverpassFake


def test_fake_retorna_elementos_configurados_por_coordenada_e_padrao() -> None:
    elementos_padrao = [{"type": "node", "id": 1, "lat": -19.5, "lon": -43.9}]
    elementos_especificos = [{"type": "node", "id": 2, "lat": -20.0, "lon": -44.0}]

    fake = ClienteOverpassFake(elementos_padrao=elementos_padrao)
    fake.registrar_resposta(-20.0, -44.0, elementos_especificos)

    assert fake.consultar_malha(-19.5, -43.9) == elementos_padrao
    assert fake.consultar_malha(-20.0, -44.0) == elementos_especificos
    assert fake.historico_consultas == [(-19.5, -43.9), (-20.0, -44.0)]


def test_fake_simular_erro_levanta_excecao() -> None:
    fake = ClienteOverpassFake(simular_erro=RuntimeError("Falha simulada Overpass"))

    with pytest.raises(RuntimeError, match="Falha simulada Overpass"):
        fake.consultar_malha(-19.5, -43.9)
