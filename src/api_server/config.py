"""Configuration management for the API server.

This module provides centralized configuration management using Pydantic settings
with environment variable support, validation, and error handling.
"""

from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support and validation."""
    
    # Database Configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL database connection URL",
        env="DATABASE_URL"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
        env="DEBUG"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        env="LOG_LEVEL"
    )
    
    # LINE Login Configuration
    line_client_id: str = Field(
        ...,
        description="LINE Login client ID",
        env="LINE_CLIENT_ID"
    )
    line_client_secret: str = Field(
        ...,
        description="LINE Login client secret",
        env="LINE_CLIENT_SECRET"
    )
    line_redirect_uri: str = Field(
        ...,
        description="LINE Login redirect URI",
        env="LINE_REDIRECT_URI"
    )
    
    # JWT Configuration
    jwt_secret: str = Field(
        ...,
        description="JWT secret key for token signing",
        env="JWT_SECRET"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm for token signing",
        env="JWT_ALGORITHM"
    )
    jwt_expire_minutes: int = Field(
        default=1440,  # 24 hours
        description="JWT token expiration time in minutes",
        env="JWT_EXPIRE_MINUTES"
    )
    
    # Environment Configuration
    environment: str = Field(
        default="development",
        description="Application environment (development, testing, production)",
        env="ENVIRONMENT"
    )
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}")
        return v.upper()
    
    @validator("jwt_expire_minutes")
    def validate_jwt_expire_minutes(cls, v: int) -> int:
        """Validate JWT expiration time is positive."""
        if v <= 0:
            raise ValueError("jwt_expire_minutes must be a positive integer")
        return v
    
    @validator("jwt_algorithm")
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm is supported."""
        allowed_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}
        if v not in allowed_algorithms:
            raise ValueError(f"jwt_algorithm must be one of {allowed_algorithms}")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://", "sqlite:///")):
            raise ValueError("database_url must be a valid PostgreSQL or SQLite URL")
        return v
    
    @validator("line_redirect_uri")
    def validate_line_redirect_uri(cls, v: str) -> str:
        """Validate LINE redirect URI format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("line_redirect_uri must be a valid HTTP/HTTPS URL")
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() == "testing"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


def get_settings() -> Settings:
    """Get application settings with error handling.
    
    Returns:
        Settings: Validated application settings
        
    Raises:
        ConfigurationError: If configuration validation fails
    """
    try:
        return Settings()
    except Exception as e:
        raise ConfigurationError(f"Configuration validation failed: {str(e)}") from e


# Global settings instance
settings = get_settings()
