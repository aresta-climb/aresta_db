# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import ast
import os
from pathlib import Path


def get_python_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                yield os.path.join(root, file)


def get_model_private_methods(models_dir):
    """
    Analisa todos os arquivos na pasta models e extrai os nomes
    de todos os metodos que comecam com '_' (e não terminam com '__').
    """
    private_methods = set()
    for filepath in get_python_files(models_dir):
        try:
            with open(filepath, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("_") and not node.name.endswith("__"):
                    private_methods.add(node.name)
    return private_methods


def check_architecture_violations():
    editor_dir = Path(__file__).parent
    models_dir = editor_dir / "models"

    # Coleta todas as funções privadas (iniciando com '_') definidas dentro de models/
    model_private_methods = get_model_private_methods(models_dir)

    violations = []

    for filepath in get_python_files(editor_dir):
        path_obj = Path(filepath)
        # Ignora este proprio arquivo e pastas de __pycache__ etc
        if (
            path_obj.name == "arquitetura_mvc_test.py"
            or "venv" in path_obj.parts
            or ".venv" in path_obj.parts
        ):
            continue

        try:
            with open(filepath, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr

                    is_self_call = (
                        isinstance(node.func.value, ast.Name) and node.func.value.id == "self"
                    )

                    if not is_self_call:
                        # Regra 1: metodos privados do Model soh podem ser chamados de models/ e commands/
                        if attr_name in model_private_methods:
                            is_in_models = "models" in path_obj.parts
                            is_in_commands = "commands" in path_obj.parts

                            if not (is_in_models or is_in_commands):
                                violations.append(
                                    f"{path_obj.relative_to(editor_dir)}:{node.lineno} - Chamada a metodo protegido '{attr_name}' "
                                    f"(pertencente a models/) em objeto externo fora das pastas permitidas (models/ ou commands/)."
                                )

                        # Regra 2: obj.__* nunca pode ser chamado externamente (deve ser chamado apenas no proprio 'self')
                        if attr_name.startswith("__") and not attr_name.endswith("__"):
                            violations.append(
                                f"{path_obj.relative_to(editor_dir)}:{node.lineno} - Chamada a metodo privado '{attr_name}' "
                                f"em objeto externo. Metodos '__*' so podem ser chamados em 'self'."
                            )

                    # Regra 4: É estritamente proibido chamar beginMacro ou endMacro diretamente no QUndoStack
                    if attr_name in ("beginMacro", "endMacro"):
                        violations.append(
                            f"{path_obj.relative_to(editor_dir)}:{node.lineno} - Chamada proibida a '{attr_name}'. "
                            f"O uso direto de beginMacro/endMacro do Qt impede a serialização no diário de recuperação. "
                            f"Utilize 'CmdMacro' em seu lugar."
                        )

                # Regra 3: Apenas controllers e commands podem instanciar classes de commands (Cmd*)
                if isinstance(node.func, ast.Name):
                    class_name = node.func.id
                    if class_name.startswith("Cmd"):
                        is_in_controllers = "controllers" in path_obj.parts
                        is_in_commands = "commands" in path_obj.parts
                        is_test_file = (
                            path_obj.name.endswith("_test.py") or "tests" in path_obj.parts
                        )
                        is_in_legacy_views = "legacy_views" in path_obj.parts

                        if not (
                            is_in_controllers
                            or is_in_commands
                            or is_test_file
                            or is_in_legacy_views
                        ):
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
    import importlib
    import inspect

    from PySide6.QtGui import QUndoCommand

    from editor.commands.comandos_protobuf import deserializar_comando

    commands_dir = Path(__file__).parent / "commands"
    classes_comando: list[type] = []

    for filepath in commands_dir.glob("*.py"):
        if filepath.name.endswith("_test.py") or filepath.name.startswith("__"):
            continue
        modulo_nome = f"editor.commands.{filepath.stem}"
        modulo = importlib.import_module(modulo_nome)
        for nome_obj, obj in inspect.getmembers(modulo, inspect.isclass):
            if (
                nome_obj.startswith("Cmd")
                and issubclass(obj, QUndoCommand)
                and obj is not QUndoCommand
            ):
                classes_comando.append(obj)

    assert len(classes_comando) > 0, (
        "Nenhuma classe de comando encontrada para teste de arquitetura."
    )

    for cls in classes_comando:
        nome_classe = cls.__name__
        # 1. Deve ter método serializar
        assert hasattr(cls, "serializar"), (
            f"Comando '{nome_classe}' não implementa o método serializar()."
        )
        assert callable(cls.serializar), f"'{nome_classe}.serializar' não é chamável."

        # 2. Deve ter método estático/classmethod deserializar
        assert hasattr(cls, "deserializar"), (
            f"Comando '{nome_classe}' não implementa o método deserializar()."
        )
        assert callable(cls.deserializar), f"'{nome_classe}.deserializar' não é chamável."

        # 3. Deve ser reconhecido pela factory global deserializar_comando
        try:
            deserializar_comando({"classe": nome_classe}, model=None)
        except ValueError as e:
            if "Classe de comando desconhecida" in str(e):
                assert False, (
                    f"Comando '{nome_classe}' não está registrado na factory global deserializar_comando: {e}"
                )
        except Exception:
            # Qualquer exceção de parsing de campos internos é esperada pois passamos dados vazios,
            # mas NÃO deve ser ValueError de classe desconhecida.
            pass


def test_proibicao_uso_comandos_legados_fora_da_deserializacao():
    """
    Guarda AST estrita:
    1. Proíbe qualquer importação ou instanciação de comandos_legados e de suas 12 classes
       fora de editor/commands/comandos_legados.py, editor/commands/comandos_legados_test.py
       e da função deserializar_comando em editor/commands/comandos_protobuf.py.
    2. Garante que todos os 7 comandos canônicos e 12 comandos legados (total 19)
       estão registrados e são aceitos por deserializar_comando.
    """
    CLASSES_LEGADAS = {
        "CmdAlterarPrimitivo",
        "CmdRenomearEscalada",
        "CmdAlterarOneof",
        "CmdAlterarRepeatedItem",
        "CmdAlterarMultiplosRepeatedItems",
        "CmdAlterarMetadadosCaminhoNovo",
        "CmdAlterarCampoImagem",
        "CmdInserirImagemMarkdown",
        "CmdInserirBotaoMarkdown",
        "CmdAdicionarMapaArquivo",
        "CmdSubstituirImagemMemoria",
        "CmdMigrarSetor",
    }
    COMANDOS_CANONICOS = {
        "CmdAlterarCampo",
        "CmdAlterarImagem",
        "CmdAlterarAnexo",
        "CmdAdicionarRepeated",
        "CmdRemoverRepeated",
        "CmdMoverRepeated",
        "CmdMacro",
    }

    editor_dir = Path(__file__).parent
    violacoes = []

    for filepath in get_python_files(editor_dir):
        path_obj = Path(filepath)

        # Arquivos autorizados a conter referências aos comandos legados
        if (
            path_obj.name == "arquitetura_mvc_test.py"
            or path_obj.name == "comandos_legados.py"
            or path_obj.name == "comandos_legados_test.py"
            or "venv" in path_obj.parts
            or ".venv" in path_obj.parts
        ):
            continue

        try:
            with open(filepath, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            continue

        rel_path = path_obj.relative_to(editor_dir)

        # Para comandos_protobuf.py, apenas o import interno de COMANDOS_LEGADOS_MAP em deserializar_comando é tolerado
        if path_obj.name == "comandos_protobuf.py":
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "comandos_legados" in node.module:
                        nomes_importados = [alias.name for alias in node.names]
                        if nomes_importados != ["COMANDOS_LEGADOS_MAP"]:
                            violacoes.append(
                                f"{rel_path}:{node.lineno} - comandos_protobuf.py só pode importar 'COMANDOS_LEGADOS_MAP', mas importou: {nomes_importados}"
                            )
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in CLASSES_LEGADAS:
                        violacoes.append(
                            f"{rel_path}:{node.lineno} - Instanciação proibida da classe legada '{node.func.id}' em comandos_protobuf.py."
                        )
            continue

        # Em qualquer outro arquivo do editor: PROIBIÇÃO TOTAL de import ou uso das 12 classes
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "comandos_legados" in alias.name:
                        violacoes.append(
                            f"{rel_path}:{node.lineno} - Import proibido de '{alias.name}'. O módulo comandos_legados é restrito à deserialização."
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and "comandos_legados" in node.module:
                    violacoes.append(
                        f"{rel_path}:{node.lineno} - Import proibido de 'editor.commands.comandos_legados'. "
                        f"O módulo comandos_legados é restrito à deserialização."
                    )
                for alias in node.names:
                    if alias.name in CLASSES_LEGADAS:
                        violacoes.append(
                            f"{rel_path}:{node.lineno} - Import proibido da classe legada '{alias.name}'. "
                            f"Utilize os comandos canônicos em comandos_protobuf.py."
                        )
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in CLASSES_LEGADAS:
                    violacoes.append(
                        f"{rel_path}:{node.lineno} - Instanciação proibida da classe legada '{node.func.id}'. "
                        f"Utilize os comandos canônicos em comandos_protobuf.py."
                    )

    assert not violacoes, "Violações de proibição de comandos legados encontradas:\n" + "\n".join(
        violacoes
    )

    # Validação do registro completo em deserializar_comando
    from editor.commands.comandos_legados import COMANDOS_LEGADOS_MAP
    from editor.commands.comandos_protobuf import deserializar_comando

    assert set(COMANDOS_LEGADOS_MAP.keys()) == CLASSES_LEGADAS, (
        f"COMANDOS_LEGADOS_MAP incompleto: esperado {CLASSES_LEGADAS}, obtido {set(COMANDOS_LEGADOS_MAP.keys())}"
    )

    total_esperado = COMANDOS_CANONICOS | CLASSES_LEGADAS
    assert len(total_esperado) == 19

    for nome_classe in total_esperado:
        try:
            deserializar_comando({"classe": nome_classe}, model=None)
        except ValueError as e:
            if "Classe de comando desconhecida" in str(e):
                assert False, (
                    f"Comando '{nome_classe}' não reconhecido por deserializar_comando: {e}"
                )
        except Exception:
            # Erros de dados vazios são normais, o que importa é não ser rejeitado como classe desconhecida
            pass
