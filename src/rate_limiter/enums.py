from enum import Enum

class Algorithm(str,Enum):
    TOKEN_BUCKET= 'token_bucket'
    SLIDING_WINDOW= 'sliding_window'
    FIXED_WINDOW= 'fixed_window'
    
class RateLimitStatus(str,Enum):
    ALLOWED='allowed'
    DENIED='denied'
    
class Scope(str,Enum):
    IP='ip'
    API_KEY='api_key'
    USER='user'
    GLOBAL='global'
