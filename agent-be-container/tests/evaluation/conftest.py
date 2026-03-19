import os
import pytest
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_google_genai import ChatGoogleGenerativeAI

class GeminiJudge(DeepEvalBaseLLM):
    def __init__(self):
        # Use gemini-1.5-pro for best reasoning/evaluation
        self._model = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
        super().__init__()

    def load_model(self):
        return self._model

    def generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        response = chat_model.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        response = await chat_model.ainvoke(prompt)
        return response.content

    def get_model_name(self):
        return "Google Gemini 1.5 Pro"

@pytest.fixture(scope="session")
def gemini_judge():
    return GeminiJudge()
