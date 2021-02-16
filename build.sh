#!/bin/bash
echo "Building PyDSS Docker image..."
docker build --rm -f Dockerfile -t pydss_service:latest .
