## 1. Documentação de Princípios Core

- [x] 1.1 Criar o arquivo `PRINCIPIOS.md` na raiz do projeto contendo as regras detalhadas sobre "Library-First", "TDD", "Integration Tests First" e "Simplicity and Anti-Abstraction".
- [x] 1.2 Atualizar o `README.md` referenciando `PRINCIPIOS.md` na seção apropriada, reforçando que agentes e desenvolvedores devem lê-lo.

## 2. Injeção nos Agentes (Workflows/Skills)

- [x] 2.1 Modificar arquivos de workflow do OPSX (por exemplo, em `.agent/workflows/opsx-apply.md` e afins) para orientar explicitamente sobre o cumprimento dos princípios durante a execução do código (especialmente TDD e Library-First).
- [x] 2.2 Criar um `.agents/skills/principios` (se fizer sentido arquiteturalmente) ou garantir que os prompts do sistema sempre orientem o uso dessas heurísticas.
