#!/usr/bin/env python3
"""
Shared helpers for the Rogue Garmin Bridge web layer.

Centralises path resolution, JSON file I/O, and the DeviceInfo
data model so that blueprints do not duplicate this logic.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

# Project root — two levels up from this file (src/web/helpers.py)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def project_path(*parts: str) -> str:
    """Return an absolute path relative to the project root."""
    return os.path.join(PROJECT_ROOT, *parts)


def settings_path() -> str:
    return project_path('settings.json')


def profile_path() -> str:
    return project_path('user_profile.json')


def fit_files_dir() -> str:
    return project_path('fit_files')


# ---------------------------------------------------------------------------
# JSON file I/O
# ---------------------------------------------------------------------------

def load_json_file(path: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """Load a JSON file, returning *default* (empty dict) if missing or invalid."""
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r') as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return default


def save_json_file(path: str, data: Dict[str, Any]) -> None:
    """Atomically write *data* as pretty-printed JSON to *path*."""
    with open(path, 'w') as fh:
        json.dump(data, fh, indent=2)


# ---------------------------------------------------------------------------
# DeviceInfo data model
# ---------------------------------------------------------------------------

@dataclass
class DeviceInfo:
    """Unified representation of a connected BLE device."""
    name: Optional[str] = None
    address: Optional[str] = None
    rssi: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_any(cls, obj) -> Optional['DeviceInfo']:
        """
        Create a DeviceInfo from *obj* regardless of whether it is a dict,
        a BLEDevice, a SimulatedBLEDevice, or ``None``.
        """
        if obj is None:
            return None
        if isinstance(obj, cls):
            return obj
        if isinstance(obj, dict):
            return cls(
                name=obj.get('name'),
                address=obj.get('address'),
                rssi=obj.get('rssi'),
                metadata=obj.get('metadata'),
            )
        # Object with attributes (BLEDevice, SimulatedBLEDevice, etc.)
        return cls(
            name=getattr(obj, 'name', None),
            address=getattr(obj, 'address', None),
            rssi=getattr(obj, 'rssi', None),
            metadata=getattr(obj, 'metadata', None),
        )


# ---------------------------------------------------------------------------
# Safe path check for file downloads
# ---------------------------------------------------------------------------

def is_safe_path(base_dir: str, user_path: str) -> bool:
    """
    Return ``True`` if *user_path* resolved under *base_dir* stays within
    *base_dir* (canonical-path comparison, immune to ``..`` tricks).
    """
    base = os.path.realpath(base_dir)
    target = os.path.realpath(os.path.join(base, user_path))
    return target.startswith(base + os.sep) or target == base
