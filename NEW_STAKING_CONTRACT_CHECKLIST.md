# New Staking Contract Setup Checklist

## Critical Parameters to Set

When deploying or initializing a new staking contract, ensure these parameters are properly configured:

### 1. Rewards Configuration

#### `rewardsPerSecond` (uint256)
- **Purpose**: Rate at which OLAS rewards are distributed per second
- **Required**: YES - must be > 0 for rewards to accrue
- **Example**: `10000000000000000` (0.01 OLAS/sec = 864 OLAS/day)
- **Storage Slot**: `0x2` (on this implementation)

```bash
# Calculate rewards per second
# For 100 OLAS per day: 100 * 10^18 / 86400 = 1157407407407407
# For 864 OLAS per day: 864 * 10^18 / 86400 = 10000000000000000

# Set via constructor or admin function
```

#### `availableRewards` (uint256)
- **Purpose**: Total OLAS tokens available for distribution
- **Required**: YES - contract must have OLAS balance
- **How to Fund**:
  ```bash
  # Approve OLAS for staking contract
  cast send <OLAS_TOKEN> "approve(address,uint256)" <STAKING_CONTRACT> <AMOUNT> \
    --from <FUNDER> --unlocked --rpc-url $RPC

  # Deposit OLAS to staking contract
  cast send <STAKING_CONTRACT> "deposit(uint256)" <AMOUNT> \
    --from <FUNDER> --unlocked --rpc-url $RPC
  ```

### 2. Staking Duration

#### `minStakingDuration` (uint256)
- **Purpose**: Minimum time (seconds) a service must be staked before unstaking
- **Typical Value**: `259200` (3 days)
- **Can be 0**: For testing
- **Storage Slot**: `0x4` (on this implementation)

```bash
# 3 days = 259200 seconds
# 1 day = 86400 seconds
```

### 3. Service Limits

#### `maxNumServices` (uint256)
- **Purpose**: Maximum number of services that can stake simultaneously
- **Required**: YES
- **Example**: `2`, `10`, `100` depending on program size

#### `numAgentInstances` (uint256)
- **Purpose**: Required number of agent instances per service
- **Typical Value**: `1` for single-agent services
- **Required**: YES

### 4. Activity Tracking (Attestation-Based)

#### `livenessRatio` (uint256) - If Available
- **Purpose**: Minimum activity rate to maintain staking eligibility
- **Value**: `11574074074074` (~1 attestation per 24 hours)
- **Formula**: `(attestations * 10^18) / seconds_elapsed >= livenessRatio`
- **Note**: May be hardcoded in contract logic

**If using custom activity checker**:
- Deploy `AttestationTracker` contract
- Configure staking contract to use it
- Set appropriate liveness thresholds

### 5. Contract References

#### Activity Checker Contract
- **For Attestation-Based**: Deploy `AttestationTracker`
- **Address**: Must be set in staking contract constructor/initializer
- **Purpose**: Tracks voting attestations via EAS (Ethereum Attestation Service)

#### Token Addresses
- **OLAS Token**: `0x54330d28ca3357F294334BDC454a032e7f353416` (Base)
- **EAS Contract**: `0x4200000000000000000000000000000000000021` (Base)

### 6. Access Control

#### Owner/Admin Address
- **Required**: YES
- **Permissions**:
  - Claim rewards on behalf of services
  - Potentially update parameters (depends on contract)
- **Important**: Only owner can call `claim(uint256 serviceId)`

## Deployment Checklist

- [ ] Deploy staking implementation contract
- [ ] Deploy proxy pointing to implementation (if using proxy pattern)
- [ ] Initialize with parameters:
  - [ ] `rewardsPerSecond` > 0
  - [ ] `minStakingDuration` (typically 3 days or 0 for testing)
  - [ ] `maxNumServices` (program capacity)
  - [ ] `numAgentInstances` (typically 1)
  - [ ] Activity checker contract address
- [ ] Fund the contract with OLAS:
  - [ ] Approve OLAS spending
  - [ ] Call `deposit()` function
- [ ] Verify parameters:
  ```bash
  cast call <STAKING_CONTRACT> "rewardsPerSecond()(uint256)" --rpc-url $RPC
  cast call <STAKING_CONTRACT> "availableRewards()(uint256)" --rpc-url $RPC
  cast call <STAKING_CONTRACT> "minStakingDuration()(uint256)" --rpc-url $RPC
  cast call <STAKING_CONTRACT> "maxNumServices()(uint256)" --rpc-url $RPC
  ```
- [ ] Update service config with new staking contract address
- [ ] Test stake/unstake flow
- [ ] Test checkpoint and rewards accrual
- [ ] Test claim functionality

## Configuration in Service Config

Update `configs/config_quorum.json` or service config:

```json
{
  "chain_configs": {
    "base": {
      "chain_data": {
        "user_params": {
          "staking_program_id": "<NEW_STAKING_CONTRACT_ADDRESS>",
          "use_staking": true,
          "cost_of_bond": 10000000000000000000
        }
      }
    }
  }
}
```

Update environment variables:
```bash
export STAKING_CONTRACT_ADDRESS=<NEW_STAKING_CONTRACT_ADDRESS>
```

## Testing New Contract

### 1. Stake Service
```bash
./stake_service.sh configs/config_quorum.json
```

### 2. Create Activity (Attestations)
```bash
python3 test_staking_rewards.py
```

### 3. Call Checkpoint
```bash
cast send <STAKING_CONTRACT> "checkpoint()" \
  --from <MULTISIG> --unlocked --rpc-url $RPC
```

### 4. Check Rewards
```bash
./staking_report.py
```

### 5. Claim Rewards
```bash
cast send <STAKING_CONTRACT> "claim(uint256)" <SERVICE_ID> \
  --from <OWNER> --unlocked --rpc-url $RPC
```

## Common Issues

### No Rewards Accruing
- ✅ Check `rewardsPerSecond > 0`
- ✅ Check `availableRewards > 0`
- ✅ Verify service is meeting liveness requirements
- ✅ Ensure checkpoint has been called

### Cannot Claim Rewards
- ✅ Must call from owner address, not multisig
- ✅ Check service is staked (state = 1)
- ✅ Ensure rewards have accrued (call `calculateStakingReward()`)

### Service Evicted
- ✅ Not meeting liveness ratio (insufficient attestations)
- ✅ Call checkpoint to reset and try to regain eligibility
- ✅ Increase attestation frequency

## Quick Reference Values

| Parameter | Test Value | Production Value |
|-----------|-----------|------------------|
| `rewardsPerSecond` | `10000000000000000` (0.01 OLAS/sec) | Depends on program budget |
| `minStakingDuration` | `0` | `259200` (3 days) |
| `maxNumServices` | `2` | `10`, `100`, etc. |
| `numAgentInstances` | `1` | `1` or `4` |
| `livenessRatio` | `11574074074074` | `11574074074074` |
| `availableRewards` | `4000000000000000000000` (4000 OLAS) | Program specific |

## Contract ABI Requirements

Your staking contract should implement:
- `getStakingState(uint256 serviceId) returns (uint256)`
- `getServiceInfo(uint256 serviceId) returns (tuple)`
- `calculateStakingReward(uint256 serviceId) returns (uint256)`
- `availableRewards() returns (uint256)`
- `rewardsPerSecond() returns (uint256)`
- `minStakingDuration() returns (uint256)`
- `checkpoint() returns (...)`
- `claim(uint256 serviceId)`
- `stake(uint256 serviceId)`
- `unstake(uint256 serviceId)`

## Support Contracts

### AttestationTracker
- Tracks voting attestations from service multisigs
- Functions:
  - `getNumAttestations(address multisig) returns (uint256)`
  - `getVotingStats(address multisig) returns (uint256[])`
  - `attestByDelegation(...)` - Called by service to record votes

### OLAS Token
- Standard ERC20
- Must approve staking contract before depositing
- Rewards are transferred from staking contract to multisig on claim
