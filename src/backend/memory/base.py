from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Load environment variables
load_dotenv()

from config import get_settings

settings = get_settings()

DATABASE_URL = settings.DATABASE_URL

ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql+asyncpg://")

# Create async engine
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)

# Create sync engine for metadata operations
sync_engine = create_engine(DATABASE_URL)

Base = declarative_base()

def get_db_connection():
    return sync_engine.connect()