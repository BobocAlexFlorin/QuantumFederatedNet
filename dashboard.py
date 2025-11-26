import streamlit as st
import pandas as pd
import time
import json
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG & CSS ---
st.set_page_config(page_title="Q-FLG Mission Control", page_icon="⚛️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #00ffcc; font-family: 'Courier New', monospace; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 5px; }
    .stMetricLabel { color: #8b949e; }
    .stMetricValue { color: #00ffcc; text-shadow: 0 0 10px #00ffcc; }
</style>
""", unsafe_allow_html=True)

# --- HELPER: DRAW BLOCH SPHERE ---
def draw_bloch_sphere(theta, phi):
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)
    x = 1 * np.outer(np.cos(u), np.sin(v))
    y = 1 * np.outer(np.sin(u), np.sin(v))
    z = 1 * np.outer(np.ones(np.size(u)), np.cos(v))

    vec_x = np.sin(theta) * np.cos(phi)
    vec_y = np.sin(theta) * np.sin(phi)
    vec_z = np.cos(theta)

    fig = go.Figure()
    fig.add_trace(go.Surface(x=x, y=y, z=z, opacity=0.1, showscale=False, colorscale='Blues'))
    fig.add_trace(go.Scatter3d(
        x=[0, vec_x], y=[0, vec_y], z=[0, vec_z],
        mode='lines+markers',
        line=dict(color='#00ffcc', width=5),
        marker=dict(size=4, color='#00ffcc'),
        name='Qubit State'
    ))
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        paper_bgcolor="rgba(0,0,0,0)",
        height=300
    )
    return fig

# --- HEADER ---
st.title("🛰️ QUANTUM SECURE GRID")
st.caption("ESA / UVT JOINT SIMULATION PROTOCOL v4.0 (Stable UI)")
st.divider()

# --- 1. DEFINE LAYOUT & PLACEHOLDERS (DO THIS ONCE) ---
# We create empty boxes first. We will fill them later.
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
with kpi_col1:
    kpi1_holder = st.empty() # Placeholder for Round
with kpi_col2:
    kpi2_holder = st.empty() # Placeholder for Nodes
with kpi_col3:
    kpi3_holder = st.empty() # Placeholder for Loss
with kpi_col4:
    kpi4_holder = st.empty() # Placeholder for Accuracy

# Main Area Placeholders
main_msg_holder = st.empty()
graph_holder = st.empty()

# Logs at the bottom
st.divider()
log_expander = st.expander("SYSTEM TELEMETRY LOGS (LIVE STREAM)", expanded=True)
with log_expander:
    log_holder = st.empty() # Placeholder for text logs

# --- 2. MAIN LOOP ---
while True:
    if os.path.exists("telemetry.json"):
        try:
            with open("telemetry.json", "r") as f:
                data = json.load(f)
            
            # Extract Data
            current_round = data.get("current_round", 0)
            total_rounds = data.get("total_rounds", 15)
            status = data.get("status", "IDLE")
            logs = data.get("logs", [])
            
            # --- UPDATE KPIs (Using the placeholders) ---
            # This REPLACES the content inside the box instead of adding a new box
            kpi1_holder.metric("ROUND", f"{current_round} / {total_rounds}")
            kpi2_holder.metric("NODES ONLINE", data.get("clients", 0))
            
            loss_val = 0
            acc_val = 0
            if logs:
                loss_val = logs[-1].get('loss', 0)
                acc_val = logs[-1].get('accuracy', 0)
            
            kpi3_holder.metric("ENTROPY LOSS", f"{loss_val:.4f}")
            kpi4_holder.metric("HIGGS ACCURACY", f"{acc_val:.1%}")

            # --- UPDATE MAIN VISUALS ---
            if status != "COMPLETE":
                # Show Training Status
                with main_msg_holder.container():
                    st.info(f"⚡ TRAINING IN PROGRESS... (Round {current_round})")
                    st.progress(current_round / total_rounds if total_rounds else 0)
                
                # Show Bloch Sphere
                if logs and 'angles' in logs[-1]:
                    theta, phi = logs[-1]['angles'][0]
                    fig = draw_bloch_sphere(theta, phi)
                    # We use a unique key based on time to force a redraw without duplication
                    graph_holder.plotly_chart(fig, use_container_width=True, key=f"bloch_{time.time()}")
            
            else:
                # Show Final Graph
                main_msg_holder.empty() # Clear the "Training" message
                
                df = pd.DataFrame(logs)
                fig_charts = make_subplots(specs=[[{"secondary_y": True}]])
                fig_charts.add_trace(go.Scatter(x=df['round'], y=df['loss'], name="Hamiltonian Energy", line=dict(color='#00ffcc', width=3)), secondary_y=False)
                if 'accuracy' in df.columns:
                    fig_charts.add_trace(go.Scatter(x=df['round'], y=df['accuracy'], name="Accuracy", fill='tozeroy', line=dict(color='#0088ff', width=1)), secondary_y=True)
                
                fig_charts.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                
                graph_holder.plotly_chart(fig_charts, use_container_width=True, key="final_chart")
                break # Stop the loop

            # --- UPDATE LOGS ---
            log_text = "\n".join([f"[{l['timestamp']}] {l['event']}" for l in reversed(logs)])
            log_holder.code(log_text, language="bash")

        except (json.JSONDecodeError, IndexError):
            pass
            
    time.sleep(1)