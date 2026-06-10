"""Quickpipe engine — pure Python, no Streamlit.

The heavy physics lives in vendored copies of the FlowBench engine modules under
``_vendor/`` (see _vendor/VENDORED_FROM.md). Those modules use absolute imports
such as ``from standards.piping import ...``, so we prepend the vendor directory
to ``sys.path`` here — before any vendored module is imported — and never edit
the vendored sources. Quickpipe-specific code (elements, march, sizing) imports
the vendored modules by their original top-level names.
"""
import os
import sys

_VENDOR_DIR = os.path.join(os.path.dirname(__file__), "_vendor")
if _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

# Public API
from .elements import (FluidSpec, LineInlet, Pipe, Misc,                  # noqa: E402
                       default_inlet, default_sections)
from .march import march, MarchResult                                    # noqa: E402
from .sizing import suggest_dn, SizingCriteria                           # noqa: E402
from .results import QuickpipeRow                                        # noqa: E402

__all__ = [
    "FluidSpec", "LineInlet", "Pipe", "Misc", "default_inlet", "default_sections",
    "march", "MarchResult", "suggest_dn", "SizingCriteria", "QuickpipeRow",
]
