
from __future__ import annotations

import json
from typing import Any, Dict, List

import streamlit as st

from virtos_engine import library as lib


COMPONENT_TYPES = [
    ("pcs", "PCS"),
    ("battery", "Battery"),
    ("cable", "Cable"),
    ("dcdc", "DC-DC Module"),
    ("dispenser", "Dispenser"),
    ("tariff", "Tariff Template"),
]

def _flatten_record(r: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(r)
    params = out.pop("parameters", {}) or {}
    costs = out.pop("costs", {}) or {}
    for k, v in params.items():
        out[f"param__{k}"] = v
    for k, v in costs.items():
        out[f"cost__{k}"] = v
    # Render arch list as comma string for editing
    arch = out.get("architecture_compatibility") or []
    out["architecture_compatibility"] = ", ".join(arch)
    return out

def _unflatten_row(row: Dict[str, Any]) -> Dict[str, Any]:
    r = dict(row)
    params: Dict[str, Any] = {}
    costs: Dict[str, Any] = {}
    for k in list(r.keys()):
        if k.startswith("param__"):
            params[k[len("param__"):]] = r.pop(k)
        if k.startswith("cost__"):
            costs[k[len("cost__"):]] = r.pop(k)
    arch_str = (r.get("architecture_compatibility") or "").strip()
    arch = [a.strip() for a in arch_str.split(",") if a.strip()]
    r["architecture_compatibility"] = arch
    r["parameters"] = params
    r["costs"] = costs
    return r

def _infer_columns(flat_rows: List[Dict[str, Any]]) -> List[str]:
    keys = set()
    for r in flat_rows:
        keys.update(r.keys())
    # Stable ordering
    base = ["component_id","component_type","name","architecture_compatibility","source","version","effective_date","notes"]
    extra = sorted([k for k in keys if k not in base])
    return base + extra

def render_library_tab() -> None:
    st.subheader("Component Library (v1)")
    st.caption("Parameter registry only. Engine semantics are locked. All changes are versioned and validated.")
    payload, lib_hash = lib.load_library()
    # Keep in-memory schema libs aligned with the active library snapshot.
    lib.apply_library_to_schemas(payload)

    st.info(f"Active library hash: {lib_hash}")

    tcol1, tcol2, tcol3 = st.columns([2,2,1])
    with tcol1:
        ctype = st.selectbox("Component type", [ct for ct, _ in COMPONENT_TYPES], format_func=lambda x: dict(COMPONENT_TYPES).get(x, x))
    with tcol2:
        note = st.text_input("Change note (stored in history)", value="", placeholder="e.g., add new cable SKU, update capex")
    with tcol3:
        st.write("")
        st.write("")
        st.download_button(
            label="Export snapshot JSON",
            data=json.dumps(payload, indent=2),
            file_name="virtos_component_library_snapshot.json",
            mime="application/json",
            key="lib_export_snapshot",
        )

    records = lib.list_records(payload, component_type=ctype)
    flat = [_flatten_record(r) for r in records]
    cols = _infer_columns(flat)

    st.write("Edit records below. Add rows to create new SKUs. Fields `param__*` and `cost__*` are free-form but validated for required keys.")
    edited = st.data_editor(
        flat,
        width="stretch",
        num_rows="dynamic",
        column_order=cols,
        hide_index=True,
        key=f"component_editor__{ctype}",
    )

    # Rebuild full record list for all types, replacing only this type
    if st.button("Validate + Save changes", type="primary", key=f"save__{ctype}"):
        # Unflatten edited rows
        updated_this_type = []
        for row in edited:
            rr = _unflatten_row(row)
            rr["component_type"] = ctype  # force type
            updated_this_type.append(rr)

        # Merge with other types
        other = [r for r in payload.get("records", []) if r.get("component_type") != ctype]
        merged = other + updated_this_type

        try:
            new_payload, new_hash = lib.upsert_records(payload, merged, user_note=note)
        except Exception as e:
            st.error(str(e))
            return

        lib.save_library(new_payload)
        lib.apply_library_to_schemas(new_payload)
        st.success(f"Saved. New library hash: {new_hash}")
        # Only rerun when a save succeeds.
        st.rerun()
        

    st.divider()
    st.subheader("Snapshot diff (read-only)")
    st.caption("Compare two exported snapshot JSON files. This does not modify the active library.")

    c1, c2 = st.columns(2)
    with c1:
        f1 = st.file_uploader("Snapshot A (JSON)", type=["json"], key="snap_a")
    with c2:
        f2 = st.file_uploader("Snapshot B (JSON)", type=["json"], key="snap_b")

    def _load_json_file(f):
        if not f:
            return None
        try:
            return json.loads(f.getvalue().decode("utf-8"))
        except Exception as e:
            st.error(f"Failed to parse JSON: {e}")
            return None

    a = _load_json_file(f1)
    b = _load_json_file(f2)

    def _index(payload):
        recs = payload.get("records") or []
        out = {}
        for r in recs:
            cid = r.get("component_id") or r.get("id")
            if cid:
                out[cid] = r
        return out

    def _diff_dict(x, y, prefix=""):
        changes = []
        keys = set((x or {}).keys()) | set((y or {}).keys())
        for k in sorted(keys):
            xv = (x or {}).get(k, None)
            yv = (y or {}).get(k, None)
            if xv != yv:
                changes.append({"field": f"{prefix}{k}", "a": xv, "b": yv})
        return changes

    if a and b:
        ia = _index(a)
        ib = _index(b)
        added = sorted(set(ib.keys()) - set(ia.keys()))
        removed = sorted(set(ia.keys()) - set(ib.keys()))
        common = sorted(set(ia.keys()) & set(ib.keys()))

        st.write({
            "added": len(added),
            "removed": len(removed),
            "modified": 0,
        })

        if added:
            st.subheader("Added (in B only)")
            st.table([{"component_id": cid, "name": (ib[cid].get("name") or ""), "type": ib[cid].get("component_type")} for cid in added])

        if removed:
            st.subheader("Removed (in A only)")
            st.table([{"component_id": cid, "name": (ia[cid].get("name") or ""), "type": ia[cid].get("component_type")} for cid in removed])

        modified_rows = []
        field_changes = []
        for cid in common:
            ra = ia[cid]; rb = ib[cid]
            # top-level compare (excluding history-like keys)
            top_exclude = {"history", "updated_at"}
            top_a = {k:v for k,v in ra.items() if k not in top_exclude and k not in {"parameters","costs"}}
            top_b = {k:v for k,v in rb.items() if k not in top_exclude and k not in {"parameters","costs"}}
            ch = []
            ch += _diff_dict(top_a, top_b, prefix="")
            ch += _diff_dict(ra.get("parameters") or {}, rb.get("parameters") or {}, prefix="param__")
            ch += _diff_dict(ra.get("costs") or {}, rb.get("costs") or {}, prefix="cost__")
            if ch:
                modified_rows.append({"component_id": cid, "type": rb.get("component_type"), "name": rb.get("name"), "n_changes": len(ch)})
                for c in ch:
                    c2 = dict(c); c2["component_id"]=cid
                    field_changes.append(c2)

        st.write({"modified": len(modified_rows)})

        if modified_rows:
            st.subheader("Modified records")
            st.table(modified_rows)

            st.subheader("Field-level changes")
            st.table(field_changes[:200])
            if len(field_changes) > 200:
                st.caption(f"Showing first 200 changes of {len(field_changes)} total.")


