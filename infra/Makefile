# Convenience Makefile for ChatOps infrastructure stack

COMPOSE_FILE = docker-compose.yml

.PHONY: help up down restart restore ps logs

help:
	@echo "ChatOps Infrastructure Management"
	@echo "Usage:"
	@echo "  make up          - Start all containers in background"
	@echo "  make down        - Stop all containers and network"
	@echo "  make restart     - Restart stack"
	@echo "  make restore     - Reset fault toggles and memory limits"
	@echo "  make ps          - List running services"
	@echo "  make logs        - Tail logs for all services"

up:
	docker compose -f $(COMPOSE_FILE) up -d

down:
	docker compose -f $(COMPOSE_FILE) down

restart: down up

restore:
	python failures/restore.py

ps:
	docker compose -f $(COMPOSE_FILE) ps

logs:
	docker compose -f $(COMPOSE_FILE) logs -f --tail=100
