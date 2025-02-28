#!/bin/bash

# Optimized startup script for Raspberry Pi
echo "Starting application with optimized settings..."

# Set environment variables for optimization
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONHASHSEED=random

# Set garbage collection thresholds
export PYTHONGC=700

# Use optimized .env file
cp .env.optimized .env

# Start with gunicorn for better performance
echo "Starting with gunicorn (2 workers, 2 threads)..."
exec gunicorn --workers 2              --threads 2              --timeout 120              --keep-alive 2              --max-requests 1000              --log-level warning              --bind 0.0.0.0:5000              app:app
