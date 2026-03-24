import asyncio
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
import os

async def main():
    # Use the DSN from the project or assume default
    dsn = "postgresql://postgres:mysecretpassword@localhost:5432/agentdb"
    
    pool_kwargs = {
        "prepare_threshold": 0,
        "row_factory": dict_row,
    }

    async with AsyncConnectionPool(
        conninfo=dsn, 
        max_size=5, 
        kwargs=pool_kwargs,
        check=AsyncConnectionPool.check_connection
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        
        thread_id = '44121d38-cf62-466d-b606-e672eb8b25c0'
        config = {"configurable": {"thread_id": thread_id}}
        
        state = await checkpointer.aget(config)
        
        if not state:
            print(f"No state found for thread {thread_id}")
            return
            
        print("\n--- Checkpoint Found ---")
        
        values = state.get('values', {})
        messages = values.get('messages', [])
        
        print(f"\n--- Messages ({len(messages)}) ---")
        for i, m in enumerate(messages):
            m_type = type(m).__name__
            content = getattr(m, 'content', str(m))
            print(f"{i}: {m_type} - {content[:100]}...")
            if hasattr(m, 'additional_kwargs') and m.additional_kwargs:
                print(f"   kwargs: {m.additional_kwargs}")

if __name__ == "__main__":
    asyncio.run(main())
