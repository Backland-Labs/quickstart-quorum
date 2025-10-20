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
ACTIVITY_CHECKER = "0x747262cC12524C571e08faCb6E6994EF2E3B97ab"
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
    {
        "inputs": [],
        "name": "livenessPeriod",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "minStakingDeposit",
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

ACTIVITY_CHECKER_ABI = [{"inputs":[{"internalType":"address","name":"_quorumTracker","type":"address"},{"internalType":"uint256","name":"_livenessRatio","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"ZeroAddress","type":"error"},{"inputs":[],"name":"ZeroValue","type":"error"},{"inputs":[{"internalType":"address","name":"multisig","type":"address"}],"name":"getMultisigNonces","outputs":[{"internalType":"uint256[]","name":"nonces","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256[]","name":"curNonces","type":"uint256[]"},{"internalType":"uint256[]","name":"lastNonces","type":"uint256[]"},{"internalType":"uint256","name":"ts","type":"uint256"}],"name":"isRatioPass","outputs":[{"internalType":"bool","name":"ratioPass","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"livenessRatio","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"quorumTracker","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]

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


def get_agent_addresses(service_dir: Path) -> list[str]:
    """Extract agent addresses from service deployment."""
    agent_addresses = []

    # First try the top-level keys.json
    keys_file = service_dir / "keys.json"
    if keys_file.exists():
        try:
            with open(keys_file) as f:
                keys_data = json.load(f)
                if isinstance(keys_data, list):
                    for key_entry in keys_data:
                        address = key_entry.get("address")
                        if address:
                            agent_addresses.append(address)
        except Exception:
            pass

    # If not found, look for keys.json files in agent directories
    if not agent_addresses:
        deployment_dir = service_dir / "deployment"
        if deployment_dir.exists():
            for agent_dir in deployment_dir.iterdir():
                if agent_dir.is_dir():
                    keys_file = agent_dir / "keys.json"
                    if keys_file.exists():
                        try:
                            with open(keys_file) as f:
                                keys_data = json.load(f)
                                if isinstance(keys_data, list) and len(keys_data) > 0:
                                    address = keys_data[0].get("address")
                                    if address:
                                        agent_addresses.append(address)
                        except Exception:
                            pass

    return agent_addresses


def print_header(text: str):
    """Print a section header."""
    print(f"\n{text}")
    print("=" * 80)


def print_subheader(text: str):
    """Print a subsection header."""
    print(f"\n{text}")
    print("-" * 80)


def main():
    """Generate staking performance report."""

    # Load configuration
    print("Loading service configuration...")
    operate_dir = SCRIPT_PATH / ".operate" / "services"
    service_dirs = [d for d in operate_dir.iterdir() if d.is_dir() and not d.name.startswith("invalid_")]
    service_dir = service_dirs[0] if service_dirs else None

    config = load_service_config()

    # Extract relevant data
    chain_config = config.get("chain_configs", {}).get("base", {})
    chain_data = chain_config.get("chain_data", {})
    ledger_config = chain_config.get("ledger_config", {})

    # Allow override for testing
    service_id = os.getenv("TEST_SERVICE_ID") or chain_data.get("token")
    if service_id:
        service_id = int(service_id)

    staking_contract_addr = os.getenv("STAKING_CONTRACT_ADDRESS") or chain_data.get("user_params", {}).get("staking_program_id")

    # If staking is not enabled, use the default staking contract
    if not staking_contract_addr or staking_contract_addr == "no_staking":
        staking_contract_addr = "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"

    # Get agent addresses
    agent_addresses = get_agent_addresses(service_dir) if service_dir else []

    # Get RPC from environment variable, config, or use hardcoded default
    rpc_url = os.getenv("BASE_LEDGER_RPC") or ledger_config.get("rpc")

    if not rpc_url:
        print("Error: No RPC URL found.")
        print("Set BASE_LEDGER_RPC environment variable or ensure it's in service config")
        sys.exit(1)

    if not all([service_id, staking_contract_addr]):
        print("Error: Missing required configuration (service_id or staking_contract)")
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
    activity_checker = w3.eth.contract(address=ACTIVITY_CHECKER, abi=ACTIVITY_CHECKER_ABI)
    staking = w3.eth.contract(address=staking_contract_addr, abi=STAKING_ABI)
    olas = w3.eth.contract(address=OLAS_TOKEN, abi=OLAS_ABI)

    # Get staking state first
    try:
        staking_state = staking.functions.getStakingState(service_id).call()
        state_name = STAKING_STATES.get(staking_state, f"Unknown ({staking_state})")
        is_staked = staking_state == 1

        # Get service info
        service_info = staking.functions.getServiceInfo(service_id).call()
        service_multisig = service_info[0]
        service_owner = service_info[1]
        nonces = service_info[2]
        stake_start_time = service_info[3]

        # Use multisig from env var if provided, otherwise from staking contract
        multisig = os.getenv("TEST_MULTISIG") or service_multisig

        # Get staking parameters
        min_staking_deposit = staking.functions.minStakingDeposit().call()

        # Get rewards
        accrued_rewards = staking.functions.calculateStakingReward(service_id).call()

        # Get current nonces from activity checker
        current_nonces = activity_checker.functions.getMultisigNonces(multisig).call()

        # Calculate attestations in current epoch (using multisig nonce at index 0)
        delta_attestations = current_nonces[0] - nonces[0]

        # Calculate liveness check using isRatioPass
        current_time = w3.eth.get_block('latest')['timestamp']
        time_elapsed = current_time - stake_start_time
        liveness_pass = activity_checker.functions.isRatioPass(current_nonces, nonces, time_elapsed).call()

        # Get balances
        multisig_eth = w3.eth.get_balance(multisig)

        # Get agent info
        agent_addresses = get_agent_addresses(service_dir) if service_dir else []
        agent_eth = w3.eth.get_balance(agent_addresses[0]) if agent_addresses else 0

        # Print simple report
        print_header("Staking")
        print(f"{'Is service staked?':<30} {'Yes' if is_staked else 'No'}")
        print(f"{'Staking program':<30} {staking_contract_addr[:20]}...")
        print(f"{'Staking state':<30} {state_name.upper()}")
        print(f"{'Staked (security deposit)':<30} {wei_to_olas(min_staking_deposit)} OLAS")
        print(f"{'Staked (agent bond)':<30} {wei_to_olas(min_staking_deposit)} OLAS")
        print(f"{'Accrued rewards':<30} {wei_to_olas(accrued_rewards)} OLAS")
        print(f"{'Num. txs current epoch':<30} {delta_attestations}")
        print(f"{'Liveness check':<30} {'PASS' if liveness_pass else 'FAIL'}")

        if not is_staked:
            return

        print_header("Service")
        print(f"{'ID':<30} {service_id}")
        print(f"Loading service {config.get('hash', 'unknown')}")

        print_header("Agent")
        print(f"{'Address':<30} {agent_addresses[0] if agent_addresses else 'N/A'}")
        print(f"{'Balance':<30} {wei_to_eth(agent_eth)} ETH")

        print_header("Safe")
        print(f"{'Address (Mode)':<30} {multisig}")
        print(f"{'ETH Balance':<30} {wei_to_eth(multisig_eth)} ETH")

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
