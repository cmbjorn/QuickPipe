"""Session-state management and picker constants for the Quickpipe UI.

State model: a single Project holding metadata + a list of Lines. Each Line has a
tag, service, inlet conditions, and an ordered list of sections. ``inlet()`` and
``sections()`` return the *active* line's data, so the editor / march code is
line-agnostic. Section ids are globally unique so widget keys never collide
across lines.
"""
from __future__ import annotations

import datetime
import json
import re

import streamlit as st

import quickpipe.engine as _engine  # noqa: F401  (runs sys.path bootstrap)
import multiphase_engine as _E
from standards.piping import (
    PIPE_DATABASE, MATERIAL_ROUGHNESS, LINER_ROUGHNESS, FITTING_Le_over_D)

from quickpipe.engine.elements import (
    Pipe, Misc, default_inlet, element_to_dict, ORIENTATIONS)

# ── Picker option lists ──────────────────────────────────────────────────────
DN_LIST = list(PIPE_DATABASE.keys())
PN_LIST = sorted({pn for d in PIPE_DATABASE.values() for pn in d})
MATERIALS = list(MATERIAL_ROUGHNESS.keys())
LINERS = list(LINER_ROUGHNESS.keys())
FITTINGS = list(FITTING_Le_over_D.keys())
GAS_LIST = list(_E.GAS_SPECIES.keys())
LIQUID_LIST = list(_E.LIQUID_COOLPROP_ID.keys()) + ["KOH solution"]
CORRELATIONS = list(_E.TWO_PHASE_CORRELATIONS)
VOIDAGE_METHODS = list(_E.VOIDAGE_METHODS)

# ── Session keys ─────────────────────────────────────────────────────────────
K_PROJECT = "qp_project"
K_IDC = "qp_id_counter"
K_CORR = "qp_correlation"
K_VOID = "qp_voidage"
K_SUBSTEP = "qp_substep_gas"


def _next_id(prefix: str) -> str:
    st.session_state[K_IDC] += 1
    return f"{prefix}{st.session_state[K_IDC]}"


def _default_section() -> dict:
    return element_to_dict(Pipe(
        id=_next_id("p"), name="Section 1", dn="DN50", pn="PN40",
        length_m=20.0, orientation="Horizontal", material="SS316L",
        fittings_list=[{"type": "90° Standard Elbow", "qty": 2}]))


def _new_line(tag: str, service: str = "") -> dict:
    return {"id": _next_id("L"), "tag": tag, "service": service,
            "inlet": default_inlet(), "sections": [_default_section()]}


def init_state() -> None:
    st.session_state.setdefault(K_IDC, 100)
    if K_PROJECT not in st.session_state:
        line = _new_line("100-PL-001")
        st.session_state[K_PROJECT] = {
            "meta": {"project_name": "", "client": "", "calc_by": "",
                     "checked_by": "", "rev": "A",
                     "date": datetime.date.today().isoformat(), "notes": ""},
            "lines": [line], "active": line["id"]}
    st.session_state.setdefault(K_CORR, "Beggs-Brill")
    st.session_state.setdefault(K_VOID, "Homogeneous")
    st.session_state.setdefault(K_SUBSTEP, False)


# ── Project / line accessors ─────────────────────────────────────────────────
def project() -> dict:
    return st.session_state[K_PROJECT]


def meta() -> dict:
    return project()["meta"]


def lines() -> list:
    return project()["lines"]


def active_id() -> str:
    return project()["active"]


def set_active(line_id: str) -> None:
    project()["active"] = line_id


def active_line() -> dict:
    p = project()
    for ln in p["lines"]:
        if ln["id"] == p["active"]:
            return ln
    return p["lines"][0]


def inlet() -> dict:
    return active_line()["inlet"]


def sections() -> list:
    return active_line()["sections"]


# ── Line operations ──────────────────────────────────────────────────────────
def add_line() -> None:
    ln = _new_line(f"Line {len(lines()) + 1}")
    lines().append(ln)
    set_active(ln["id"])


def delete_line(line_id: str) -> None:
    ls = lines()
    if len(ls) <= 1:
        return
    idx = next((i for i, ln in enumerate(ls) if ln["id"] == line_id), None)
    if idx is not None:
        ls.pop(idx)
        if active_id() == line_id:
            set_active(ls[max(0, idx - 1)]["id"])


def duplicate_line(line_id: str) -> None:
    import copy
    src = next((ln for ln in lines() if ln["id"] == line_id), None)
    if not src:
        return
    dup = copy.deepcopy(src)
    dup["id"] = _next_id("L")
    dup["tag"] = f"{src['tag']} copy"
    for s in dup["sections"]:        # re-id sections so widget keys stay unique
        s["id"] = _next_id("p")
    lines().append(dup)
    set_active(dup["id"])


# ── Section operations (act on the active line) ──────────────────────────────
def add_pipe() -> None:
    secs = sections()
    n = sum(1 for e in secs if e.get("kind") == "pipe") + 1
    secs.append(element_to_dict(Pipe(id=_next_id("p"), name=f"Section {n}")))


def add_misc() -> None:
    secs = sections()
    n = sum(1 for e in secs if e.get("kind") == "misc") + 1
    secs.append(element_to_dict(Misc(id=_next_id("m"), name=f"Equipment {n}")))


def delete_section(idx: int) -> None:
    secs = sections()
    if len(secs) > 1 and 0 <= idx < len(secs):
        secs.pop(idx)


def move_section(idx: int, delta: int) -> None:
    secs = sections()
    j = idx + delta
    if 0 <= idx < len(secs) and 0 <= j < len(secs):
        secs[idx], secs[j] = secs[j], secs[idx]


# ── Save / load to file ──────────────────────────────────────────────────────
def export_project_json() -> str:
    payload = {"format": "quickpipe-project", "version": 1, **project()}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _bump_id_counter(proj: dict) -> None:
    mx = st.session_state.get(K_IDC, 100)
    for ln in proj.get("lines", []):
        tokens = [ln.get("id", "")] + [s.get("id", "") for s in ln.get("sections", [])]
        for tok in tokens:
            m = re.search(r"(\d+)$", str(tok))
            if m:
                mx = max(mx, int(m.group(1)))
    st.session_state[K_IDC] = mx + 1


def import_project(data: dict) -> None:
    if not isinstance(data, dict) or not data.get("lines"):
        raise ValueError("Not a valid Quickpipe project file (no lines).")
    proj = {
        "meta": data.get("meta", {}) or {},
        "lines": data["lines"],
        "active": data.get("active") or data["lines"][0]["id"],
    }
    if not any(ln["id"] == proj["active"] for ln in proj["lines"]):
        proj["active"] = proj["lines"][0]["id"]
    st.session_state[K_PROJECT] = proj
    _bump_id_counter(proj)
