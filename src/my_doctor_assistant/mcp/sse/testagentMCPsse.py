import os, re, asyncio
from functools import lru_cache

# Imports for LLM and Tools
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, initialize_agent
from my_doctor_assistant.agents.structured_chat.types import AgentType

# MCP Client Imports
from mcp.client.sse import sse_client
from mcp import ClientSession

# Project-Specific Imports
from my_doctor_assistant.utils.helper import get_openai_api_key, get_mcp_url, lowercase_literals
from my_doctor_assistant.mcp.prompts import domain_prompts as dp 
from my_doctor_assistant.mcp.sse.server.medical_graph_server import TOOL_NAME 

# Retrieve and set OpenAI API key
openai_api_key = get_openai_api_key()
os.environ["OPENAI_API_KEY"] = openai_api_key

MCP_URL = get_mcp_url()

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

async def _with_new_session(coro):
    """Open a one‑shot SSE connection, run *coro(session)*, then close."""
    async with sse_client(f"{MCP_URL}/sse") as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            return await coro(session)

@lru_cache(maxsize=8)
def get_domain_prompt(kind: str = "schema") -> str:
    """Fetch & cache prompt slice, fallback to offline constant on error."""
    uri = PROMPT_URI_MAP.get(kind, PROMPT_URI_MAP["schema"])

    async def _fetch(session: ClientSession):
        resp = await session.read_resource(uri)
        return resp.content[0].text

    try:
        return asyncio.run(_with_new_session(_fetch))
    except Exception:
        return OFFLINE_PROMPT_MAP[kind]
    
async def _graphdb_async(query: str) -> str:
    """Execute GraphDB tool and return raw result string."""
    query = lowercase_literals(query)

    async def _call(session: ClientSession):
        resp = await session.call_tool(TOOL_NAME, {"query": query})
        return resp.content[0].text if resp.content else "No content returned."

    return await _with_new_session(_call)

def graphdb_sync(query: str) -> str:
    """LangChain expects a blocking callable for Tool.func."""
    return asyncio.run(_graphdb_async(query))


def make_graph_tool() -> Tool:
    return Tool(
        name=TOOL_NAME,
        func=graphdb_sync,
        description="Execute Cypher against the medical Neo4j database.",
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
        prompt = f"{self.prompt.format(user_question=question)}\nUser question: {question}"
        return self.agent.run(prompt)

def main():
    agent = MedicalQAAgent(domain="vitals") # pick any slice here
    question = "what's sir blood pressure in December 2023?"
    print(f"\nUser question: {question}")
    final_answer = agent.answer(question)
    print("\nFinal Answer:", final_answer)

if __name__ == "__main__":
    main()