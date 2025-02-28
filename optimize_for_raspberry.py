#!/usr/bin/env python3

import os
import sys
import logging
import gc
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('optimizer')

# Ensure we're in the correct directory
project_dir = Path(__file__).parent
os.chdir(project_dir)

# Import performance settings
try:
    spec = importlib.util.spec_from_file_location(
        "performance", project_dir / "config" / "performance.py")
    performance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(performance)
    logger.info("Loaded performance settings")
except Exception as e:
    logger.error(f"Failed to load performance settings: {e}")
    sys.exit(1)


def optimize_app():
    """Apply performance optimizations to the application"""
    logger.info("Starting optimization process...")
    
    # Create .env.optimized file with performance settings
    create_optimized_env()
    
    # Create optimized startup script
    create_startup_script()
    
    # Create systemd service file for auto-start
    create_systemd_service()
    
    # Create cache directory if it doesn't exist
    cache_dir = project_dir / "cache"
    cache_dir.mkdir(exist_ok=True)
    
    logger.info("Optimization complete! Use 'start_optimized.sh' to run the application.")
    print("\n===== OPTIMIZATION COMPLETE =====\n")
    print("The application has been optimized for Raspberry Pi.")
    print("To start the optimized application, run:")
    print("  chmod +x start_optimized.sh")
    print("  ./start_optimized.sh")
    print("\nTo enable auto-start on boot:")
    print("  sudo cp monitor-produtosespera.service /etc/systemd/system/")
    print("  sudo systemctl enable monitor-produtosespera.service")
    print("  sudo systemctl start monitor-produtosespera.service")


def create_optimized_env():
    """Create an optimized .env file with performance settings"""
    logger.info("Creating optimized .env file")
    
    # Read existing .env file
    env_path = project_dir / ".env"
    env_optimized_path = project_dir / ".env.optimized"
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_content = f.read()
    else:
        env_content = ""
        logger.warning(".env file not found, creating new one")
    
    # Add performance settings
    performance_settings = f"""
# Performance optimization settings
LOG_LEVEL={performance.LOG_LEVEL}
CACHE_ENABLED={str(performance.CACHE_ENABLED).lower()}
CACHE_TIMEOUT={performance.CACHE_DEFAULT_TIMEOUT}
DB_POOL_SIZE={performance.DB_POOL_SIZE}
DB_POOL_TIMEOUT={performance.DB_POOL_TIMEOUT}
SCHEDULER_UPDATE_SECONDS={performance.SCHEDULER_JOBS['update_pending_orders']['seconds']}
"""
    
    # Write optimized .env file
    with open(env_optimized_path, 'w') as f:
        f.write(env_content + performance_settings)
    
    logger.info(f"Created optimized .env file at {env_optimized_path}")


def create_startup_script():
    """Create an optimized startup script"""
    logger.info("Creating optimized startup script")
    
    script_content = f"""#!/bin/bash

# Optimized startup script for Raspberry Pi
echo "Starting application with optimized settings..."

# Set environment variables for optimization
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONHASHSEED=random

# Set garbage collection thresholds
export PYTHONGC={performance.GC_THRESHOLD}

# Use optimized .env file
cp .env.optimized .env

# Start with gunicorn for better performance
echo "Starting with gunicorn ({performance.WORKERS} workers, {performance.THREADS} threads)..."
exec gunicorn --workers {performance.WORKERS} \
             --threads {performance.THREADS} \
             --timeout {performance.TIMEOUT} \
             --keep-alive {performance.KEEPALIVE} \
             --max-requests {performance.MAX_REQUESTS} \
             --log-level {performance.LOG_LEVEL.lower()} \
             --bind 0.0.0.0:5000 \
             app:app
"""
    
    script_path = project_dir / "start_optimized.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    logger.info(f"Created startup script at {script_path}")


def create_systemd_service():
    """Create systemd service file for auto-start"""
    logger.info("Creating systemd service file")
    
    service_content = f"""[Unit]
Description=Monitor Produtos Espera - Optimized for Raspberry Pi
After=network.target

[Service]
User=pi
WorkingDirectory={project_dir}
ExecStart={project_dir}/start_optimized.sh
Restart=always
RestartSec=10
Environment=LANG=en_US.UTF-8
Environment=LC_ALL=en_US.UTF-8
Environment=LC_LANG=en_US.UTF-8

[Install]
WantedBy=multi-user.target
"""
    
    service_path = project_dir / "monitor-produtosespera.service"
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    logger.info(f"Created systemd service file at {service_path}")


if __name__ == "__main__":
    optimize_app()