#!/bin/bash

# Fund the staking contract with OLAS rewards

set -e

RPC_URL="${BASE_LEDGER_RPC:-http://localhost:8545}"
OLAS_TOKEN="0x54330d28ca3357F294334BDC454a032e7f353416"
OLAS_WHALE="0xC8F7030a4e25585624e2Fc792255a547255Cd77c"
STAKING_CONTRACT="${STAKING_CONTRACT_ADDRESS:-0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb}"

# Amount to fund (1000 OLAS = 1000 * 10^18 wei)
AMOUNT="1000000000000000000000"

echo "=== Funding Staking Contract with OLAS ==="
echo ""
echo "Staking Contract: $STAKING_CONTRACT"
echo "OLAS Token: $OLAS_TOKEN"
echo "Amount: 1000 OLAS"
echo ""

# Check current balance
echo "Current available rewards:"
cast call "$STAKING_CONTRACT" "availableRewards()(uint256)" --rpc-url "$RPC_URL"

echo ""
echo "Approving OLAS for staking contract..."
cast send "$OLAS_TOKEN" "approve(address,uint256)" "$STAKING_CONTRACT" "$AMOUNT" \
  --from "$OLAS_WHALE" \
  --unlocked \
  --rpc-url "$RPC_URL"

echo ""
echo "Depositing OLAS to staking contract..."
cast send "$STAKING_CONTRACT" "deposit(uint256)" "$AMOUNT" \
  --from "$OLAS_WHALE" \
  --unlocked \
  --rpc-url "$RPC_URL"

echo ""
echo "New available rewards:"
cast call "$STAKING_CONTRACT" "availableRewards()(uint256)" --rpc-url "$RPC_URL"

echo ""
echo "✓ Staking contract funded successfully!"
