from pydantic import BaseModel,SecretStr, Field
from pydantic_settings import BaseSettings,SettingsConfigDict
from typing import Literal
from rate_limiter.enums import Algorithm
from functools import lru_cache

class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None

    @property
    def url(self):
        if(self.password is not None):
            passwordVal = self.password.get_secret_value()
            return f'redis://:{passwordVal}@{self.host}:{self.port}/{self.db}'
        else:
            return f'redis://{self.host}:{self.port}/{self.db}'
    

class RateLimitDefaults(BaseModel):
    requests: int = 100
    window_seconds: int = 60
    burst: int = 20
    

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RL_", 
        env_file=".env", 
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    redis : RedisSettings = Field(default_factory=RedisSettings) 
    rate_limit : RateLimitDefaults = Field(default_factory=RateLimitDefaults)
    algorithm : Algorithm = Algorithm.TOKEN_BUCKET
    admin_key : SecretStr
    debug : bool = False
    log_level : Literal["DEBUG", "INFO", "WARNING", "ERROR"] =  "INFO"

@lru_cache()   
def get_settings() -> Settings:
    return Settings() # type: ignore[call-arg]

# without the comment it shows error: Argument missing for parameter "admin_key":
#     It's a known limitation of static type checkers with pydantic_settings.BaseSettings — they can't see that required fields get populated from environment variables at runtime, so they flag it as if you forgot to pass an argument to a regular constructor.
# type: ignore[call-arg]

# This tells Pyright/Pylance specifically "I know what I'm doing here, don't flag this line." It doesn't affect runtime behavior at all.