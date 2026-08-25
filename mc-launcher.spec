# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：生成单文件 Windows 可执行程序。

在 Windows 上运行：pyinstaller mc-launcher.spec
"""

import os

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyQt6 组件
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # 核心模块
        'core',
        'core.config',
        'core.downloader',
        'core.version',
        'core.compat',
        'core.java_manager',
        'core.launcher',
        'core.auth',
        'core.app',
        # GUI
        'gui',
        'gui.theme',
        'gui.widgets',
        'gui.main_window',
        'gui.pages.home',
        'gui.pages.versions',
        'gui.pages.settings',
        'gui.pages.mods',
        'gui.pages.loader',
        # API
        'api.modrinth',
        'api.curseforge',
        # 模组
        'mods.fabric',
        'mods.forge',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WorkBuddyMC启动器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI 程序，不显示控制台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
