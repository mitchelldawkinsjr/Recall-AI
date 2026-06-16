# AskMyVideo Developer Guide

## Overview

This guide helps developers understand, set up, and contribute to the AskMyVideo project.

## Prerequisites

- Python 3.9+
- pip
- Git
- FFmpeg (for video processing)
- PostgreSQL (optional, SQLite works for development)

## Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd video-processor-mvp
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r core_requirements.txt
```

### 4. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### 5. Configure Environment

Create a `.env` file (optional):
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Run Development Server

```bash
python manage.py runserver
```

Visit http://localhost:8000

## Project Structure

```
video-processor-mvp/
├── video_processor/          # Main Django app
│   ├── models.py            # Database models
│   ├── views.py             # View controllers and API endpoints
│   ├── urls.py              # URL routing
│   ├── admin.py             # Admin configuration
│   ├── templates/           # HTML templates
│   └── management/          # Management commands
├── video_recall_project/    # Django project settings
│   ├── settings/            # Settings modules
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI configuration
├── core_video_processor.py  # Core video processing engine
├── semantic_search.py       # Basic semantic search
├── enhanced_semantic_search.py  # Enhanced search engine
├── ai_enhanced_search.py    # AI search enhancements
├── rag_qa_system.py         # RAG Q&A system
├── enhanced_whisper_pipeline.py  # Enhanced transcription
├── docs/                    # Documentation
├── media/                   # User-uploaded files
├── search_cache/            # Search indices and cache
└── static/                  # Static files
```

## Key Components

### Video Processing Pipeline

**File:** `core_video_processor.py`

The core processor handles:
- Video validation
- Metadata extraction
- Audio extraction
- Transcription (Whisper)
- Segment creation

**Usage:**
```python
from core_video_processor import CoreVideoProcessor

processor = CoreVideoProcessor()
result = processor.create_comprehensive_video_summary(video_path)
```

### Search Engines

#### Basic Semantic Search
**File:** `semantic_search.py`

```python
from semantic_search import SemanticSearchEngine

engine = SemanticSearchEngine()
engine.build_index(video_segments)
results = engine.semantic_search("query", top_k=10)
```

#### Enhanced Search
**File:** `enhanced_semantic_search.py`

```python
from enhanced_semantic_search import get_enhanced_search_engine

engine = get_enhanced_search_engine()
results = engine.search(
    query="query",
    k=20,
    min_similarity=0.3,
    diversify_results=True
)
```

### Database Models

**File:** `video_processor/models.py`

Key models:
- `VideoJob`: Video processing jobs and metadata
- `VideoSearchQuery`: Search query tracking

**Usage:**
```python
from video_processor.models import VideoJob, JobStatus

# Create video job
job = VideoJob.objects.create(
    user=user,
    video_path=path,
    video_name=name,
    status=JobStatus.PENDING
)

# Query videos
completed_videos = VideoJob.objects.filter(status=JobStatus.COMPLETED)
```

## Development Workflow

### Running Tests

```bash
pytest
```

### Code Style

The project uses:
- **Black**: Code formatting
- **isort**: Import sorting

```bash
black .
isort .
```

### Database Migrations

Create migrations:
```bash
python manage.py makemigrations
```

Apply migrations:
```bash
python manage.py migrate
```

### Management Commands

```bash
# Process a video
python manage.py video_manager process <job_id>

# Rebuild search index
python manage.py video_manager rebuild_index

# Cleanup YouTube videos
python manage.py video_manager cleanup_youtube
```

## API Development

### Adding New Endpoints

1. Add view function in `video_processor/views.py`:

```python
from drf_spectacular.utils import extend_schema

@extend_schema(
    tags=['YourTag'],
    summary='Endpoint summary',
    description='Endpoint description',
    responses={200: {'description': 'Success'}}
)
@csrf_exempt
def api_your_endpoint(request):
    # Your implementation
    return JsonResponse({"success": True})
```

2. Add URL route in `video_processor/urls.py`:

```python
path("api/your-endpoint/", views.api_your_endpoint, name="api_your_endpoint"),
```

### Testing API Endpoints

```python
from django.test import Client
import json

client = Client()
response = client.post(
    '/api/search/',
    json.dumps({"query": "test"}),
    content_type='application/json'
)
```

## Search Engine Development

### Adding New Search Features

1. Extend `SemanticSearchEngine` or create new engine
2. Implement search method
3. Add to views for API access
4. Update documentation

### Custom Embeddings

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("your-model-name")
embeddings = model.encode(["text1", "text2"])
```

### FAISS Index Management

```python
import faiss
import numpy as np

# Create index
dimension = 384
index = faiss.IndexFlatIP(dimension)

# Add vectors
faiss.normalize_L2(embeddings)
index.add(embeddings.astype('float32'))

# Search
query_embedding = model.encode(["query"])
faiss.normalize_L2(query_embedding)
distances, indices = index.search(query_embedding, k=10)
```

## Background Processing

### Using Threading (Current)

```python
import threading

def process_video_job(job_id):
    # Processing logic
    pass

threading.Thread(target=process_video_job, args=(job_id,)).start()
```

### Using Celery (Optional)

```python
from video_recall_project.celery import app

@app.task
def process_video_job_async(job_id):
    # Processing logic
    pass

# Call it
process_video_job_async.delay(job_id)
```

## Configuration

### Settings Files

- `video_recall_project/settings/base.py`: Base settings
- `video_recall_project/settings/production.py`: Production settings

### Key Settings

```python
# Media files
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Search cache
SEARCH_CACHE_DIR = BASE_DIR / 'search_cache'

# Video processing
MAX_VIDEO_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
```

## Debugging

### Enable Debug Mode

In `settings/base.py`:
```python
DEBUG = True
```

### View Logs

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Debug message")
```

### Django Debug Toolbar

Add to `INSTALLED_APPS`:
```python
'debug_toolbar',
```

## Performance Optimization

### Database Queries

Use `select_related` and `prefetch_related`:
```python
videos = VideoJob.objects.select_related('user').prefetch_related('transcription')
```

### Caching

```python
from django.core.cache import cache

# Cache search results
cache_key = f"search_{query}"
results = cache.get(cache_key)
if not results:
    results = perform_search(query)
    cache.set(cache_key, results, 3600)
```

### Search Index Optimization

- Use appropriate FAISS index type
- Normalize embeddings for cosine similarity
- Batch embedding generation
- Persist indices to disk

## Deployment

### Production Settings

1. Set `DEBUG = False`
2. Configure `ALLOWED_HOSTS`
3. Use PostgreSQL
4. Set up static file serving
5. Configure media file storage (S3 recommended)
6. Set up SSL/TLS
7. Configure logging

### Docker Deployment

```bash
docker-compose up -d
```

### Environment Variables

```env
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@host/db
ALLOWED_HOSTS=yourdomain.com
```

## Contributing

### Code Style
- Follow PEP 8
- Use Black for formatting
- Write docstrings for functions/classes
- Add type hints where appropriate

### Commit Messages
- Use clear, descriptive messages
- Reference issue numbers if applicable

### Pull Requests
1. Create feature branch
2. Make changes
3. Add tests
4. Update documentation
5. Submit PR with description

## Troubleshooting

### Common Issues

**Import Errors:**
- Ensure virtual environment is activated
- Check all dependencies are installed
- Verify Python version compatibility

**Video Processing Fails:**
- Check FFmpeg is installed and in PATH
- Verify video file format is supported
- Check file permissions

**Search Not Working:**
- Verify FAISS and sentence-transformers are installed
- Check search index is built
- Verify model files are downloaded

**Database Errors:**
- Run migrations: `python manage.py migrate`
- Check database connection
- Verify database permissions

## Resources

- **Django Documentation**: https://docs.djangoproject.com/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **FAISS Documentation**: https://github.com/facebookresearch/faiss
- **Sentence Transformers**: https://www.sbert.net/
- **OpenAI Whisper**: https://github.com/openai/whisper

## Getting Help

- Check existing documentation
- Review code comments
- Check GitHub issues
- Ask questions in discussions

