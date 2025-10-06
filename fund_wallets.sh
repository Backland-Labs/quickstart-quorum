#!/bin/bash

# RPC URL
RPC_URL="${1:-http://localhost:8545}"

# Funding account (Anvil's first account)
FROM_ACCOUNT="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# OLAS Token address on Base
OLAS_TOKEN="0x54330d28ca3357F294334BDC454a032e7f353416"

# OLAS Whale account on Base
OLAS_WHALE="0xC8F7030a4e25585624e2Fc792255a547255Cd77c"

echo "📋 Extracting initial wallet addresses..."

# Master EOA (externally owned account)
MASTER_EOA=$(cat .operate/wallets/ethereum.json | grep '"address"' | head -1 | grep -o '0x[^"]*')
echo "Master EOA: $MASTER_EOA"

# Master Safe
MASTER_SAFE=$(cat .operate/wallets/ethereum.json | grep -A 1 '"safes"' | grep -o '0x[^"]*' | tail -1)
echo "Master Safe: $MASTER_SAFE"

echo ""
echo "💰 Funding initial wallets on Anvil..."

# Fund Master EOA with ETH
echo "Funding Master EOA with 1 ETH..."
cast send "$MASTER_EOA" --value 1000000000000000000 --from "$FROM_ACCOUNT" --unlocked --rpc-url "$RPC_URL" > /dev/null 2>&1
echo "✓ Master EOA funded with ETH"
sleep 3

# Fund Master Safe with ETH
echo "Funding Master Safe with 1 ETH..."
cast send "$MASTER_SAFE" --value 1000000000000000000 --from "$FROM_ACCOUNT" --unlocked --rpc-url "$RPC_URL" > /dev/null 2>&1
echo "✓ Master Safe funded with ETH"
sleep 3

# Fund Master Safe with OLAS
echo "Funding Master Safe with 200 OLAS..."
cast send "$OLAS_TOKEN" "transfer(address,uint256)" "$MASTER_SAFE" 200000000000000000000 --from "$OLAS_WHALE" --unlocked --rpc-url "$RPC_URL" > /dev/null 2>&1
echo "✓ Master Safe funded with OLAS"
sleep 3

echo ""
echo "📋 Checking for Agent EOA (created after initial funding)..."

# Agent EOA - extracted after initial funding
AGENT_EOA=$(cat .operate/services/sc-*/config.json 2>/dev/null | grep '"address"' | head -1 | grep -o '0x[^"]*')
if [ -n "$AGENT_EOA" ]; then
    echo "Agent EOA: $AGENT_EOA"
    echo "Funding Agent EOA with 1 ETH..."
    cast send "$AGENT_EOA" --value 1000000000000000000 --from "$FROM_ACCOUNT" --unlocked --rpc-url "$RPC_URL" > /dev/null 2>&1
    echo "✓ Agent EOA funded with ETH"
    sleep 3
else
    echo "Agent EOA: Not created yet"
fi

echo ""
echo "💎 Funding staking contract..."

# Staking contract address
STAKING_CONTRACT="${STAKING_CONTRACT_ADDRESS:-0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb}"
STAKING_AMOUNT="1000000000000000000000"  # 1000 OLAS

echo "Approving OLAS for staking contract..."
cast send "$OLAS_TOKEN" "approve(address,uint256)" "$STAKING_CONTRACT" "$STAKING_AMOUNT" --from "$OLAS_WHALE" --unlocked --rpc-url "$RPC_URL" > /dev/null 2>&1
echo "✓ OLAS approved for staking contract"
sleep 3

echo "Depositing 1000 OLAS to staking contract..."
cast send "$STAKING_CONTRACT" "deposit(uint256)" "$STAKING_AMOUNT" --from "$OLAS_WHALE" --unlocked --rpc-url "$RPC_URL" > /dev/null 2>&1
echo "✓ Staking contract funded with OLAS"
sleep 3

echo ""
echo "✅ All wallets funded!"
echo ""
echo "📊 Balances:"
echo "Master EOA ETH: $(cast balance "$MASTER_EOA" --rpc-url "$RPC_URL" | awk '{print $1/1e18}') ETH"
echo "Master Safe ETH: $(cast balance "$MASTER_SAFE" --rpc-url "$RPC_URL" | awk '{print $1/1e18}') ETH"
echo "Master Safe OLAS: $(cast call "$OLAS_TOKEN" "balanceOf(address)(uint256)" "$MASTER_SAFE" --rpc-url "$RPC_URL" | awk '{print $1/1e18}') OLAS"
if [ -n "$AGENT_EOA" ]; then
    echo "Agent EOA ETH: $(cast balance "$AGENT_EOA" --rpc-url "$RPC_URL" | awk '{print $1/1e18}') ETH"
fi
echo "Staking Contract Available Rewards: $(cast call "$STAKING_CONTRACT" "availableRewards()(uint256)" --rpc-url "$RPC_URL" | awk '{print $1/1e18}') OLAS"

echo ""
echo "💾 Saving Anvil state..."
curl -s -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"anvil_dumpState","params":[],"id":1}' \
  | jq -r '.result' > anvil_state.json
echo "✓ Anvil state saved to anvil_state.json"
echo ""
echo "To restore this state later, use:"
echo "  anvil --load-state anvil_state.json"
