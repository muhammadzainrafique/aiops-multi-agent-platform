# agents/evaluator/main.py
"""
Entrypoint for the Evaluator agent.
Starts the blocking Redis consumer loop.
"""
from dotenv import load_dotenv
from shared.utils.logger import get_logger
from agents.evaluator.agent import EvaluatorAgent

load_dotenv()

log = get_logger("evaluator.main")


if __name__ == "__main__":
    log.info("Evaluator agent starting ...")
    agent = EvaluatorAgent()
    agent.run()
