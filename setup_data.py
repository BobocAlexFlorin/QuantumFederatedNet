import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.decomposition import PCA
import sys

# CONFIGURATION
# We limit to 2000 events to keep the simulation fast on a laptop
SAMPLE_SIZE = 2000 
NUM_CLIENTS = 2
CSV_PATH = "atlas-higgs-challenge-2014-v2.csv"

def process_higgs_data():
    print(f"[DATA ENGINEER] 🧹 Loading ATLAS Higgs Dataset from {CSV_PATH}...")
    
    try:
        # Load data
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"❌ ERROR: Could not find '{CSV_PATH}'.")
        print("   Please download it from: http://opendata.cern.ch/record/328")
        print("   And place it in this folder.")
        sys.exit(1)

    # 1. CLEANING
    print("[DATA ENGINEER] 🏷️  Encoding Labels (s -> 1, b -> -1)...")
    le = LabelEncoder()
    # Handle the fact that some versions of the CSV use 'Label' or 'Label '
    label_col = 'Label' if 'Label' in df.columns else df.columns[-1]
    
    df[label_col] = le.fit_transform(df[label_col]) # Maps to 0 and 1
    y = 2 * df[label_col].values - 1 # Maps to -1 and 1 (Quantum format)

    # Drop non-physics columns
    drop_cols = ['EventId', 'Weight', 'Label', 'KaggleSet', 'KaggleWeight']
    cols_to_drop = [c for c in drop_cols if c in df.columns]
    X_raw = df.drop(columns=cols_to_drop).values

    # Handle missing values (-999.0 is standard HEP code for missing)
    X_raw[X_raw == -999.0] = 0

    # 2. SAMPLING
    # Shuffle and take a small slice for the simulation
    indices = np.random.choice(len(X_raw), size=min(SAMPLE_SIZE, len(X_raw)), replace=False)
    X_sample = X_raw[indices]
    y_sample = y[indices]

    # 3. DIMENSIONALITY REDUCTION (PCA)
    print(f"[DATA ENGINEER] 📉 Performing PCA (30 features -> 2 features)...")
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_sample)

    # 4. NORMALIZATION
    print("[DATA ENGINEER] ⚖️  Scaling features to [0, 1]...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X_pca)

    # 5. DISTRIBUTE TO CLIENTS
    print(f"[DATA ENGINEER] 📦 Splitting data for {NUM_CLIENTS} clients...")
    
    # Split data into N chunks
    X_splits = np.array_split(X_scaled, NUM_CLIENTS)
    y_splits = np.array_split(y_sample, NUM_CLIENTS)

    for i in range(NUM_CLIENTS):
        filename = f"client_data_{i}.npz"
        np.savez(filename, X=X_splits[i], y=y_splits[i])
        print(f"   -> Created {filename} ({len(y_splits[i])} events)")

    print("[DATA ENGINEER] ✅ Data Preparation Complete.\n")

if __name__ == "__main__":
    process_higgs_data()