# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / 'gui.py')],
    pathex=[str(project_root / 'src')],
    binaries=collect_dynamic_libs('lupa'),
    datas=[
        (str(project_root / 'resources'), 'resources'),
        (str(project_root / 'licenses'), 'licenses'),
        (str(project_root / 'THIRD_PARTY_LICENSES.md'), '.'),
        (str(project_root / 'src' / 'laitoxx' / 'core' / 'translations'), 'src/laitoxx/core/translations'),
        (str(project_root / 'bd'), 'bd'),
        (str(project_root / 'lua_plugins'), 'lua_plugins'),
    ] + collect_data_files('lupa'),
    hiddenimports=[
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
        'laitoxx.app.plugins.engine',
        'dns.resolver',
        'dns.rdatatype',
        'lupa',
        'duckdb',
        'networkx',
        'PIL',
        'mutagen',
        'olefile',
        'pefile',
        'colorama',
        'bs4',
        'google.protobuf',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'keras', 'keras_core', 'keras_preprocessing',
        'torch', 'torchvision', 'torchaudio', 'functorch',
        'transformers', 'tokenizers',
        'tensorflow', 'tensorboard', 'tf_keras',
        'sklearn', 'scipy',
        'onnxruntime',
        'dill', 'regex',
        'IPython', 'notebook', 'jupyter', 'nbformat', 'nbconvert',
        'wx', 'tkinter', 'PyQt5', 'PySide6', 'PySide2',
        'docutils', 'sphinx',
        'torchgen', 'torio', 'timm', 'accelerate', 'diffusers',
        'llmcompressor', 'compressed_tensors', 'auto_gptq',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LaitoxxMultiTool',
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
    icon=str(project_root / 'resources' / 'icons' / 'ico.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LaitoxxMultiTool',
)
