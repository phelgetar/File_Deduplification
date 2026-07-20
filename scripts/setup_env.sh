#!/bin/bash
#
# setup_env.sh — Set up local environment variables for File Deduplication
#
# Author: Tim Canady
# Version: 0.1.0
# Last Modified: 2025-11-04

cat << EOF > .env
# Environment Variables
OPENAI_API_KEY=your_openai_api_key_here
EOF

echo ".env file created. Please replace your_openai_api_key_here with your actual OpenAI key."
