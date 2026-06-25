from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "iot-core-backend"
    environment: str = "dev"
    log_level: str = "INFO"

    mongo_uri: str = Field("mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db_name: str = Field("ota", alias="MONGO_DB_NAME")
    mongo_min_pool_size: int = Field(5, alias="MONGO_MIN_POOL_SIZE")
    mongo_max_pool_size: int = Field(50, alias="MONGO_MAX_POOL_SIZE")
    mongo_server_selection_timeout_ms: int = Field(3000, alias="MONGO_SERVER_SELECTION_TIMEOUT_MS")
    mongo_connect_timeout_ms: int = Field(5000, alias="MONGO_CONNECT_TIMEOUT_MS")
    mongo_socket_timeout_ms: int = Field(10000, alias="MONGO_SOCKET_TIMEOUT_MS")

    gridfs_bucket_name: str = Field("firmware", alias="GRIDFS_BUCKET_NAME")

    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_audience: str | None = Field(default=None, alias="JWT_AUDIENCE")

    check_rate_limit: str = Field("60/minute", alias="CHECK_RATE_LIMIT")
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    public_base_url: str = Field("http://localhost:8000", alias="PUBLIC_BASE_URL")
    signed_url_secret: str | None = Field(default=None, alias="SIGNED_URL_SECRET")
    signed_url_ttl_seconds: int = Field(1800, alias="SIGNED_URL_TTL_SECONDS")

    # ---------------------------------------------------------------------------
    # MQTT broker (internal plain-text connection used by the FastAPI bridge)
    # ---------------------------------------------------------------------------
    mqtt_broker_host: str = Field("localhost", alias="MQTT_BROKER_HOST")
    mqtt_broker_port: int = Field(1883, alias="MQTT_BROKER_PORT")

    # ---------------------------------------------------------------------------
    # OAuth 2.0 — Google Home Account Linking
    # ---------------------------------------------------------------------------
    oauth_client_id: str = Field("", alias="OAUTH_CLIENT_ID")
    oauth_client_secret: str = Field("", alias="OAUTH_CLIENT_SECRET")
    oauth_redirect_uris: list[str] = Field(default_factory=list, alias="OAUTH_REDIRECT_URIS")
    oauth_auth_code_ttl_seconds: int = Field(600, alias="OAUTH_AUTH_CODE_TTL_SECONDS")

    # ---------------------------------------------------------------------------
    # Google Sign-In — shared Client ID for consumers AND admins
    # Obtain from Google Cloud Console → APIs & Services → Credentials
    # ---------------------------------------------------------------------------
    google_client_id: str = Field("", alias="GOOGLE_CLIENT_ID")

    # ---------------------------------------------------------------------------
    # Admin RBAC — Google SSO
    # SUPER_ADMIN_EMAIL always has root access regardless of the admin_users table.
    # ---------------------------------------------------------------------------
    super_admin_email: str = Field("", alias="SUPER_ADMIN_EMAIL")

    # ---------------------------------------------------------------------------
    # Consumer JWT — issued after Google Sign-In verification
    # ---------------------------------------------------------------------------
    consumer_jwt_secret: str = Field("", alias="CONSUMER_JWT_SECRET")
    consumer_jwt_algorithm: str = Field("HS256", alias="CONSUMER_JWT_ALGORITHM")
    consumer_jwt_ttl_seconds: int = Field(3600, alias="CONSUMER_JWT_TTL_SECONDS")
    consumer_refresh_token_ttl_seconds: int = Field(2592000, alias="CONSUMER_REFRESH_TOKEN_TTL_SECONDS")

    # ---------------------------------------------------------------------------
    # MQTT Binding Token — device provisioning
    # ---------------------------------------------------------------------------
    binding_token_ttl_seconds: int = Field(600, alias="BINDING_TOKEN_TTL_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
