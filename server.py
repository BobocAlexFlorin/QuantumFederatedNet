import sys
import numpy as np
import os
from utils import load_packet, save_packet

# --- FORCE UTF-8 FOR WINDOWS ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def aggregate(num_clients):
    print(f"[SERVER] 🛡️  Secure Aggregator Online. Listening for {num_clients} nodes...")
    
    collected_weights = []
    
    for i in range(num_clients):
        filename = f"client_{i}_update.npz"
        
        if os.path.exists(filename):
            try:
                # DECRYPTION
                payload = load_packet(filename)
                
                # UNPACK METRICS (The Upgrade)
                # The last 3 values are [accuracy, theta, phi]
                weights = payload[:-3] 
                metrics = payload[-3:] 
                
                accuracy = metrics[0]
                theta = metrics[1]
                phi = metrics[2]
                
                collected_weights.append(weights)
                
                # Save metrics to a separate file for the Orchestrator/Dashboard
                np.savez(f"client_{i}_metrics.npz", acc=accuracy, theta=theta, phi=phi)
                
                print(f"[SERVER] ✅ Node {i}: Verified. Higgs Acc: {accuracy:.1%}")
            except Exception as e:
                print(f"[SERVER] ❌ Node {i}: INTEGRITY CHECK FAILED. ({e})")
        else:
            print(f"[SERVER] ⚠️  Node {i}: TIMEOUT (Packet missing).")

    if collected_weights:
        # FEDERATED AVERAGING
        avg_weights = np.mean(collected_weights, axis=0)
        
        # ENCRYPT GLOBAL MODEL
        save_packet("global_model.npz", avg_weights)
        print(f"[SERVER] 🧠 New Global State Computed & Encrypted.")
    else:
        print("[SERVER] 💥 Critical Failure: No models received.")

if __name__ == "__main__":
    aggregate(int(sys.argv[1]))