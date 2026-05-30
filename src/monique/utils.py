"""Utility helpers: XDG paths, file I/O, app configuration."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


APP_ID = "com.github.monique"

# Override runtime impostato via --config-dir (priorità su settings.json)
_runtime_config_dir: str | None = None


def config_dir() -> Path:
    """Return ~/.config/monique, creating it if needed."""
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / "monique"
    d.mkdir(parents=True, exist_ok=True)
    return d


def profiles_dir() -> Path:
    """Return the profiles subdirectory."""
    d = config_dir() / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_sway_installed() -> bool:
    """Return True if Sway is available on the system."""
    return shutil.which("sway") is not None


def is_hyprland_installed() -> bool:
    """Return True if Hyprland is available on the system."""
    return shutil.which("Hyprland") is not None


def is_niri_installed() -> bool:
    """Return True if Niri is available on the system."""
    return shutil.which("niri") is not None


def _config_dir_override() -> Path | None:
    """Restituisce il percorso personalizzato per la config monitor, se configurato.

    Priorità: --config-dir (runtime) > settings.json > default del compositor.
    """
    if _runtime_config_dir:
        return Path(_runtime_config_dir).expanduser()
    override = load_app_settings().get("config_dir")
    if override:
        return Path(override).expanduser()
    return None


def _settings_path_override(key: str) -> Path | None:
    """Return a configured file path override unless --config-dir is active."""
    if _runtime_config_dir:
        return None
    override = load_app_settings().get(key)
    if override:
        return Path(override).expanduser()
    return None


def sway_config_dir() -> Path:
    """Return the Sway config directory."""
    override = _config_dir_override()
    if override:
        return override
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "sway"


def hyprland_config_dir() -> Path:
    """Return the Hyprland config directory."""
    override = _config_dir_override()
    if override:
        return override
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "hypr"


def hyprland_uses_lua_config() -> bool:
    """Return True when Hyprland should receive Lua monitor config."""
    if _runtime_config_dir:
        return False
    monitors_override = _settings_path_override("hyprland_monitors_path")
    workspaces_override = _settings_path_override("hyprland_workspaces_path")
    if monitors_override and monitors_override.suffix == ".lua":
        return True
    if workspaces_override and workspaces_override.suffix == ".lua":
        return True
    conf_dir = hyprland_config_dir()
    return (conf_dir / "hyprland.lua").exists()


def hyprland_monitors_path() -> Path:
    """Return the Hyprland monitor config file Monique should write."""
    override = _settings_path_override("hyprland_monitors_path")
    if override:
        return override
    conf_dir = hyprland_config_dir()
    if hyprland_uses_lua_config():
        return conf_dir / "monitors.lua"
    return conf_dir / "monitors.conf"


def hyprland_workspaces_path() -> Path:
    """Return the Hyprland workspace config file Monique should write."""
    override = _settings_path_override("hyprland_workspaces_path")
    if override:
        return override
    conf_dir = hyprland_config_dir()
    if hyprland_uses_lua_config():
        return conf_dir / "workspaces.lua"
    return conf_dir / "monitors.conf"


def hyprland_managed_paths() -> list[Path]:
    """Return Hyprland config files managed by Monique."""
    paths = (
        [hyprland_workspaces_path(), hyprland_monitors_path()]
        if hyprland_uses_lua_config()
        else [hyprland_monitors_path()]
    )
    result: list[Path] = []
    for path in paths:
        if path not in result:
            result.append(path)
    return result


def niri_config_dir() -> Path:
    """Return the Niri config directory."""
    override = _config_dir_override()
    if override:
        return override
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "niri"


def hyprland_runtime_dir() -> Path:
    """Return the Hyprland runtime directory for IPC sockets."""
    his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    xdg = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return Path(xdg) / "hypr" / his


def read_json(path: Path) -> dict | list | None:
    """Read and parse a JSON file, returning None on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path: Path, data: dict | list) -> None:
    """Write data as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    """Write text to a file, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def backup_file(path: Path) -> Path | None:
    """Create a .bak copy of a file. Returns backup path or None."""
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    bak.write_bytes(path.read_bytes())
    return bak


def restore_backup(path: Path) -> bool:
    """Restore a file from its .bak copy."""
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        return False
    path.write_bytes(bak.read_bytes())
    bak.unlink()
    return True


def sddm_xsetup_path() -> Path:
    """Return the path to the SDDM Xsetup script."""
    return Path("/usr/share/sddm/scripts/Xsetup")


def is_sddm_running() -> bool:
    """Return True if SDDM is installed (Xsetup script path exists)."""
    return sddm_xsetup_path().exists()


def write_xsetup(content: str) -> None:
    """Write the SDDM Xsetup script using pkexec for root privileges."""
    subprocess.run(
        ["pkexec", "tee", str(sddm_xsetup_path())],
        input=content.encode(),
        stdout=subprocess.DEVNULL,
        check=True,
    )


def greetd_sway_config_path() -> Path:
    """Return the path to the greetd sway config file."""
    return Path("/etc/greetd/sway-config")


def greetd_monitors_path() -> Path:
    """Return the path to the greetd monitors config file."""
    return Path("/etc/greetd/monique-monitors.conf")


def is_greetd_running() -> bool:
    """Return True if greetd is configured with sway (sway-config exists)."""
    return greetd_sway_config_path().exists()


def write_greetd_monitors(content: str) -> None:
    """Write the greetd monitors config using pkexec for root privileges."""
    subprocess.run(
        ["pkexec", "tee", str(greetd_monitors_path())],
        input=content.encode(),
        stdout=subprocess.DEVNULL,
        check=True,
    )


def _settings_path() -> Path:
    """Return the path to the global app settings file."""
    return config_dir() / "settings.json"


def load_app_settings() -> dict:
    """Load global application settings."""
    return read_json(_settings_path()) or {}


def save_app_settings(settings: dict) -> None:
    """Save global application settings."""
    write_json(_settings_path(), settings)


def save_active_profile(name: str | None) -> None:
    """Persist the name of the last applied profile."""
    settings = load_app_settings()
    write_json(_settings_path(), {**settings, "active_profile": name})


def get_active_profile() -> str | None:
    """Return the name of the last applied profile, or None."""
    return load_app_settings().get("active_profile")
