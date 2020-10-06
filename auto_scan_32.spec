# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['auto_scan.py'],
             pathex=['F:\\Projects\\OpenCV-Document-Scanner'],
             binaries=[('bin\\*.exe', 'bin')],
             datas=[('bin\\fsscore.dll', 'bin'), ('bin\\PDF-XChange Viewer Settings.dat', 'bin')],
             hiddenimports=['pikepdf._cpphelpers', 'Crypto'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='auto_scan_32',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , icon='scan.ico')
