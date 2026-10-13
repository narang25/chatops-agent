#!/usr/bin/env bash
# Restore script to return all services to healthy state
set -e

echo "=== Restoring ChatOps Stack to Healthy State ==="

# 1. Reset memory limit on payment-service
docker update --memory 128m --memory-swap 128m payment-service || true

# 2. Clean temporary badenv containers and restart standard compose stack
docker rm -f order-service-badenv 2>/dev/null || true
docker compose -f infra/docker-compose.yml up -d

# 3. Reset faults on all services
curl -s -X POST http://localhost:8001/admin/fault -H "Content-Type: application/json" -d '{"health_fail": false, "slow_db": false, "db_error": false}' || true
curl -s -X POST http://localhost:8002/admin/fault -H "Content-Type: application/json" -d '{"health_fail": false, "slow_db": false, "db_error": false}' || true
curl -s -X POST http://localhost:8003/admin/fault -H "Content-Type: application/json" -d '{"health_fail": false, "slow_db": false, "db_error": false}' || true

echo ""
echo "Verifying health checks:"
curl -s http://localhost:8001/health && echo " (payment-service)"
curl -s http://localhost:8002/health && echo " (order-service)"
curl -s http://localhost:8003/health && echo " (inventory-service)"

echo "=== Restore Complete ==="
