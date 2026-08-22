#!/bin/bash
# Air-Gapped Deployment Launch Script for Tactical Hardware

echo "=== GARZA GLOBAL GRAVITON AIR-GAPPED DEPLOYMENT ==="

# Build OCI image locally without web registry calls
podman build --no-cache -t graviton-mesh-node:latest -f Containerfile .

# Execute isolated container node
podman run -it --rm \
  --name graviton_node_alpha \
  --network none \
  graviton-mesh-node:latest
