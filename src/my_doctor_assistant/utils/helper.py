import os, sys, re
from dotenv import dotenv_values, load_dotenv

# Determine the absolute path to the .env file located in the config folder.
# Adjust the relative path as needed for your project structure.
current_dir = os.path.dirname(os.path.abspath(__file__))
# print("Current directory:", current_dir)
print("Current directory:", current_dir, file=sys.stderr)
env_path = os.path.join(current_dir, "../../../config/.env")
# print("Environment file path:", env_path)
print("Environment file path:", env_path, file=sys.stderr)

# Returns a dictionary containing all the environment variables from the .env file.
env_vars = dotenv_values(env_path)

# Loads the .env file and automatically sets all key-value pairs in the environment.
load_dotenv(dotenv_path=env_path)

# If .env has OPENAI_API_KEY, set it in os.environ as well.
openai_key = env_vars.get("OPENAI_API_KEY", "")
if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

# Load Neo4j credentials as well
neo4j_uri = env_vars.get("NEO4J_URI", "")
neo4j_user = env_vars.get("NEO4J_USER", "")
neo4j_password = env_vars.get("NEO4J_PASSWORD", "")

if neo4j_uri and neo4j_user and neo4j_password:
    os.environ["NEO4J_URI"] = neo4j_uri
    os.environ["NEO4J_USER"] = neo4j_user
    os.environ["NEO4J_PASSWORD"] = neo4j_password

def load_environment_variables() -> dict:
    """
    Explicitly re-loads the .env file from the config folder and updates environment variables.
    Returns:
        dict: A dictionary of the newly loaded values.
    """
    reloaded = dotenv_values(env_path)
    load_dotenv(dotenv_path=env_path)
    if "OPENAI_API_KEY" in reloaded:
        os.environ["OPENAI_API_KEY"] = reloaded["OPENAI_API_KEY"]
    
    # Reload Neo4j vars
    if "NEO4J_URI" in reloaded and "NEO4J_USER" in reloaded and "NEO4J_PASSWORD" in reloaded:
        os.environ["NEO4J_URI"] = reloaded["NEO4J_URI"]
        os.environ["NEO4J_USER"] = reloaded["NEO4J_USER"]
        os.environ["NEO4J_PASSWORD"] = reloaded["NEO4J_PASSWORD"]
        
    return reloaded

def get_openai_api_key() -> str:
    """
    Returns the current OPENAI_API_KEY from the environment (if available).
    """
    return os.environ.get("OPENAI_API_KEY", "")

def get_neo4j_credentials() -> tuple[str, str, str]:
    """
    Returns the Neo4j credentials (URI, user, password) from the environment.
    """
    uri = os.environ.get("NEO4J_URI", "")
    user = os.environ.get("NEO4J_USER", "")
    password = os.environ.get("NEO4J_PASSWORD", "")
    return (uri, user, password)

# ──────────────────────────────────────────────────────────────────────────
#  New MCP helpers
# ──────────────────────────────────────────────────────────────────────────
def get_mcp_host() -> str:
    """Return the MCP server host (defaults to 0.0.0.0)."""
    return os.environ.get("MCP_HOST", "0.0.0.0")

def get_mcp_port() -> int:
    """Return the MCP server port (defaults to 8080)."""
    return int(os.environ.get("MCP_PORT", "8080"))

def get_mcp_url() -> str:
    """Return 'http(s)://host:port' for the MCP server."""
    return os.environ.get("MCP_URL", f"http://{get_mcp_host()}:{get_mcp_port()}")

# ──────────────────────────────────────────────────────────────────────────
#  Shared utility
# ──────────────────────────────────────────────────────────────────────────
def lowercase_literals(query: str) -> str:
    """
    Lower‑case every quoted literal inside a Cypher query to satisfy
    prompt constraints.
    """
    return re.sub(r"['\"]([^'\"]*)['\"]", lambda m: f"'{m.group(1).lower()}'", query)