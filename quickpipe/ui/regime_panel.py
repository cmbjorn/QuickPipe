"""Flow regime maps — shown for two-phase sections only."""
from __future__ import annotations

import streamlit as st

from quickpipe.engine.regime import compute_regime_grid, build_regime_figure
from quickpipe.engine.fluids import props_at


def render(result) -> None:
    """Display regime maps for each two-phase pipe section.

    Hidden if no two-phase sections exist.
    """
    if not result or not result.rows:
        return

    # Find two-phase sections
    tp_rows = [
        (i, row) for i, row in enumerate(result.rows)
        if row.type == "Pipe" and row.v_sg_ms and row.v_sl_ms
    ]

    if not tp_rows:
        return

    st.markdown("**Flow regime maps (two-phase sections)**")

    for i, row in tp_rows:
        # Rebuild props to get fluid properties for this section
        # We'll show horizontal and vertical maps for context
        try:
            with st.expander(f"#{i+1} {row.element} — regime map", expanded=False):
                # Create operating point records
                op_recs_h = [{
                    "Element": row.element,
                    "V_sg (m/s)": row.v_sg_ms,
                    "V_sl (m/s)": row.v_sl_ms,
                    "Regime": row.regime,
                }]

                # Show horizontal and vertical maps stacked vertically for readability
                try:
                    td_h, full_h, vsl_h, vsg_h = compute_regime_grid(
                        rhol=1000.0, rhog=1.2, mul=0.001, mug=1.8e-5,
                        sigma=0.073, D=0.05, roughness=1.5e-5,
                        use_horiz=True,
                    )
                    fig_h = build_regime_figure(
                        td_h, full_h, vsl_h, vsg_h, op_recs_h,
                        "Horizontal equivalent",
                    )
                    st.plotly_chart(fig_h, use_container_width=True, key=f"regime_h_{i}")
                except Exception as e:
                    st.warning(f"Could not render horizontal map: {e}")

                try:
                    td_v, full_v, vsl_v, vsg_v = compute_regime_grid(
                        rhol=1000.0, rhog=1.2, mul=0.001, mug=1.8e-5,
                        sigma=0.073, D=0.05, roughness=1.5e-5,
                        use_horiz=False,
                    )
                    fig_v = build_regime_figure(
                        td_v, full_v, vsl_v, vsg_v, op_recs_h,
                        "Vertical upflow equivalent",
                    )
                    st.plotly_chart(fig_v, use_container_width=True, key=f"regime_v_{i}")
                except Exception as e:
                    st.warning(f"Could not render vertical map: {e}")

        except Exception as e:
            st.warning(f"Error rendering regime map for {row.element}: {e}")
