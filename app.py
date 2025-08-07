import streamlit as st
from pathlib import Path
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq
import pandas as pd
import ast
from urllib.parse import quote_plus

# ---------------------- Page Config ----------------------
st.set_page_config(page_title="LangChain: Chat with SQL DB", page_icon="🐦")
st.title("🐦 LangChain: Chat with SQL DB")

# ---------------------- Constants ----------------------
LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"
radio_opt = ["Use SQLLite 3 Database - student.db", "Connect to your SQL Database"]

# ---------------------- Sidebar UI ----------------------
select_opt = st.sidebar.radio(label="Choose the DB which you want to chat", options=radio_opt)

if radio_opt.index(select_opt) == 1:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("MySQL Hostname")
    mysql_user = st.sidebar.text_input("MySQL Username")
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("MySQL Database Name")
else:
    db_uri = LOCALDB

# ---------------------- Groq API ----------------------
api_key = st.sidebar.text_input("Groq API Key", type="password")

# ---------------------- Input Validation ----------------------
if not db_uri:
    st.info("Please select the database.")
    st.stop()

if not api_key:
    st.info("Please provide the Groq API Key.")
    st.stop()

# ---------------------- LLM Init ----------------------
try:
    llm = ChatGroq(groq_api_key=api_key, model_name="Llama3-8b-8192", streaming=True)
except Exception as e:
    st.error(f"Failed to initialize LLM: {e}")
    st.stop()

# ---------------------- Configure DB ----------------------
@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    if db_uri == LOCALDB:
        dbfilepath = (Path(__file__).parent / "student.db").absolute()
        if not dbfilepath.exists():
            st.error("student.db file not found in project directory.")
            st.stop()
        st.write(f"Using local SQLite DB at: `{dbfilepath}`")
        creator = lambda: sqlite3.connect(str(dbfilepath))
        return SQLDatabase(create_engine("sqlite://", creator=creator))

    elif db_uri == MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Incomplete MySQL connection details.")
            st.stop()

        if "@" in mysql_host:
            st.error("Hostname should not contain '@'. Use only 'localhost' or an IP address.")
            st.stop()

        encoded_password = quote_plus(mysql_password)

        st.success("Connected to MySQL database.")
        return SQLDatabase(create_engine(
            f"mysql+mysqlconnector://{mysql_user}:{encoded_password}@{mysql_host}/{mysql_db}"
        ))

# ---------------------- Load DB ----------------------
if db_uri == MYSQL:
    db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
else:
    db = configure_db(db_uri)

# ---------------------- Toolkit & Agent ----------------------
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True
)

# ---------------------- Chat State ----------------------
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

user_query = st.chat_input(placeholder="Ask anything from database")

# ---------------------- Run Query ----------------------
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])

        # Try to parse output as table
        try:
            parsed_response = ast.literal_eval(response)
            if isinstance(parsed_response, list) and all(isinstance(row, tuple) for row in parsed_response):
                df = pd.DataFrame(parsed_response)
                st.write("### Result Table:")
                st.dataframe(df)

                # ✅ Download CSV button
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="query_result.csv",
                    mime="text/csv"
                )
            else:
                st.write(response)
        except Exception as e:
            st.write(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
