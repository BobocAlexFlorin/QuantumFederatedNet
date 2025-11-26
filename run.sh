#!/bin/bash

# Configuration
NUM_ROUNDS=3
NUM_CLIENTS=2
LOG_FILE="system.log"

echo "================================================="
echo "   QUANTUM SECURE FEDERATED GRID (QSFG) v2.0     "
echo "================================================="
echo "Date: $(date)" > $LOG_FILE

# 1. CLEANUP (SysAdmin Hygiene)
echo "[SYSTEM] Cleaning workspace..."
rm -f *.npz
rm -f *.txt

# 2. MAIN LOOP
for (( r=1; r<=NUM_ROUNDS; r++ ))
do
    echo ""
    echo ">>> STARTING ROUND $r Of $NUM_ROUNDS <<<" | tee -a $LOG_FILE
    
    # Launch Clients
    pids=""
    for (( c=0; c<NUM_CLIENTS; c++ ))
    do
        python client.py $c >> $LOG_FILE 2>&1 &
        pids="$pids $!"
    done

    # Wait for completion
    wait $pids
    echo "[SYSTEM] All clients finished training."
    
    # Run Server
    python server.py $NUM_CLIENTS
    
    # Check if server created the file (Bash Error Checking)
    if [ ! -f "global_model.npz" ]; then
        echo "[ERROR] Server failed to update global model!"
        exit 1
    fi
done

echo ""
echo "================================================="
echo "✅  SIMULATION COMPLETE. CHECK $LOG_FILE FOR DETAILS"
echo "================================================="