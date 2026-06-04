class RateLimiterError(Exception):
    pass
class RedisError(RateLimiterError):
    pass
    
class ConfigurationError(RateLimiterError):
    pass
    
class RedisConnectionError(RedisError):
    pass
        
class RedisOperationError(RedisError):
    pass

class InvalidConfigurationError(ConfigurationError):
    pass

class MissingConfigurationError(ConfigurationError):
    pass

class RateLimitExceeded(RateLimiterError):
    def __init__(self, message:str, retry_after: float , limit: int):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        
class RateLimitIndeterminate(RateLimiterError):
    pass
        
class IdentifierMissingError(RateLimiterError):
    pass

class RuleNotFoundError(RateLimiterError):
    def __init__(self, message:str,rule:str):
        super().__init__(message)
        self.rule = rule
        
    
    