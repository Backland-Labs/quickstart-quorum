# Staking Testing Guide

Complete guide for testing the Quorum voting agent's staking functionality on a local Anvil fork of Base mainnet.

## Prerequisites

Complete the Quick Setup steps in [README.md](README.md) first. This guide assumes:
- Anvil fork is running
- Environment variables are set  
- Service is deployed and staked
- Two Docker containers are running
- Agent UI is accessible at `http://localhost:8716`

## Wallet Funding

The `fund_wallets.sh` script automates funding all necessary wallets on your Anvil fork.

### What It Does

Automatically funds:
- **Master EOA**: 1 ETH (for gas fees)
- **Master Safe**: 1 ETH + 200 OLAS (for staking and operations)
- **Agent EOA**: 1 ETH (if already created)
- **Staking Contract**: 1000 OLAS (rewards pool)

Then saves the Anvil state to `anvil_state.json` for later restoration.

### Usage

**After deploying service** (wallets must exist in `.operate/`):

```bash
./fund_wallets.sh
```

**Or specify custom RPC:**

```bash
./fund_wallets.sh http://localhost:8545
```

**Expected output:**
```
📋 Extracting initial wallet addresses...
Master EOA: 0x...
Master Safe: 0x...

💰 Funding initial wallets on Anvil...
✓ Master EOA funded with ETH
✓ Master Safe funded with ETH
✓ Master Safe funded with OLAS
✓ Agent EOA funded with ETH

💎 Funding staking contract...
✓ Staking contract funded with OLAS

📊 Balances:
Master EOA ETH: 1.0 ETH
Master Safe ETH: 1.0 ETH
Master Safe OLAS: 200.0 OLAS
Agent EOA ETH: 1.0 ETH
Staking Contract Available Rewards: 1000.0 OLAS

💾 Anvil state saved to anvil_state.json
```

### When to Use

- **After first deployment**: Run once wallets are created
- **When starting fresh**: To fund a new set of wallets
- **After Anvil restart**: If state wasn't saved

### Restore Saved State

Instead of re-funding, you can restart Anvil with saved state:

```bash
anvil --load-state anvil_state.json --auto-impersonate
```

This preserves all funded balances and contract state.

## What You're Testing

The agent must successfully:
1. Stake in the OLAS staking contract
2. Make attestations at a rate of ~1 per 24 hours (liveness check)
3. Accrue staking rewards based on activity
4. Claim accumulated rewards after 72+ hours

## Testing Workflow

### Check Staking Status

Run this anytime to see a comprehensive snapshot of your agent's staking performance:

```bash
./staking_report.py
```

**What you'll see:**
- **Staking State:** Staked, Unstaked, or Evicted
- **Attestation Activity:** How many attestations have been made
- **Liveness Status:** ✅ PASS or ❌ FAIL (must average ~1 attestation per 24 hours)
- **Accrued Rewards:** How much OLAS you can claim
- **Balances:** ETH and OLAS held by the multisig

**When to run:** After triggering attestations, after advancing time, or when debugging.

### Run Checkpoint Tests

Track staking performance across multiple time periods to simulate 24-hour checkpoint intervals.

**Typical test flow:**

```bash
# 1. Record baseline state (hour 0)
./test_staking_checkpoints.py --checkpoint
```
**Expected:** Checkpoint 0 showing initial attestations and zero rewards.

```bash
# 2. Trigger 2-3 attestations via http://localhost:8716

# 3. Advance time by 25 hours and record checkpoint
./test_staking_checkpoints.py --advance 25
```
**Expected:** Checkpoint 1 showing new attestations and liveness status.

```bash
# 4. Trigger more attestations, then advance another 25 hours
./test_staking_checkpoints.py --advance 25
```
**Expected:** Checkpoint 2 showing accumulated attestations and accrued rewards.

```bash
# 5. View complete test report
./test_staking_checkpoints.py --report
```
**Expected:** Table showing all checkpoints with progression of attestations, rewards, and liveness.

**Utility commands:**
```bash
# Reset all checkpoint data to start over
./test_staking_checkpoints.py --reset
```

### Claim Staking Rewards

Once `staking_report.py` shows accrued rewards > 0:

```bash
./claim_staking_rewards.sh configs/config_quorum.json
```

**What happens:** OLAS tokens are transferred from staking contract to your service's multisig wallet.

**Verify:** Run `./staking_report.py` to confirm "Multisig OLAS" balance increased.

## Time Manipulation

Fast-forward blockchain time using Anvil RPC:

```bash
# Advance 24 hours (one checkpoint interval)
cast rpc evm_increaseTime 86400 && cast rpc evm_mine

# Advance 72 hours (minimum unstaking period)
cast rpc evm_increaseTime 259200 && cast rpc evm_mine
```

**Note:** The `test_staking_checkpoints.py --advance` command does this automatically.

## Troubleshooting

### Service Not Staked
**Symptom:** `staking_report.py` shows "Unstaked" state.

**Solution:** Re-run deployment: `./run_service.sh configs/config_quorum.json --attended=false`

### Liveness Failing
**Symptom:** `staking_report.py` shows "❌ FAIL" for liveness.

**Cause:** Insufficient attestations for time elapsed (need ~1 per 24 hours).

**Solution:** Trigger more attestations via `http://localhost:8716`.

### No Rewards Accruing
**Symptom:** Accrued rewards remain at 0.00 OLAS.

**Causes:**
- Liveness checks failing
- Insufficient time elapsed (need 24+ hours)
- Staking contract out of rewards (check "Available in pool")

### Service Evicted
**Symptom:** State shows "Evicted".

**Cause:** Failed liveness for 2+ consecutive checkpoints.

**Solution:**
1. `./stop_service.sh configs/config_quorum.json`
2. `cast rpc evm_increaseTime 259200 && cast rpc evm_mine`
3. `./run_service.sh configs/config_quorum.json --attended=false`

### View Logs
```bash
docker logs $(docker ps --filter "name=quorum" --format "{{.Names}}" | grep "_abci" | head -n 1) --follow
```

### Stop Services
```bash
./stop_service.sh configs/config_quorum.json
```

## Key Staking Parameters

- **Minimum staking duration**: 72 hours (259,200 seconds)
- **Liveness threshold**: ~1 attestation per 24 hours
- **Eviction**: After 2 consecutive checkpoints failing liveness
- **Checkpoint interval**: Every 24 hours

## Contract Addresses

- **Staking Contract**: `0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb`
- **Attestation Tracker**: `0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC`
- **OLAS Token**: `0x54330d28ca3357F294334BDC454a032e7f353416`
- **OLAS Whale (for funding)**: `0xC8F7030a4e25585624e2Fc792255a547255Cd77c`

## Testing Checklist

- [ ] Anvil fork running (`anvil --fork-url https://mainnet.base.org --auto-impersonate`)
- [ ] Environment variables set (verify: `echo $BASE_LEDGER_RPC`)
- [ ] Service deployed and staked (`./run_service.sh configs/config_quorum.json --attended=false`)
- [ ] Both containers running (`docker ps` shows 2 containers)
- [ ] Agent UI accessible (`http://localhost:8716`)
- [ ] Initial checkpoint recorded (`./test_staking_checkpoints.py --checkpoint`)
- [ ] Attestations triggered (via UI, verify with `./staking_report.py`)
- [ ] Liveness passing (`./staking_report.py` shows "✅ PASS")
- [ ] Time advanced (`./test_staking_checkpoints.py --advance 25`)
- [ ] Rewards accruing (`./staking_report.py` shows OLAS > 0)
- [ ] Rewards claimed (`./claim_staking_rewards.sh configs/config_quorum.json`)
- [ ] Balance increased (verify with `./staking_report.py`)

## Example Output

See successful staking report output:

![Example Staking Report](Screenshot%202025-10-07%20at%2016.17.55.png)
