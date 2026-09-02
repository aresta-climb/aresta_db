# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# Garante que o módulo do editor possa ser importado para obter funções puras de filtro
if 'SPECPATH' in globals():
    spec_dir = Path(SPECPATH).resolve()
elif '__file__' in globals():
    spec_dir = Path(__file__).parent.resolve()
else:
    spec_dir = (Path.cwd() / 'editor').resolve() if (Path.cwd() / 'editor').exists() else Path.cwd().resolve()

repo_root = spec_dir.parent if spec_dir.name == 'editor' else spec_dir
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from editor.build import (
        obter_modulos_excluidos,
        filtrar_binarios_desnecessarios,
        filtrar_datas_desnecessarios,
    )
    modulos_excluidos = obter_modulos_excluidos()
except Exception:
    modulos_excluidos = []
    def filtrar_binarios_desnecessarios(b):
        return b
    def filtrar_datas_desnecessarios(d):
        return d

datas = [(str(spec_dir / 'recursos'), 'recursos')]
binaries = []
hiddenimports = ['sentry_sdk']

for pacote in ['pygit2', 'keyring', 'qtawesome']:
    tmp_ret = collect_all(pacote)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# Filtra arquivos de dados não essenciais (ex: famílias de fontes não usadas do QtAwesome)
datas = filtrar_datas_desnecessarios(datas)

a = Analysis(
    [str(spec_dir / 'main.py')],
    pathex=[str(repo_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=modulos_excluidos,
    noarchive=False,
    optimize=0,
)

# Filtra DLLs de fallback de hardware e submódulos gráficos dispensáveis
a.binaries = filtrar_binarios_desnecessarios(a.binaries)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EditorAresta',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(spec_dir / 'logo.ico')],
)
