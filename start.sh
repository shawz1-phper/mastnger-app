#!/bin/bash

if [ "$RENDER" = "true" ]; then
    echo "Running on Render production environment..."
    gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:$PORT
else
    echo "Running in development mode..."
    python app.py
fi
