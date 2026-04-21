import asyncio
import logging

from core.config import get_env, get_float, get_int, validate_config
from economy import simulation_engine

logger = logging.getLogger("AgentManager")

DEMAND_THRESHOLD = get_float("ARCOS_DEMAND_THRESHOLD", 1.1)
MAX_COMPUTE_AGENTS = get_int("ARCOS_MAX_COMPUTE_AGENTS", 10)


def _compute_agent_accounts():
    configured_keys = list(validate_config()["config"]["ECONOMY"].get("compute_agent_keys", []))
    fallback_keys = [
        str(get_env("ARCOS_COMPUTE_AGENT_PK_1", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_2", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_3", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_4", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_5", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_6", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_7", "") or ""),
        str(get_env("ARCOS_COMPUTE_AGENT_PK_8", "") or ""),
    ]
    private_keys = configured_keys + fallback_keys[len(configured_keys):]
    wallets = [
        "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
        "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
        "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
        "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",
        "0x976EA74026E726554dB657fA54763abd0C3a0aa9",
        "0x14dC79964da2C08dA15Fb5cd2e40DEE5d1545727",
        "0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f",
        "0xa0Ee7A142d267C1f36714E4a8F75612F20a79720",
    ]
    return list(zip(wallets, private_keys, strict=False))

class AgentManager:
    # Hardhat test accounts (indices 2-19 are available)
    HARDHAT_ACCOUNTS = _compute_agent_accounts()
    def __init__(self, market, market_agent, event_bus=None):
        self.market = market
        self.market_agent = market_agent
        self.event_bus = event_bus
        self.compute_agents = []
        self._next_account_idx = 1  # 0 is already used by ComputeAgent_1

    def register_compute_agent(self, agent):
        self.compute_agents.append(agent)

    def _get_next_wallet(self):
        if self._next_account_idx >= len(self.HARDHAT_ACCOUNTS):
            logger.warning("No more Hardhat accounts available for new agents.")
            return None, None
        wallet, pk = self.HARDHAT_ACCOUNTS[self._next_account_idx]
        self._next_account_idx += 1
        return wallet, pk

    def spawn_compute_agent(self):
        from agents.compute_agent import ComputeAgent

        if len(self.compute_agents) >= MAX_COMPUTE_AGENTS:
            logger.warning(f"[ARCOS ECONOMY LOG] Max compute agents reached ({MAX_COMPUTE_AGENTS}). Scaling aborted.")
            return None

        wallet, pk = self._get_next_wallet()
        if not wallet:
            return None

        agent_id = f"ComputeAgent_{len(self.compute_agents)}"
        agent = ComputeAgent(
            wallet=wallet,
            market=self.market,
            market_agent=self.market_agent,
            event_bus=self.event_bus,
            agent_id=agent_id,
        )
        self.register_compute_agent(agent)

        # Launch in current event loop
        asyncio.get_event_loop().create_task(agent.run())
        print(f"\033[94m[ARCOS ECONOMY LOG] Spawning {agent_id} (wallet: {wallet[:10]}...)\033[0m")
        logger.info(f"[ARCOS] Spawned {agent_id}")

        # Update the shared agent registry so the /agents API sees new agents
        simulation_engine.agent_registry.append(
            {"agent_id": agent_id, "wallet": wallet, "role": "compute"}
        )

        if self.event_bus:
            self.event_bus.publish("agent_spawned", {
                "agent_id": agent_id,
                "wallet": wallet,
                "role": "compute",
            })
        return agent

    async def monitor(self):
        """Periodically check demand and scale agents."""
        logger.info("[ARCOS] Agent Manager monitoring started.")
        while True:
            await asyncio.sleep(2)
            pending = len(self.market.pending_jobs)
            active = len(self.compute_agents)
            ratio = pending / max(active, 1)

            if ratio >= DEMAND_THRESHOLD:
                print(f"\033[93m[ARCOS ECONOMY LOG] Demand spike detected! Ratio: {ratio:.1f} (Pending: {pending})\033[0m")
                self.spawn_compute_agent()
            else:
                logger.debug(f"[ARCOS] Demand normal. Pending: {pending}, Agents: {active}, Ratio: {ratio:.1f}")
