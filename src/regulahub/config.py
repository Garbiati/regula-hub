from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"
    log_format: str = "console"  # "console" or "json"
    cors_origins: str = "*"


class ApiAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_keys: str = Field(..., min_length=1, description="Comma-separated API keys")

    def get_allowed_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DB_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    name: str = "regulahub"
    user: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    pool_size: int = Field(10, ge=1)
    max_overflow: int = Field(20, ge=0)
    pool_timeout: int = Field(10, ge=1)


@lru_cache
def get_auth_settings() -> ApiAuthSettings:
    return ApiAuthSettings()


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    admin_api_url: str = "http://api:8000"


@lru_cache
def get_admin_settings() -> AdminSettings:
    return AdminSettings()


class SeedSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    seed_credentials_path: str = "docker/seed/credentials.enc.json"


@lru_cache
def get_seed_settings() -> SeedSettings:
    return SeedSettings()


class CredentialEncryptionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    credential_encryption_key: str = Field(..., min_length=44, description="44-char base64 Fernet key")

    @field_validator("credential_encryption_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        from cryptography.fernet import Fernet

        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError("Invalid Fernet key — must be a valid base64-encoded 32-byte key") from exc
        return v


@lru_cache
def get_credential_encryption_settings() -> CredentialEncryptionSettings:
    return CredentialEncryptionSettings()


class CadsusSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cadsus_auth_url: str = Field("https://ehr-auth.saude.gov.br", description="Token endpoint base URL")
    cadsus_services_url: str = Field("https://servicos.saude.gov.br", description="SOAP services base URL")
    cadsus_enabled: bool = Field(True, description="Enable/disable CADSUS integration")
    cadsus_token_margin_seconds: int = Field(300, ge=0, description="Seconds before token expiry to refresh")
    cadsus_cert_path: str = Field("", description="Path to client certificate (.pfx) for mTLS auth")
    cadsus_cert_password: str = Field("", description="Password for the client certificate")

    @field_validator("cadsus_auth_url", "cadsus_services_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from urllib.parse import urlparse

        result = urlparse(v)
        if not result.scheme or not result.netloc:
            raise ValueError(f"Invalid URL: {v}")
        return v.rstrip("/")


@lru_cache
def get_cadsus_settings() -> CadsusSettings:
    return CadsusSettings()


class IntegrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    integration_api_key: str = Field("", description="API key for integration system (Core API + Auth API)")
    integration_core_api_url: str = Field(
        "https://api.sosportal.com.br/api/core/v1", description="Core API base URL"
    )
    integration_auth_api_url: str = Field(
        "https://api.sosportal.com.br/api/auth/v1", description="Auth API base URL"
    )


@lru_cache
def get_integration_settings() -> IntegrationSettings:
    return IntegrationSettings()
