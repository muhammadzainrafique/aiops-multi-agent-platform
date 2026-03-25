# agents/resolver/main.py
"""
Entrypoint for the Resolver agent.
Starts the blocking Redis consumer loop.
"""
from dotenv import load_dotenv
from shared.utils.logger import get_logger
from agents.resolver.agent import ResolverAgent

load_dotenv()

log = get_logger("resolver.main")

if __name__ == "__main__":
    log.info("Resolver agent starting ...")
    agent = ResolverAgent()
    agent.run()
