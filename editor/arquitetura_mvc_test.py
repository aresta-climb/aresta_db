# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import ast
from pathlib import Path

def get_python_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                yield os.path.join(root, file)

def get_model_private_methods(models_dir):
    """
    Analisa todos os arquivos na pasta models e extrai os nomes
    de todos os metodos que comecam com '_' (e não terminam com '__').
    """
    private_methods = set()
    for filepath in get_python_files(models_dir):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('_') and not node.name.endswith('__'):
                    private_methods.add(node.name)
    return private_methods

def check_architecture_violations():
    editor_dir = Path(__file__).parent
    models_dir = editor_dir / 'models'
    
    # Coleta todas as funções privadas (iniciando com '_') definidas dentro de models/
    model_private_methods = get_model_private_methods(models_dir)
    
    violations = []

    for filepath in get_python_files(editor_dir):
        path_obj = Path(filepath)
        # Ignora este proprio arquivo e pastas de __pycache__ etc
        if path_obj.name == 'arquitetura_mvc_test.py' or 'venv' in path_obj.parts or '.venv' in path_obj.parts:
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr
                    
                    is_self_call = isinstance(node.func.value, ast.Name) and node.func.value.id == 'self'
                    
                    if not is_self_call:
                        # Regra 1: metodos privados do Model soh podem ser chamados de models/ e commands/
                        if attr_name in model_private_methods:
                            is_in_models = 'models' in path_obj.parts
                            is_in_commands = 'commands' in path_obj.parts
                            
                            if not (is_in_models or is_in_commands):
                                violations.append(
                                    f"{path_obj.relative_to(editor_dir)}:{node.lineno} - Chamada a metodo protegido '{attr_name}' "
                                    f"(pertencente a models/) em objeto externo fora das pastas permitidas (models/ ou commands/)."
                                )
                                
                        # Regra 2: obj.__* nunca pode ser chamado externamente (deve ser chamado apenas no proprio 'self')
                        if attr_name.startswith('__') and not attr_name.endswith('__'):
                            violations.append(
                                f"{path_obj.relative_to(editor_dir)}:{node.lineno} - Chamada a metodo privado '{attr_name}' "
                                f"em objeto externo. Metodos '__*' so podem ser chamados em 'self'."
                            )
                            
                # Regra 3: Apenas controllers e commands podem instanciar classes de commands (Cmd*)
                if isinstance(node.func, ast.Name):
                    class_name = node.func.id
                    if class_name.startswith('Cmd'):
                        is_in_controllers = 'controllers' in path_obj.parts
                        is_in_commands = 'commands' in path_obj.parts
                        is_test_file = path_obj.name.endswith('_test.py') or 'tests' in path_obj.parts
                        is_in_legacy_views = 'legacy_views' in path_obj.parts
                        
                        if not (is_in_controllers or is_in_commands or is_test_file or is_in_legacy_views):
                            violations.append(
                                f"{path_obj.relative_to(editor_dir)}:{node.lineno} - Instanciação do comando '{class_name}' "
                                f"fora das pastas permitidas (controllers/ ou commands/)."
                            )

    return violations

def test_arquitetura_mvc_privacidade_metodos():
    violations = check_architecture_violations()
    if violations:
        msg = "Violacoes de arquitetura encontradas:\n" + "\n".join(violations)
        assert False, msg


def test_todos_comandos_implementam_serializacao_e_deserializacao():
    """
    Garante que qualquer classe de comando (Cmd*) implemente serializar() e deserializar(),
    além de estar registrada para reconstrução a partir do diário de comandos.
    """
    import inspect
    import importlib
    from PyQt6.QtGui import QUndoCommand
    from editor.commands.comandos_protobuf import deserializar_comando

    commands_dir = Path(__file__).parent / "commands"
    classes_comando: list[type] = []

    for filepath in commands_dir.glob("*.py"):
        if filepath.name.endswith("_test.py") or filepath.name.startswith("__"):
            continue
        modulo_nome = f"editor.commands.{filepath.stem}"
        modulo = importlib.import_module(modulo_nome)
        for nome_obj, obj in inspect.getmembers(modulo, inspect.isclass):
            if nome_obj.startswith("Cmd") and issubclass(obj, QUndoCommand) and obj is not QUndoCommand:
                classes_comando.append(obj)

    assert len(classes_comando) > 0, "Nenhuma classe de comando encontrada para teste de arquitetura."

    for cls in classes_comando:
        nome_classe = cls.__name__
        # 1. Deve ter método serializar
        assert hasattr(cls, "serializar"), f"Comando '{nome_classe}' não implementa o método serializar()."
        assert callable(getattr(cls, "serializar")), f"'{nome_classe}.serializar' não é chamável."

        # 2. Deve ter método estático/classmethod deserializar
        assert hasattr(cls, "deserializar"), f"Comando '{nome_classe}' não implementa o método deserializar()."
        assert callable(getattr(cls, "deserializar")), f"'{nome_classe}.deserializar' não é chamável."

        # 3. Deve ser reconhecido pela factory global deserializar_comando
        try:
            deserializar_comando({"classe": nome_classe}, model=None)
        except ValueError as e:
            assert False, f"Comando '{nome_classe}' não está registrado na factory global deserializar_comando: {e}"
        except Exception:
            # Qualquer exceção de parsing de campos internos é esperada pois passamos dados vazios,
            # mas NÃO deve ser ValueError de classe desconhecida.
            pass
