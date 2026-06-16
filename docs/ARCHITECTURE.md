# AskMyVideo Architecture

## Overview

AskMyVideo is an intelligent video search and recall system that processes videos, transcribes them using AI, and enables semantic search through video content. This document describes the high-level architecture of the system.

## System Components

### 1. Web Application Layer (Django)

The Django web framework provides:
- **User Interface**: HTML templates for video library, search, and management
- **REST API**: JSON endpoints for programmatic access
- **Authentication**: User management and multi-tenancy
- **Admin Panel**: Administrative interface for system management

**Key Files:**
- `video_processor/views.py` - View controllers and API endpoints
- `video_processor/models.py` - Database models (VideoJob, VideoSearchQuery)
- `video_processor/urls.py` - URL routing

### 2. Video Processing Pipeline

The core video processing system handles:
- **Video Upload**: File uploads and YouTube URL processing
- **Metadata Extraction**: Video properties (duration, resolution, codec)
- **Audio Extraction**: Converting video to audio for transcription
- **Transcription**: Using OpenAI Whisper for speech-to-text
- **Segment Creation**: Breaking transcriptions into searchable segments

**Key Files:**
- `core_video_processor.py` - Main processing engine
- `enhanced_whisper_pipeline.py` - Enhanced transcription pipeline

### 3. Search Engine System

Multi-layered search architecture:

#### 3.1 Semantic Search Engine
- **Embeddings**: Sentence transformers convert text to vectors
- **FAISS Index**: High-performance vector similarity search
- **Models**: `all-MiniLM-L6-v2` (default) or `BAAI/bge-large-en-v1.5` (enhanced)

#### 3.2 Enhanced Search Engine
- **Advanced Features**: Topic extraction, sentiment analysis, diversification
- **Better Embeddings**: Uses larger, more accurate models
- **Context Windows**: Better chunking with overlap for context preservation

#### 3.3 Search Modes
- **Keyword Search**: Traditional text matching
- **Semantic Search**: Vector similarity search
- **Hybrid Search**: Combines keyword and semantic approaches
- **Enhanced Search**: Advanced features with diversification

**Key Files:**
- `semantic_search.py` - Basic semantic search engine
- `enhanced_semantic_search.py` - Enhanced search with advanced features
- `ai_enhanced_search.py` - AI-powered search enhancements

### 4. RAG (Retrieval-Augmented Generation) System

Question-answering system that:
- Retrieves relevant video segments
- Generates answers using LLMs
- Provides source citations

**Key Files:**
- `rag_qa_system.py` - RAG-based Q&A implementation

### 5. Data Storage

#### 5.1 Database (SQLite/PostgreSQL)
- **VideoJob**: Stores video metadata, processing status, transcriptions
- **VideoSearchQuery**: Tracks search queries for analytics
- **User**: Multi-tenant user management

#### 5.2 File Storage
- **Media Files**: Video files stored in `media/videos/`
- **Search Cache**: FAISS indices and embeddings in `search_cache/`
- **Model Cache**: Downloaded AI models cached locally

### 6. Background Processing

- **Threading**: Video processing runs in background threads
- **Celery** (optional): For distributed task processing
- **Status Tracking**: Real-time job status updates

## Data Flow

### Video Processing Flow

```
1. User Uploads Video
   ↓
2. VideoJob Created (status: PENDING)
   ↓
3. Background Thread Starts Processing
   ↓
4. Extract Metadata (duration, resolution, etc.)
   ↓
5. Extract Audio from Video
   ↓
6. Transcribe Audio (Whisper AI)
   ↓
7. Create Text Segments with Timestamps
   ↓
8. Store Transcription in Database
   ↓
9. Update VideoJob (status: COMPLETED)
   ↓
10. Index Segments in Search Engine (optional)
```

### Search Flow

```
1. User Submits Search Query
   ↓
2. Query Processed Based on Search Mode:
   - Keyword: Text matching
   - Semantic: Embedding generation → FAISS search
   - Hybrid: Both methods combined
   - Enhanced: Advanced features + diversification
   ↓
3. Results Ranked by Relevance
   ↓
4. Results Returned with Timestamps
   ↓
5. User Clicks Result → Video Jumps to Timestamp
```

## Technology Stack

### Backend
- **Django 4.2**: Web framework
- **Django REST Framework**: API layer
- **SQLite/PostgreSQL**: Database
- **Celery**: Background task processing (optional)
- **Redis**: Caching and task queue (optional)

### AI/ML
- **OpenAI Whisper**: Speech-to-text transcription
- **Sentence Transformers**: Text embeddings
- **FAISS**: Vector similarity search
- **Transformers**: Advanced NLP models
- **scikit-learn**: ML utilities

### Video Processing
- **FFmpeg**: Video/audio processing
- **OpenCV**: Video analysis
- **yt-dlp**: YouTube video downloading

### API Documentation
- **drf-spectacular**: OpenAPI/Swagger documentation

## Deployment Architecture

### Development
- Django development server
- SQLite database
- Local file storage

### Production
- **WSGI Server**: Gunicorn
- **Reverse Proxy**: Nginx
- **Database**: PostgreSQL
- **File Storage**: Local or S3
- **Container**: Docker
- **Orchestration**: Docker Compose or AWS ECS

## Security

- **Authentication**: Django's built-in auth system
- **Multi-tenancy**: User-based data isolation
- **CSRF Protection**: Django CSRF middleware
- **File Upload Validation**: Size and type checks
- **SQL Injection Protection**: Django ORM

## Scalability Considerations

### Current Architecture
- Single-server deployment
- In-memory search indices
- File-based storage

### Scaling Options
1. **Horizontal Scaling**: Multiple Django instances behind load balancer
2. **Database Scaling**: PostgreSQL with read replicas
3. **Search Scaling**: Distributed FAISS indices or Elasticsearch
4. **Storage Scaling**: S3 or cloud storage
5. **Processing Scaling**: Celery workers for video processing

## Performance Optimizations

- **FAISS Index**: Fast vector similarity search
- **Embedding Caching**: Reuse embeddings for similar queries
- **Lazy Loading**: Models loaded on demand
- **Background Processing**: Non-blocking video processing
- **Index Persistence**: Save/load FAISS indices to disk

## Monitoring and Logging

- **Django Logging**: Application logs
- **Health Checks**: `/api/health/` endpoint
- **Statistics**: `/api/detailed-stats/` endpoint
- **Error Tracking**: Sentry integration (optional)

## Future Enhancements

- **Real-time Processing**: WebSocket updates for processing status
- **Distributed Search**: Multi-node FAISS clusters
- **Advanced Analytics**: Search analytics and insights
- **Video Thumbnails**: Automatic thumbnail generation
- **Speaker Diarization**: Identify different speakers
- **Multi-language Support**: Enhanced language detection

