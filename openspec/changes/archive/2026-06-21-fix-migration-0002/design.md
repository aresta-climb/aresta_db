## Context

O script de migração atual (0002) que tenta centralizar os metadados de referência de IDs de escaladas em mapas é falho, não lidando bem com strings compostas por `/` (usadas para separar as referências de acordo com os mapas em um grupo) nem verificando se um ponto de interesse efetivamente existe no mapa alvo antes de incluir a referência.

## Goals / Non-Goals

**Goals:**
- Ajustar a rotina de extração e parsing do ID (quebrando por barras e depois por números/letras)
- Realizar a intersecção entre os IDs requeridos por uma via e os pontos efetivamente desenhados em um mapa.
- Emitir um log yaml (na pasta do croqui modificado) constando as referências não resolvidas para facilitar edição manual posterior, evitando silenciosamente a perda de dados.
- Seguir as regras definidas: correspondência total para match, separação isolada das partes separadas por `/` mapeadas restritamente pelo índice (se fornecido por meio de `/`), ou validação ampla por intersecção se a via só fornecer 1 "grupo" de referências, propagando propriedades complementares pelo array caso existam `/` numa key mas não na outra.
- **Aderir estritamente ao `PRINCIPIOS.md`**, garantindo 100% de unit test coverage e aplicando o ciclo Vermelho-Verde-Refatorar (TDD) rigorosamente.

**Non-Goals:**
- Otimização algorítmica de processamento além do necessário.
- Refatorar a forma que o front-end trata os mapas.

## Decisions

**Adesão Inegociável ao `PRINCIPIOS.md`**
Todo o código será em Português Brasileiro. Seguiremos TDD estrito: os testes em `0002_centralizar_map_references_test.py` devem ser criados (e falhar) antes de alterar a lógica em `0002_centralizar_map_references.py`. Qualquer nova rotina (como o parser de letras/números ou a injeção do validador YAML) passará por 100% de cobertura de código comprovada via pytest, mantendo a simplicidade e anti-abstração exigidas.

**Validação de Correspondência Total e Exata**
Nós só incluiremos uma via em um mapa se a totalidade das pontes dela (seja 1 ponto simples ou seja `["1", "a"]`) estiverem simultaneamente mapeadas no `pontos_de_interesse` do próprio mapa. Se não baterem perfeitamente, o dado inteiro vai para o `.yaml` de aviso. Isso garante uma interface sem bugs na qual todo dado processado reflete diretamente o desenho do croqui.

**Formatação do Aviso YAML**
Optou-se por separar um array top-level no qual cada item tem nome da escalada e IDs que não foram achados, visando facilitar a iteração em massa.

## Risks / Trade-offs

- **Risk:** Muitas escaladas pararem no `.yaml` de validação.
  *Mitigation:* Isso é intencional. É melhor a base de dados ficar explicitamente declarando IDs órfãos em um arquivo à parte a serem corrigidos no editor depois, do que corromper silenciosamente o croqui centralizando um ponto inexistente na imagem.
