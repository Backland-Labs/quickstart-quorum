#!/usr/bin/env python3
"""Test staking rewards by creating real attestations and checking if the service passes liveness."""

import os
import json
import time
from pathlib import Path
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_structured_data
from eth_abi.abi import encode

# Configuration
RPC_URL = os.getenv("BASE_LEDGER_RPC", "http://localhost:8545")
ATTESTATION_TRACKER = "0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
MULTISIG = "0x7E5A4eA25001a46133e423BAC3512EaB798fcB3B"
EAS_CONTRACT = "0x4200000000000000000000000000000000000021"  # Base EAS
STAKING_CONTRACT = "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"
SERVICE_ID = 167
SCHEMA_UID = "0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4"
NO_EXPIRATION = 0

# Load private key
keys_file = Path(".operate/keys.json")
if keys_file.exists():
    with open(keys_file) as f:
        keys_data = json.load(f)
        first_addr = list(keys_data.keys())[0]
        PRIVATE_KEY = keys_data[first_addr]
        print(f"Loaded key for {first_addr}")
else:
    PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    print("Using Anvil default key")

def encode_attestation_data(agent_address, space_id, proposal_id, vote_choice, snapshot_sig, run_id, confidence):
    """Encode attestation data according to the schema."""
    timestamp = int(time.time())
    encoded_data = encode(
        ['address', 'string', 'string', 'uint8', 'string', 'uint256', 'string', 'uint8'],
        [agent_address, space_id, proposal_id, vote_choice, snapshot_sig, timestamp, run_id, confidence]
    )
    return encoded_data

def create_eip712_signature(w3, account, schema_uid, recipient, encoded_data, nonce, deadline):
    """Create EIP-712 signature for EAS delegated attestation."""
    
    types = {
        'EIP712Domain': [
            {'name': 'name', 'type': 'string'},
            {'name': 'version', 'type': 'string'},
            {'name': 'chainId', 'type': 'uint256'},
            {'name': 'verifyingContract', 'type': 'address'},
        ],
        'Attest': [
            {'name': 'schema', 'type': 'bytes32'},
            {'name': 'recipient', 'type': 'address'},
            {'name': 'expirationTime', 'type': 'uint64'},
            {'name': 'revocable', 'type': 'bool'},
            {'name': 'refUID', 'type': 'bytes32'},
            {'name': 'data', 'type': 'bytes'},
            {'name': 'value', 'type': 'uint256'},
            {'name': 'nonce', 'type': 'uint256'},
            {'name': 'deadline', 'type': 'uint64'},
        ]
    }
    
    domain = {
        'name': 'EAS',
        'version': '1.0.1',
        'chainId': w3.eth.chain_id,
        'verifyingContract': Web3.to_checksum_address(EAS_CONTRACT),
    }
    
    message = {
        'schema': bytes.fromhex(schema_uid[2:]),
        'recipient': recipient,
        'expirationTime': NO_EXPIRATION,
        'revocable': True,
        'refUID': bytes(32),
        'data': encoded_data,
        'value': 0,
        'nonce': nonce,
        'deadline': deadline,
    }
    
    typed_data = {
        'domain': domain,
        'primaryType': 'Attest', 
        'types': types,
        'message': message,
    }
    
    encoded = encode_structured_data(typed_data)
    signature = account.sign_message(encoded)
    return signature.signature

def create_attestation(w3, account, tracker, attestation_num):
    """Create a single attestation."""
    
    # Encode attestation data
    encoded_data = encode_attestation_data(
        agent_address=MULTISIG,
        space_id=f"test-space-{attestation_num}",
        proposal_id=f"0xprop{attestation_num:04d}",
        vote_choice=(attestation_num % 3),
        snapshot_sig=f"sig-{attestation_num}",
        run_id=f"run-{attestation_num}",
        confidence=85
    )
    
    recipient = "0x0000000000000000000000000000000000000000"
    nonce = w3.eth.get_transaction_count(account.address)
    deadline = int(time.time()) + 3600
    
    # Create EIP-712 signature
    signature = create_eip712_signature(
        w3=w3,
        account=account,
        schema_uid=SCHEMA_UID,
        recipient=recipient,
        encoded_data=encoded_data,
        nonce=nonce,
        deadline=deadline
    )
    
    # Extract v, r, s
    r = signature[:32]
    s = signature[32:64]
    v = signature[64]
    
    # Call attestByDelegation with 12 separate parameters
    schema_bytes = bytes.fromhex(SCHEMA_UID[2:])
    ref_uid = bytes(32)
    
    # Build transaction data - call FROM multisig (impersonated)
    tx_data = tracker.encodeABI(
        fn_name='attestByDelegation',
        args=[
            schema_bytes,      # schema (bytes32)
            recipient,         # recipient (address)
            NO_EXPIRATION,     # expirationTime (uint64)
            True,              # revocable (bool)
            ref_uid,           # refUID (bytes32)
            encoded_data,      # data (bytes)
            0,                 # value (uint256)
            v,                 # v (uint8)
            r,                 # r (bytes32)
            s,                 # s (bytes32)
            account.address,   # attester (signer's address)
            deadline           # deadline (uint64)
        ]
    )
    
    # Test with eth_call first to get revert reason
    try:
        w3.eth.call({
            'from': MULTISIG,
            'to': ATTESTATION_TRACKER,
            'data': tx_data
        })
    except Exception as e:
        print(f"Call would revert: {e}")
        return False
    
    # Send transaction FROM multisig (impersonated by Anvil)
    tx_hash = w3.provider.make_request('eth_sendTransaction', [{
        'from': MULTISIG,  # Call from multisig, not from signer
        'to': ATTESTATION_TRACKER,
        'data': tx_data,  # Already a hex string
        'gas': hex(1000000)
    }])
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash['result'], timeout=30)
    
    return receipt['status'] == 1

def main():
    print("=== Staking Rewards Test ===\n")
    
    # Connect to network
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    print(f"Connected: {w3.is_connected()}, Chain ID: {w3.eth.chain_id}\n")
    
    # Load ABIs
    with open('../quorum-ai/contracts/abi/AttestationTracker.json') as f:
        tracker_abi = json.load(f)
    
    staking_abi = json.loads('''[
        {"inputs":[{"internalType":"uint256","name":"serviceId","type":"uint256"}],"name":"getStakingState","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"uint256","name":"serviceId","type":"uint256"}],"name":"getServiceInfo","outputs":[{"components":[{"internalType":"address","name":"multisig","type":"address"},{"internalType":"address","name":"owner","type":"address"},{"internalType":"uint256[]","name":"nonces","type":"uint256[]"},{"internalType":"uint256","name":"tsStart","type":"uint256"}],"internalType":"struct StakingBase.ServiceInfo","name":"","type":"tuple"}],"stateMutability":"view","type":"function"}
    ]''')
    
    tracker = w3.eth.contract(address=ATTESTATION_TRACKER, abi=tracker_abi)
    staking = w3.eth.contract(address=STAKING_CONTRACT, abi=staking_abi)
    account = Account.from_key(PRIVATE_KEY)
    
    print(f"Using account: {account.address}")
    print(f"Multisig: {MULTISIG}\n")
    
    # Check initial state
    print("Initial State:")
    initial_count = tracker.functions.getNumAttestations(MULTISIG).call()
    print(f"  Attestations: {initial_count}")
    
    service_info = staking.functions.getServiceInfo(SERVICE_ID).call()
    baseline = service_info[2][1]  # nonces[1]
    print(f"  Baseline (at stake): {baseline}")
    print(f"  Delta: {initial_count - baseline}\n")
    
    # Create 20 attestations
    print("Creating 20 attestations...\n")
    
    created = 0
    for i in range(20):
        try:
            success = create_attestation(w3, account, tracker, i)
            if success:
                created += 1
                if (i + 1) % 5 == 0:
                    current = tracker.functions.getNumAttestations(MULTISIG).call()
                    print(f"  Created {created} attestations, current count: {current}")
            else:
                print(f"❌ Attestation {i+1} FAILED (transaction reverted)")
                break
        except Exception as e:
            print(f"❌ Attestation {i+1} ERROR: {e}")
            break
    
    # Check final state
    print("\nFinal State:")
    final_count = tracker.functions.getNumAttestations(MULTISIG).call()
    print(f"  Attestations: {final_count}")
    print(f"  Baseline (at stake): {baseline}")
    print(f"  Delta: {final_count - baseline}\n")
    
    # Check if service would pass liveness
    delta = final_count - baseline
    service_info = staking.functions.getServiceInfo(SERVICE_ID).call()
    stake_time = service_info[3]
    current_time = w3.eth.get_block('latest')['timestamp']
    time_elapsed = current_time - stake_time
    
    # Liveness threshold: 1 attestation per 24 hours
    threshold = 11574074074074
    ratio = (delta * 10**18) // time_elapsed if time_elapsed > 0 else 0
    
    print(f"Liveness Check:")
    print(f"  Time elapsed: {time_elapsed}s ({time_elapsed/3600:.1f} hours)")
    print(f"  Ratio: {ratio:,}")
    print(f"  Threshold: {threshold:,}")
    print(f"  Would pass: {ratio >= threshold}\n")
    
    if ratio >= threshold:
        print("✅ Service should pass liveness check!")
        print("   You can now run: ./claim_staking_rewards.sh configs/config_quorum.json")
    else:
        print("❌ Service still fails liveness check")
        needed = ((threshold * time_elapsed) // 10**18) - delta + 1
        print(f"   Need {needed} more attestations")

if __name__ == "__main__":
    main()
