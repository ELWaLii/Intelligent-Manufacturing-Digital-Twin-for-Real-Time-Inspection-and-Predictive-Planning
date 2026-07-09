import os
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
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
    api_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    if not api_token:
        st.error("HUGGINGFACEHUB_API_TOKEN environment variable not found. Please set it in your .env file.")
        return None

    try:
        llm = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            task="text-generation",
            max_new_tokens=1024,
            temperature=0.1,
            huggingfacehub_api_token=api_token
        )
        chat_model = ChatHuggingFace(llm=llm)
    except Exception as e:
        st.error(f"Failed to initialize Hugging Face model. Error: {e}")
        return None

    tools = [query_postgresql, get_postgres_schema, query_influxdb, get_influx_schema]

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an Elite Senior Data Engineer AI for KAVE Intelligent Manufacturing. "
                   "You MUST use your tools SILENTLY to fetch data. DO NOT explain your thought process. "
                   "DO NOT output raw SQL queries or Flux queries to the user. "
                   "DO NOT write phrases like 'I will execute this query now' or 'Let me check'. "
                   "NEVER output raw function calls like `query_postgresql(...)` to the user. "
                   "Simply observe the tool's result internally and provide ONLY the final, concise, human-readable answer.\n"
                   "ALWAYS follow these rules:\n"
                   "1. Your tone must be strictly professional, technical, direct, and concise.\n"
                   "2. Do NOT use casual filler language, emojis, or unnecessary emotional phrasing.\n"
                   "3. Use query_postgresql to interact with business tables like 'production_scenarios' or 'defect_logs'.\n"
                   "4. Use query_influxdb to interact with the 'cnc_digital_twin' bucket for live sensors.\n"
                   "5. Use schema tools (get_postgres_schema, get_influx_schema) to understand structures before querying.\n"
                   "6. Execute analytical requests efficiently and return ONLY the final synthesized data-driven answer."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(chat_model, tools, prompt)
    return AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=False, 
        handle_parsing_errors=True,
        return_intermediate_steps=False
    )

def render_chatbot():
    """Renders the Chatbot UI in Streamlit."""
    st.markdown("### KAVE Intelligence Engine")
    st.markdown("Dual-Database AI Agent (Powered by Qwen 2.5 - Hugging Face): PostgreSQL & InfluxDB. Enter query parameters below.")
    
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
