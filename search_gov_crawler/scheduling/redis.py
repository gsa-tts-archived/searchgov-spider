import os


def get_redis_connection_args() -> dict:
    """Get the Redis connection arguments from environment variables."""
    return {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": 1,  # The searchgov app uses db 0
    }
