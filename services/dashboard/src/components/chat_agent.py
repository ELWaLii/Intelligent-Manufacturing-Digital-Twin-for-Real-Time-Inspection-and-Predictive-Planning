import os
import streamlit as st

# Load .env as fallback for local development (Docker injects env vars directly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed — rely on OS/Docker env vars

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from influxdb_client import InfluxDBClient

# Setup PostgreSQL DB Connection
def get_sql_db():
    """Initializes and returns a SQLDatabase connection to PostgreSQL.

    Returns:
        SQLDatabase: A LangChain SQLDatabase instance connected to kave_db,
            or None if the connection fails.
    """
    db_user = os.environ.get("POSTGRES_USER", "admin")
    db_password = os.environ.get("POSTGRES_PASSWORD", "kave_pass")
    db_host = os.environ.get("DB_HOST", "kave_db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("POSTGRES_DB", "kave_db")
    db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    try:
        return SQLDatabase.from_uri(db_uri)
    except Exception as e:
        return None

sql_db = get_sql_db()

@tool
def query_postgresql(query: str) -> str:
    """Executes a PostgreSQL query on kave_db to retrieve business data, defect logs, scenarios, and profitability metrics.
    First, use the get_postgres_schema tool if you do not know the tables."""
    try:
        return sql_db.run(query)
    except Exception as e:
        return f"Error executing PostgreSQL query: {str(e)}"

@tool
def get_postgres_schema() -> str:
    """Returns the table schema and information for the PostgreSQL database kave_db."""
    try:
        return sql_db.get_table_info()
    except Exception as e:
        return f"Error getting schema: {str(e)}"

@tool
def query_influxdb(flux_query: str) -> str:
    """Executes a Flux query on the InfluxDB 'cnc_digital_twin' bucket to retrieve real-time CNC machine sensor data, machine wear stage, and anomaly probability.
    The measurement is 'machine_health'.
    Tags: 'machine_id', 'process'. Fields: 'prediction_stage' (int 0-3), 'confidence_percent' (float 0-100), 'x1_current', 'z1_current'."""
    token = os.environ.get("INFLUX_TOKEN", "t4Zac1hxXZQvIIfeBCoJLJgxJwWIPDPTknBSl54o1erJHqfG3vPdr0RVZocUGIrfSppVa5nF4gXyKbxEnVJRQA==")
    org = os.environ.get("DOCKER_INFLUXDB_INIT_ORG", "kave_org")
    url = "http://kave_influx_db:8086"
    
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        query_api = client.query_api()
        result = query_api.query(org=org, query=flux_query)
        
        output = []
        for table in result:
            for record in table.records:
                output.append(f"Time: {record.get_time()}, Machine: {record.values.get('machine_id', 'N/A')}, Field: {record.get_field()}, Value: {record.get_value()}")
        
        if not output:
            return "Query executed successfully, but no results were found."
        
        return "\n".join(output[:50]) # limit output to prevent context overflow
    except Exception as e:
        return f"Error executing InfluxDB Flux query: {str(e)}"

@tool
def get_influx_schema() -> str:
    """Returns the schema information for InfluxDB. Useful before writing complex Flux queries to understand available measurements and fields in the 'cnc_digital_twin' bucket."""
    flux_query = '''
    import "influxdata/influxdb/schema"
    schema.measurements(bucket: "cnc_digital_twin")
    '''
    return query_influxdb.invoke({"flux_query": flux_query})

def get_agent():
    """Initializes and returns the Langchain ReAct tool-calling agent.

    Returns:
        AgentExecutor: The configured Langchain agent executor, or None if
            initialization fails (e.g. missing API key).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY environment variable not found. Please set it in your .env file.")
        return None

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0)
        # We can attempt a dummy call or just trust it. If it fails on generation, we might need a fallback.
        # But initialization validates the model if the library tries to fetch model info.
    except Exception as e:
        st.warning(f"Failed to initialize gemini-1.5-flash. Error: {e}")
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0)
        except Exception as e_fallback:
            st.error(f"Failed to initialize Gemini fallback: {e_fallback}")
            return None

    tools = [query_postgresql, get_postgres_schema, query_influxdb, get_influx_schema]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Elite Senior Data Engineer AI for KAVE Intelligent Manufacturing. "
                   "You answer questions using PostgreSQL (for business, defect logs, planning) "
                   "and InfluxDB (for live CNC sensor, machine wear, and real-time streams). "
                   "ALWAYS follow these rules:\n"
                   "1. Your tone must be strictly professional, technical, direct, and concise.\n"
                   "2. Do NOT use casual filler language, emojis, or unnecessary emotional phrasing.\n"
                   "3. If you need to write SQL, use the query_postgresql tool. If you need to write Flux, use the query_influxdb tool.\n"
                   "   - Use query_postgresql to interact with business tables like 'production_scenarios' or 'defect_logs'.\n"
                   "   - Use query_influxdb to interact with the 'cnc_digital_twin' bucket for live sensors.\n"
                   "4. Use the schema tools to understand the data structures before querying.\n"
                   "   - Call get_postgres_schema to see available PostgreSQL tables and columns.\n"
                   "   - Call get_influx_schema to see available InfluxDB measurements.\n"
                   "5. When providing a final answer, be precise and data-driven.\n"
                   "Execute the analytical request efficiently."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

def render_chatbot():
    """Renders the Chatbot UI in Streamlit."""
    st.markdown("### KAVE Intelligence Engine")
    st.markdown("Dual-Database AI Agent (Powered by Gemini 1.5 Flash): PostgreSQL & InfluxDB. Enter query parameters below.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    if prompt := st.chat_input("Query system data (e.g. scrap rates, CNC machine wear)..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Executing analytical procedures..."):
                agent_executor = get_agent()
                if agent_executor:
                    try:
                        response = agent_executor.invoke({"input": prompt})
                        answer = response.get("output", "Analysis complete but no output generated.")
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        error_msg = f"System Error during execution: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                else:
                    st.markdown("System Initialization Failure. Check logs.")
