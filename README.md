Quantum-Secured Federated Learning Grid (QS-FLG)
A distributed, fault-tolerant Quantum Machine Learning architecture designed to train Variational Quantum Classifiers on CERN ATLAS data using privacy-preserving Federated Learning.

📖 Project Overview
This project simulates a Quantum Sensor Network where multiple clients (representing satellites or research nodes) collaboratively train a model to detect the Higgs Boson without sharing raw data.
The system integrates Theoretical Physics (Hamiltonian optimization, Bloch Sphere tracking) with Systems Engineering (Asynchronous multiprocessing, Atomic I/O, Cryptography) to create a robust, dashboard-monitored simulation.

🛠️ Technical & Physics Challenges
This project was built to address specific obstacles found at the intersection of Quantum Computing and Distributed Systems. Below are the key engineering challenges solved during development.

1.The Physics Obstacle: Simulation of Hardware Noise

The Challenge: Ideal quantum simulators do not reflect reality. Real quantum processors suffer from decoherence and control errors.
A standard QNN simulation would converge too perfectly, failing to demonstrate robustness.
The Solution: I implemented a custom Noise Injection layer in the client circuit using RZGate jitter. This introduces a "Coherent Control Error" (Hamiltonian perturbation) into the Ansatz, forcing the optimizer (COBYLA)
to find a robust minimum on the cost landscape despite the noise.

Metric: The dashboard visualizes this via the Bloch Sphere, tracking the qubit state trajectory (theta, phi) in real-time.


2. The Systems Obstacle: Asynchronous Race Conditions
The Challenge: In a high-frequency federated loop, the Server writes the global model (.npz file) while Clients attempt to read it simultaneously. This led to I/O Race Conditions where clients would read
partial/corrupted files, causing InvalidTag cryptography errors.

The Solution: Implemented an Atomic Write Pattern.Server writes encrypted data to a temporary file (model.tmp).Server forces a hardware flush (os.fsync).Server performs an atomic swap (os.replace), 
guaranteeing that at any given nanosecond, the file is either non-existent or perfectly valid.


3. The Security Obstacle: Quantum-Classical Serialization

The Challenge: Integrating AES-256-GCM encryption with NumPy arrays proved difficult. NumPy wraps binary data in 0-dimensional arrays, which causes buffer protocol mismatches when passed to the cryptography 
library.

The Solution: Engineered a custom serialization protocol in utils.py. The system serializes quantum weights and telemetry into a binary payload, encrypts them with a simulated QKD key, and strictly types the 
output before transmission.


🔬 Scientific Methodology
The DatasetSource: CERN Open Data Portal (ATLAS Higgs Challenge 2014).
Preprocessing: Principal Component Analysis (PCA) was applied to reduce the feature space from 30 dimensions to 2, mapping the high-energy physics variables onto the Hilbert space of a 2-qubit system.

The Quantum Model:
We minimize the expectation value of the Hamiltonian, where the ansatz theta is composed of ZZFeatureMap (Entanglement) and RealAmplitudes (Rotation).

🚀 How to Run
Clone the Repository:
Bash:git clone https://github.com/BobocAlexFlorin/QuantumFederatedNet

Install Dependencies:
Bash: pip install -r requirements.txt

Run the Mission Control Dashboard:
Bash: streamlit run dashboard.py

Ignite the Simulation:
Bash: python orchestrator.py
👨‍💻 Author Boboc Alexandru-Florin Final Year Student | Theoretical Physics & Computer Science | West University of Timisoara (UVT) | I am passionate about the intersection of High-Performance Computing, Quantum Mechanics, and Distributed Systems. This project serves as a proof-of-concept for my Bachelor's Thesis on secure quantum distributed networks.
🌐 LinkedIn: [linkedin.com/in/your-profile-id](https://www.linkedin.com/in/alexandru-florin-boboc-a25a43266/)
🐙 GitHub: github.com/BobocAlexFlorin
📧 Email: bobocalexflorin@gmail.com
Developed with ⚛️ and ☕ in Timisoara.
