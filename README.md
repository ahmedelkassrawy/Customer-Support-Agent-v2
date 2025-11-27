# Customer Support Agent v2

An intelligent AI-powered customer service system built with LangChain, FastAPI, and Celery. This system provides automated customer support for order tracking, complaint management, and FAQ handling with support for escalations.

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Endpoints](#-api-endpoints)
- [Agent Capabilities](#-agent-capabilities)
- [Docker Services](#-docker-services)
- [Development](#-development)

## ✨ Features

### Customer Service Agent
- **AI-Powered Chat Interface**: Natural language understanding using Google Gemini 2.0 Flash
- **Order Tracking**: Real-time order status and delivery information
- **Complaint Management**: Submit, track, and manage customer complaints
- **Automatic Escalation**: Intelligent complaint escalation based on severity
- **FAQ System**: Vector-based retrieval for store policies, hours, and product information
- **Conversation Memory**: Maintains context across interactions with summarization
- **PII Protection**: Detects and blocks sensitive information like API keys

### Backend API
- **RESTful API**: FastAPI-based async API for all operations
- **Database Integration**: PostgreSQL with async SQLAlchemy
- **Task Queue**: Celery for asynchronous task processing
- **Retry Logic**: Automatic retry with exponential backoff
- **Health Checks**: Database and service health monitoring

### Advanced Features
- **LLM Caching**: Semantic caching using Redis Stack (RediSearch)
- **Observability**: Integrated with Langfuse and LangSmith for tracing
- **Batch Processing**: Bulk order checking and report generation
- **Middleware**: PII detection and conversation summarization

## 🏗 Architecture

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  LangChain Agent (Gemini)   │
│  - Tools: Order, Complaint  │
│  - Memory: Conversation     │
│  - Middleware: PII, Summary │
└────────┬────────────────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ Vector Store │ │ Celery   │ │  FastAPI     │
│ (FAQ System) │ │ Tasks    │ │  Backend     │
└──────────────┘ └────┬─────┘ └──────┬───────┘
                      │               │
                      ▼               ▼
                ┌──────────┐   ┌─────────────┐
                │  Redis   │   │  PostgreSQL │
                │  Stack   │   │  Database   │
                └──────────┘   └─────────────┘
```

## 🛠 Tech Stack

### Core Framework
- **LangChain**: Agent orchestration and tool calling
- **LangGraph**: Stateful agent workflows
- **Google Gemini 2.0**: LLM for natural language understanding

### Backend
- **FastAPI**: High-performance async web framework
- **SQLAlchemy**: ORM with async support
- **PostgreSQL**: Primary database with pgvector extension
- **Celery**: Distributed task queue
- **Redis Stack**: Message broker + semantic caching (RediSearch)

### AI/ML
- **HuggingFace Transformers**: Embeddings (sentence-transformers/all-mpnet-base-v2)
- **Langfuse**: LLM observability and tracing
- **LangSmith**: Debugging and monitoring

### Additional Tools
- **Tavily**: Web search integration
- **ScrapegraphAI**: Website scraping for product research

## 📁 Project Structure

```
customer/
├── src/
│   ├── agents/
│   │   ├── conversation.py      # Main customer service agent
│   │   └── agent.py             # Product research agent
│   ├── backend/
│   │   ├── api.py               # FastAPI application
│   │   ├── trial.py             # Legacy sync API
│   │   ├── memory/
│   │   │   ├── base.py          # Database configuration
│   │   │   ├── complaints.py    # Complaint model
│   │   │   ├── order.py         # Order model
│   │   │   └── escalation.py    # Escalation model
│   │   └── celery/
│   │       ├── celery_app.py    # Celery configuration
│   │       └── tasks.py         # Async tasks (complaints, orders, escalations)
│   └── data/
│       └── store_qa.csv         # FAQ knowledge base
├── config.py                     # Settings management
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Multi-container orchestration
├── Dockerfile                    # Container definition
├── .env.example                  # Environment template
└── README.md                     # This file
```

## 🚀 Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### Quick Start with Docker

1. **Clone the repository**
```bash
git clone https://github.com/ahmedelkassrawy/Customer-Support-Agent-v2.git
cd Customer-Support-Agent-v2
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Start all services**
```bash
docker compose up -d
```

4. **Verify services are running**
```bash
docker compose ps
```

### Local Development Setup

1. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Start infrastructure services**
```bash
docker compose up -d postgres redis
```

4. **Run the agent**
```bash
python src/agents/conversation.py
```

## ⚙ Configuration

### Required API Keys (in `.env`)

```bash
# AI/LLM Services
GOOGLE_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_key
COHERE_API_KEY=your_cohere_key
SCRAPEGRAPH_API_KEY=your_scrapegraph_key
TAVILY_API_KEY=your_tavily_key

# Observability
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=customer-support

LANGFUSE_SECRET_KEY=your_langfuse_secret
LANGFUSE_PUBLIC_KEY=your_langfuse_public
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Infrastructure
DATABASE_URL=postgresql+psycopg://kassra:admin@postgres:5432/customer
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
API_BASE_URL=http://localhost:8000
```

## Usage

### Running the Customer Service Agent

```bash
python src/agents/conversation.py
```

**Example Interaction:**
```
Customer Service Agent Ready.
Enter your name: John

You: Track my order ORD123
=== Assistant ===
📦 **Order Status:**
Order ID: ORD123
Status: Shipped
Estimated Delivery: 2025-07-20
=================

You: I want to file a complaint about a damaged item
=== Assistant ===
Please provide Order ID: ORD123
Please provide Complaint Reason: Item arrived damaged

✅ Complaint submitted successfully!
Complaint ID: abc-123-def
Order ID: ORD123
Issue: Item arrived damaged
=================
```

### Running the Product Research Agent

```bash
python src/agents/agent.py
```

### Using the API Directly

```bash
# Check order status
curl http://localhost:8000/orders/ORD123

# Create a complaint
curl -X POST http://localhost:8000/complaints \
  -H "Content-Type: application/json" \
  -d '{
    "id": "CMP001",
    "order_id": "ORD123",
    "issue": "Product damaged"
  }'

# Escalate complaint
curl -X POST http://localhost:8000/escalations \
  -H "Content-Type: application/json" \
  -d '{"complaint_id": "CMP001"}'
```

## API Endpoints

### Orders
- `GET /orders/{order_id}` - Get order status and delivery info

### Complaints
- `POST /complaints` - Create a new complaint
- `GET /complaints/{complaint_id}` - Get complaint details
- `GET /complaints/check_by_order/{order_id}` - Check if complaint exists for order
- `GET /complaints/check_by_id/{complaint_id}` - Check complaint existence

### Escalations
- `POST /escalations` - Escalate a complaint

## Agent Capabilities

### Tools Available

1. **retrieve_context**: Search FAQ database for store information
2. **order_track**: Track order status and delivery
3. **complaint**: File a new complaint
4. **check_complaint_status**: Check existing complaint status
5. **escalate**: Escalate complaint to senior support

### Middleware Features

- **Summarization**: Automatically summarizes long conversations
- **PII Detection**: Blocks API keys and sensitive information
- **Context Management**: Maintains user state across conversations

## 🐳 Docker Services

### Services Overview

| Service | Port | Description |
|---------|------|-------------|
| **api** | 8000 | FastAPI backend application |
| **mcp** | 8001 | MCP server interface |
| **postgres** | 6024 | PostgreSQL database with pgvector |
| **redis** | 6379 | Redis Stack (includes RediSearch) |
| **celery_worker** | - | Background task processor |

### Service Management

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Restart a service
docker compose restart api

# Stop all services
docker compose down

# Remove volumes (clean slate)
docker compose down -v
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Celery Task Management

```bash
# Monitor tasks
celery -A src.backend.celery.celery_app inspect active

# Purge all tasks
celery -A src.backend.celery.celery_app purge
```

### Adding New Tools

1. Define tool in `src/agents/conversation.py`:
```python
@tool
@traceable
def my_new_tool(runtime: ToolRuntime[Context]) -> str:
    """Tool description for the LLM"""
    # Implementation
    return "Result"
```

2. Add to agent tools list:
```python
agent = create_agent(
    tools=[..., my_new_tool],
    ...
)
```

### Environment Variables

See `.env.example` for all configuration options. Key settings:

- `CELERY_TASK_MAX_RETRIES`: Number of retry attempts (default: 3)
- `CELERY_TASK_RETRY_DELAY`: Delay between retries in seconds (default: 5)
- `FAQ_DATA_PATH`: Path to FAQ CSV file
- `DATABASE_URL`: PostgreSQL connection string

## 📊 Observability

### Langfuse Dashboard
- Monitor LLM calls and costs
- Trace agent decision-making
- View conversation flows

### LangSmith
- Debug agent behavior
- Track tool usage
- Performance metrics

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 👤 Author

**Ahmed Elkassrawy**
- GitHub: [@ahmedelkassrawy](https://github.com/ahmedelkassrawy)

## 🙏 Acknowledgments

- LangChain for the agent framework
- Google for Gemini API
- FastAPI team for the excellent web framework
- Celery for task queue management

---

**Note**: This is an educational project demonstrating AI agent capabilities. For production use, implement proper security, error handling, and monitoring.
