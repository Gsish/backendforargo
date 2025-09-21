from langchain_groq import ChatGroq
import psycopg2
import chromadb
from langchain.vectorstores import Chroma
from langchain.tools import tool
from langchain.agents import initialize_agent
from langchain.prompts import ChatPromptTemplate
from datapipline.vectorization import BAAIBGEEmbeddings 
embedding_fn = BAAIBGEEmbeddings() 


client = chromadb.CloudClient(
  api_key='ck-8zuWUKiU2u54CvB8TfzKA5n9GA7p3Rv3guHSa4sVYut1',
  tenant='55d1436a-2863-493d-8be4-66db67963ad7',
  database='metadataforargo'
)


# Use embed_documents for Chroma
vectorstore = Chroma(
    client=client,
    collection_name="my_collection",
    embedding_function=embedding_fn
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a PostgreSQL query generator. Only output valid SQL queries."),
        ("user", "Using the following retrieved context:\n{context}\nAnswer the following question: {query}")
    ]
)

# Tool to execute SQL queries
@tool
def queryexecutiontool(sqlquery: str) -> str:
    """Execute SQL query and return results"""
    cursor = client.cursor()
    try:
        cursor.execute(sqlquery)
        result = cursor.fetchall()
        return str(result)
    except Exception as e:
        return f"Error executing query: {e}"

# LLM setup
llm = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0,
    api_key="your_groq_api_key_here"
)

# Initialize agent
agent = initialize_agent(
    tools=[queryexecutiontool],
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True,
)

# User query
def runcode(query:str):

# Retrieve context from Chroma
    docs = retriever.get_relevant_documents(query)
    context = "\n".join([doc.page_content for doc in docs])

# Format the prompt
    messages = prompt.format_prompt(context=context, query=query).to_messages()

# Run agent using the last user message content
    result = agent.run(messages[-1].content)
    return result

