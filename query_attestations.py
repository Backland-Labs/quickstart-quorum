#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=6.0.0",
# ]
# ///
"""Query the Attestation Tracker contract directly for voting data."""

from web3 import Web3

# Configuration
RPC_URL = "https://cosmopolitan-cosmological-resonance.base-mainnet.quiknode.pro/b4c827323f0a8012212429b0bd4a72a060c5373c/"
ATTESTATION_TRACKER = "0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
MULTISIG = "0x7dF2A42C5a9006B16E6c7e6Ac750cdf336489c80"

# ABI for the attestation tracker
ATTESTATION_TRACKER_ABI = [
    {
        "type": "function",
        "name": "getNumAttestations",
        "inputs": [{"name": "multisig", "type": "address", "internalType": "address"}],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view"
    },
    {
        "type": "function",
        "name": "getVotingStats",
        "inputs": [{"name": "multisig", "type": "address", "internalType": "address"}],
        "outputs": [{"name": "votingStats", "type": "uint256[]", "internalType": "uint256[]"}],
        "stateMutability": "view"
    },
    {
        "type": "function",
        "name": "mapMultisigAttestations",
        "inputs": [{"name": "", "type": "address", "internalType": "address"}],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view"
    }
]

def main():
    # Connect to Base
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        print(f"Error: Could not connect to RPC")
        return
    
    print(f"Connected to chain ID: {w3.eth.chain_id}")
    print(f"Attestation Tracker: {ATTESTATION_TRACKER}")
    print(f"Multisig: {MULTISIG}")
    print()
    
    # Initialize contract
    tracker = w3.eth.contract(address=ATTESTATION_TRACKER, abi=ATTESTATION_TRACKER_ABI)
    
    # Query attestation count
    print("=" * 60)
    print("ATTESTATION DATA")
    print("=" * 60)
    
    try:
        num_attestations = tracker.functions.getNumAttestations(MULTISIG).call()
        print(f"Total Attestations: {num_attestations}")
    except Exception as e:
        print(f"Error getting attestation count: {e}")
    
    # Query voting stats
    print("\nVOTING BREAKDOWN")
    print("-" * 60)
    
    try:
        voting_stats = tracker.functions.getVotingStats(MULTISIG).call()
        if voting_stats:
            vote_labels = ["For", "Against", "Abstain"]
            for i, count in enumerate(voting_stats):
                if i < len(vote_labels):
                    print(f"{vote_labels[i]:>10}: {count}")
                else:
                    print(f"Choice {i:>3}: {count}")
        else:
            print("No voting stats available")
    except Exception as e:
        print(f"Error getting voting stats: {e}")
    
    # Query direct mapping
    print("\nDIRECT MAPPING QUERY")
    print("-" * 60)
    
    try:
        map_value = tracker.functions.mapMultisigAttestations(MULTISIG).call()
        print(f"mapMultisigAttestations[{MULTISIG}]: {map_value}")
    except Exception as e:
        print(f"Error querying mapping: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
