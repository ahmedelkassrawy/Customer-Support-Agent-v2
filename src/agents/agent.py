import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain.tools import tool
from scrapegraph_py import Client
from config import get_settings
from langchain_tavily import TavilySearch
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langsmith.run_helpers import traceable
from dataclasses import dataclass
from langchain.tools import tool,ToolRuntime
from langgraph.store.memory import InMemoryStore
from datetime import datetime

load_dotenv()

settings = get_settings()
client = Client(api_key= settings.SCRAPEGRAPH_API_KEY)
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                             google_api_key = settings.GOOGLE_API_KEY)

@dataclass
class Context:
    user_name: str

@tool
@traceable
def scraper(website_url:str):
    """Scrapes a website for information useful for product research."""
    response = client.smartscraper(
        website_url=website_url,
        user_prompt="Extract info about the company"
    )

    print(f"Scraper response: {response}")
    return response

# Initialize Tavily search tool
tavily_search_tool = TavilySearch(
    api_key=settings.TAVILY_API_KEY,
    max_results=5,
)

@tool
@traceable
def add_user_preferences(runtime: ToolRuntime[Context]) -> str:
    """Add user preferences to the stored context."""
    user_name = runtime.context.user_name
    messages = runtime.state["messages"]

    # Clear, simple extraction prompt
    system_prompt = "Extract the user's product preferences (budget, use case, brand, etc.) from the following conversation."

    # Merge all messages into a plain text
    chat_text = system_prompt + "\n\n" + "\n".join(
        [f"{m['role'].capitalize()}: {m['content']}" for m in messages if "content" in m]
    )

    # Call Gemini with single text
    preferences = llm.invoke(chat_text)

    # Save to memory
    store = runtime.store
    store.put(("users",), user_name, {"preferences": preferences.content})

    return f"✅ Successfully stored preferences for user '{user_name}'."


@tool
@traceable
def fetch_user_preferences(runtime: ToolRuntime[Context]) -> str:
    """Fetch user preferences from the stored context."""
    user_name = runtime.context.user_name
    
    store = runtime.store
    # InMemoryStore.get() requires namespace and key separately
    user_data = store.get(("users",), user_name)
    
    if user_data:
        return str(user_data.value.get("preferences", "No preferences found"))
    return "No preferences stored for this user"


sys_prompt = """You are an expert product research agent.

You can use these tools:
- **AddUserPreferences**: when the user mentions their preferences (budget, type, brand, use case, etc.)
- **FetchUserPreferences**: when you need to recall previously stored preferences for this user.
- **TavilySearch**: when you need to search the web for product details or pricing.
- **Scraper**: when you need to extract details from a specific product or company website.

Your process:
1. If the user expresses preferences (like "I have $1200 and want a gaming laptop"), call **AddUserPreferences**.
2. If the user doesn't specify new preferences but you need them, call **FetchUserPreferences**.
3. Use **TavilySearch** to gather information about the product category.
4. Optionally use **Scraper** to extract structured info from a specific website.
5. Summarize all findings clearly.

Return a final structured summary in this format:
- User preferences (if any)
- Product summary
- Key features
- Pros & cons
- Recommendation

DO NOT return JSON — use Markdown.
"""

agent = create_agent(model=llm, 
					tools=[scraper, add_user_preferences, tavily_search_tool, fetch_user_preferences],
                    system_prompt = sys_prompt,
                    store = InMemoryStore())


print("Product Research Agent ready. Type 'quit' to exit.")
while True:
    try:
        username = input("Enter your user name: ").strip()
        context = Context(user_name=username)
        query = input("Enter your question: ").strip()
        if query.lower() in ("quit", "exit"):
            break

        config = {"configurable": {"thread_id": "1"}}

        response = agent.invoke({
            "messages": [
                {"role": "system", "content": f"User name: {context.user_name}"},
                {"role": "user", "content": query}
            ]
        },
        config = config,
        context = context)
        output = response.get("output") or response["messages"][-1].content
        print("\n=== Agent Response ===")
        print(output)
        print("======================\n")

    except Exception as e:
        print(f"⚠️ Error: {e}\n")

