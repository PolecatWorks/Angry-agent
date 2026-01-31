import unittest
from unittest.mock import MagicMock
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from agent import create_agent

class TestAgent(unittest.IsolatedAsyncioTestCase):
    async def test_echo_agent(self):
        # Use MemorySaver for testing
        checkpointer = MemorySaver()
        agent = create_agent(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": "1"}}
        input_msg = HumanMessage(content="Hello")

        # Invoke
        result = await agent.ainvoke({"messages": [input_msg]}, config=config)

        # Verify output
        messages = result["messages"]
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertIsInstance(messages[1], AIMessage)
        self.assertEqual(messages[1].content, "Echo: Hello")

        # Verify memory (resume)
        input_msg_2 = HumanMessage(content="World")
        result_2 = await agent.ainvoke({"messages": [input_msg_2]}, config=config)

        messages_2 = result_2["messages"]
        # Should have 4 messages now: Hello, Echo Hello, World, Echo World
        self.assertEqual(len(messages_2), 4)
        self.assertEqual(messages_2[3].content, "Echo: World")

if __name__ == '__main__':
    unittest.main()
