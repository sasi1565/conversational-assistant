from langchain.tools.render import render_text_description
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
import json

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///shopping_assistant.db', echo=False)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(128))
    email = Column(String(100))
    chats = relationship('Chat', back_populates='user')

class Chat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    chat_name = Column(String(100))
    timestamp = Column(DateTime, default=datetime.now)
    messages = Column(Text)
    user = relationship('User', back_populates='chats')

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Load environment variables
load_dotenv()

# --- Tools ---

@tool
def search_products(query: str) -> str:
    """Searches for products based on the user queries."""
    search = TavilySearchResults(max_results=20,include_domains=["www.91mobiles.com","www.flipkart.com","www.amazon.in","www.gsmarena.com","www.gadgets360.com"])
    returned_results = search.invoke({"query": query})
    return str(returned_results)
@tool
def compare_prices(product_name: str) -> str:
    """Compares prices of a product across different websites and provides links."""
    try:
        from serpapi import GoogleSearch
        params = {
            "engine": "google_shopping",
            "q": product_name,
            "api_key": os.getenv("SERPAPI_API_KEY"),
            "gl": "in",
            "domain": "google.co.in",
            "hl": "en",
            "num": "10"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        if "shopping_results" in results:
            comparison_info = []
            for item in results["shopping_results"][:5]:
                comparison_info.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "source": item.get("source"),
                    "price": item.get("price"),
                })
            formatted_output = "Price Comparison:\n"
            for item in comparison_info:
                formatted_output += f"- {item['source']}: {item['price']} - [Link]({item['link']})\n"
            return formatted_output
        else:
            return "Could not find price comparisons for the specified product."
    except Exception as e:
         return f"Error during price comparison: {e}"

# --- Tavily Tool ---
@tool
def general_shopping_search(query: str) -> str:
    """Searches for general shopping information using Tavily like more information about the product or popularity trends or other general queries ."""
    try:
        search = TavilySearchResults(tavily_api_key=os.getenv("TAVILY_API_KEY"),results = 15)
        results = search.invoke({"query": query})
        return str(results)
    except Exception as e:
        return f"Error during Tavily search: {e}"
# --- Agent Setup ---
def setup_agent(chat_history=None):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"), convert_system_message_to_human=True)

    tools = [search_products, compare_prices, general_shopping_search]

    template = """You are a helpful shopping assistant. Your goal is to help users find products, compare prices, provide detailed product information (including links), and guide them through the purchase process. You can also answer general shopping-related questions.
     
    And also ask for the user's preferences and provide the best product according to the user's preferences.

    Include icons along with the products for better user experience.

    Always be polite and friendly. If the user asks for something outside of your capabilities, politely explain that you cannot perform that task.

    Use the available tools to fulfill the user's requests. Prioritize providing accurate and up-to-date information.  When comparing prices, ALWAYS include links to the product pages. When listing products, ALWAYS include a link, price, and source.

    Important:
    - You shouldn't answer to these type of questions:
        "What is 2+2", "What is the capital of India", "What is the weather today", etc. 
    - When ever the user ask for comparison of products, you should provide indetailed comparision of the products.
    - when ever you are suggesting some products, you should give description of the product with the information you have from the tools.

    TOOLS:
    ------

    You have access to the following tools:

    {tools}

    To use a tool, please use the following format:

    ```
    Thought: Do I need to use a tool? Yes
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ```

    When you have a final response to say to the Human, or if you do not need to use a tool, you MUST use the format:

    ```
    Thought: Do I need to use a tool? No
    Final Answer: [your response here]
    ```

    Begin!

    Previous conversation history:
    {chat_history1}

    New input: {input}
    {agent_scratchpad}
    """

    prompt = PromptTemplate.from_template(template)
    prompt = prompt.partial(
        tools=render_text_description(tools),
        tool_names=", ".join([t.name for t in tools]),
    )

    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            MessagesPlaceholder(variable_name="chat_history1"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    memory = ConversationBufferMemory(memory_key="chat_history1", return_messages=True)
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                memory.chat_memory.add_user_message(msg["content"])
            elif msg["role"] == "assistant":
                memory.chat_memory.add_ai_message(msg["content"])
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, memory=memory, handle_parsing_errors=True
    )
    return agent_executor

# from langchain.tools.render import render_text_description

# # --- Agent Execution (for testing outside Streamlit) ---
# if __name__ == "__main__":
#     agent_executor = setup_agent()
#     response = agent_executor.invoke({"input": "I want to buy a new gaming laptop."})
#     print(response["output"])

#     response = agent_executor.invoke({"input": "Can you compare prices for the Razer Blade 15?"})
#     print(response["output"])

#     response = agent_executor.invoke({"input": "What are the latest trends in gaming laptops?"})
#     print(response["output"])

#     response = agent_executor.invoke({"input": "Tell me more about the ASUS ROG Zephyrus G14."})
#     print(response["output"])