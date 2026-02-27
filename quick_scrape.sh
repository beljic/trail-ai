#!/bin/bash
# Quick Scraping Script - sve u jednom
# Usage: ./quick_scrape.sh [full]

set -e

echo "============================================"
echo "🚀 Trail AI - Quick Scraping Script"
echo "============================================"
echo ""

# Aktiviraj venv
source venv/bin/activate

# 1. Backup
echo "📦 Step 1/4: Backing up existing data..."
python prepare_scrape.py
echo ""

# 2. Scrape
if [ "$1" == "full" ]; then
    echo "🏃 Step 2/4: Running FULL scrape..."
    python scrape_all.py --all
else
    echo "🏃 Step 2/4: Running incremental scrape..."
    python scrape_all.py
fi
echo ""

# 3. Export
echo "📤 Step 3/4: Exporting to formats..."
python export_races.py
echo ""

# 4. Analyze
echo "📊 Step 4/4: Analyzing results..."
python analyze_scrape_results.py
echo ""

echo "============================================"
echo "✅ Scraping complete!"
echo "============================================"
echo ""
echo "📁 Results:"
echo "  - JSONL: data/clean/races.jsonl"
echo "  - JSON:  data/export/races.json"
echo "  - CSV:   data/export/races.csv"
echo ""
echo "Next steps:"
echo "  - Import to DB: make db-import"
echo "  - Create embeddings: make ai-embed"
echo "  - Start API: make api-up"
echo ""
