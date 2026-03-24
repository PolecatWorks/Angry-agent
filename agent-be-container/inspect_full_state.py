import asyncio
import os

# Set dummy environment variables to pass validation
os.environ["APP_MAIN_AICLIENT__CONTEXT_LENGTH"] = "8192"
os.environ["APP_MAIN_AICLIENT__GOOGLE_API_KEY"] = "dummy"
os.environ["APP_PACKAGER_AICLIENT__CONTEXT_LENGTH"] = "8192"
os.environ["APP_PACKAGER_AICLIENT__GOOGLE_API_KEY"] = "dummy"
os.environ["APP_EMBEDDING_CLIENT__MODEL_PROVIDER"] = "google_genai"
os.environ["APP_EMBEDDING_CLIENT__MODEL"] = "text-embedding-004"
os.environ["APP_EMBEDDING_CLIENT__GOOGLE_API_KEY"] = "dummy"
os.environ["APP_HAMS__URL"] = "http://localhost:8079"
os.environ["APP_WEBSERVICE__URL"] = "http://localhost:8080"
os.environ["APP_PERSISTENCE__DB__POOL_SIZE"] = "10"
os.environ["APP_PERSISTENCE__DB__AUTOMIGRATE"] = "false"
os.environ["APP_PERSISTENCE__DB__ACQUIRE_TIMEOUT"] = "10"
os.environ["APP_PERSISTENCE__DB__CONNECTION__URL"] = "postgresql://localhost:5432/agentdb"
os.environ["APP_PERSISTENCE__DB__CONNECTION__USERNAME"] = "postgres"
os.environ["APP_PERSISTENCE__DB__CONNECTION__PASSWORD"] = "mysecretpassword"


from src.agent.handler import LLMHandler
from src.config import ServiceConfig
from langchain_core.messages import HumanMessage
import logging

# Set logging to see what's happening
logging.basicConfig(level=logging.INFO)

async def main():
    config = ServiceConfig()
    try:
        handler = LLMHandler(db_dsn=config.persistence.db.connection.dsn)
        await handler.initialize()
        
        thread_id = '44121d38-cf62-466d-b606-e672eb8b25c0'
        state = await handler.get_thread_state(thread_id)
        
        print("\n--- Agent State Values ---")
        if state and state.values:
            messages = state.values.get("messages", [])
            print(f"Messages count: {len(messages)}")
            for i, m in enumerate(messages):
                print(f"{i}: {type(m).__name__} | {m.content[:50]}")
        else:
            print("No state values found.")
            
        print("\n--- Agent State Next Node ---")
        print(state.next if state else "None")
        
        await handler.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
