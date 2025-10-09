#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=6.0.0",
# ]
# ///
"""Deep dive into attestation data structure."""

from web3 import Web3

RPC_URL = "https://cosmopolitan-cosmological-resonance.base-mainnet.quiknode.pro/b4c827323f0a8012212429b0bd4a72a060c5373c/"
ATTESTATION_TRACKER = "0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
MULTISIG = "0x7dF2A42C5a9006B16E6c7e6Ac750cdf336489c80"

# Extended ABI
ATTESTATION_TRACKER_ABI = [
    {
        "type": "function",
        "name": "getNumAttestations",
        "inputs": [{"name": "multisig", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "type": "function",
        "name": "getVotingStats",
        "inputs": [{"name": "multisig", "type": "address"}],
        "outputs": [{"name": "votingStats", "type": "uint256[]"}],
        "stateMutability": "view"
    }
]

def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    tracker = w3.eth.contract(address=ATTESTATION_TRACKER, abi=ATTESTATION_TRACKER_ABI)
    
    print("=" * 70)
    print("ATTESTATION DATA ANALYSIS")
    print("=" * 70)
    
    # Get counts
    num_attestations = tracker.functions.getNumAttestations(MULTISIG).call()
    voting_stats = tracker.functions.getVotingStats(MULTISIG).call()
    
    print(f"\nMultisig: {MULTISIG}")
    print(f"\ngetNumAttestations() returns: {num_attestations}")
    print(f"  → This is the number of attestation transactions")
    
    print(f"\ngetVotingStats() returns: {voting_stats}")
    print(f"  → Array of vote counts: [For, Against, Abstain, ...]")
    
    total_votes = sum(voting_stats[:3]) if len(voting_stats) >= 3 else sum(voting_stats)
    
    print(f"\nTotal individual votes: {total_votes}")
    print(f"  - For:     {voting_stats[0] if len(voting_stats) > 0 else 0}")
    print(f"  - Against: {voting_stats[1] if len(voting_stats) > 1 else 0}")
    print(f"  - Abstain: {voting_stats[2] if len(voting_stats) > 2 else 0}")
    
    print("\n" + "-" * 70)
    print("INTERPRETATION:")
    print("-" * 70)
    
    if num_attestations == 1 and total_votes == 2:
        print("✓ One attestation contains TWO separate votes")
        print("  (likely votes on 2 different proposals)")
    elif num_attestations == total_votes:
        print("✓ Each attestation contains ONE vote")
    else:
        print(f"? Unusual pattern: {num_attestations} attestations, {total_votes} votes")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
