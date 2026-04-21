import asyncio
import logging

from agents.compute_agent import ComputeAgent
from agents.market_agent import MarketAgent
from agents.research_agent import ResearchAgent
from core.config import get_env
from economy.agent_manager import AgentManager
from economy.event_bus import event_bus
from economy.job_market import JobMarket
from services.insight_engine import start_insight_manager
from services.payment_service import ensure_seed_balance

logger = logging.getLogger("SimulationEngine")

RESEARCH_WALLET = str(get_env("ARCOS_RESEARCH_WALLET", "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"))
RESEARCH_PK = str(get_env("ARCOS_RESEARCH_PRIVATE_KEY", "") or "")
COMPUTE_WALLET = str(get_env("ARCOS_COMPUTE_WALLET", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"))
COMPUTE_PK = str(get_env("ARCOS_COMPUTE_PRIVATE_KEY", "") or "")

agent_registry: list[dict] = []
market_ref: JobMarket | None = None
manager_ref: AgentManager | None = None
_simulation_started = False


async def start_simulation():
    global market_ref, manager_ref, _simulation_started
    if _simulation_started:
        logger.info("Simulation already running; startup skipped.")
        return
    _simulation_started = True

    logger.info("=======================================")
    logger.info("   ARCOS Simulation Engine Starting")
    logger.info("=======================================")

    try:
        ensure_seed_balance(RESEARCH_WALLET, RESEARCH_PK)
        ensure_seed_balance(COMPUTE_WALLET, COMPUTE_PK)
        logger.info("Funded ARCOS settlement wallets with simulated USDC float.")
    except Exception as exc:
        logger.warning("Initial deposit issue (may already exist): %s", exc)

    market = JobMarket()
    market_ref = market
    market_agent = MarketAgent(event_bus=event_bus)

    manager = AgentManager(market=market, market_agent=market_agent, event_bus=event_bus)
    manager_ref = manager

    researcher = ResearchAgent(
        wallet=RESEARCH_WALLET,
        private_key=RESEARCH_PK,
        market=market,
        event_bus=event_bus,
        agent_id="ResearchAgent_0",
    )
    computer = ComputeAgent(
        wallet=COMPUTE_WALLET,
        market=market,
        market_agent=market_agent,
        event_bus=event_bus,
        agent_id="ComputeAgent_0",
    )
    wallet2, _pk2 = AgentManager.HARDHAT_ACCOUNTS[0]
    computer2 = ComputeAgent(
        wallet=wallet2,
        market=market,
        market_agent=market_agent,
        event_bus=event_bus,
        agent_id="ComputeAgent_1",
    )
    manager.register_compute_agent(computer)
    manager.register_compute_agent(computer2)

    agent_registry.clear()
    agent_registry.extend(
        [
            {"agent_id": "ResearchAgent_0", "wallet": RESEARCH_WALLET, "role": "research"},
            {"agent_id": "ComputeAgent_0", "wallet": COMPUTE_WALLET, "role": "compute"},
            {"agent_id": "ComputeAgent_1", "wallet": wallet2, "role": "compute"},
        ]
    )

    loop = asyncio.get_running_loop()
    loop.create_task(researcher.run())
    loop.create_task(computer.run())
    loop.create_task(computer2.run())
    loop.create_task(manager.monitor())
    loop.create_task(start_insight_manager(event_bus))

    logger.info("Simulation running. Agents are trading autonomously.")
