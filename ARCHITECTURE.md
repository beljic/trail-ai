```
🏗️ TRAIL AI - KOMPLETNA ARHITEKTURA

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WEB SCRAPER   │───▶│   JSONL FILES    │───▶│    PostgreSQL   │
│   (trka.rs)     │    │ (data/clean/)    │    │  (master data)  │
│  scrapers/      │    │                  │    │                 │
│  - trka_rs.py   │    │  races.jsonl     │    │   races table   │
│  - runtrace.py  │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        ▼
                                │               ┌─────────────────┐
                                │               │  VECTOR DATABASE│
                                │               │   (ChromaDB/    │
                                │               │    TF-IDF)      │
                                │               │  ai/            │
                                │               │  - embeddings.py│
                                │               │  - lite.py      │
                                │               └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI SERVER                            │
│                     api/main.py                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ PostgreSQL APIs │  │   AI/RAG APIs   │  │  CHAT APIs      │ │
│  │                 │  │                 │  │                 │ │
│  │ /races/search   │  │ /query          │  │ /chat           │ │
│  │ /races/{id}     │  │ /recommendations│  │ /sessions       │ │
│  │ /database/stats │  │ /analyze        │  │                 │ │
│  │                 │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  WEB FRONTEND   │  │  MOBILE APP     │  │  CURL/POSTMAN   │ │
│  │                 │  │                 │  │                 │ │
│  │ React/Vue/HTML  │  │ React Native    │  │ API Testing     │ │
│  │ JavaScript      │  │ Flutter/Swift   │  │                 │ │
│  │                 │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

🤖 OLLAMA (Windows host)
┌─────────────────┐
│ Ollama Server   │◀── Docker containers pristupaju preko
│ localhost:11434 │    host.docker.internal:11434
│                 │
│ Models:         │
│ - llama3.2      │
│ - mistral       │
└─────────────────┘
```