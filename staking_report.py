#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=6.0.0",
# ]
# ///
"""Generate a comprehensive staking performance report for the Quorum voting agent."""

import os
import json
import sys
from pathlib import Path
from web3 import Web3
from decimal import Decimal

# Configuration
SCRIPT_PATH = Path(__file__).resolve().parent

# Contract addresses
ATTESTATION_TRACKER = "0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
EAS_CONTRACT = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"
OLAS_TOKEN = "0x54330d28ca3357F294334BDC454a032e7f353416"

# Staking ABIs (inline for simplicity)
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

OLAS_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

ATTESTATION_TRACKER_ABI = [
  {
    "type": "constructor",
    "inputs": [
      {
        "name": "initialOwner",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "_EAS",
        "type": "address",
        "internalType": "address"
      }
    ],
    "stateMutability": "nonpayable"
  },
  {
    "type": "function",
    "name": "EAS",
    "inputs": [],
    "outputs": [
      {
        "name": "",
        "type": "address",
        "internalType": "address"
      }
    ],
    "stateMutability": "view"
  },
  {
    "type": "function",
    "name": "attestByDelegation",
    "inputs": [
      {
        "name": "schema",
        "type": "bytes32",
        "internalType": "bytes32"
      },
      {
        "name": "recipient",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "expirationTime",
        "type": "uint64",
        "internalType": "uint64"
      },
      {
        "name": "revocable",
        "type": "bool",
        "internalType": "bool"
      },
      {
        "name": "refUID",
        "type": "bytes32",
        "internalType": "bytes32"
      },
      {
        "name": "data",
        "type": "bytes",
        "internalType": "bytes"
      },
      {
        "name": "value",
        "type": "uint256",
        "internalType": "uint256"
      },
      {
        "name": "v",
        "type": "uint8",
        "internalType": "uint8"
      },
      {
        "name": "r",
        "type": "bytes32",
        "internalType": "bytes32"
      },
      {
        "name": "s",
        "type": "bytes32",
        "internalType": "bytes32"
      },
      {
        "name": "attester",
        "type": "address",
        "internalType": "address"
      },
      {
        "name": "deadline",
        "type": "uint64",
        "internalType": "uint64"
      }
    ],
    "outputs": [
      {
        "name": "attestationUID",
        "type": "bytes32",
        "internalType": "bytes32"
      }
    ],
    "stateMutability": "payable"
  },
  {
    "type": "function",
    "name": "getNumAttestations",
    "inputs": [
      {
        "name": "multisig",
        "type": "address",
        "internalType": "address"
      }
    ],
    "outputs": [
      {
        "name": "",
        "type": "uint256",
        "internalType": "uint256"
      }
    ],
    "stateMutability": "view"
  },
  {
    "type": "function",
    "name": "getVotingStats",
    "inputs": [
      {
        "name": "multisig",
        "type": "address",
        "internalType": "address"
      }
    ],
    "outputs": [
      {
        "name": "votingStats",
        "type": "uint256[]",
        "internalType": "uint256[]"
      }
    ],
    "stateMutability": "view"
  },
  {
    "type": "function",
    "name": "mapMultisigAttestations",
    "inputs": [
      {
        "name": "", 
        "type": "address",
        "internalType": "address"
      }
    ],
    "outputs": [
      {
        "name": "",
        "type": "uint256",
        "internalType": "uint256"
      }
    ],
    "stateMutability": "view"
  },
  {
    "type": "function",
    "name": "owner",
    "inputs": [],
    "outputs": [
      {
        "name": "",
        "type": "address",
        "internalType": "address"
      }
    ],
    "stateMutability": "view"
  },
  {
    "type": "function",
    "name": "renounceOwnership",
    "inputs": [],
    "outputs": [],
    "stateMutability": "nonpayable"
  },
  {
    "type": "function",
    "name": "transferOwnership",
    "inputs": [
      {
        "name": "newOwner",
        "type": "address",
        "internalType": "address"
      }
    ],
    "outputs": [],
    "stateMutability": "nonpayable"
  },
  {
    "type": "event",
    "name": "AttestationMade",
    "inputs": [
      {
        "name": "multisig",
        "type": "address",
        "indexed": True,
        "internalType": "address"
      },
      {
        "name": "attestationUID",
        "type": "bytes32",
        "indexed": True,
        "internalType": "bytes32"
      }
    ],
    "anonymous": False
  },
  {
    "type": "event",
    "name": "OwnershipTransferred",
    "inputs": [
      {
        "name": "previousOwner",
        "type": "address",
        "indexed": True,
        "internalType": "address"
      },
      {
        "name": "newOwner",
        "type": "address",
        "indexed": True,
        "internalType": "address"
      }
    ],
    "anonymous": False
  }
]

# Staking states
STAKING_STATES = {
    0: "Unstaked",
    1: "Staked",
    2: "Evicted"
}


def wei_to_olas(wei_amount: int) -> str:
    """Convert wei to OLAS with 2 decimal places."""
    olas = Decimal(wei_amount) / Decimal(10**18)
    return f"{olas:.2f}"


def wei_to_eth(wei_amount: int) -> str:
    """Convert wei to ETH with 4 decimal places."""
    eth = Decimal(wei_amount) / Decimal(10**18)
    return f"{eth:.4f}"


def load_service_config() -> dict:
    """Load service configuration from .operate directory."""
    operate_dir = SCRIPT_PATH / ".operate" / "services"

    if not operate_dir.exists():
        print("Error: No .operate/services directory found. Has the service been deployed?")
        sys.exit(1)

    # Find the service directory (should be only one)
    # Skip any services with "invalid_" prefix
    service_dirs = [d for d in operate_dir.iterdir() if d.is_dir() and not d.name.startswith("invalid_")]

    if not service_dirs:
        print("Error: No valid service found in .operate/services")
        sys.exit(1)

    if len(service_dirs) > 1:
        print(f"Warning: Multiple services found. Using {service_dirs[0].name}")

    config_path = service_dirs[0] / "config.json"

    if not config_path.exists():
        print(f"Error: config.json not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return json.load(f)


def print_header(text: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_subheader(text: str):
    """Print a subsection header."""
    print(f"\n{text}")
    print("-" * 40)


def main():
    """Generate staking performance report."""

    # Load configuration
    print("Loading service configuration...")
    config = load_service_config()

    # Extract relevant data
    chain_config = config.get("chain_configs", {}).get("base", {})
    chain_data = chain_config.get("chain_data", {})
    ledger_config = chain_config.get("ledger_config", {})

    service_id = chain_data.get("token")
    multisig = "0x7dF2A42C5a9006B16E6c7e6Ac750cdf336489c80"
    staking_contract_addr = chain_data.get("user_params", {}).get("staking_program_id")

    # Get RPC from environment variable, config, or use hardcoded default
    rpc_url = os.getenv("BASE_LEDGER_RPC") or ledger_config.get("rpc") or "https://cosmopolitan-cosmological-resonance.base-mainnet.quiknode.pro/b4c827323f0a8012212429b0bd4a72a060c5373c/"

    if not rpc_url:
        print("Error: No RPC URL found.")
        print("Set BASE_LEDGER_RPC environment variable or ensure it's in service config")
        sys.exit(1)

    if not all([service_id, multisig, staking_contract_addr]):
        print("Error: Missing required configuration (service_id, multisig, or staking_contract)")
        sys.exit(1)

    # Connect to blockchain
    print(f"Connecting to RPC: {rpc_url}")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print(f"Error: Could not connect to RPC at {rpc_url}")
        sys.exit(1)

    print(f"Connected to chain ID: {w3.eth.chain_id}")

    # Initialize contracts
    tracker = w3.eth.contract(address=ATTESTATION_TRACKER, abi=ATTESTATION_TRACKER_ABI)
    staking = w3.eth.contract(address=staking_contract_addr, abi=STAKING_ABI)
    olas = w3.eth.contract(address=OLAS_TOKEN, abi=OLAS_ABI)

    # Start report
    print_header("STAKING PERFORMANCE REPORT")

    # Service Information
    print_subheader("Service Information")
    print(f"Service ID:         {service_id}")
    print(f"Multisig:           {multisig}")
    print(f"Staking Contract:   {staking_contract_addr}")

    # Get staking state
    try:
        staking_state = staking.functions.getStakingState(service_id).call()
        state_name = STAKING_STATES.get(staking_state, f"Unknown ({staking_state})")

        print_subheader("Staking Status")
        print(f"Current State:      {state_name}")

        if staking_state == 0:  # Unstaked
            print("\n⚠️  Service is not currently staked.")
            print("   Run: ./stake_service.sh configs/config_quorum.json")
            return

        # Get service info
        service_info = staking.functions.getServiceInfo(service_id).call()
        service_multisig = service_info[0]
        service_owner = service_info[1]
        nonces = service_info[2]
        stake_start_time = service_info[3]

        if service_multisig.lower() != multisig.lower():
            print(f"\n⚠️  Warning: Multisig mismatch!")
            print(f"   Config: {multisig}")
            print(f"   Staking: {service_multisig}")

        # Attestation activity
        print_subheader("Attestation Activity")
        current_attestations = tracker.functions.getNumAttestations(multisig).call()
        baseline_attestations = nonces[1] if len(nonces) > 1 else 0
        delta = current_attestations - baseline_attestations

        print(f"Baseline (at stake): {baseline_attestations}")
        print(f"Current count:       {current_attestations}")
        print(f"New attestations:    {delta}")

        # Get voting stats if available
        try:
            voting_stats = tracker.functions.getVotingStats(multisig).call()
            if voting_stats:
                print(f"\nVoting breakdown:")
                vote_labels = ["For", "Against", "Abstain"]
                for i, count in enumerate(voting_stats[:3]):
                    label = vote_labels[i] if i < len(vote_labels) else f"Choice {i}"
                    print(f"  {label}: {count}")
        except Exception:
            pass  # Voting stats not available

        # Liveness check
        print_subheader("Liveness Check")
        current_time = w3.eth.get_block('latest')['timestamp']
        time_elapsed = current_time - stake_start_time
        hours_elapsed = time_elapsed / 3600
        days_elapsed = time_elapsed / 86400

        print(f"Staked since:        {stake_start_time}")
        print(f"Time elapsed:        {int(hours_elapsed)} hours ({days_elapsed:.1f} days)")

        # Calculate liveness ratio
        # Threshold: 1 attestation per 24 hours (from staking contract logic)
        threshold = 11574074074074
        ratio = (delta * 10**18) // time_elapsed if time_elapsed > 0 else 0
        passes = ratio >= threshold

        print(f"\nLiveness ratio:      {ratio:,}")
        print(f"Required threshold:  {threshold:,}")
        print(f"Status:              {'✅ PASS' if passes else '❌ FAIL'}")

        if not passes and time_elapsed > 0:
            needed = ((threshold * time_elapsed) // 10**18) - delta + 1
            print(f"\nAttestations needed: {needed}")
            rate_per_day = threshold * 86400 / 10**18
            print(f"Required rate:       {rate_per_day:.1f} attestations/day")

        # Rewards
        print_subheader("Staking Rewards")
        try:
            accrued_rewards = staking.functions.calculateStakingReward(service_id).call()
            available_rewards = staking.functions.availableRewards().call()

            print(f"Accrued rewards:     {wei_to_olas(accrued_rewards)} OLAS")
            print(f"Available in pool:   {wei_to_olas(available_rewards)} OLAS")

            if accrued_rewards > 0:
                print(f"\n✅ You have rewards to claim!")
                print(f"   Run: ./claim_staking_rewards.sh configs/config_quorum.json")
            else:
                print(f"\nℹ️  No rewards accrued yet.")
        except Exception as e:
            print(f"Could not retrieve rewards: {e}")

        # Balances
        print_subheader("Balances")
        multisig_eth = w3.eth.get_balance(multisig)
        multisig_olas = olas.functions.balanceOf(multisig).call()

        print(f"Multisig ETH:        {wei_to_eth(multisig_eth)} ETH")
        print(f"Multisig OLAS:       {wei_to_olas(multisig_olas)} OLAS")

        # Summary
        print_header("SUMMARY")
        if staking_state == 1:  # Staked
            if passes if 'passes' in locals() else True:
                print("✅ Service is staked and meeting liveness requirements")
            else:
                print("⚠️  Service is staked but NOT meeting liveness requirements")
                print("   Risk of eviction if activity does not increase")
        elif staking_state == 2:  # Evicted
            print("❌ Service has been evicted from staking")
            print("   You can unstake and claim any accrued rewards")

    except Exception as e:
        print(f"\nError retrieving staking information: {e}")
        print("\nThis may occur if:")
        print("  - Service has never been staked")
        print("  - RPC connection issues")
        print("  - Contract not deployed at specified address")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
