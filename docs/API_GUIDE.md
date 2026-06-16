# AskMyVideo API Guide

## Overview

The AskMyVideo API provides programmatic access to video processing, search, and management functionality. All API endpoints return JSON responses.

## Base URL

```
http://localhost:8000/api/
```

## Authentication

Most endpoints require authentication. Use one of the following methods:

### Session Authentication
For browser-based requests, use Django session authentication.

### Token Authentication
For programmatic access, use token authentication:

```bash
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/api/search/
```

## API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **OpenAPI Schema**: `/api/schema/`

## Endpoints

### Search Endpoints

#### Search Videos
Search through video transcriptions.

**Endpoint:** `POST /api/search/`

**Request Body:**
```json
{
  "query": "relationship advice",
  "search_mode": "hybrid"
}
```

**Parameters:**
- `query` (string, required): Search query text
- `search_mode` (string, optional): One of `keyword`, `semantic`, or `hybrid` (default: `hybrid`)

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "video_id": "uuid",
      "video_name": "Video Title",
      "start_time": 120.5,
      "end_time": 125.0,
      "text": "Matching segment text...",
      "relevance_score": 0.85,
      "search_type": "semantic",
      "timestamp_formatted": "2:00"
    }
  ],
  "query": "relationship advice",
  "search_mode": "hybrid",
  "total_results": 10
}
```

#### Enhanced Search
Advanced semantic search with diversification and filtering.

**Endpoint:** `POST /api/enhanced-search/`

**Request Body:**
```json
{
  "query": "personal growth",
  "k": 20,
  "min_similarity": 0.3,
  "diversify": true,
  "max_per_video": 3,
  "filter_topics": ["self-improvement", "motivation"]
}
```

**Parameters:**
- `query` (string, required): Search query
- `k` (integer, optional): Number of results (default: 20)
- `min_similarity` (float, optional): Minimum similarity score 0-1 (default: 0.3)
- `diversify` (boolean, optional): Enable result diversification (default: true)
- `max_per_video` (integer, optional): Maximum results per video (default: 3)
- `filter_topics` (array, optional): Filter by topic tags

**Response:**
```json
{
  "success": true,
  "results": [...],
  "query": "personal growth",
  "search_mode": "enhanced_diversified",
  "total_results": 15,
  "unique_videos": 5,
  "search_params": {...}
}
```

#### Advanced Search
Comprehensive search with full control over parameters.

**Endpoint:** `POST /api/advanced-search/`

**Request Body:**
```json
{
  "query": "anxiety management",
  "k": 25,
  "min_similarity": 0.25,
  "diversify": true,
  "max_per_video": 2,
  "search_type": "enhanced",
  "include_context": true,
  "include_sentiment": false
}
```

**Parameters:**
- `query` (string, required): Search query
- `k` (integer, optional): Number of results (default: 25)
- `min_similarity` (float, optional): Minimum similarity (default: 0.25)
- `diversify` (boolean, optional): Enable diversification (default: true)
- `max_per_video` (integer, optional): Max per video (default: 2)
- `filter_topics` (array, optional): Topic filters
- `search_type` (string, optional): `enhanced`, `semantic`, `keyword`, or `hybrid` (default: `enhanced`)
- `include_context` (boolean, optional): Include context window (default: true)
- `include_sentiment` (boolean, optional): Include sentiment scores (default: false)

#### RAG Question Answering
Answer questions using Retrieval-Augmented Generation.

**Endpoint:** `POST /api/rag-qa/`

**Request Body:**
```json
{
  "question": "What are the main points about building confidence?",
  "method": "auto",
  "include_sources": true,
  "filter_topics": ["confidence", "self-improvement"]
}
```

**Parameters:**
- `question` (string, required): Question to answer
- `method` (string, optional): `auto`, `extractive`, or `generative` (default: `auto`)
- `include_sources` (boolean, optional): Include source segments (default: true)
- `filter_topics` (array, optional): Filter by topics

**Response:**
```json
{
  "success": true,
  "question": "What are the main points about building confidence?",
  "answer": "Based on the video content...",
  "confidence": 0.92,
  "method": "extractive",
  "processing_time": 1.2,
  "sources": [...],
  "metadata": {...}
}
```

### Video Management Endpoints

#### Get Video Details
Retrieve information about a specific video.

**Endpoint:** `GET /api/video/<job_id>/`

**Response:**
```json
{
  "job_id": "uuid",
  "video_name": "Video Title",
  "status": "completed",
  "is_youtube": true,
  "youtube_video_id": "abc123",
  "duration_seconds": 3600,
  "youtube_watch_url": "https://www.youtube.com/watch?v=abc123",
  "youtube_embed_url": "https://www.youtube.com/embed/abc123"
}
```

#### Update Video Metadata
Update video title and YouTube URL.

**Endpoint:** `POST /api/video/<job_id>/update-metadata/`

**Request Body:**
```json
{
  "title": "New Video Title",
  "youtube_url": "https://www.youtube.com/watch?v=abc123"
}
```

**Response:**
```json
{
  "success": true
}
```

### Admin Endpoints

#### Get Search Engine Status
Check search engine initialization status.

**Endpoint:** `GET /api/search-status/`

**Response:**
```json
{
  "available": true,
  "initialized": true,
  "model_name": "all-MiniLM-L6-v2",
  "indexed_segments": 1250
}
```

#### Get Detailed Statistics
Comprehensive system statistics.

**Endpoint:** `GET /api/detailed-stats/`

**Response:**
```json
{
  "video_stats": {
    "total_videos": 50,
    "pending_jobs": 2,
    "processing_jobs": 1,
    "failed_jobs": 0,
    "recent_jobs_7_days": 10
  },
  "processing_stats": {
    "total_processing_time": 1250.5,
    "average_processing_time": 25.0,
    "total_duration_hours": 12.5
  },
  "content_stats": {
    "total_words": 50000,
    "language_distribution": {"en": 50}
  },
  "storage_stats": {
    "total_file_size_gb": 5.2
  },
  "search_stats": {
    "indexed_segments": 1250,
    "is_initialized": true,
    "model_name": "all-MiniLM-L6-v2"
  }
}
```

#### Get Pending Jobs
List pending video processing jobs.

**Endpoint:** `GET /api/pending-jobs/`

**Response:**
```json
{
  "count": 2,
  "pending_jobs": [
    {
      "job_id": "uuid",
      "video_name": "Video.mp4",
      "file_size_mb": 125.5,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### Health Check

#### API Health Check
System health status.

**Endpoint:** `GET /api/health/`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "search_engine": "available",
  "enhanced_search": "available"
}
```

### Teams Endpoints

#### Get Teams Summary
User's video collection summary.

**Endpoint:** `GET /api/teams/summary/`

**Response:**
```json
{
  "success": true,
  "data": {
    "total_videos": 25,
    "completed_videos": 23,
    "processing_videos": 1,
    "failed_videos": 1,
    "total_storage_bytes": 5368709120,
    "total_storage_mb": 5120.0,
    "user_id": 1,
    "username": "user",
    "email": "user@example.com"
  }
}
```

#### Get Teams List
List of teams for current user.

**Endpoint:** `GET /api/teams/`

**Response:**
```json
{
  "success": true,
  "data": {
    "teams": [
      {
        "id": 1,
        "name": "Personal Videos",
        "description": "Your personal video collection",
        "member_count": 1,
        "video_count": 25,
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
  }
}
```

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Resource not found
- `405 Method Not Allowed`: Invalid HTTP method
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

Error responses follow this format:

```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

## Rate Limiting

Currently, there are no rate limits. Future versions may implement rate limiting for production deployments.

## Best Practices

1. **Use Appropriate Search Mode**: 
   - Use `keyword` for exact matches
   - Use `semantic` for meaning-based search
   - Use `hybrid` for balanced results
   - Use `enhanced` for best quality with advanced features

2. **Handle Errors Gracefully**: Always check response status codes and handle errors appropriately.

3. **Cache Results**: Search results can be cached client-side for better performance.

4. **Use Pagination**: For large result sets, implement client-side pagination.

5. **Monitor Health**: Regularly check `/api/health/` to ensure system availability.

## Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Search videos
response = requests.post(
    f"{BASE_URL}/search/",
    json={
        "query": "motivation and success",
        "search_mode": "hybrid"
    }
)
results = response.json()

# Get video details
video_id = results["results"][0]["video_id"]
response = requests.get(f"{BASE_URL}/video/{video_id}/")
video = response.json()
```

### JavaScript Example

```javascript
const BASE_URL = 'http://localhost:8000/api';

// Search videos
const searchResponse = await fetch(`${BASE_URL}/search/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'motivation and success',
    search_mode: 'hybrid'
  })
});

const results = await searchResponse.json();
```

### cURL Example

```bash
# Search videos
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "motivation and success",
    "search_mode": "hybrid"
  }'

# Get video details
curl http://localhost:8000/api/video/UUID/
```

## Support

For API support and questions, please refer to:
- Interactive API documentation: `/api/docs/`
- Architecture documentation: `docs/ARCHITECTURE.md`
- Search system documentation: `docs/SEARCH_SYSTEM.md`

