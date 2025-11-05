import sys
import os
import uuid
import requests
import warnings
from pathlib import Path

# Suppress specific warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*pynvml.*")

# Add parent directories to path first
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "celery"))

from dotenv import load_dotenv

# === Load Environment Variables FIRST ===
load_dotenv()

from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langsmith.run_helpers import traceable
from config import get_settings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from typing import Optional,Annotated
from langchain.agents.middleware import PIIMiddleware

# Import Celery tasks
try:
    from backend.celery.tasks import (
        check_complaint_by_id,
        check_complaint_by_order,
        create_complaint,
        get_complaint_details,
        get_order_status,
        escalate_complaint as escalate_complaint_task
    )
    CELERY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Warning: Celery tasks not available: {e}")
    CELERY_AVAILABLE = False

# === Environment Setup ===
FAQ_DATA_PATH_RAW = os.getenv("FAQ_DATA_PATH", "src/data/store_qa.csv")

# Build absolute path for FAQ data
if os.path.isabs(FAQ_DATA_PATH_RAW):
    FAQ_DATA_PATH = FAQ_DATA_PATH_RAW
else:
    # Relative to project root (parent of parent of this file)
    FAQ_DATA_PATH = str(Path(__file__).parent.parent.parent / FAQ_DATA_PATH_RAW)

checkpointer = MemorySaver()
checkpointer = InMemorySaver()
store = InMemoryStore()
settings = get_settings()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=settings.GOOGLE_API_KEY)
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001",
                                          google_api_key=settings.GOOGLE_API_KEY)

# === Context ===
@dataclass
class Context:
    user_name: str
    order_id: str = None
    complaint_id: str = None
    complaint_reason : Optional[str] = None


# === Tools ===
"""Answer general store-related questions using the FAQ system."""
vector_store = InMemoryVectorStore(embeddings)

loader = CSVLoader(file_path = FAQ_DATA_PATH)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
chunk_size=500,  # chunk size (characters)
chunk_overlap=200,  # chunk overlap (characters)
add_start_index=True,  # track index in original document
)
all_splits = text_splitter.split_documents(docs)

document_ids = vector_store.add_documents(documents=all_splits)

@tool(response_format="content_and_artifact")
@traceable
def retrieve_context(query: str):
    """Retrieve information to help answer a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


@tool
@traceable
def complaint(runtime: ToolRuntime[Context]) -> str:
    """Submit a complaint related to an order."""
    ctx = runtime.context
    if not ctx.order_id:
        ctx.order_id = input("Please provide Order ID: ").strip() or "ORD123"

    # Check if complaint already exists for this order using Celery
    if CELERY_AVAILABLE:
        try:
            result = check_complaint_by_order.delay(ctx.order_id)
            data = result.get(timeout=10)  # Wait up to 10 seconds for result
            
            if data.get("exists"):
                ctx.complaint_id = data['complaint_id']  # Store existing complaint ID
                return f"⚠️ A complaint already exists for order {ctx.order_id}:\n" \
                       f"Complaint ID: {data['complaint_id']}\n" \
                       f"Issue: {data['issue']}\n" \
                       f"Escalation Status: {data['escalation_status']}"
        except Exception as e:
            print(f"Warning: Celery task failed, falling back to direct API: {e}")

    if not ctx.complaint_reason:
        ctx.complaint_reason = input("Please provide Complaint Reason: ").strip() or "General Issue"

    ctx.complaint_id = str(uuid.uuid4())

    # Create complaint using Celery
    if CELERY_AVAILABLE:
        try:
            result = create_complaint.delay(ctx.complaint_id, ctx.order_id, ctx.complaint_reason)
            response_data = result.get(timeout=10)
            
            if "error" in response_data:
                if response_data.get("status_code") == 400:
                    return f"⚠️ Complaint already exists for this order."
                elif response_data.get("status_code") == 404:
                    return f"❌ Order {ctx.order_id} not found in the system."
                else:
                    return f"❌ Failed to submit complaint: {response_data['error']}"
            
            return f"✅ Complaint submitted successfully!\n" \
                   f"Complaint ID: {ctx.complaint_id}\n" \
                   f"Order ID: {ctx.order_id}\n" \
                   f"Issue: {ctx.complaint_reason}"
        except Exception as e:
            return f"⚠️ Error processing complaint via Celery: {e}"
    else:
        # Fallback to direct API call
        payload = {"id": ctx.complaint_id, 
                   "order_id": ctx.order_id, 
                   "issue": ctx.complaint_reason}
        try:
            response = requests.post("http://localhost:8000/complaints", json=payload, timeout=5)
            if response.status_code == 200:
                return f"✅ Complaint submitted successfully (ID: {ctx.complaint_id})."
            return f"❌ Failed to submit complaint: {response.status_code}"
        except Exception as e:
            return f"⚠️ Error connecting to complaint system: {e}"

@tool
@traceable
def check_complaint_status(runtime: ToolRuntime[Context]) -> str:
    """Check the status of an existing complaint."""
    ctx = runtime.context
    if not ctx.complaint_id:
        ctx.complaint_id = input("Enter your Complaint ID: ").strip() or "CMP123"

    # Use Celery task if available
    if CELERY_AVAILABLE:
        try:
            result = check_complaint_by_id.delay(ctx.complaint_id)
            data = result.get(timeout=10)
            
            if data.get("exists"):
                return f"📝 **Complaint Details:**\n" \
                       f"Complaint ID: {data['complaint_id']}\n" \
                       f"Issue: {data['issue']}\n" \
                       f"Escalation Status: {data['escalation_status']}"
            else:
                return f"❌ Complaint {ctx.complaint_id} not found in the system."
        except Exception as e:
            return f"⚠️ Error checking complaint via Celery: {e}"
    else:
        # Fallback to direct API call
        try:
            url = f"http://localhost:8000/complaints/check_by_id/{ctx.complaint_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return f"📝 Complaint Details: {response.json()}"
            return f"Complaint not found (Status: {response.status_code})"
        except Exception as e:
            return f"Error connecting to complaint system: {e}"

@tool
@traceable
def order_track(runtime: ToolRuntime[Context]) -> str:
    """Track the status of an order."""
    ctx = runtime.context
    if not ctx.order_id:
        ctx.order_id = input("Enter your Order ID: ").strip() or "ORD123"

    # Use Celery task if available
    if CELERY_AVAILABLE:
        try:
            result = get_order_status.delay(ctx.order_id)
            data = result.get(timeout=10)
            
            if "error" in data:
                if data.get("status_code") == 404:
                    return f"❌ Order {ctx.order_id} not found in the system."
                else:
                    return f"❌ Error tracking order: {data['error']}"
            
            return f"📦 **Order Status:**\n" \
                   f"Order ID: {data['order_id']}\n" \
                   f"Status: {data['status']}\n" \
                   f"Estimated Delivery: {data['estimated_delivery']}"
        except Exception as e:
            return f"⚠️ Error tracking order via Celery: {e}"
    else:
        # Fallback to direct API call
        try:
            url = f"http://localhost:8000/orders/{ctx.order_id}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return f"📦 Order Status: {response.json()}"
            return f"Order not found (Status: {response.status_code})"
        except Exception as e:
            return f"Error connecting to tracking system: {e}"


@tool
@traceable
def escalate(runtime: ToolRuntime[Context]) -> str:
    """Escalate an existing complaint."""
    ctx = runtime.context
    
    if not ctx.complaint_id:
        return "⚠️ No complaint found. Please file a complaint first before requesting escalation."

    # Use Celery task if available
    if CELERY_AVAILABLE:
        try:
            result = escalate_complaint_task.delay(ctx.complaint_id)
            response_data = result.get(timeout=10)
            
            if "error" in response_data:
                if response_data.get("status_code") == 404:
                    return f"❌ Complaint ID {ctx.complaint_id} not found in the system."
                else:
                    return f"❌ Escalation failed: {response_data['error']}"
            
            escalation_id = response_data.get("escalation_id", "")
            return f"✅ Complaint {ctx.complaint_id} has been escalated successfully!\n" \
                   f"Escalation ID: {escalation_id}\n" \
                   f"A senior support team member will review it shortly."
        except Exception as e:
            return f"⚠️ Error escalating complaint via Celery: {e}"
    else:
        # Fallback to direct API call
        payload = {"complaint_id": ctx.complaint_id}
        try:
            response = requests.post("http://localhost:8000/escalations", json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                escalation_id = result.get("escalation_id", "")
                return f"✅ Complaint {ctx.complaint_id} has been escalated successfully (Escalation ID: {escalation_id})! A senior support team member will review it shortly."
            elif response.status_code == 404:
                return f"❌ Complaint ID {ctx.complaint_id} not found in the system. The complaint may have been processed already."
            else:
                error_detail = response.text if response.text else "No error details provided"
                return f"❌ Escalation failed (Status {response.status_code}). Details: {error_detail}"
                
        except requests.exceptions.ConnectionError:
            return f"⚠️ Unable to connect to the escalation system. The service may be offline. Complaint ID for reference: {ctx.complaint_id}"
        except requests.exceptions.Timeout:
            return f"⚠️ The escalation request timed out. Please try again. Complaint ID: {ctx.complaint_id}"
        except Exception as e:
            return f"⚠️ Error during escalation: {str(e)}. Complaint ID: {ctx.complaint_id}"




# === System Prompt ===
sys_prompt = """You are a helpful **Customer Service Agent** for our store.

You have access to a tool that retrieves context from a blog post. Use the tool to help answer user queries.

**IMPORTANT INSTRUCTIONS:**
1. For general questions about the store (hours, policies, products, payments, discounts, etc.), ALWAYS use the **faq** tool first.
2. For document-specific questions (user uploads their own PDF/CSV/TXT), use the **rag** tool.
3. For order tracking, use **order_track**.
4. For complaints, use **complaint**.
5. For escalations, use **escalate**.
6. For conversation summary, use **summarizer**.

**When a user asks a question, analyze it and use the appropriate tool immediately.**

Always provide clear, helpful, and friendly responses based on the tool's output.
"""


# === Agent Creation ===
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=[retrieve_context, complaint, order_track, escalate, check_complaint_status],
    system_prompt=sys_prompt,
    store=store,
    middleware=[
        SummarizationMiddleware(
            model = llm,
            max_tokens_before_summary = 4000,
            messages_to_keep = 10
        ),
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
            apply_to_input=True,
        ),
    ],
    checkpointer = checkpointer
)


# === Main Loop ===
def run_customer_agent():
    print("🤖 Customer Service Agent Ready.")
    print("Type 'exit' or 'quit' to stop.\n")

    username = input("Enter your name: ").strip() or "guest"
    
    # Create context once and reuse it to maintain state across interactions
    context = Context(user_name=username)
    thread_id = f"thread_{username}_{uuid.uuid4()}"

    while True:
        try:
            query = input("You: ").strip()
            if query.lower() in ("exit", "quit"):
                print("👋 Goodbye!")
                break

            config = {"configurable": {"thread_id": thread_id}}
            response = agent.invoke(
                {
                    "messages": [
                        {"role": "system", "content": f"User: {context.user_name}"},
                        {"role": "user", "content": query},
                    ]
                },
                config=config,
                context=context
            )

            output = response.get("output") or response["messages"][-1].content
            print("\n=== Assistant ===")
            print(output)
            print("=================\n")

        except Exception as e:
            print(f"⚠️ Error: {e}\n")


if __name__ == "__main__":
    run_customer_agent()

