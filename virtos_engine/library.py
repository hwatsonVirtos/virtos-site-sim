
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# v1.4 requires explicit provenance + version stamping for extracted params.
# This module implements Variant A: parameter library editable in UI, semantics remain in engine.

LIBRARY_REL_PATH = Path("data") / "component_library.json"

@dataclass
class ComponentRecord:
    component_id: str
    component_type: str  # "pcs", "battery", "cable", "dcdc", "dispenser", "tariff"
    name: str
    architecture_compatibility: List[str]  # ["virtos","grid_only","ac_coupled"] subset
    parameters: Dict[str, Any]
    costs: Dict[str, Any]
    source: str  # e.g. "Virtos Pilot System Datasheet (PDF)" or "user_input"
    version: int
    effective_date: str  # ISO date
    notes: str = ""

def _default_library_path(base_dir: Optional[Path] = None) -> Path:
    if base_dir is None:
        # Place library beside app.py by default (repo root)
        base_dir = Path(__file__).resolve().parents[1]
    return base_dir / LIBRARY_REL_PATH

def _hash_library(payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]

def default_records() -> List[ComponentRecord]:
    # Defaults derived from existing v1.3 code + v1.4 canonical params.
    # Sources: internal defaults (user_input) unless explicitly from artifact.
    today = "2026-01-07"
    return [
        ComponentRecord(
            component_id="PCS_500",
            component_type="pcs",
            name="PCS 500 kW",
            architecture_compatibility=["virtos","grid_only","ac_coupled"],
            parameters={"power_kw": 500.0},
            costs={"capex_aud": 0.0},
            source="user_input",
            version=1,
            effective_date=today,
            notes="Default placeholder PCS size."
        ),
        ComponentRecord(
            component_id="PCS_1000",
            component_type="pcs",
            name="PCS 1000 kW",
            architecture_compatibility=["virtos","grid_only","ac_coupled"],
            parameters={"power_kw": 1000.0},
            costs={"capex_aud": 0.0},
            source="user_input",
            version=1,
            effective_date=today,
            notes="Default placeholder PCS size."
        ),
        ComponentRecord(
            component_id="BATT_500_1000",
            component_type="battery",
            name="Battery 500 kW / 1000 kWh",
            architecture_compatibility=["virtos","ac_coupled"],
            parameters={"power_kw": 500.0, "energy_kwh": 1000.0},
            costs={"capex_aud": 0.0},
            source="user_input",
            version=1,
            effective_date=today,
            notes="Default placeholder battery."
        ),
        ComponentRecord(
            component_id="BATT_1000_2000",
            component_type="battery",
            name="Battery 1000 kW / 2000 kWh",
            architecture_compatibility=["virtos","ac_coupled"],
            parameters={"power_kw": 1000.0, "energy_kwh": 2000.0},
            costs={"capex_aud": 0.0},
            source="user_input",
            version=1,
            effective_date=today,
            notes="Default placeholder battery."
        ),
        # Cables: v1 normalised to 800 V and Imax. Source is datasheet-driven in spirit.
        ComponentRecord(
            component_id="CABLE_375A",
            component_type="cable",
            name="Cable 375A (CCS Fleet)",
            architecture_compatibility=["virtos","grid_only","ac_coupled"],
            parameters={"imax_a": 375},
            costs={"capex_aud": 0.0},
            source="Virtos Pilot System Datasheet (PDF)",
            version=1,
            effective_date=today,
            notes="CCS Fleet: 375A continuous."
        ),
        ComponentRecord(
            component_id="CABLE_600A",
            component_type="cable",
            name="Cable 600A (CCS Ultra)",
            architecture_compatibility=["virtos","grid_only","ac_coupled"],
            parameters={"imax_a": 600},
            costs={"capex_aud": 0.0},
            source="Virtos Pilot System Datasheet (PDF)",
            version=1,
            effective_date=today,
            notes="CCS Ultra: 600A continuous; boost excluded in v1."
        ),
        ComponentRecord(
            component_id="CABLE_1500A",
            component_type="cable",
            name="Cable 1500A (MCS)",
            architecture_compatibility=["virtos","grid_only","ac_coupled"],
            parameters={"imax_a": 1500},
            costs={"capex_aud": 0.0},
            source="Virtos Pilot System Datasheet (PDF)",
            version=1,
            effective_date=today,
            notes="MCS: 1500A continuous."
        ),
        # DC-DC module: cap is locked elsewhere, but we allow a cost record.
        ComponentRecord(
            component_id="DCDC_100KW",
            component_type="dcdc",
            name="DC-DC Module 100 kW",
            architecture_compatibility=["virtos"],
            parameters={"cap_kw": 100.0},
            costs={"capex_aud": 0.0},
            source="Locked decision",
            version=1,
            effective_date=today,
            notes="Cap locked in v1.4 at 100 kW per module."
        ),
    ]

def load_library(base_dir: Optional[Path] = None) -> Tuple[Dict[str, Any], str]:
    path = _default_library_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        payload = {
            "schema_version": "v1.0",
            "generated_from": "default_records",
            "records": [r.__dict__ for r in default_records()],
            "history": [],
        }
        payload["library_hash"] = _hash_library(payload)
        path.write_text(json.dumps(payload, indent=2))
        return payload, payload["library_hash"]

    payload = json.loads(path.read_text())
    lib_hash = payload.get("library_hash") or _hash_library(payload)
    return payload, lib_hash

def save_library(payload: Dict[str, Any], base_dir: Optional[Path] = None) -> str:
    path = _default_library_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload["library_hash"] = _hash_library(payload)
    path.write_text(json.dumps(payload, indent=2))
    return payload["library_hash"]

def list_records(payload: Dict[str, Any], component_type: Optional[str] = None) -> List[Dict[str, Any]]:
    recs = payload.get("records", [])
    if component_type:
        recs = [r for r in recs if r.get("component_type") == component_type]
    return recs

def validate_records(records: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    seen_ids = set()
    allowed_types = {"pcs","battery","cable","dcdc","dispenser","tariff"}
    allowed_arch = {"virtos","grid_only","ac_coupled"}
    for i, r in enumerate(records):
        cid = (r.get("component_id") or "").strip()
        if not cid:
            errors.append(f"[row {i}] component_id is required")
            continue
        if cid in seen_ids:
            errors.append(f"[row {i}] duplicate component_id: {cid}")
        seen_ids.add(cid)

        ctype = r.get("component_type")
        if ctype not in allowed_types:
            errors.append(f"[{cid}] invalid component_type: {ctype}")

        arch = r.get("architecture_compatibility") or []
        if not isinstance(arch, list) or any(a not in allowed_arch for a in arch):
            errors.append(f"[{cid}] architecture_compatibility must be list subset of {sorted(allowed_arch)}")

        params = r.get("parameters") or {}
        costs = r.get("costs") or {}
        if not isinstance(params, dict) or not isinstance(costs, dict):
            errors.append(f"[{cid}] parameters and costs must be dicts")

        # Minimal per-type required params (keeps semantics in engine)
        if ctype == "pcs":
            if "power_kw" not in params:
                errors.append(f"[{cid}] pcs requires parameters.power_kw")
        if ctype == "battery":
            for k in ("power_kw","energy_kwh"):
                if k not in params:
                    errors.append(f"[{cid}] battery requires parameters.{k}")
        if ctype == "cable":
            if "imax_a" not in params:
                errors.append(f"[{cid}] cable requires parameters.imax_a")
        if ctype == "dcdc":
            if "cap_kw" not in params:
                errors.append(f"[{cid}] dcdc requires parameters.cap_kw")

        # Numeric sanity checks (no units inferred)
        for k, v in params.items():
            if isinstance(v, (int,float)) and v < 0:
                errors.append(f"[{cid}] parameters.{k} must be >= 0")
        for k, v in costs.items():
            if isinstance(v, (int,float)) and v < 0:
                errors.append(f"[{cid}] costs.{k} must be >= 0")

        for field_name in ("name","source","effective_date"):
            if not (r.get(field_name) or "").strip():
                errors.append(f"[{cid}] {field_name} is required")

        if not isinstance(r.get("version", 0), int) or r.get("version", 0) < 1:
            errors.append(f"[{cid}] version must be int >= 1")

    return errors

def apply_library_to_schemas(payload: Dict[str, Any]) -> None:
    """
    Updates the in-memory libraries in schemas.py for compatibility with existing engine code.
    Semantics remain in core; this only supplies parameters.
    """
    from . import schemas  # local import to avoid cycles

    # Reset and repopulate
    schemas.PCS_LIBRARY.clear()
    schemas.BATTERY_LIBRARY.clear()
    schemas.CABLE_LIBRARY.clear()

    for r in payload.get("records", []):
        ctype = r.get("component_type")
        cid = r.get("component_id")
        params = r.get("parameters") or {}
        if ctype == "pcs":
            schemas.PCS_LIBRARY[cid] = float(params["power_kw"])
        elif ctype == "battery":
            schemas.BATTERY_LIBRARY[cid] = {"power_kw": float(params["power_kw"]), "energy_kwh": float(params["energy_kwh"])}
        elif ctype == "cable":
            schemas.CABLE_LIBRARY[cid] = {"amps": float(params["imax_a"])}  # existing code expects "amps"
        # dcdc is locked in schemas (DC_DC_MODULE_KW), but costs may still be stored.

def upsert_records(payload: Dict[str, Any], updated_records: List[Dict[str, Any]], user_note: str = "") -> Tuple[Dict[str, Any], str]:
    """
    Replace records list with updated_records after validation; append to history with a snapshot hash.
    """
    errors = validate_records(updated_records)
    if errors:
        raise ValueError("Library validation failed:\n" + "\n".join(errors))

    old_hash = payload.get("library_hash", "")
    new_payload = dict(payload)
    new_payload["records"] = updated_records
    history = list(new_payload.get("history", []))
    history.append({
        "ts": datetime_now_iso(),
        "prev_hash": old_hash,
        "note": user_note[:2000],
    })
    new_payload["history"] = history
    new_hash = _hash_library(new_payload)
    new_payload["library_hash"] = new_hash
    return new_payload, new_hash

def datetime_now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
