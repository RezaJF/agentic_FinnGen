import logging
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_trace.log")
    ]
)

def get_logger(name: str):
    return logging.getLogger(name)

def log_agent_action(agent_name: str, action: str, details: Any):
    logger = get_logger(agent_name)
    logger.info(json.dumps({
        "agent": agent_name,
        "action": action,
        "details": details
    }))
