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

eh_beta = os.environ.get("ARESTA_CANAL", "").strip().lower() == "beta"

canal_nome = "beta" if eh_beta else "producao"
caminho_canal = spec_dir / "canal.txt"
caminho_canal.write_text(canal_nome, encoding="utf-8")

datas = [
    (str(spec_dir / 'recursos'), 'recursos'),
    (str(spec_dir / 'recursos'), 'editor/recursos'),
    (str(caminho_canal), '.'),
    (str(caminho_canal), 'editor'),
]
if (spec_dir / 'logo.ico').exists():
    datas.append((str(spec_dir / 'logo.ico'), '.'))
    datas.append((str(spec_dir / 'logo.ico'), 'editor'))
if (spec_dir / 'logo.icns').exists():
    datas.append((str(spec_dir / 'logo.icns'), '.'))
    datas.append((str(spec_dir / 'logo.icns'), 'editor'))
if eh_beta and (spec_dir / 'recursos_beta').exists():
    datas.append((str(spec_dir / 'recursos_beta'), 'recursos_beta'))
    datas.append((str(spec_dir / 'recursos_beta'), 'editor/recursos_beta'))
if (repo_root / 'migracoes').exists():
    datas.append((str(repo_root / 'migracoes'), 'migracoes'))
binaries = []
hiddenimports = ['sentry_sdk']

pacotes_para_coletar = ['pygit2', 'keyring', 'qtawesome']
if sys.platform.startswith("linux"):
    pacotes_para_coletar += ['secretstorage', 'jeepney']

for pacote in pacotes_para_coletar:
    try:
        tmp_ret = collect_all(pacote)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

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

if sys.platform == "darwin":
    caminho_icone_exe = (
        spec_dir / 'recursos_beta' / 'logo.icns'
        if (eh_beta and (spec_dir / 'recursos_beta' / 'logo.icns').exists())
        else spec_dir / 'logo.icns'
    )
    if not caminho_icone_exe.exists():
        caminho_icone_exe = spec_dir / 'recursos' / 'logo.icns'
    icone_pyinstaller = [str(caminho_icone_exe)]
elif sys.platform.startswith("win"):
    caminho_icone_exe = (
        spec_dir / 'recursos_beta' / 'logo.ico'
        if (eh_beta and (spec_dir / 'recursos_beta' / 'logo.ico').exists())
        else spec_dir / 'logo.ico'
    )
    if not caminho_icone_exe.exists():
        caminho_icone_exe = spec_dir / 'recursos' / 'logo.ico'
    icone_pyinstaller = [str(caminho_icone_exe)]
else:
    # No Linux (binários ELF), o executável não possui seção de ícones embutidos.
    # O ícone da aplicação é provido pelo arquivo .desktop e definido em tempo de execução via Qt.
    icone_pyinstaller = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EditorAresta',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icone_pyinstaller,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='EditorAresta',
)
