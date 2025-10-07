#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=6.0.0",
# ]
# ///
"""
End-to-end staking test with manual attestation execution.

Usage:
  # Initial checkpoint (hour 0)
  ./test_staking_checkpoints.py --checkpoint

  # After attestations, advance 25 hours
  ./test_staking_checkpoints.py --advance 25

  # After more attestations, advance another 25 hours
  ./test_staking_checkpoints.py --advance 25

  # Final report
  ./test_staking_checkpoints.py --report
"""

import os
import json
import sys
from pathlib import Path
from web3 import Web3
from decimal import Decimal
from datetime import datetime, timedelta
import argparse

# Configuration
SCRIPT_PATH = Path(__file__).resolve().parent
CHECKPOINT_FILE = SCRIPT_PATH / "staking_checkpoints.json"

# Contract addresses
ATTESTATION_TRACKER = "0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
OLAS_TOKEN = "0x54330d28ca3357F294334BDC454a032e7f353416"

# ABIs
STAKING_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "serviceId", "type": "uint256"}],
        "name": "getStakingState",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "serviceId", "type": "uint256"}],
        "name": "getServiceInfo",
        "outputs": [{
            "components": [
                {"internalType": "address", "name": "multisig", "type": "address"},
                {"internalType": "address", "name": "owner", "type": "address"},
                {"internalType": "uint256[]", "name": "nonces", "type": "uint256[]"},
                {"internalType": "uint256", "name": "tsStart", "type": "uint256"}
            ],
            "internalType": "struct StakingBase.ServiceInfo",
            "name": "",
            "type": "tuple"
        }],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "serviceId", "type": "uint256"}],
        "name": "calculateStakingReward",
        "outputs": [{"internalType": "uint256", "name": "reward", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "availableRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
]

ATTESTATION_TRACKER_ABI = [
    {
        "type": "function",
        "name": "getNumAttestations",
        "inputs": [{"name": "multisig", "type": "address", "internalType": "address"}],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view"
    },
]

STAKING_STATES = {0: "Unstaked", 1: "Staked", 2: "Evicted"}


def wei_to_olas(wei_amount: int) -> str:
    """Convert wei to OLAS with 2 decimal places."""
    olas = Decimal(wei_amount) / Decimal(10**18)
    return f"{olas:.2f}"


def load_service_config() -> dict:
    """Load service configuration from .operate directory."""
    operate_dir = SCRIPT_PATH / ".operate" / "services"
    
    if not operate_dir.exists():
        print("Error: No .operate/services directory found")
        sys.exit(1)
    
    service_dirs = [d for d in operate_dir.iterdir() if d.is_dir()]
    if not service_dirs:
        print("Error: No service found in .operate/services")
        sys.exit(1)
    
    config_path = service_dirs[0] / "config.json"
    with open(config_path) as f:
        return json.load(f)


def load_checkpoints() -> dict:
    """Load checkpoint data from file."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"checkpoints": [], "baseline_attestations": None}


def save_checkpoints(data: dict):
    """Save checkpoint data to file."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def advance_time(w3: Web3, hours: int):
    """Advance blockchain time using Anvil RPC."""
    seconds = hours * 3600
    
    # Increase time
    w3.provider.make_request("evm_increaseTime", [seconds])
    
    # Mine a block to apply the time change
    w3.provider.make_request("evm_mine", [])
    
    print(f"⏰ Advanced time by {hours} hours ({seconds} seconds)")


def get_current_state(w3: Web3, config: dict) -> dict:
    """Get current staking state."""
    chain_config = config.get("chain_configs", {}).get("base", {})
    chain_data = chain_config.get("chain_data", {})
    
    service_id = chain_data.get("token")
    multisig = chain_data.get("multisig")
    staking_contract_addr = chain_data.get("user_params", {}).get("staking_program_id")
    
    # Initialize contracts
    tracker = w3.eth.contract(address=ATTESTATION_TRACKER, abi=ATTESTATION_TRACKER_ABI)
    staking = w3.eth.contract(address=staking_contract_addr, abi=STAKING_ABI)
    
    # Get state
    staking_state = staking.functions.getStakingState(service_id).call()
    service_info = staking.functions.getServiceInfo(service_id).call()
    current_attestations = tracker.functions.getNumAttestations(multisig).call()
    
    baseline_attestations = service_info[2][1] if len(service_info[2]) > 1 else 0
    stake_start_time = service_info[3]
    
    try:
        accrued_rewards = staking.functions.calculateStakingReward(service_id).call()
    except Exception:
        accrued_rewards = 0
    
    current_time = w3.eth.get_block('latest')['timestamp']
    time_elapsed = current_time - stake_start_time
    
    # Calculate liveness
    delta_attestations = current_attestations - baseline_attestations
    threshold = 11574074074074
    liveness_ratio = (delta_attestations * 10**18) // time_elapsed if time_elapsed > 0 else 0
    passes_liveness = liveness_ratio >= threshold
    
    return {
        "timestamp": current_time,
        "staking_state": staking_state,
        "baseline_attestations": baseline_attestations,
        "current_attestations": current_attestations,
        "delta_attestations": delta_attestations,
        "accrued_rewards": accrued_rewards,
        "time_elapsed_hours": time_elapsed / 3600,
        "liveness_ratio": liveness_ratio,
        "passes_liveness": passes_liveness,
        "service_id": service_id,
        "multisig": multisig,
        "staking_contract": staking_contract_addr,
    }


def record_checkpoint(w3: Web3, config: dict, checkpoint_data: dict):
    """Record a checkpoint."""
    state = get_current_state(w3, config)
    
    # If this is the first checkpoint and we loaded from Anvil state,
    # we need to account for existing attestations
    if checkpoint_data["baseline_attestations"] is None:
        checkpoint_data["baseline_attestations"] = state["current_attestations"]
        print(f"📍 Initial state baseline: {state['current_attestations']} attestations from Anvil state file")
    
    checkpoint = {
        "checkpoint_num": len(checkpoint_data["checkpoints"]),
        "timestamp": state["timestamp"],
        "datetime": datetime.fromtimestamp(state["timestamp"]).isoformat(),
        "hours_elapsed": state["time_elapsed_hours"],
        "staking_state": STAKING_STATES.get(state["staking_state"], "Unknown"),
        "attestations_total": state["current_attestations"],
        "attestations_since_stake": state["delta_attestations"],
        "attestations_since_baseline": state["current_attestations"] - checkpoint_data["baseline_attestations"],
        "accrued_rewards_olas": wei_to_olas(state["accrued_rewards"]),
        "accrued_rewards_wei": state["accrued_rewards"],
        "liveness_ratio": state["liveness_ratio"],
        "passes_liveness": state["passes_liveness"],
    }
    
    checkpoint_data["checkpoints"].append(checkpoint)
    save_checkpoints(checkpoint_data)
    
    # Print checkpoint
    print("\n" + "="*60)
    print(f"📊 CHECKPOINT {checkpoint['checkpoint_num']}")
    print("="*60)
    print(f"Time:                    {checkpoint['datetime']}")
    print(f"Hours elapsed:           {checkpoint['hours_elapsed']:.1f}")
    print(f"Staking state:           {checkpoint['staking_state']}")
    print(f"Total attestations:      {checkpoint['attestations_total']}")
    print(f"  (from Anvil baseline:  {checkpoint_data['baseline_attestations']})")
    print(f"  (since stake:          {checkpoint['attestations_since_stake']})")
    print(f"New this test:           {checkpoint['attestations_since_baseline']}")
    print(f"Accrued rewards:         {checkpoint['accrued_rewards_olas']} OLAS")
    print(f"Liveness status:         {'✅ PASS' if checkpoint['passes_liveness'] else '❌ FAIL'}")
    print("="*60)


def print_report(checkpoint_data: dict):
    """Print final report."""
    if not checkpoint_data["checkpoints"]:
        print("No checkpoints recorded yet")
        return
    
    print("\n" + "="*80)
    print("📈 72-HOUR STAKING TEST REPORT")
    print("="*80)
    
    print(f"\nBaseline attestations (from Anvil state): {checkpoint_data['baseline_attestations']}")
    
    print("\n" + "-"*80)
    print(f"{'CP':<4} {'Hours':<8} {'State':<12} {'Total':<10} {'New':<8} {'Rewards (OLAS)':<18} {'Liveness':<10}")
    print("-"*80)
    
    for cp in checkpoint_data["checkpoints"]:
        print(f"{cp['checkpoint_num']:<4} "
              f"{cp['hours_elapsed']:<8.1f} "
              f"{cp['staking_state']:<12} "
              f"{cp['attestations_total']:<10} "
              f"{cp['attestations_since_baseline']:<8} "
              f"{cp['accrued_rewards_olas']:<18} "
              f"{'✅ PASS' if cp['passes_liveness'] else '❌ FAIL':<10}")
    
    print("-"*80)
    
    # Summary
    if len(checkpoint_data["checkpoints"]) > 1:
        first = checkpoint_data["checkpoints"][0]
        last = checkpoint_data["checkpoints"][-1]
        
        total_attestations = last["attestations_since_baseline"] - first["attestations_since_baseline"]
        total_rewards = last["accrued_rewards_wei"] - first["accrued_rewards_wei"]
        
        print(f"\n📊 Summary:")
        print(f"  Total test duration:     {last['hours_elapsed'] - first['hours_elapsed']:.1f} hours")
        print(f"  New attestations:        {total_attestations}")
        print(f"  Total rewards accrued:   {wei_to_olas(total_rewards)} OLAS")
        print(f"  Final liveness status:   {'✅ PASS' if last['passes_liveness'] else '❌ FAIL'}")


def main():
    parser = argparse.ArgumentParser(description="72-hour staking checkpoint test")
    parser.add_argument("--checkpoint", action="store_true", help="Record current checkpoint")
    parser.add_argument("--advance", type=int, metavar="HOURS", help="Advance time by N hours and record checkpoint")
    parser.add_argument("--report", action="store_true", help="Print final report")
    parser.add_argument("--reset", action="store_true", help="Reset checkpoint data")
    
    args = parser.parse_args()
    
    if args.reset:
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
        print("✅ Checkpoint data reset")
        return
    
    # Load config
    config = load_service_config()
    chain_config = config.get("chain_configs", {}).get("base", {})
    ledger_config = chain_config.get("ledger_config", {})
    
    rpc_url = os.getenv("BASE_LEDGER_RPC") or ledger_config.get("rpc")
    if not rpc_url:
        print("Error: No RPC URL found (set BASE_LEDGER_RPC)")
        sys.exit(1)
    
    # Connect to blockchain
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Error: Could not connect to {rpc_url}")
        sys.exit(1)
    
    # Load checkpoints
    checkpoint_data = load_checkpoints()
    
    if args.report:
        print_report(checkpoint_data)
    elif args.advance:
        advance_time(w3, args.advance)
        record_checkpoint(w3, config, checkpoint_data)
        print(f"\n💡 Next: Execute attestations, then run:")
        print(f"   ./test_staking_checkpoints.py --advance 25")
    elif args.checkpoint:
        record_checkpoint(w3, config, checkpoint_data)
        print(f"\n💡 Next: Execute attestations, then run:")
        print(f"   ./test_staking_checkpoints.py --advance 25")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
