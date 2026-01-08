import numpy as np
import pandas as pd

def run_engine(cfg: dict) -> dict:
    util_df = cfg.get("util_curve")
    if util_df is None or len(util_df)==0:
        util = np.zeros(96, dtype=float)
    else:
        util = util_df["utilisation"].to_numpy(dtype=float)

    max_power = float(cfg.get("super_strings", 0)) * float(cfg.get("dc_dc_modules_per_string", 0)) * 100.0
    demand = util * max_power

    grid_cap = float(cfg.get("grid_connection_kw", 0.0))
    pcs_cap  = float(cfg.get("pcs_shared_kw", 0.0))
    supply_cap = min(grid_cap, pcs_cap)

    served = np.minimum(demand, supply_cap)
    unserved = np.maximum(demand - served, 0.0)

    energy_kwh = served.sum() * 0.25
    peak_kw = served.max() if len(served) else 0.0

    n = len(served)
    thirds = max(n//3, 1)
    off = served[:thirds].sum()*0.25*float(cfg.get("tou_offpeak_per_kwh",0))
    sh  = served[thirds:2*thirds].sum()*0.25*float(cfg.get("tou_shoulder_per_kwh",0))
    pk  = served[2*thirds:].sum()*0.25*float(cfg.get("tou_peak_per_kwh",0))
    energy_cost = off+sh+pk

    sat = (served.sum()/demand.sum()) if demand.sum()>0 else 0.0

    ts = pd.DataFrame({
        "t": np.arange(n),
        "demand_kw": demand,
        "served_kw": served,
        "grid_import_kw": served,
        "unserved_kw": unserved,
    })
    return {
        "summary": {
            "energy_kwh": float(energy_kwh),
            "peak_kw": float(peak_kw),
            "energy_cost_$": float(energy_cost),
            "power_satisfied_pct": float(100.0*sat),
        },
        "timeseries": ts,
    }
