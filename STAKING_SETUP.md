# Staking Contract Setup and Rewards Claiming

## Overview

This guide covers how to configure the staking contract parameters on a local testnet and claim rewards.

## Staking Contract Details

- **Proxy Contract**: `0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb`
- **Implementation Contract**: `0xEB5638eefE289691EcE01943f768EDBF96258a80`
- **Service ID**: `167`
- **Multisig Address**: `0x55196464De636b8ddA93Bdf78831b3aA0e429d60`
- **Owner Address**: `0x39D9195fF4691ed1C9254EfA367a1c65D46C227E`

## Problem

The staking contract was deployed with:
- `rewardsPerSecond` = **0** (no rewards being distributed)
- `minStakingDuration` = **0**

Even with 4000 OLAS in the rewards pool, services could not earn rewards.

## Solution: Configure Staking Parameters

On a local Anvil testnet, you can modify contract storage directly:

### 1. Set Rewards Per Second

```bash
export BASE_LEDGER_RPC=http://localhost:8545

# Set to 0.01 OLAS per second = 864 OLAS per day
REWARD_VALUE="0x000000000000000000000000000000000000000000000000002386f26fc10000"

cast rpc anvil_setStorageAt \
  0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb \
  0x2 \
  $REWARD_VALUE \
  --rpc-url $BASE_LEDGER_RPC
```

### 2. Verify Configuration

```bash
# Check rewardsPerSecond (should return 10000000000000000 = 0.01 OLAS/sec)
cast call 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb \
  "rewardsPerSecond()(uint256)" \
  --rpc-url $BASE_LEDGER_RPC
```

## Earning Rewards

### 1. Create Attestations

Your service must create voting attestations to maintain liveness:

```bash
# Run test script to create attestations
python3 test_staking_rewards.py
```

**Liveness Requirement**:
- Threshold: `11574074074074` (~1 attestation per 24 hours)
- Formula: `(new_attestations * 10^18) / time_elapsed >= threshold`

### 2. Call Checkpoint

Checkpoint triggers reward calculation based on activity:

```bash
cast send 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb \
  "checkpoint()" \
  --from 0x55196464De636b8ddA93Bdf78831b3aA0e429d60 \
  --unlocked \
  --rpc-url $BASE_LEDGER_RPC
```

### 3. Check Accrued Rewards

```bash
# Use the staking report
./staking_report.py

# Or check directly
cast call 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb \
  "calculateStakingReward(uint256)(uint256)" \
  167 \
  --rpc-url $BASE_LEDGER_RPC
```

## Claiming Rewards

**Important**: Rewards must be claimed by the **owner address**, not the multisig.

### Direct Claim Command

```bash
export BASE_LEDGER_RPC=http://localhost:8545

# Claim rewards (must be called by owner)
cast send 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb \
  "claim(uint256)" \
  167 \
  --from 0x39D9195fF4691ed1C9254EfA367a1c65D46C227E \
  --unlocked \
  --rpc-url $BASE_LEDGER_RPC
```

### Verify Claim

```bash
# Check multisig OLAS balance
cast call 0x54330d28ca3357F294334BDC454a032e7f353416 \
  "balanceOf(address)(uint256)" \
  0x55196464De636b8ddA93Bdf78831b3aA0e429d60 \
  --rpc-url $BASE_LEDGER_RPC
```

## Complete Workflow

```bash
# 1. Set rewards rate (one-time setup)
cast rpc anvil_setStorageAt 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb 0x2 \
  0x000000000000000000000000000000000000000000000000002386f26fc10000 \
  --rpc-url $BASE_LEDGER_RPC

# 2. Create attestations (service activity)
python3 test_staking_rewards.py

# 3. Call checkpoint to calculate rewards
cast send 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb "checkpoint()" \
  --from 0x55196464De636b8ddA93Bdf78831b3aA0e429d60 \
  --unlocked \
  --rpc-url $BASE_LEDGER_RPC

# 4. Check rewards
./staking_report.py

# 5. Claim rewards (from owner address)
cast send 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb "claim(uint256)" 167 \
  --from 0x39D9195fF4691ed1C9254EfA367a1c65D46C227E \
  --unlocked \
  --rpc-url $BASE_LEDGER_RPC

# 6. Verify balance
cast call 0x54330d28ca3357F294334BDC454a032e7f353416 \
  "balanceOf(address)(uint256)" \
  0x55196464De636b8ddA93Bdf78831b3aA0e429d60 \
  --rpc-url $BASE_LEDGER_RPC
```

## Monitoring

Use the staking report tool to monitor status:

```bash
./staking_report.py
```

The report shows:
- Staking status (Staked/Unstaked/Evicted)
- Attestation activity and liveness ratio
- Accrued rewards
- Balances

## Key Takeaways

1. **Proxy Pattern**: Staking contract uses a proxy, actual logic is in implementation contract
2. **Rewards Calculation**: Rewards accrue based on `rewardsPerSecond × time_elapsed` when liveness is met
3. **Checkpoint Required**: Must call `checkpoint()` to trigger reward calculation
4. **Owner Claims**: Only the owner address can call `claim()`, but rewards go to the multisig
5. **Liveness Matters**: Service must maintain attestation activity to earn rewards

## Storage Slot Reference

- **Slot 2**: `rewardsPerSecond` (uint256)
- **Slot 4**: `minStakingDuration` (uint256)

## Production Notes

On production networks:
- You cannot modify storage slots
- Staking contracts should be properly initialized with correct parameters
- Consider using governance or admin functions to update parameters
- The contract owner has privileged access for claiming
