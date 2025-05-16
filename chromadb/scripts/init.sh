#!/bin/bash

# This script sets up the ChromaDB environment

# Create necessary directories
mkdir -p config

# Ensure auth_credentials.json exists with proper permissions
if [ ! -f config/auth_credentials.json ]; then
  cat > config/auth_credentials.json << 'EOL'
{
  "tokens": {
    "admin-token": {
      "token": "admin-token-9a621a8b5e4f3c2d1e0f7a6b5c4d3e2f",
      "api_key": "admin-api-key-7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d",
      "tenant": "default",
      "read": true,
      "write": true,
      "admin": true
    },
    "app-token": {
      "token": "app-token-1a0b9c8d7e6f5a4b3c2d1e0f7a6b5c4d",
      "api_key": "app-api-key-3c2d1e0f7a6b5c4d3e2f1a0b9c8d7e6f",
      "tenant": "default",
      "read": true,
      "write": true,
      "admin": false
    },
    "read-token": {
      "token": "read-token-5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f",
      "api_key": "read-api-key-1e0f7a6b5c4d3e2f1a0b9c8d7e6f5a4b",
      "tenant": "default",
      "read": true,
      "write": false,
      "admin": false
    }
  }
}
EOL
  echo "Created auth_credentials.json with default tokens"
  echo "WARNING: These are default tokens. For production, please replace with secure tokens."
fi

# Set proper permissions
chmod 600 config/auth_credentials.json

echo "ChromaDB setup complete!"
echo "To start ChromaDB: docker-compose up -d"
echo "To check logs: docker-compose logs -f chromadb"