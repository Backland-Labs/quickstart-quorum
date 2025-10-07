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

- You may need to run this a few times to fully fund the wallets/contracts

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

## Service Configuration

The `example_service.yaml` file provides a reference configuration for the Quorum agent service.

### Key Configuration Sections

**Port Mapping:**
- Exposes port `8716` for the agent UI and API endpoints

**Network Configuration:**
- `BASE_LEDGER_RPC`: RPC endpoint for Base network (defaults to `http://host.docker.internal:8545` for local Anvil)
- `CHAIN_ID`: Base mainnet chain ID (`8453`)

**Contract Addresses:**
- `EAS_CONTRACT_ADDRESS`: Ethereum Attestation Service contract
- `ATTESTATION_TRACKER_ADDRESS`: Tracks voting attestations for staking
- `BASE_SAFE_ADDRESS`: Safe multisig address for the service

**Agent Behavior:**
- `MONITORED_DAOS`: Which DAOs to monitor (default: `quorum-ai.eth`)
- `AGENT_CONFIDENCE_THRESHOLD`: Minimum confidence to vote (`0.7`)
- `MAX_PROPOSALS_PER_RUN`: Proposals to process per execution (`3`)
- `VOTING_STRATEGY`: How the agent votes (`balanced`)

**Environment Variables:**
All values use the format `${VAR_NAME:type:default}` and can be overridden via environment variables.

### When to Modify

You typically don't need to modify this file for testing. However, you might customize:
- `PORT` if 8716 conflicts with another service
- `MONITORED_DAOS` to watch different DAOs
- `DEBUG` to enable verbose logging
- `DRY_RUN_DEFAULT` to test without making on-chain transactions

The deployed service will use this configuration merged with values from `configs/config_quorum.json`.

## Testing Against Testnet or Mainnet

While this guide focuses on local Anvil testing, you can also test against live networks.

### Configuration Changes

**1. Set Environment Variables for Live Network:**

For Base Mainnet:
```bash
export OPERATE_PASSWORD="your-secure-password"
export BASE_LEDGER_RPC=https://mainnet.base.org  # Or your RPC provider URL
export STAKING_CONTRACT_ADDRESS=0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb
export STAKING_PROGRAM='custom_staking'
```

For Base Sepolia Testnet:
```bash
export OPERATE_PASSWORD="your-secure-password"
export BASE_LEDGER_RPC=https://sepolia.base.org
export STAKING_CONTRACT_ADDRESS=<testnet-staking-contract>
export STAKING_PROGRAM='custom_staking'
```

**2. Deploy Service:**
```bash
./run_service.sh configs/config_quorum.json
```

The service will prompt you to fund wallets with real ETH and OLAS tokens.


### Testing Workflow on Live Networks

1. **Deploy and stake** service (`./run_service.sh configs/config_quorum.json`)
2. **Fund wallets** when prompted (use faucets for testnet, purchase for mainnet)
3. **Trigger attestations** via `curl -X POST http://localhost:8716/agent-run`
4. **Monitor status** with `./staking_report.py`
5. **Wait 24+ hours** for first checkpoint (real time, no fast-forward)
6. **Continue activity** to maintain liveness
7. **Wait 72+ hours** minimum staking period
8. **Claim rewards** with `./claim_staking_rewards.sh configs/config_quorum.json`

### Recommended Testing Path

1. **Local Anvil** → Quick validation, iterate on issues
2. **Testnet** → Verify with real network conditions, no cost
3. **Mainnet** → Production deployment with real value

## Agent API Endpoints

Once containers are running, the agent exposes several HTTP endpoints on `http://localhost:8716`:

### Trigger Vote Decision

**POST** `http://localhost:8716/agent-run`

Manually triggers the agent to check for proposals and make voting decisions. This creates attestations that count toward staking liveness.

**Example:**
```bash
curl -X POST http://localhost:8716/agent-run
```

### View API Documentation

**GET** `http://localhost:8716/docs`

Opens interactive API documentation showing all available endpoints with descriptions and request/response schemas.

**Access in browser:** `http://localhost:8716/docs`

### Other Useful Endpoints

- **GET** `/healthcheck` - Check if agent is running
- **GET** `/` - Basic service information

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
# 2. Trigger 2-3 attestations
curl -X POST http://localhost:8716/agent-run
# Wait a few seconds between calls
curl -X POST http://localhost:8716/agent-run

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

**Solution:** Trigger more attestations:
```bash
curl -X POST http://localhost:8716/agent-run
```

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
- [ ] Agent UI accessible (`http://localhost:8716/docs`)
- [ ] Initial checkpoint recorded (`./test_staking_checkpoints.py --checkpoint`)
- [ ] Attestations triggered (`curl -X POST http://localhost:8716/agent-run`, verify with `./staking_report.py`)
- [ ] Liveness passing (`./staking_report.py` shows "✅ PASS")
- [ ] Time advanced (`./test_staking_checkpoints.py --advance 25`)
- [ ] Rewards accruing (`./staking_report.py` shows OLAS > 0)
- [ ] Rewards claimed (`./claim_staking_rewards.sh configs/config_quorum.json`)
- [ ] Balance increased (verify with `./staking_report.py`)

## Example Output

See successful staking report output:

![Example Staking Report](Screenshot%202025-10-07%20at%2016.17.55.png)
