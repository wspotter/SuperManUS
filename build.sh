#!/bin/bash

set -e

REGISTRY=${REGISTRY:-"ghcr.io/wspotter/supermanus"}
VERSION=${VERSION:-"latest"}
SERVICES="main-app mcp-server voice image code search"

echo "Building SuperManUS Docker images..."
echo "Registry: $REGISTRY"
echo "Version: $VERSION"

for service in $SERVICES; do
    echo "Building $service..."
    docker build \
        -f docker/$service/Dockerfile \
        -t $REGISTRY/$service:$VERSION \
        -t $REGISTRY/$service:latest \
        .
    echo "✓ $service built successfully"
done

echo ""
echo "All images built successfully!"
echo ""
echo "To push images to registry:"
echo "  ./build.sh push"
echo ""
echo "To run locally:"
echo "  docker-compose up"

if [ "$1" == "push" ]; then
    echo ""
    echo "Pushing images to registry..."
    for service in $SERVICES; do
        echo "Pushing $service..."
        docker push $REGISTRY/$service:$VERSION
        docker push $REGISTRY/$service:latest
    done
    echo "✓ All images pushed successfully"
fi

if [ "$1" == "run" ]; then
    echo ""
    echo "Starting services..."
    docker-compose up -d
    echo "✓ Services started"
    echo ""
    echo "Service URLs:"
    echo "  MCP Server: http://localhost:3000"
    echo "  Voice:      http://localhost:8001"
    echo "  Image:      http://localhost:8002"
    echo "  Code:       http://localhost:8003"
    echo "  Search:     http://localhost:8004"
fi