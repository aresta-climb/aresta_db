import pytest
from editor.core.formatacao import para_id_croqui

@pytest.mark.parametrize("texto, esperado", [
    ("Pedra do Baú", "pedra_do_bau"),
    ("Serra do Cipó", "serra_do_cipo"),
    ("São João del Rei", "sao_joao_del_rei"),
    ("  Nome com   Espaços  ", "nome_com_espacos"),
    ("CamelCaseName", "camelcasename"),
    ("Açúcar e Café", "acucar_e_cafe"),
    ("Pico 123!", "pico_123"),
    ("NOME_EM_MAIUSCULO", "nome_em_maiusculo"),
])

def test_para_id_croqui_normaliza_texto(texto, esperado):
    assert para_id_croqui(texto) == esperado

def test_gerar_id_completo_croqui():
    # Padrão: <pais>_<estado>_<cidade>_<nome_pico>
    pais = "BR"
    estado = "MG"
    cidade = "Belo Horizonte"
    pico = "Pedra do Baú"
    
    # Agora tudo deve ser snake_case e minúsculo
    from editor.core.formatacao import para_snake_case
    id_final = f"{para_snake_case(pais)}_{para_snake_case(estado)}_{para_snake_case(cidade)}_{para_snake_case(pico)}"
    assert id_final == "br_mg_belo_horizonte_pedra_do_bau"

