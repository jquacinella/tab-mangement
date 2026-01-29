"""
TabBacklog v1 - Shared Configuration Module

This module provides centralized configuration management for all services.
It loads settings from environment variables and provides typed access.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = Field(alias="DATABASE_URL")
    pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LLMSettings(BaseSettings):
    """LLM service configuration"""
    api_base: str = Field(alias="LLM_API_BASE")
    api_key: str = Field(default="dummy_key", alias="LLM_API_KEY")
    model_name: str = Field(alias="LLM_MODEL_NAME")
    timeout: int = Field(default=60, alias="LLM_TIMEOUT")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ServiceSettings(BaseSettings):
    """Service endpoint configuration"""
    parser_url: str = Field(alias="PARSER_SERVICE_URL")
    enrichment_url: str = Field(alias="ENRICHMENT_SERVICE_URL")
    web_ui_url: str = Field(alias="WEB_UI_URL")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ProcessingSettings(BaseSettings):
    """Processing and batch configuration"""
    batch_size: int = Field(default=10, alias="BATCH_SIZE")
    max_concurrent: int = Field(default=2, alias="MAX_CONCURRENT_REQUESTS")
    fetch_timeout: int = Field(default=30, alias="FETCH_TIMEOUT")
    retry_delay: int = Field(default=5, alias="RETRY_DELAY")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class SearchSettings(BaseSettings):
    """Search configuration"""
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    similarity_threshold: float = Field(default=0.3, alias="SIMILARITY_THRESHOLD")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(BaseSettings):
    """General application settings"""
    env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(alias="APP_SECRET_KEY")
    debug: bool = Field(default=False, alias="APP_DEBUG")
    default_user_id: str = Field(alias="DEFAULT_USER_ID")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Config:
    """Main configuration class that combines all settings"""
    
    def __init__(self):
        self.database = DatabaseSettings()
        self.llm = LLMSettings()
        self.services = ServiceSettings()
        self.processing = ProcessingSettings()
        self.search = SearchSettings()
        self.app = AppSettings()
    
    @property
    def is_development(self) -> bool:
        return self.app.env == "development"
    
    @property
    def is_production(self) -> bool:
        return self.app.env == "production"


# Global config instance
config = Config()


# Helper function to get config
def get_config() -> Config:
    """Get the global configuration instance"""
    return config


# Helper function to load environment from file
def load_env(env_file: str = ".env") -> None:
    """Load environment variables from file"""
    from dotenv import load_dotenv
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"Warning: {env_file} not found")


# Example usage:
if __name__ == "__main__":
    load_env()
    cfg = get_config()
    
    print(f"Environment: {cfg.app.env}")
    print(f"Database URL: {cfg.database.url[:50]}...")
    print(f"LLM Model: {cfg.llm.model_name}")
    print(f"Parser Service: {cfg.services.parser_url}")
    print(f"Batch Size: {cfg.processing.batch_size}")
