from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
STATIC = ROOT / "static"


def _ensure_pyinstaller() -> None:
    if shutil.which("pyinstaller"):
        return
    print("PyInstaller não encontrado. Instalando...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"], check=True)


def _remover_exe_ativo(exe: Path) -> None:
    if not exe.exists():
        return

    for attempt in range(1, 11):
        try:
            exe.unlink()
            return
        except PermissionError:
            if attempt == 10:
                raise RuntimeError(
                    f"Não foi possível remover {exe}. Feche o executável antes de gerar uma nova versão."
                ) from None
            print(
                f"O executável {exe} está em uso. Tentando liberar e repetir em {attempt}s..."
            )
            subprocess.run(["taskkill", "/F", "/IM", exe.name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(attempt)


def _remover_builds_antigos() -> None:
    for pasta in (DIST, BUILD):
        if pasta.exists():
            print(f"Removendo build antigo em: {pasta}")
            shutil.rmtree(pasta)
    

def main() -> int:
    _ensure_pyinstaller()
    _remover_builds_antigos()
    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)

    exe = DIST / "CopilotoN1.exe"
    _remover_exe_ativo(exe)

    extra_data = []
    if STATIC.exists():
        extra_data.append(f"{STATIC}{os.pathsep}static")

    perfil_dir = ROOT / "src" / "copiloto_n1" / "perfis"
    if perfil_dir.exists():
        extra_data.append(f"{perfil_dir}{os.pathsep}copiloto_n1/perfis")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        "CopilotoN1",
        "--distpath",
        str(DIST),
        "--workpath",
        str(BUILD),
        "--specpath",
        str(BUILD),
        "--collect-all",
        "PySide6",
        "--collect-all",
        "sounddevice",
        "--collect-all",
        "soundfile",
        "--collect-all",
        "faster_whisper",
        "--collect-all",
        "ctranslate2",
        "--hidden-import",
        "PySide6",
        "--hidden-import",
        "PySide6.QtCore",
        "--hidden-import",
        "PySide6.QtWidgets",
        "--hidden-import",
        "PySide6.QtGui",
        "--hidden-import",
        "sounddevice",
        "--hidden-import",
        "soundfile",
        "--hidden-import",
        "faster_whisper",
        "--hidden-import",
        "ctranslate2",
    ]

    for item in extra_data:
        cmd.extend(["--add-data", item])

    cmd.append(str(ROOT / "src" / "copiloto_n1" / "desktop_app.py"))

    print("Gerando executável...")
    print("Comando:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    if not exe.exists():
        exe = DIST / "CopilotoN1"

    if exe.exists():
        print(f"Executável pronto em: {exe}")
    else:
        print("Executável gerado, mas o nome final pode variar dependendo do sistema operacional.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
