from .tool import ToolBoxConfig, ToolConfig
from pydantic import ConfigDict, Field, BaseModel, SecretStr, field_validator, HttpUrl
from pathlib import Path
from typing import (
    Any,
    Self,
    Type,
    Tuple,
    Literal,
    Union,
    Annotated,
)
from datetime import timedelta
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
    NestedSecretsSettingsSource,
    SettingsConfigDict,
)
from ..hams.config import HamsConfig

import os


class DbConnectionConfig(BaseModel):
    url: str = Field(description="Base Postgres URL without credentials")
    username: str = Field(description="Database username")
    password: SecretStr = Field(description="Database password")

    @property
    def dsn(self) -> str:
        base_url = self.url.replace("postgresql://", "").replace("postgres://", "")
        return f"postgresql://{self.username}:{self.password.get_secret_value()}@{base_url}"


class DbOptionsConfig(BaseModel):
    pool_size: int = Field(description="Max size of the asyncpg pool")
    automigrate: bool = Field(description="Whether to run migrations on startup")
    acquire_timeout: int = Field(description="Pool acquire timeout in seconds")
    connection: DbConnectionConfig


class PersistenceConfig(BaseModel):
    db: DbOptionsConfig


class WebServerConfig(BaseModel):
    """
    Configuration for the web server
    """

    url: HttpUrl = Field(description="Host to listen on")
    prefix: str = Field(default="", description="Prefix for the name of the resources")


# Define a timing object to capture time between event processing
# Keeping this generic event config as it might be useful
class EventConfig(BaseModel):
    """
    Process costs for a given events
    """

    maxChunks: int = Field(default=10, description="Max number of chunks that can be processed after which cannot take more load")
    chunkDuration: timedelta = Field(default=timedelta(seconds=1), description="Duration of events")
    checkTime: timedelta = Field(default=timedelta(seconds=5), description="Time between checking for new events")


class AIPromptConfig(BaseModel):
    text: str = Field(
        description="The text of the AI prompt",
    )


class MyAiConfig(BaseModel):
    """
    Configuration for the MyAI bot
    """

    system_instruction: list[AIPromptConfig] = Field(
        default=[],
        description="List of system instructions for the bot",
    )

    toolbox: ToolBoxConfig = Field(
        default_factory=lambda: ToolBoxConfig(tools=[], max_concurrent=5, mcps=[]),
        description="Default configuration for tool execution, including limits and enabled status",
    )


class BaseAiClientConfig(BaseModel):
    """
    Common configuration for all AI client providers
    """
    httpx_verify_ssl: str | bool = Field(
        default=True,
        description="Whether to verify SSL certificates for HTTP requests, can be a boolean or a path to a CA bundle",
    )
    model: str = Field(default="gemini-1.5-flash-latest", description="The model to use (e.g., 'gemini-1.5-flash-latest' or GitHub model name)")
    temperature: float = Field(
        default=0.7,
        description="Temperature for the model, controlling randomness in responses",
    )
    context_length: int = Field(description="Maximum context length for the model")
    stop_sequences: list[str] = Field(default_factory=list, description="List of sequences that will stop generation")
    timeout: int = Field(default=60, description="Timeout in seconds for model API calls")
    streaming: bool = Field(default=True, description="Whether to stream responses from the model")
    system_prompt: str | None = Field(default=None, description="System prompt for the model")

    model_config = ConfigDict(extra="forbid")


class AzureOpenAIConfig(BaseAiClientConfig):
    model_provider: Literal["azure_openai"] = Field(default="azure_openai", description="Azure OpenAI provider")
    azure_endpoint: HttpUrl = Field(description="Azure OpenAI endpoint for LangChain")
    azure_api_key: SecretStr = Field(description="API key for Azure OpenAI access")
    azure_deployment: str = Field(description="Azure OpenAI deployment name for LangChain")
    azure_api_version: str | None = Field(
        default=None,
        description="API version for Azure OpenAI, default is None",
    )


class GitHubConfig(BaseAiClientConfig):
    model_provider: Literal["github"] = Field(default="github", description="GitHub-hosted model provider")
    github_model_repo: str = Field(
        description="GitHub repository containing the model in owner/repo format",
    )
    github_api_base_url: HttpUrl = Field(description="Base URL for the GitHub model API endpoint")
    github_api_key: SecretStr = Field(
        description="API key for authenticated access to GitHub model",
    )


class GoogleGenAIConfig(BaseAiClientConfig):
    model_provider: Literal["google_genai"] = Field(default="google_genai", description="Google GenAI provider")
    google_api_key: SecretStr = Field(
        description="API key for authenticated access to Genai model",
    )


class EmbeddingConfig(BaseModel):
    model_provider: Literal["google_genai"] = Field(description="Embedding model provider")
    model: str = Field(description="Embedding model name")
    google_api_key: SecretStr = Field(description="API key for authenticated access to Genai model")

    model_config = ConfigDict(extra="forbid")


class OllamaConfig(BaseAiClientConfig):
    model_provider: Literal["ollama"] = Field(default="ollama", description="Ollama provider")
    ollama_base_url: HttpUrl = Field(
        description="Base URL for your local Ollama instance (e.g. http://localhost:11434)",
    )


LangchainConfig = Annotated[
    Union[AzureOpenAIConfig, GitHubConfig, GoogleGenAIConfig, OllamaConfig],
    Field(discriminator="model_provider")
]

class ServiceConfig(BaseSettings):
    """
    Configuration for the service
    """

    logging: dict[str, Any] = Field(default_factory=dict, description="Logging configuration")
    main_aiclient: LangchainConfig = Field(description="Main AI Client configuration")
    packager_aiclient: LangchainConfig = Field(description="Packager AI Client configuration")
    embedding_client: EmbeddingConfig = Field(description="Embedding AI Client configuration")
    myai: MyAiConfig = Field(default_factory=MyAiConfig, description="MyAI bot configuration")
    hams: HamsConfig = Field(description="Health and monitoring configuration")

    webservice: WebServerConfig = Field(description="Web server configuration")
    persistence: PersistenceConfig = Field(description="Database persistence configuration")
    events: EventConfig = Field(default_factory=EventConfig, description="Process costs for events")

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        secrets_nested_subdir=True,  # Prevents additional fields not defined in the model
        env_nested_delimiter="__",
    )

    @classmethod
    def from_yaml_and_secrets_dir(cls, yaml_file: Path, secrets_path: Path) -> Self:

        cls.model_config["yaml_file"] = yaml_file
        cls.model_config["secrets_dir"] = secrets_path

        return cls()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:

        # Explicitly create NestedSecretsSettingsSource with NO prefix
        # so it maps filenames like 'api_key' and 'db/password' directly.
        nested_secrets = NestedSecretsSettingsSource(file_secret_settings, env_prefix="")

        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            nested_secrets,
        )
