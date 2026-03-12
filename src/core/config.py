from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    ENV: str = Field("dev", env="ENV")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")

    # Mongo (Atlas ou self-hosted)
    MONGO_URI: str = Field(..., env="MONGO_URI")
    MONGO_DB: str = Field("logcenter", env="MONGO_DB")
    MONGO_DEBUG: bool = Field(False, env="MONGO_DEBUG")

    
    #API
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY") 
    OPENAI_MODEL: str = Field(..., env="OPENAI_MODEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
