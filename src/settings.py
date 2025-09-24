import os
from src.app.utils.aws.secrets_manager_client import SecretsManagerClient
from pydantic_settings import BaseSettings, SettingsConfigDict

def read_docker_secret(secret_name: str) -> str | None:
    secret_path = f"/run/secrets/{secret_name}"
    try:
        with open(secret_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    
secrets_manager_client = SecretsManagerClient(region_name="eu-central-1")

class Settings(BaseSettings):
    # OPIK_API_KEY: str | None = None
    COMET_API_KEY: str | None = secrets_manager_client.get_secret("gma-dev-opik-api-sec")["api_key"]
    COMET_PROJECT: str = os.getenv("COMET_PROJECT", "guideme")
    


