# Performance optimization settings for Raspberry Pi

# Database connection pool settings
DB_POOL_SIZE = 5  # Reduced pool size for Raspberry Pi
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30

# Cache settings
CACHE_ENABLED = True
CACHE_TYPE = 'simple'  # Use simple cache for lower memory usage
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
CACHE_THRESHOLD = 1000  # Maximum number of items in cache

# Logging settings
LOG_LEVEL = 'WARNING'  # Reduce logging verbosity
LOG_FILE_MAX_BYTES = 1024 * 1024  # 1MB
LOG_FILE_BACKUP_COUNT = 3

# Scheduler settings
SCHEDULER_JOBS = {
    'update_pending_orders': {
        'seconds': 300  # Reduced frequency to 5 minutes
    },
    'cleanup_cache': {
        'seconds': 3600  # Run cache cleanup every hour
    }
}

# WSGI server settings
WORKERS = 2  # Reduced number of workers for Raspberry Pi
THREADS = 2  # Reduced number of threads per worker
TIMEOUT = 120  # Increased timeout for slower hardware
KEEPALIVE = 2  # Reduced keepalive connections

# Memory optimization
GC_THRESHOLD = 700  # Lower garbage collection threshold
MAX_REQUESTS = 1000  # Restart workers after handling this many requests