import asyncio
from src.database import init_db_pool, get_db_pool
from src.config import ServiceConfig
from src.agent.handler import LLMHandler
import logging

# Set logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def main():
    config = ServiceConfig()
    try:
        pool = await init_db_pool(config.persistence.db)
        handler = LLMHandler(db_dsn=config.persistence.db.connection.dsn)
        await handler.initialize()
        
        thread_id = '44121d38-cf62-466d-b606-e672eb8b25c0'
        state = await handler.get_thread_state(thread_id)
        
        print("\n--- Agent State Values ---")
        print(state.values)
        print("\n--- Agent State Next Node ---")
        print(state.next)
        
        await handler.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
