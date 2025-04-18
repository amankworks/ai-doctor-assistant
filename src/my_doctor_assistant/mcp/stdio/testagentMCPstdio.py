import os
import re
import asyncio
from functools import lru_cache

# Imports for LLM and Tools
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, initialize_agent
from my_doctor_assistant.agents.structured_chat.types import AgentType

# MCP Client Imports
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from my_doctor_assistant.mcp.prompts import domain_prompts as dp 

from my_doctor_assistant.utils.helper import get_openai_api_key, lowercase_literals
from my_doctor_assistant.mcp.stdio.server.medical_graph_server import TOOL_NAME 

# Retrieve and set OpenAI API key
openai_api_key = get_openai_api_key()
os.environ["OPENAI_API_KEY"] = openai_api_key

PROMPT_URI_MAP = {
    "schema":       "resource://neo4j-schema",
    "vitals":       "resource://prompts/vitals-bp",
    "appointments": "resource://prompts/appointments-billing",
    "consultation": "resource://prompts/consultation-clinical",
    "diagnoses":    "resource://prompts/diagnoses-conditions",
    "treatment":    "resource://prompts/treatment-plans-history",
    "medications":  "resource://prompts/medications-prescriptions",
    "labs":         "resource://prompts/lab-results",
}

OFFLINE_PROMPT_MAP = {
    "schema":       dp.MEDICAL_SCHEMA_PROMPT,
    "vitals":       dp.VITALS_BLOOD_PRESSURE_PROMPT,
    "appointments": dp.APPOINTMENTS_BILLING_PROMPT,
    "consultation": dp.CONSULTATION_CLINICAL_PROMPT,
    "diagnoses":    dp.DIAGNOSES_CONDITIONS_PROMPT,
    "treatment":    dp.TREATMENT_PLANS_HISTORY_PROMPT,
    "medications":  dp.MEDICATIONS_PRESCRIPTIONS_PROMPT,
    "labs":         dp.LAB_RESULTS_PROMPT,
}

# Helpers: MCP resources
SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=["-m", "my_doctor_assistant.mcp.stdio.server.medical_graph_server"],
    env=None,
)

@lru_cache(maxsize=8)
def get_domain_prompt(kind: str = "schema") -> str:
    """Fetch a prompt slice from the MCP server or fall back to local constant."""
    uri = PROMPT_URI_MAP.get(kind, PROMPT_URI_MAP["schema"])

    async def _fetch() -> str:
        async with stdio_client(SERVER_PARAMS) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                resp = await session.read_resource(uri)
                return resp.content[0].text

    try:
        return asyncio.run(_fetch())
    except Exception:
        return OFFLINE_PROMPT_MAP[kind]

async def _graphdb_async(query: str) -> str:
    query = lowercase_literals(query)
    async with stdio_client(SERVER_PARAMS) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            resp = await session.call_tool(TOOL_NAME, {"query": query})
            return resp.content

def graphdb_sync(query: str) -> str:
    return asyncio.run(_graphdb_async(query))

def get_domain_prompt(kind: str = "schema") -> str:
    """
    Download the requested prompt slice from the MCP server once (LRU‑cached).
    Falls back to the baked‑in constant if the server is not reachable.
    """
    uri = PROMPT_URI_MAP.get(kind, PROMPT_URI_MAP["schema"])

    @lru_cache(maxsize=8)
    def _pull(uri_: str) -> str:
        async def _fetch() -> str:
            async with stdio_client(SERVER_PARAMS) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    resp = await session.read_resource(uri_)
                    return resp.content[0].text
        try:
            return asyncio.run(_fetch())
        except Exception:
            # offline fallback
            return OFFLINE_PROMPT_MAP.get(kind, OFFLINE_PROMPT_MAP["schema"])

    return _pull(uri)

def make_graph_tool() -> Tool:
    return Tool(
        name=TOOL_NAME,
        func=graphdb_sync,
        description="Execute Cypher against the medical Neo4j database."
    )

# Agent Wrapper
class MedicalQAAgent:
    def __init__(self, domain: str = "schema", temperature: float = 0.0):
        self.prompt = get_domain_prompt(domain)
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=temperature,
            # top_p=1,
            # n=1,
        )
        self.agent = initialize_agent(
            tools=[make_graph_tool()],
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
        )

    def answer(self, question: str) -> str:
        prompt = f"{self.prompt.format(user_question=question)}\\nUser question: {question}"
        return self.agent.run(prompt)

def main():
    agent = MedicalQAAgent(domain="vitals") # pick any slice here
    question = "How many investigation orders are still marked ‘active’ for Siri?"
    print(f"\\nUser question: {question}")
    final_answer = agent.answer(question)
    print("\\nFinal Answer:", final_answer)

if __name__ == "__main__":
    main()
