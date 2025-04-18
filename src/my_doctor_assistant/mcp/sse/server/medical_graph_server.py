"""
MCP Server exposing a Neo4j GraphDB tool for the Doctor Assistant project.
Run with:
    python -m my_doctor_assistant.mcp.stdio.server.medical_graph_server
The server now speaks SSE/HTTP instead of stdio.
"""

import os, re 
from mcp.server.fastmcp import FastMCP
from typing import List
from my_doctor_assistant.infrastructure.database.neo4j.connection import Neo4jDBConnection
from my_doctor_assistant.mcp.prompts import domain_prompts as dp
from starlette.middleware.cors import CORSMiddleware

from my_doctor_assistant.utils.helper import (
    get_mcp_host,
    get_mcp_port,
    lowercase_literals,
)

# Cypher Execution Helper
def _run_cypher_query(cypher_query: str) -> str:
    """Lower‑cases quoted literals, runs the query, returns raw results."""
    try:
        cypher_query = lowercase_literals(cypher_query)
        conn = Neo4jDBConnection()
        graph = conn.start()
        results = graph.query(cypher_query)
        if not results:
            return "No results returned."
        return str(results)
    except Exception as exc:  # noqa: BLE001
        return f"Error executing Cypher: {exc}"

# FastMCP server definition
mcp = FastMCP("neo4j-medical-server")

mcp.settings.host = get_mcp_host()
mcp.settings.port = get_mcp_port()

# CORS so browsers & reverse proxies can connect
mcp.sse_app().add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

TOOL_NAME = "GraphDB" # public identifier used by clients

@ mcp.tool(name=TOOL_NAME, description="Run a Cypher query against the medical Neo4j database")
async def graphdb(query: str) -> str:  # noqa: D401
    """Run a Cypher query against the medical Neo4j database."""
    return _run_cypher_query(query)

__all__ = ["TOOL_NAME"] # export the constant for client reuse

@mcp.resource(
    uri="resource://neo4j-schema",         # unique identifier
    name="Medical Graph Schema",           # human‑readable label
    description="Full Cypher schema prompt for the Neo4j medical graph",
    mime_type="text/plain",
)
async def medical_schema() -> str:
    """
    Return the full MEDICAL_SCHEMA_PROMPT so that IDEs / LLMs
    can retrieve the latest schema programmatically.
    """
    return dp.MEDICAL_SCHEMA_PROMPT

@mcp.resource(uri="resource://prompts/vitals-bp",
              name="Vitals – Blood Pressure",
              description="Prompt slice for vitals & blood‑pressure queries",
              mime_type="text/plain")
async def vitals_bp_prompt() -> str:
    return dp.VITALS_BLOOD_PRESSURE_PROMPT

@mcp.resource(uri="resource://prompts/appointments-billing",
              name="Appointments & Billing",
              description="Prompt slice for appointment scheduling & billing",
              mime_type="text/plain")
async def appointments_billing_prompt() -> str:
    return dp.APPOINTMENTS_BILLING_PROMPT

@mcp.resource(uri="resource://prompts/consultation-clinical",
              name="Consultation & Clinical Notes",
              description="Prompt slice for consultation/clinical‑note queries",
              mime_type="text/plain")
async def consultation_clinical_prompt() -> str:
    return dp.CONSULTATION_CLINICAL_PROMPT


@mcp.resource(uri="resource://prompts/diagnoses-conditions",
              name="Diagnoses & Conditions",
              description="Prompt slice for diagnosis tracking queries",
              mime_type="text/plain")
async def diagnoses_conditions_prompt() -> str:
    return dp.DIAGNOSES_CONDITIONS_PROMPT


@mcp.resource(uri="resource://prompts/treatment-plans-history",
              name="Treatment Plans & History",
              description="Prompt slice for treatment‑plan queries",
              mime_type="text/plain")
async def treatment_plans_history_prompt() -> str:
    return dp.TREATMENT_PLANS_HISTORY_PROMPT


@mcp.resource(uri="resource://prompts/medications-prescriptions",
              name="Medications & Prescriptions",
              description="Prompt slice for prescription queries",
              mime_type="text/plain")
async def medications_prescriptions_prompt() -> str:
    return dp.MEDICATIONS_PRESCRIPTIONS_PROMPT


@mcp.resource(uri="resource://prompts/lab-results",
              name="Lab / Investigation Results",
              description="Prompt slice for lab result & investigation queries",
              mime_type="text/plain")
async def lab_results_prompt() -> str:
    return dp.LAB_RESULTS_PROMPT

# Entry‑point when executed directly

def main() -> None:
    """
    Console‑script entry‑point so the SSE server can be launched with

        $ medical-mcp-sse
        # – or –
        $ python -m my_doctor_assistant.mcp.sse.server.medical_graph_server
    """
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()