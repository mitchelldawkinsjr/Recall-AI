# Database Schema Diagram

## Entity Relationship Diagram

```mermaid
erDiagram
    User ||--o{ VideoJob : owns
    User ||--o{ VideoSearchQuery : creates
    
    VideoJob {
        uuid job_id PK
        int user_id FK
        string video_path
        string video_name
        string youtube_url
        bigint file_size_bytes
        string status
        datetime created_at
        datetime updated_at
        datetime started_at
        datetime completed_at
        float processing_time
        text error_message
        json metadata
        json transcription
        json processing_errors
        string title
        text transcript
    }
    
    VideoSearchQuery {
        int id PK
        string query
        int results_count
        datetime created_at
    }
    
    User {
        int id PK
        string username
        string email
        string password
        datetime date_joined
    }
```

## VideoJob Model Structure

```mermaid
classDiagram
    class VideoJob {
        +UUID job_id
        +User user
        +str video_path
        +str video_name
        +str youtube_url
        +int file_size_bytes
        +str status
        +datetime created_at
        +datetime updated_at
        +datetime started_at
        +datetime completed_at
        +float processing_time
        +str error_message
        +dict metadata
        +dict transcription
        +list processing_errors
        +str title
        +str transcript
        +duration_seconds() float
        +resolution() str
        +transcription_text() str
        +text_segments() list
        +word_count() int
        +language() str
        +is_youtube_video() bool
        +get_youtube_video_id() str
        +search_segments(query) list
    }
    
    class JobStatus {
        <<enumeration>>
        PENDING
        PROCESSING
        COMPLETED
        FAILED
    }
    
    VideoJob --> JobStatus : status
```

## Data Flow Through Database

```mermaid
flowchart TD
    Start([Video Upload]) --> Create[Create VideoJob<br/>Status: PENDING]
    Create --> Store1[Store in Database]
    
    Store1 --> Process[Processing Starts]
    Process --> Update1[Update Status: PROCESSING<br/>Set started_at]
    Update1 --> Store2[Update Database]
    
    Store2 --> Complete[Processing Complete]
    Complete --> Update2[Update Status: COMPLETED<br/>Set completed_at<br/>Store metadata<br/>Store transcription]
    Update2 --> Store3[Update Database]
    
    Store3 --> Index[Index for Search]
    Index --> Ready([Video Ready])
    
    style Start fill:#e1f5e1
    style Ready fill:#e1f5e1
    style Store1 fill:#fff4e1
    style Store2 fill:#fff4e1
    style Store3 fill:#fff4e1
```

## Database Relationships

```mermaid
graph TB
    subgraph "User Table"
        User[User<br/>id, username, email]
    end
    
    subgraph "VideoJob Table"
        VideoJob[VideoJob<br/>job_id, user_id,<br/>video_path, status,<br/>metadata, transcription]
    end
    
    subgraph "VideoSearchQuery Table"
        SearchQuery[VideoSearchQuery<br/>id, query,<br/>results_count]
    end
    
    User -->|One to Many| VideoJob
    User -->|One to Many| SearchQuery
    
    style User fill:#e1f5e1
    style VideoJob fill:#fff4e1
    style SearchQuery fill:#fff4e1
```

## VideoJob Status Transitions

```mermaid
stateDiagram-v2
    [*] --> PENDING: Video Uploaded
    PENDING --> PROCESSING: Processing Started
    PROCESSING --> COMPLETED: Processing Success
    PROCESSING --> FAILED: Processing Error
    COMPLETED --> [*]: Video Ready
    FAILED --> [*]: Error Recorded
    
    note right of PENDING
        Initial state
        Video file saved
        Waiting for processing
    end note
    
    note right of PROCESSING
        Active processing
        Transcription in progress
        Metadata extraction
    end note
    
    note right of COMPLETED
        Processing complete
        Transcription stored
        Ready for search
    end note
    
    note right of FAILED
        Processing failed
        Error message stored
        Can be retried
    end note
```

## Transcription Data Structure

```mermaid
graph TB
    VideoJob --> Transcription[Transcription JSON]
    
    Transcription --> Text[text: Full transcription]
    Transcription --> Segments[text_segments: Array]
    Transcription --> Metadata[Metadata: Language, word_count]
    
    Segments --> Segment1[Segment 1<br/>start, end, text]
    Segments --> Segment2[Segment 2<br/>start, end, text]
    Segments --> SegmentN[Segment N<br/>start, end, text]
    
    style VideoJob fill:#e1f5e1
    style Transcription fill:#fff4e1
    style Segments fill:#fff4e1
```

## Search Query Tracking

```mermaid
flowchart LR
    User[User] --> Query[Search Query]
    Query --> Store[Store in VideoSearchQuery]
    Store --> Track[Track Results Count]
    Track --> Analytics[Analytics Data]
    
    style User fill:#e1f5e1
    style Analytics fill:#fff4e1
```

