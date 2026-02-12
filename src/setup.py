#!/usr/bin/env python3
"""
server_setup.py

Friend-proof Minecraft Java server setup:
- Downloads the official Mojang server.jar for a chosen version
- Generates start scripts (Windows .bat + Linux/macOS .sh)
- Runs the jar once to generate eula.txt (it will stop)
- Prompts to accept EULA (or --agree-eula), sets eula=true
- (Optional) tweaks server.properties and whitelist defaults

Usage:
  python scripts/server_setup.py
  python scripts/server_setup.py --dir server --latest
  python scripts/server_setup.py --version 1.21.4 --xms 2G --xmx 4G --agree-eula

Notes:
- Do NOT commit server.jar or worlds to git.
- This script downloads from Mojang's official version manifest.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import urlopen, Request


MANIFEST_URLS = [
    "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
    "https://launchermeta.mojang.com/mc/game/version_manifest.json",
]


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def http_get_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": "minecraft-server-setup/1.0"})
    with urlopen(req, timeout=timeout) as r:
        data = r.read().decode("utf-8")
    return json.loads(data)


def download_file(url: str, dest: Path, timeout: int = 60) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "minecraft-server-setup/1.0"})
    with urlopen(req, timeout=timeout) as r:
        total = r.headers.get("Content-Length")
        total_bytes = int(total) if total and total.isdigit() else None

        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            downloaded = 0
            last_print = 0.0
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                now = time.time()
                if now - last_print > 0.2:
                    last_print = now
                    if total_bytes:
                        pct = (downloaded / total_bytes) * 100
                        print(f"\rDownloading {dest.name}: {pct:6.2f}% ({downloaded}/{total_bytes} bytes)", end="")
                    else:
                        print(f"\rDownloading {dest.name}: {downloaded} bytes", end="")

        print()  # newline
        tmp.replace(dest)


def find_java() -> Optional[str]:
    # Prefer JAVA_HOME if set
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        cand = Path(java_home) / ("bin/java.exe" if platform.system() == "Windows" else "bin/java")
        if cand.exists():
            return str(cand)

    # Fall back to PATH
    java = shutil.which("java")
    return java


def run_java(java: str, cwd: Path, args: list[str]) -> int:
    try:
        proc = subprocess.run([java] + args, cwd=str(cwd))
        return proc.returncode
    except FileNotFoundError:
        return 127


def make_executable(path: Path) -> None:
    if platform.system() == "Windows":
        return
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def pick_manifest() -> Dict[str, Any]:
    last_err = None
    for url in MANIFEST_URLS:
        try:
            return http_get_json(url)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Failed to fetch Mojang version manifest. Last error: {last_err}")


def resolve_version(manifest: Dict[str, Any], requested: str) -> Dict[str, Any]:
    versions = manifest.get("versions", [])
    for v in versions:
        if v.get("id") == requested:
            return v
    raise ValueError(
        f"Version '{requested}' not found in Mojang manifest. "
        f"Try --latest or check spelling (example: 1.21.4)."
    )


def latest_release_id(manifest: Dict[str, Any]) -> str:
    latest = manifest.get("latest", {})
    rel = latest.get("release")
    if not rel:
        raise RuntimeError("Manifest did not include latest release.")
    return str(rel)


def get_server_jar_url(version_meta_url: str) -> str:
    vjson = http_get_json(version_meta_url)
    downloads = vjson.get("downloads", {})
    server = downloads.get("server", {})
    url = server.get("url")
    if not url:
        raise RuntimeError("Version metadata did not include a server download URL.")
    return str(url)


def write_start_scripts(server_dir: Path, xms: str, xmx: str, jar_name: str = "server.jar", nogui: bool = True) -> None:
    java_cmd = f'java -Xms{xms} -Xmx{xmx} -jar "{jar_name}"' + (" nogui" if nogui else "")
    # Windows
    bat = server_dir / "start.bat"
    bat.write_text(
        "@echo off\n"
        "setlocal\n"
        "cd /d %~dp0\n"
        f"{java_cmd}\n"
        "pause\n",
        encoding="utf-8",
    )

    # Linux/macOS
    sh = server_dir / "start.sh"
    sh.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'cd "$(dirname "$0")"\n'
        f"{java_cmd}\n",
        encoding="utf-8",
    )
    make_executable(sh)


def set_eula_true(server_dir: Path) -> None:
    eula_path = server_dir / "eula.txt"
    if not eula_path.exists():
        raise FileNotFoundError("eula.txt not found. Run the server once first to generate it.")
    lines = eula_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    replaced = False
    for line in lines:
        if line.strip().startswith("eula="):
            out.append("eula=true")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append("eula=true")
    eula_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def maybe_patch_server_properties(server_dir: Path, *, whitelist: Optional[bool], online_mode: Optional[bool]) -> None:
    prop = server_dir / "server.properties"
    if not prop.exists():
        return

    text = prop.read_text(encoding="utf-8", errors="replace").splitlines()
    kv = {}
    order = []
    for line in text:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            order.append(("raw", line))
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        kv[k] = v
        order.append(("kv", k))

    def set_k(key: str, value: str) -> None:
        kv[key] = value

    if whitelist is not None:
        set_k("white-list", "true" if whitelist else "false")
        # newer versions sometimes use "enforce-whitelist"
        set_k("enforce-whitelist", "true" if whitelist else "false")

    if online_mode is not None:
        set_k("online-mode", "true" if online_mode else "false")

    # Write back preserving comments/raw lines
    out_lines = []
    for typ, val in order:
        if typ == "raw":
            out_lines.append(val)
        else:
            k = val
            out_lines.append(f"{k}={kv.get(k, '')}")

    # Add any new keys not in original
    existing_keys = {val for typ, val in order if typ == "kv"}
    for k, v in kv.items():
        if k not in existing_keys:
            out_lines.append(f"{k}={v}")

    prop.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def prompt_yes_no(msg: str, default: bool = False) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        ans = input(msg + suffix).strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please enter y or n.")


def main() -> int:
    p = argparse.ArgumentParser(
        description="Set up a Minecraft Java server directory (downloads official server.jar and creates run scripts)."
    )
    p.add_argument("--dir", default="server", help="Server directory to create/use (default: server)")
    p.add_argument("--latest", action="store_true", help="Use latest release version")
    p.add_argument("--version", default=None, help="Minecraft version id, e.g. 1.21.4")
    p.add_argument("--xms", default="2G", help="Initial heap size, e.g. 2G (default: 2G)")
    p.add_argument("--xmx", default="4G", help="Max heap size, e.g. 4G (default: 4G)")
    p.add_argument("--nogui", action="store_true", default=True, help="Run with nogui (default: true)")
    p.add_argument("--no-nogui", dest="nogui", action="store_false", help="Run with GUI (not recommended)")
    p.add_argument("--agree-eula", action="store_true", help="Non-interactive: accept Mojang EULA (sets eula=true)")
    p.add_argument("--whitelist", action="store_true", help="Enable whitelist in server.properties (if present)")
    p.add_argument("--no-whitelist", action="store_true", help="Disable whitelist in server.properties (if present)")
    p.add_argument("--online-mode", action="store_true", help="Set online-mode=true in server.properties (if present)")
    p.add_argument("--offline-mode", action="store_true", help="Set online-mode=false in server.properties (NOT recommended)")

    args = p.parse_args()

    server_dir = Path(args.dir).resolve()
    server_dir.mkdir(parents=True, exist_ok=True)

    java = find_java()
    if not java:
        eprint("ERROR: Could not find Java. Install Java (Temurin / OpenJDK) and ensure 'java' is on PATH.")
        return 2

    # Resolve version
    manifest = pick_manifest()
    if args.latest and args.version:
        eprint("ERROR: Use only one of --latest or --version.")
        return 2

    if args.latest or not args.version:
        ver_id = latest_release_id(manifest) if args.latest or not args.version else args.version
    else:
        ver_id = args.version

    vmeta = resolve_version(manifest, ver_id)
    vmeta_url = vmeta.get("url")
    if not vmeta_url:
        eprint("ERROR: Version metadata did not include a URL.")
        return 2

    print(f"Selected Minecraft version: {ver_id}")
    print(f"Server directory: {server_dir}")

    # Download server.jar
    jar_url = get_server_jar_url(str(vmeta_url))
    jar_path = server_dir / "server.jar"
    if jar_path.exists():
        overwrite = prompt_yes_no("server.jar already exists. Re-download and overwrite?", default=False)
        if overwrite:
            jar_path.unlink(missing_ok=True)
        else:
            print("Keeping existing server.jar")
    if not jar_path.exists():
        print("Downloading official server.jar from Mojang...")
        download_file(jar_url, jar_path)

    # Write start scripts
    write_start_scripts(server_dir, args.xms, args.xmx, jar_name="server.jar", nogui=args.nogui)
    print("Wrote start scripts: start.bat, start.sh")

    # Run once to generate eula.txt (it will exit because eula=false)
    eula_path = server_dir / "eula.txt"
    if not eula_path.exists():
        print("Running server once to generate eula.txt (expected to stop immediately)...")
        rc = run_java(java, server_dir, [f"-Xms{args.xms}", f"-Xmx{args.xmx}", "-jar", "server.jar", "nogui"])
        if rc not in (0, 1):  # 1 often happens on first run; varies by version
            print(f"Server exited with code {rc} (this can be normal on first run).")

    # EULA acceptance
    if not eula_path.exists():
        eprint("ERROR: eula.txt still not found after first run. Check Java output above for errors.")
        return 3

    if args.agree_eula:
        accepted = True
    else:
        print()
        print(
            textwrap.dedent(
                """\
                Mojang requires accepting the Minecraft EULA to run a server.
                You can review it here: https://www.minecraft.net/eula
                """
            )
        )
        accepted = prompt_yes_no("Do you accept the Minecraft EULA and want to set eula=true?", default=False)

    if accepted:
        set_eula_true(server_dir)
        print("Set eula=true in eula.txt")
    else:
        print("EULA not accepted. Setup completed, but the server will not run until eula=true.")
        print(f"Edit: {eula_path}")
        return 0

    # Run again to generate server.properties + more files (optional but helpful)
    if prompt_yes_no("Run server now to generate remaining files (server.properties, etc.)?", default=True):
        rc = run_java(java, server_dir, [f"-Xms{args.xms}", f"-Xmx{args.xmx}", "-jar", "server.jar", "nogui"])
        print(f"Server exited with code {rc}. If it's still running, type 'stop' in the server console.")

    # Optional property tweaks
    whitelist_opt = None
    if args.whitelist:
        whitelist_opt = True
    if args.no_whitelist:
        whitelist_opt = False

    online_mode_opt = None
    if args.online_mode:
        online_mode_opt = True
    if args.offline_mode:
        online_mode_opt = False

    maybe_patch_server_properties(server_dir, whitelist=whitelist_opt, online_mode=online_mode_opt)

    print()
    print("Done.")
    print("To start the server:")
    if platform.system() == "Windows":
        print(f"  {server_dir / 'start.bat'}")
    else:
        print(f"  cd {server_dir} && ./start.sh")
    print()
    print("Next steps (README-worthy):")
    print("  - Set a whitelist (recommended).")
    print("  - Port forward TCP 25565 to this machine's LAN IP if hosting publicly.")
    print("  - Consider DuckDNS for a stable hostname if your IP changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
