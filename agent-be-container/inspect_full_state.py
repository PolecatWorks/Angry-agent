import asyncio
import os

# Set dummy environment variables to pass validation
os.environ["APP_MAIN_AICLIENT__CONTEXT_LENGTH"] = "8192"
os.environ["APP_MAIN_AICLIENT__MODEL_PROVIDER"] = "google_genai"
os.environ["APP_MAIN_AICLIENT__GOOGLE_API_KEY"] = "dummy"
os.environ["APP_PACKAGER_AICLIENT__CONTEXT_LENGTH"] = "8192"
os.environ["APP_PACKAGER_AICLIENT__MODEL_PROVIDER"] = "google_genai"
os.environ["APP_PACKAGER_AICLIENT__GOOGLE_API_KEY"] = "dummy"
os.environ["APP_EMBEDDING_CLIENT__MODEL_PROVIDER"] = "google_genai"
os.environ["APP_EMBEDDING_CLIENT__MODEL"] = "text-embedding-004"
os.environ["APP_EMBEDDING_CLIENT__GOOGLE_API_KEY"] = "dummy"
os.environ["APP_HAMS__URL"] = "http://localhost:8079"
os.environ["APP_WEBSERVICE__URL"] = "http://localhost:8080"
os.environ["APP_WEBSERVICE__PREFIX"] = ""
os.environ["APP_HAMS__PREFIX"] = "hams"
os.environ["APP_HAMS__SHUTDOWNDURATION"] = "PT10S"
os.environ["APP_HAMS__CHECKS__TIMEOUT"] = "5"
os.environ["APP_HAMS__CHECKS__FAILS"] = "2"
os.environ["APP_HAMS__CHECKS__PREFLIGHTS"] = "[]"
os.environ["APP_HAMS__CHECKS__SHUTDOWNS"] = "[]"
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
        
        thread_id = '2da8ca03-a664-4108-b1d6-6d9b7c63caa3'
        state = await handler.get_thread_state(thread_id)
        
        print("\n--- Agent State Values ---")
        if state and state.values:
            messages = state.values.get("messages", [])
            print(f"Messages count: {len(messages)}")
            for i, m in enumerate(messages):
                print(f"{i}: {type(m).__name__}")
                print(f"  Content: {repr(m.content)}")
                if hasattr(m, 'additional_kwargs') and m.additional_kwargs:
                    print(f"  Kwargs: {m.additional_kwargs.keys()}")
                if hasattr(m, 'tool_calls') and m.tool_calls:
                    print(f"  ToolCalls: {len(m.tool_calls)}")
        else:
            print("No state values found.")
            
        print("\n--- Agent State Next Node ---")
        print(state.next if state else "None")
        
        await handler.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
