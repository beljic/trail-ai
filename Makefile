.PHONY: build run clean help db-up db-down db-import db-shell db-reset db-logs

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Scraper:"
	@echo "  make build       - Build Docker image"
	@echo "  make run         - Run scraper in Docker (incremental)"
	@echo "  make scrape      - Run scraper locally (incremental)"
	@echo "  make scrape-full - Run full scrape locally"
	@echo "  make clean       - Remove output file (data/clean/races.jsonl)"
	@echo ""
	@echo "Scraping Workflow:"
	@echo "  make prepare     - Backup data before scraping"
	@echo "  make analyze     - Analyze scrape results"
	@echo "  make test        - Test new scraper features"
	@echo "  make workflow    - Full workflow: prepare → scrape → analyze"
	@echo ""
	@echo "Database:"
	@echo "  make db-up       - Start PostgreSQL database"
	@echo "  make db-down     - Stop PostgreSQL database"
	@echo "  make db-import   - Import races.jsonl into database"
	@echo "  make db-shell    - Open PostgreSQL shell (psql)"
	@echo "  make db-reset    - Reset database (remove all data)"
	@echo "  make db-logs     - Show PostgreSQL logs"
	@echo ""
	@echo "AI/RAG:"
	@echo "  make ai-embed    - Create embeddings from PostgreSQL data"
	@echo "  make ai-jsonl    - Create embeddings directly from JSONL"
	@echo "  make ai-reset    - Reset vector database"
	@echo "  make api-up      - Start API server"
	@echo "  make api-down    - Stop API server"
	@echo "  make api-logs    - Show API server logs"
	@echo ""
	@echo "  make help        - Show this help message"

# Build Docker image
build:
	docker compose build

# Run scraper
run:
	docker compose run --rm scraper

# Clean output file
clean:
	@echo "Removing data/clean/races.jsonl..."
	@rm -f data/clean/races.jsonl
	@echo "Done."

# Build and run in one command
all: build run

# Start PostgreSQL database
db-up:
	docker compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	@docker compose exec postgres pg_isready -U trailuser -d traildb || echo "Database is starting..."

# Stop PostgreSQL database
db-down:
	docker compose down

# Import data from JSONL to database
db-import:
	docker compose run --rm scraper python import_to_db.py

# Open PostgreSQL shell
db-shell:
	docker compose exec postgres psql -U trailuser -d traildb

# Reset database (WARNING: removes all data)
db-reset:
	@echo "WARNING: This will delete all data in the database!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose exec postgres psql -U trailuser -d traildb -c "TRUNCATE TABLE races RESTART IDENTITY CASCADE;"; \
		echo "Database reset complete."; \
	else \
		echo "Cancelled."; \
	fi

# Show PostgreSQL logs
db-logs:
	docker compose logs -f postgres

# Create embeddings from PostgreSQL data
ai-embed:
	docker compose run --rm scraper python embed_races.py

# Create embeddings directly from JSONL (skip PostgreSQL)
ai-jsonl:
	docker compose run --rm scraper python embed_from_jsonl.py

# Reset vector database
ai-reset:
	docker compose run --rm scraper python embed_races.py --reset --force

# Start API server
api-up:
	docker compose up -d api

# Stop API server  
api-down:
	docker compose stop api

# Show API server logs
api-logs:
	docker compose logs -f api

# === NEW: Scraping Workflow Commands ===

# Prepare for scraping (backup existing data)
prepare:
	@echo "🔄 Preparing for scraping..."
	python prepare_scrape.py

# Run scraper locally (no Docker, incremental mode)
scrape:
	@echo "🏃 Running incremental scrape..."
	python scrape_all.py

# Run full scrape locally (no Docker)
scrape-full:
	@echo "🏃 Running FULL scrape..."
	python scrape_all.py --all

# Analyze scrape results
analyze:
	@echo "📊 Analyzing scrape results..."
	python analyze_scrape_results.py

# Test new features
test:
	@echo "🧪 Testing new features..."
	python test_new_features.py

# Full workflow: prepare → scrape → analyze
workflow: prepare scrape analyze
	@echo "✅ Complete scraping workflow finished!"

# Full workflow with full scrape
workflow-full: prepare scrape-full analyze
	@echo "✅ Complete FULL scraping workflow finished!"
