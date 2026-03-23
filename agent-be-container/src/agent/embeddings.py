import logging

logger = logging.getLogger(__name__)

def get_embeddings_model(config):
    """Factory function to initialize the embedding model based on configuration."""
    model_provider = config.model_provider

    if model_provider == "google_genai":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        logger.info(f"Initializing GoogleGenerativeAIEmbeddings with model: {config.model}")
        return GoogleGenerativeAIEmbeddings(
            model=config.model,
            google_api_key=config.google_api_key.get_secret_value()
        )
    else:
        raise ValueError(f"Unsupported embedding model provider: {model_provider}")
