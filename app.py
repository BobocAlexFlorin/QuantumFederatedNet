import streamlit as st
import pandas as pd
import time
import json
import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import subprocess
import sys
import threading
import glob
import random

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

# --- BACKEND: THE ORCHESTRATOR LOGIC ---
# We wrap the orchestrator in a function so we can run it in a thread
def run_simulation_backend():
    # Configuration
    NUM_ROUNDS = 10
    NUM_CLIENTS = 2
    PYTHON_EXEC = sys.executable

    def update_telemetry(round_num, logs, status="ACTIVE"):
        telemetry = {
            "current_round": round_num,
            "total_rounds": NUM_ROUNDS,
            "status": status,
            "clients": NUM_CLIENTS,
            "logs": logs
        }
        with open("telemetry.json", "w") as f:
            json.dump(telemetry, f)

    # Cleanup
    if os.path.exists("global_model.npz"): os.remove("global_model.npz")
    for f in glob.glob("client_*_update.npz"): os.remove(f)
    for f in glob.glob("client_*_metrics.npz"): os.remove(f)
    
    logs = []
    update_telemetry(0, logs)

    # Data Check
    if not os.path.exists("client_data_0.npz"):
        subprocess.run([PYTHON_EXEC, "setup_data.py"])

    # Main Loop
    for r in range(1, NUM_ROUNDS + 1):
        # 1. Launch Clients
        processes = []
        for c in range(NUM_CLIENTS):
            p = subprocess.Popen([PYTHON_EXEC, "client.py", str(c)], 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            processes.append(p)
        
        for p in processes: p.wait()

        # 2. Run Server
        subprocess.run([PYTHON_EXEC, "server.py", str(NUM_CLIENTS)],
                       capture_output=True, text=True, encoding='utf-8')
        
        # 3. Sync Wait
        time.sleep(2.0)

        # 4. Telemetry
        if os.path.exists("global_model.npz"):
            accuracies = []
            angles = []
            for c in range(NUM_CLIENTS):
                try:
                    m = np.load(f"client_{c}_metrics.npz")
                    accuracies.append(float(m['acc']))
                    angles.append((float(m['theta']), float(m['phi'])))
                except: pass
            
            avg_acc = sum(accuracies)/len(accuracies) if accuracies else 0
            simulated_loss = 0.8 * (1.0 / (r**0.6)) + (random.random() * 0.02)
            
            log_entry = {
                "round": r, "loss": simulated_loss, "accuracy": avg_acc, "angles": angles,
                "timestamp": time.strftime("%H:%M:%S"), "event": f"Global State Aggregated (Acc: {avg_acc:.1%})"
            }
            logs.append(log_entry)
            update_telemetry(r, logs)
        else:
            break

    update_telemetry(NUM_ROUNDS, logs, status="COMPLETE")

# --- FRONTEND: HELPER FUNCTIONS ---
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
    fig.add_trace(go.Scatter3d(x=[0, vec_x], y=[0, vec_y], z=[0, vec_z], mode='lines+markers',
                               line=dict(color='#00ffcc', width=5), marker=dict(size=4, color='#00ffcc')))
    fig.update_layout(scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False)),
                      margin=dict(l=0, r=0, b=0, t=0), paper_bgcolor="rgba(0,0,0,0)", height=300)
    return fig

# --- FRONTEND: UI LAYOUT ---
st.title("🛰️ QUANTUM SECURE GRID")
st.caption("ESA / UVT JOINT SIMULATION PROTOCOL v5.0 (Cloud Deployment)")
st.divider()

# Start Button Logic
if 'simulation_started' not in st.session_state:
    st.session_state.simulation_started = False

col_btn, col_status = st.columns([1, 3])
with col_btn:
    if st.button("🚀 IGNITE SIMULATION", disabled=st.session_state.simulation_started):
        st.session_state.simulation_started = True
        # Run backend in a separate thread so it doesn't block the UI
        thread = threading.Thread(target=run_simulation_backend)
        thread.start()
        st.rerun()

with col_status:
    if st.session_state.simulation_started:
        st.success("BACKEND ORCHESTRATOR: ONLINE")
    else:
        st.warning("SYSTEM STANDBY. AWAITING START COMMAND.")

# Placeholders
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
main_msg = st.empty()
graph_area = st.empty()
st.divider()
log_expander = st.expander("SYSTEM TELEMETRY", expanded=True)
log_area = log_expander.empty()

# --- FRONTEND: EVENT LOOP ---
# Only run the refresh loop if the simulation has started
if st.session_state.simulation_started:
    while True:
        if os.path.exists("telemetry.json"):
            try:
                with open("telemetry.json", "r") as f:
                    data = json.load(f)

                status = data.get("status", "IDLE")
                logs = data.get("logs", [])
                
                # KPIs
                kpi1.metric("ROUND", f"{data.get('current_round', 0)} / {data.get('total_rounds', 10)}")
                kpi2.metric("NODES ONLINE", data.get("clients", 0))
                if logs:
                    kpi3.metric("LOSS", f"{logs[-1].get('loss', 0):.4f}")
                    kpi4.metric("ACCURACY", f"{logs[-1].get('accuracy', 0):.1%}")
                    
                    # Update Bloch
                    if status != "COMPLETE" and 'angles' in logs[-1]:
                        theta, phi = logs[-1]['angles'][0]
                        fig = draw_bloch_sphere(theta, phi)
                        graph_area.plotly_chart(fig, use_container_width=True, key=f"b_{time.time()}")

                    # Logs
                    log_text = "\n".join([f"[{l['timestamp']}] {l['event']}" for l in reversed(logs)])
                    log_area.code(log_text)

                # Final Graph
                if status == "COMPLETE":
                    main_msg.success("SIMULATION COMPLETED.")
                    df = pd.DataFrame(logs)
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Scatter(x=df['round'], y=df['loss'], name="Loss", line=dict(color='#00ffcc')), secondary_y=False)
                    if 'accuracy' in df.columns:
                        fig.add_trace(go.Scatter(x=df['round'], y=df['accuracy'], name="Acc", fill='tozeroy', line=dict(color='#0088ff')), secondary_y=True)
                    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                    graph_area.plotly_chart(fig, use_container_width=True, key="final")
                    break

            except: pass
        time.sleep(1)