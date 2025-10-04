You are an expert blockchain engineer. You're goal is to successfully test and confirm the agent can claim staking rewards.



## Resources
- All information related to wallets, keys, and deployments can be found in .operate/
- The repo for the agent being tested is located at ../quorum-ai
- Olas staking contracts: https://github.com/valory-xyz/autonolas-registries/tree/a85d0d802c2127b01bc69194df8ef7921d365231/contracts/staking
- Olas staking contract ABIs: https://github.com/valory-xyz/autonolas-registries/tree/a85d0d802c2127b01bc69194df8ef7921d365231/abis
- Key Base contract addresses: https://github.com/valory-xyz/autonolas-staking-programmes/blob/65b3045ee92c90ff660fc79eed269bb9fbc9c04e/scripts/deployment/externals/globals_base_mainnet_backland_test.json

To start the local blockchain:
```bash
anvil --fork-url https://mainnet.base.org --auto-impersonate
```

To deploy services including after the service state is EVICTED this will unstake and then stake:
```bash
export OPERATE_PASSWORD=“” / 
export BASE_LEDGER_RPC=http://localhost:8545 /
export STAKING_PROGRAM=custom_staking
export STAKING_CONTRACT_ADDRESS=0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb
```
This script will tell when the service is staked and available for testing
```bash
./run_service.sh configs/config_quorum.json --attended=false
```

To kill services run docker-compose down

THIS IS THE KEY SCRIPT.
The test script can be ran with:
```bash
./test_staking_rewards.py
```

The goal is to make this return a successful response and prove staking rewards were received by the agent.
```bash
./claim_staking_rewards.sh <agent_config.json>
```

## Staking Info
- Agent can only be unstaked after 72 hours. You may need to advance time
- TO UNSTAKE THE AGENT: Fast forward time via Anvil so that it's been at least 72 hours, Then confirm the agent service is marked as evicted. then stop the services and then rerun the run_service.sh script. 