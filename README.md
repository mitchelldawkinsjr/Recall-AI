# AskMyVideo 🧠🎥

**Intelligent Video Search & Recall System** - Upload videos, search content with AI, and jump to exact moments.

## ✨ What AskMyVideo Does

- 🎥 **Smart Video Processing** - Automatic transcription with OpenAI Whisper
- 🔍 **AI-Powered Search** - Find content using natural language queries
- ⚡ **Instant Recall** - Jump to exact timestamps in videos
- 🌐 **Modern Web Interface** - Clean, intuitive search experience
- 📺 **YouTube Integration** - Process YouTube videos with automatic cleanup
- 🧮 **Semantic Search** - FAISS vector similarity with sentence transformers
- 📚 **Comprehensive API** - RESTful API with Swagger/OpenAPI documentation

## 📖 Documentation

### For Users
- **[User Guide](docs/USER_GUIDE.md)** - Complete guide on using AskMyVideo
- **[API Guide](docs/API_GUIDE.md)** - API reference and examples

### For Developers
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Setup, development, and contribution guide
- **[Architecture Documentation](docs/ARCHITECTURE.md)** - System architecture overview
- **[Search System](docs/SEARCH_SYSTEM.md)** - Deep dive into search functionality

### Architecture Diagrams
- **[System Architecture](docs/diagrams/system-architecture.md)** - High-level system design
- **[Data Flow](docs/diagrams/data-flow.md)** - Video processing and search flows
- **[Search Architecture](docs/diagrams/search-architecture.md)** - Search system details
- **[API Endpoints](docs/diagrams/api-endpoints.md)** - API structure and flows
- **[Database Schema](docs/diagrams/database-schema.md)** - Database design

### API Documentation
- **Swagger UI**: `/api/docs/` - Interactive API documentation
- **ReDoc**: `/api/redoc/` - Alternative API documentation
- **OpenAPI Schema**: `/api/schema/` - OpenAPI 3.0 schema (JSON/YAML)

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r core_requirements.txt

# Start AskMyVideo
python3 manage.py runserver

# Visit: http://localhost:8000
```

## 💡 How It Works

1. **Upload** videos or paste YouTube URLs
2. **AI processes** content and generates searchable transcripts  
3. **Search** using natural language like "relationship advice" or "personal growth"
4. **Jump** to exact moments with timestamp-based video seeking

## 🔍 Search Modes

- **🧠 Smart Search** - Hybrid AI + keyword matching
- **🤖 AI Search** - Pure semantic similarity search
- **📝 Keyword Search** - Traditional text matching

## 🏗️ Architecture

```
Clean Search UI → Django Backend → AI Search Engine → Video Database
                                      ↓
              Whisper AI ← Video Processor ← YouTube/Upload
```

### System Components

1. **Web Application Layer** - Django web framework with REST API
2. **Video Processing Pipeline** - Video validation, transcription, segmentation
3. **Search Engine System** - Multi-layered search (keyword, semantic, hybrid, enhanced)
4. **RAG System** - Retrieval-Augmented Generation for question answering
5. **Data Storage** - Database (SQLite/PostgreSQL) and file storage
6. **Background Processing** - Asynchronous video processing

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed information.

## 📁 Key Components

- **`core_video_processor.py`** - Video processing & transcription engine
- **`semantic_search.py`** - AI-powered search with FAISS vectors  
- **`enhanced_semantic_search.py`** - Enhanced search with advanced features
- **`ai_enhanced_search.py`** - Advanced AI features (OpenAI/HuggingFace)
- **`rag_qa_system.py`** - RAG-based question answering
- **`video_processor/`** - Django app with web interface and API
- **`video_recall_project/`** - Django project settings

## 🔌 API Access

AskMyVideo provides a comprehensive REST API for programmatic access:

- **Base URL**: `http://localhost:8000/api/`
- **Interactive Documentation**: Visit `/api/docs/` for Swagger UI
- **API Reference**: See [API Guide](docs/API_GUIDE.md) for complete reference

### Quick API Example

```bash
# Search videos
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "motivation and success", "search_mode": "hybrid"}'
```

## 🎯 Features

### Core Intelligence
- 🎯 **Semantic Search** - Understand meaning, not just keywords
- 📊 **Relevance Scoring** - AI-ranked search results
- 🎪 **Multiple AI Models** - Sentence transformers, OpenAI, HuggingFace
- 💾 **Smart Storage** - Automatic YouTube cleanup saves 89% disk space

### User Experience  
- 🎨 **Modern UI** - Glassmorphism design with smooth animations
- 📱 **Mobile Responsive** - Works perfectly on any device
- ⚙️ **Admin Panel** - Advanced management tools
- 🔗 **Direct Links** - Share exact video moments with timestamps

### Technical Excellence
- ⚡ **Fast Search** - FAISS vector database for millisecond queries
- 🔄 **Auto-Reload** - Real-time updates and progress tracking
- 🛡️ **Error Handling** - Graceful fallbacks for all AI services
- 🐳 **Production Ready** - Scalable Django architecture

## 🌟 Example Searches

Try searching for:
- "How to overcome challenges"
- "Relationship advice" 
- "Personal growth and development"
- "Dealing with anxiety"
- "Building confidence"

AskMyVideo understands context and meaning, not just exact word matches!

## 🎉 Why AskMyVideo?

- ✅ **Actually Intelligent** - Real AI understanding, not just keyword matching
- ✅ **Instant Results** - Jump to exact video moments in seconds
- ✅ **Beautiful Interface** - Modern, intuitive design
- ✅ **Production Ready** - Robust Django backend with error handling
- ✅ **Cost Effective** - Free tier AI with smart fallbacks
- ✅ **Privacy Focused** - All processing can run locally

Transform how you search and recall video content with **AskMyVideo** - where intelligence meets simplicity. 🚀

## 🚀 Quick Links

- **Getting Started**: See [User Guide](docs/USER_GUIDE.md)
- **API Documentation**: Visit `/api/docs/` or see [API Guide](docs/API_GUIDE.md)
- **Development**: See [Developer Guide](docs/DEVELOPER_GUIDE.md)
- **Architecture**: See [Architecture Documentation](docs/ARCHITECTURE.md)
- **Search Details**: See [Search System](docs/SEARCH_SYSTEM.md)

## 📊 Architecture Diagrams

Visual representations of the system:

- [System Architecture](docs/diagrams/system-architecture.md) - Overall system design
- [Data Flow](docs/diagrams/data-flow.md) - Processing and search flows
- [Search Architecture](docs/diagrams/search-architecture.md) - Search system design
- [API Endpoints](docs/diagrams/api-endpoints.md) - API structure
- [Database Schema](docs/diagrams/database-schema.md) - Data model

All diagrams use Mermaid format and render automatically on GitHub/GitLab. 