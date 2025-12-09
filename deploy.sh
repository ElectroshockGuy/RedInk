#!/bin/bash
set -e

# Configuration
IMAGE_NAME="ghcr.io/netlops/redink"
NAMESPACE="redink"
DOMAIN="redink.shunleite.com"

echo "=== 1. Building Docker Image ==="
docker build -t $IMAGE_NAME:latest .

echo "=== 2. Pushing Docker Image ==="
# Assuming user is logged in to ghcr.io
docker push $IMAGE_NAME:latest

echo "=== 3. Preparing Kubernetes Namespace ==="
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

echo "=== 4. Updating Configuration Secrets ==="
# Delete existing secret to allow updating (or use apply with --force, but delete is cleaner for secrets from files)
kubectl delete secret redink-config -n $NAMESPACE --ignore-not-found

kubectl create secret generic redink-config \
    -n $NAMESPACE \
    --from-file=text_providers.yaml=./text_providers.yaml \
    --from-file=image_providers.yaml=./image_providers.yaml \
    --from-file=auth.yaml=./auth.yaml

echo "=== 5. Handling TLS Certificate (Self-Signed) ==="
# Check if TLS secret exists, if not create a new self-signed cert
if ! kubectl get secret redink-tls -n $NAMESPACE > /dev/null 2>&1; then
    echo "Creating self-signed certificate for $DOMAIN..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /tmp/redink.key -out /tmp/redink.crt \
        -subj "/CN=$DOMAIN/O=RedInk/C=CN"
    
    kubectl create secret tls redink-tls \
        -n $NAMESPACE \
        --key /tmp/redink.key \
        --cert /tmp/redink.crt
    
    rm /tmp/redink.key /tmp/redink.crt
else
    echo "TLS secret 'redink-tls' already exists. Skipping generation."
fi

echo "=== 6. Deploying to Kubernetes ==="
kubectl apply -f k8s/

echo "=== 7. Restarting Deployment ==="
kubectl rollout restart deployment redink -n $NAMESPACE

echo "=== Deployment Complete! ==="
echo "Access your application at: https://$DOMAIN"
