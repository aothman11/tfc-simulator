"""Load YAML data files and assumptions into Python dicts."""
from __future__ import annotations
import pathlib
from typing import Any
import yaml

ROOT = pathlib.Path(__file__).parent.parent.parent
DATA = ROOT / "data"
ASSUMPTIONS_FILE = ROOT / "assumptions.yaml"


def load_yaml(path: pathlib.Path) -> Any:
    with open(path) as f:
        return yaml.safe_load(f)


def load_products() -> dict:
    return load_yaml(DATA / "products.yaml")


def load_customers() -> dict:
    return load_yaml(DATA / "customers.yaml")


def load_suppliers() -> dict:
    return load_yaml(DATA / "suppliers.yaml")


def load_operations() -> dict:
    return load_yaml(DATA / "operations.yaml")


def load_baseline(round_num: int = 2) -> dict:
    fname = "round2_baseline.yaml" if round_num == 2 else "round3_current.yaml"
    return load_yaml(DATA / fname)


def load_assumptions() -> dict[str, dict]:
    raw = load_yaml(ASSUMPTIONS_FILE)
    return {a["name"]: a for a in raw["assumptions"]}


def get_assumption_default(name: str, overrides: dict | None = None) -> Any:
    if overrides and name in overrides:
        return overrides[name]
    assumptions = load_assumptions()
    if name not in assumptions:
        raise KeyError(f"Unknown assumption: {name}")
    return assumptions[name]["default"]


def list_unverified(assumptions: dict[str, dict]) -> list[str]:
    return [name for name, a in assumptions.items() if a["status"] == "UNVERIFIED"]
