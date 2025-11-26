import sys
import numpy as np
import warnings
import time

# --- FORCE UTF-8 FOR WINDOWS ---
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# --- Qiskit Imports ---
from qiskit.circuit.library import ZZFeatureMap, RealAmplitudes, RZGate
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit_machine_learning.optimizers import COBYLA

# --- Project Imports ---
try:
    from utils import save_packet, load_packet
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

warnings.filterwarnings("ignore")

def train_client(client_id):
    print(f"[{client_id}] ⚛️  QUANTUM NODE INITIALIZED (PID: {sys.argv[0]})")
    
    # 1. SETUP DATA (Real ATLAS Data)
    try:
        data = np.load(f"client_data_{client_id}.npz")
        X_local = data['X']
        y_local = data['y']
        print(f"[{client_id}] 📊 Loaded {len(y_local)} Higgs events from local drive.")
    except FileNotFoundError:
        print(f"[{client_id}] ❌ ERROR: Data file 'client_data_{client_id}.npz' missing.")
        print(f"[{client_id}] Please ensure setup_data.py ran successfully.")
        sys.exit(1)

    # 2. BUILD CIRCUIT WITH CONTROL ERROR
    num_qubits = 2
    feature_map = ZZFeatureMap(feature_dimension=num_qubits, reps=1)
    ansatz = RealAmplitudes(num_qubits=num_qubits, reps=1)
    
    # Noise Injection (Hamiltonian Jitter)
    noisy_ansatz = QuantumCircuit(num_qubits)
    noisy_ansatz.compose(ansatz, inplace=True)
    jitter_angle = 0.05 
    for q in range(num_qubits):
        noisy_ansatz.append(RZGate(jitter_angle), [q])

    qc = feature_map.compose(noisy_ansatz)

    # 3. DEFINE HAMILTONIAN
    qnn = EstimatorQNN(
        circuit=qc,
        input_params=feature_map.parameters,
        weight_params=ansatz.parameters,
        observables=SparsePauliOp.from_list([("ZZ", 1)])
    )

    # 4. LOAD GLOBAL WEIGHTS
    try:
        initial_weights = load_packet("global_model.npz")
        print(f"[{client_id}] 📥 Global Parameters Decrypted.")
    except (FileNotFoundError, IOError):
        initial_weights = 2 * np.pi * np.random.random(ansatz.num_parameters)
        print(f"[{client_id}] ⚠️  Cold Start: Random Initialization.")

    # 5. TRAINING LOOP
    def loss_function(params):
        preds = qnn.forward(X_local, params)
        return np.mean((preds - y_local.reshape(-1, 1))**2)

    optimizer = COBYLA(maxiter=10)
    result = optimizer.minimize(loss_function, initial_weights)

    # 6. CALCULATE METRICS
    final_preds = qnn.forward(X_local, result.x)
    class_preds = np.sign(final_preds).flatten()
    correct = np.sum(class_preds == y_local)
    accuracy = correct / len(y_local)

    # B. Qubit Angles
    theta = result.x[0] % (2*np.pi)
    phi = result.x[1] % (2*np.pi) if len(result.x) > 1 else 0

    # 7. PACK & ENCRYPT
    payload = np.concatenate([result.x, [accuracy, theta, phi]])
    
    save_packet(f"client_{client_id}_update.npz", payload)
    print(f"[{client_id}] 🔒 Telemetry Encrypted. Acc: {accuracy:.1%}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <client_id>")
    else:
        train_client(sys.argv[1])