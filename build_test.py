# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import os
import sys
import unittest
import importlib.util
from unittest.mock import patch, MagicMock
from pathlib import Path

# Localiza o build.py da raiz de forma segura
_root_dir = os.path.dirname(os.path.abspath(__file__))
_build_path = os.path.join(_root_dir, "build.py")
_spec = importlib.util.spec_from_file_location("root_build", _build_path)
root_build = importlib.util.module_from_spec(_spec)
# Adicionamos ao sys.modules com um nome único para evitar conflito com aresta_api/build.py
sys.modules["root_build"] = root_build
_spec.loader.exec_module(root_build)

class TestRootBuild(unittest.TestCase):
    
    @patch('subprocess.run')
    def test_generate_protos(self, mock_run):
        # Testa chamada sem force
        root_build.generate_protos(force=False)
        args, kwargs = mock_run.call_args
        self.assertNotIn('-f', args[0])
        
        # Testa chamada com force
        root_build.generate_protos(force=True)
        args, kwargs = mock_run.call_args
        self.assertIn('-f', args[0])

    @patch('subprocess.run')
    def test_run_tests(self, mock_run):
        mock_run.return_value.returncode = 0
        
        # Caso em que a pasta tests existe
        with patch('pathlib.Path.exists', return_value=True):
            root_build.run_tests()
            args, kwargs = mock_run.call_args
            self.assertIn("tests", args[0])
            self.assertIn("pytest", args[0])
            self.assertIn("scripts", args[0])
            self.assertIn("aresta_api", args[0])
            self.assertIn("editor", args[0])
            self.assertEqual(kwargs['cwd'], str(root_build.ROOT_DIR))
            
        # Caso em que a pasta tests NÃO existe
        mock_run.reset_mock()
        with patch('pathlib.Path.exists', return_value=False):
            root_build.run_tests()
            args, _ = mock_run.call_args
            self.assertNotIn("tests", args[0])

        # Testa com testmon=True
        mock_run.reset_mock()
        root_build.run_tests(testmon=True)
        args, _ = mock_run.call_args
        self.assertIn("--testmon", args[0])

        # Testa com parallel=True
        mock_run.reset_mock()
        root_build.run_tests(parallel=True)
        args, _ = mock_run.call_args
        self.assertIn("-n", args[0])
        idx = args[0].index("-n")
        self.assertTrue(args[0][idx+1].isdigit())

    @patch('subprocess.run')
    def test_run_deploy(self, mock_run):
        mock_run.return_value.returncode = 0
        root_build.run_deploy()
        args, kwargs = mock_run.call_args
        self.assertIn("deploy_generated.py", str(args[0][1]))
        self.assertTrue(kwargs['check'])

    @patch('subprocess.run')
    def test_run_coverage(self, mock_run):
        mock_run.return_value.returncode = 0
        
        # Caso em que a pasta tests existe
        with patch('pathlib.Path.exists', return_value=True):
            root_build.run_coverage()
            args, kwargs = mock_run.call_args
            self.assertIn("tests", args[0])
            self.assertIn("pytest", args[0])
            self.assertIn("--cov", args[0])
            self.assertIn("--cov-report=html:reports/coverage", args[0])
            self.assertEqual(kwargs['cwd'], str(root_build.ROOT_DIR))
            
        # Caso em que a pasta tests NÃO existe
        mock_run.reset_mock()
        with patch('pathlib.Path.exists', return_value=False):
            root_build.run_coverage()
            args, _ = mock_run.call_args
            self.assertNotIn("tests", args[0])

    @patch('root_build.run_health_check')
    @patch('root_build.run_coverage')
    @patch('root_build.generate_protos')
    @patch('root_build.run_tests')
    @patch('root_build.run_deploy')
    def test_main_commands(self, mock_deploy, mock_tests, mock_protos, mock_coverage, mock_health):
        # Comando: protos
        with patch('sys.argv', ['build.py', 'protos']):
            root_build.main()
        mock_protos.assert_called_with(force=False)
        mock_tests.assert_not_called()
        mock_coverage.assert_not_called()
        mock_health.assert_not_called()
        
        # Comando: test com force
        mock_protos.reset_mock()
        with patch('sys.argv', ['build.py', 'test', '-f']):
            root_build.main()
        mock_protos.assert_called_with(force=True)
        mock_tests.assert_called_once()
        
        # Comando: tudo (explicitamente)
        mock_protos.reset_mock()
        mock_tests.reset_mock()
        mock_deploy.reset_mock()
        mock_coverage.reset_mock()
        mock_health.reset_mock()
        with patch('sys.argv', ['build.py', 'tudo']):
            root_build.main()
        mock_protos.assert_called_with(force=False)
        mock_tests.assert_called_once()
        mock_deploy.assert_called_once()
        mock_coverage.assert_not_called()
        mock_health.assert_not_called() # deploy already does health check
        
        # Comando padrão: agora deve ser 'tudo'
        mock_protos.reset_mock()
        mock_tests.reset_mock()
        mock_deploy.reset_mock()
        mock_coverage.reset_mock()
        mock_health.reset_mock()
        with patch('sys.argv', ['build.py']):
            root_build.main()
        mock_protos.assert_called_with(force=False)
        mock_tests.assert_called_once()
        mock_deploy.assert_called_once()
        mock_coverage.assert_not_called()
        mock_health.assert_not_called()
        
        # Comando: coverage
        mock_protos.reset_mock()
        mock_tests.reset_mock()
        mock_deploy.reset_mock()
        mock_coverage.reset_mock()
        mock_health.reset_mock()
        with patch('sys.argv', ['build.py', 'coverage']):
            root_build.main()
        mock_protos.assert_called_with(force=False)
        mock_tests.assert_not_called()
        mock_coverage.assert_called_once()
        mock_health.assert_not_called()
        
        # Comando: saude
        mock_protos.reset_mock()
        mock_tests.reset_mock()
        mock_deploy.reset_mock()
        mock_coverage.reset_mock()
        mock_health.reset_mock()
        with patch('sys.argv', ['build.py', 'saude']):
            root_build.main()
        mock_health.assert_called_once()

    @patch('root_build.generate_protos')
    @patch('root_build.run_tests')
    @patch('root_build.run_deploy')
    def test_main_invalid_command(self, mock_deploy, mock_tests, mock_protos):
        with patch('sys.argv', ['build.py', 'invalid']):
            with self.assertRaises(SystemExit) as cm:
                # O argparse vai imprimir o help e sair com erro 2 por padrão para escolhas inválidas
                root_build.main()
            self.assertEqual(cm.exception.code, 2)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    @patch('root_build.generate_protos')
    @patch('root_build.run_tests')
    def test_main_drop_cache(self, mock_tests, mock_protos, mock_unlink, mock_exists):
        mock_exists.return_value = True
        with patch('sys.argv', ['build.py', 'test', '--drop-cache']):
            root_build.main()
        mock_unlink.assert_called_once()

    @patch('root_build.generate_protos')
    def test_main_invalid_flag(self, mock_protos):
        with patch('sys.argv', ['build.py', '--unknown-flag']):
            with self.assertRaises(SystemExit) as cm:
                root_build.main()
            self.assertEqual(cm.exception.code, 2)

if __name__ == '__main__':
    unittest.main()
