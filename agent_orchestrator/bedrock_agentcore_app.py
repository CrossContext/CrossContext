"""
OmniContext - AWS Bedrock AgentCore Production Runtime Entrypoint
Deploys the agent within the AWS AgentCore serverless container runtime.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.agent import OmniContextAgent

agent = OmniContextAgent(db_path=os.getenv("SQLITE_DB_PATH", "data/omnicontext_graph.db"))


async def entrypoint(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    Standard AWS Bedrock AgentCore entrypoint handler.
    Receives incoming payload from Bedrock AgentCore dispatcher.
    Payload format: {"prompt": str, "target_repos": list, "session_id": str}
    """
    prompt = event.get("prompt", "Analyze repository dependencies")
    repos = event.get("target_repos", [])

    result = await agent.run(prompt=prompt, repos=repos)
    return {
        "statusCode": 200,
        "body": {
            "status": "success",
            "response": result["response"],
            "telemetry": result["telemetry"],
            "affected_files": result["nodes_touched"]
        }
    }


if __name__ == "__main__":
    # Local CLI runner for AgentCore simulation
    test_event = {
        "prompt": "Deprecate legacy /v1/auth/verify endpoint and update downstream frontend consumers to /v2/auth/token",
        "target_repos": ["repo_auth_core", "repo_frontend_portal"]
    }
    print("[AgentCore Runner] Dispatching event to entrypoint...")
    output = asyncio.run(entrypoint(test_event))
    print(f"\n[AgentCore Result Status]: {output['body']['status']}")
    print(f"\n[Agent Response]:\n{output['body']['response']}")
    print(f"\n[Tool Telemetry]: {output['body']['telemetry']}")
