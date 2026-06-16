# AskMyVideo User Guide

## Introduction

AskMyVideo is an intelligent video search and recall system that allows you to upload videos, automatically transcribe them, and search through the content using natural language queries.

## Getting Started

### Creating an Account

1. Navigate to the registration page
2. Fill in your username, email, and password
3. Click "Register"
4. Log in with your credentials

### First Steps

1. **Upload Your First Video**: Click "Upload Video" in the library
2. **Wait for Processing**: Videos are processed automatically
3. **Start Searching**: Use the search interface to find content

## Features

### Video Upload

#### Uploading Files
1. Go to the Video Library
2. Click "Upload Video"
3. Select a video file (MP4, AVI, MOV, MKV, WEBM)
4. Wait for processing to complete

#### Processing YouTube Videos
1. Go to the Video Library
2. Paste a YouTube URL in the "YouTube URL" field
3. Click "Process"
4. The video will be downloaded and processed automatically

#### Processing YouTube Playlists
1. Paste a YouTube playlist URL
2. The system will process up to 10 videos from the playlist
3. Each video is processed individually

### Video Library

The Video Library shows:
- **All Your Videos**: List of uploaded/processed videos
- **Status Indicators**: 
  - 🟢 Completed: Ready for search
  - 🟡 Processing: Currently being transcribed
  - 🔴 Failed: Processing encountered an error
  - ⚪ Pending: Waiting to be processed
- **Video Information**: Title, duration, processing time
- **Quick Actions**: View, edit transcript, delete

### Search Functionality

#### Basic Search
1. Enter your search query in the search box
2. Select search mode:
   - **Keyword**: Exact text matching
   - **Semantic**: AI-powered meaning-based search
   - **Hybrid**: Combines both methods (recommended)
3. Click "Search"
4. Results show matching segments with timestamps
5. Click a result to jump to that moment in the video

#### Enhanced Search
Access enhanced search for:
- **Better Results**: Advanced AI models for improved accuracy
- **Diversification**: Results from different parts of videos
- **Topic Filtering**: Filter by specific topics
- **Similarity Control**: Adjust minimum similarity thresholds

#### Search Tips
- Use natural language: "How to build confidence" works better than "confidence building"
- Be specific: "relationship advice for long-distance couples" is better than "relationships"
- Try different search modes if results aren't satisfactory
- Use quotes for exact phrases: "exact phrase here"

### Transcript Editor

1. Open a video from your library
2. Click "Edit Transcript"
3. Make corrections to the transcription
4. Save your changes
5. Updated transcriptions improve search accuracy

### Video Management

#### Viewing Videos
- Click on any video in your library to view details
- Watch videos directly in the browser
- Jump to specific timestamps from search results

#### Deleting Videos
1. Go to your Video Library
2. Click "Delete" on the video you want to remove
3. Confirm deletion
4. Video and all associated data will be removed

#### Updating Metadata
- Edit video titles
- Add or update YouTube URLs
- Metadata updates are saved automatically

## Search Modes Explained

### Keyword Search
- **Best For**: Exact word or phrase matching
- **Example**: Searching for "Python programming" finds segments containing those exact words
- **Limitations**: Won't find synonyms or related concepts

### Semantic Search
- **Best For**: Finding content by meaning, not exact words
- **Example**: Searching for "building confidence" finds segments about "self-esteem", "self-assurance", etc.
- **Advantages**: Understands context and meaning

### Hybrid Search
- **Best For**: Balanced results combining exact matches and semantic similarity
- **Example**: Finds both exact keyword matches and semantically similar content
- **Recommended**: Best overall results for most queries

### Enhanced Search
- **Best For**: Highest quality results with advanced features
- **Features**: 
  - Better AI models
  - Result diversification
  - Topic extraction
  - Sentiment analysis
- **Use When**: You need the best possible search results

## Understanding Search Results

### Result Components

Each search result shows:
- **Video Title**: Name of the video
- **Timestamp**: Exact moment in the video (e.g., "2:30")
- **Segment Text**: The matching text segment
- **Relevance Score**: How well the result matches (0-1, higher is better)
- **Search Type**: Which search method found this result

### Interpreting Scores

- **0.9-1.0**: Excellent match, highly relevant
- **0.7-0.9**: Good match, relevant content
- **0.5-0.7**: Moderate match, somewhat relevant
- **Below 0.5**: Weak match, may not be relevant

### Using Timestamps

- Click any timestamp to jump directly to that moment
- Timestamps are formatted as "minutes:seconds"
- Results are sorted by relevance, not chronological order

## Public Search

### Public Search Interface
- Access at `/public/enhanced/`
- Search across all public videos
- No authentication required
- Same search capabilities as authenticated users

### User-Specific Public Search
- Access at `/search/<username>/`
- Search through a specific user's public videos
- Useful for sharing your video collection

## Tips and Best Practices

### Video Quality
- **Clear Audio**: Better audio = better transcriptions
- **Minimal Background Noise**: Reduces transcription errors
- **Single Speaker**: Works best with one clear speaker
- **Good Microphone Quality**: Improves accuracy

### Search Optimization
1. **Use Natural Language**: Write queries as you would ask a question
2. **Be Specific**: More specific queries yield better results
3. **Try Different Modes**: If one mode doesn't work, try another
4. **Refine Queries**: Start broad, then narrow down based on results

### Organization
- **Use Descriptive Titles**: Helps identify videos quickly
- **Edit Transcripts**: Correct errors to improve search
- **Delete Unused Videos**: Keeps your library organized
- **Regular Cleanup**: Remove failed or unwanted videos

## Troubleshooting

### Video Not Processing
- **Check File Format**: Ensure video is in supported format
- **Check File Size**: Very large files may take longer
- **Check Status**: Look for error messages in video details
- **Retry**: Sometimes processing fails due to temporary issues

### Poor Search Results
- **Try Different Search Mode**: Switch between keyword, semantic, and hybrid
- **Refine Query**: Make your search more specific
- **Check Transcription**: Poor transcriptions lead to poor search results
- **Edit Transcript**: Correct errors in transcription

### Video Playback Issues
- **Check Browser**: Ensure browser supports video playback
- **Check Format**: Video format must be browser-compatible
- **Check Network**: Slow connection may cause playback issues
- **Try Different Browser**: Some browsers handle video differently

### YouTube Processing Issues
- **Check URL**: Ensure YouTube URL is valid
- **Check Privacy**: Private/unlisted videos may not process
- **Check Availability**: Video must be publicly accessible
- **Wait**: YouTube processing can take longer than file uploads

## Keyboard Shortcuts

- **Search**: Press Enter in search box to submit
- **Navigate Results**: Use arrow keys to move through results
- **Play Video**: Spacebar to play/pause (when video is focused)

## FAQ

### How long does processing take?
Processing time depends on video length. Typically:
- 1 minute video: ~30 seconds
- 10 minute video: ~3-5 minutes
- 1 hour video: ~15-30 minutes

### What video formats are supported?
Supported formats: MP4, AVI, MOV, MKV, WEBM

### Can I search across multiple videos?
Yes! Search results include matches from all your processed videos.

### How accurate are transcriptions?
Transcription accuracy depends on:
- Audio quality
- Background noise
- Speaker clarity
- Language (English is most accurate)

Typically 90-95% accuracy for clear English audio.

### Can I edit transcriptions?
Yes! Use the Transcript Editor to correct any errors.

### What happens to my videos?
- Videos are stored securely
- Only you can access your videos (unless made public)
- You can delete videos at any time
- YouTube videos can be cleaned up to save space

### Is my data private?
Yes! Your videos and transcriptions are private by default. Only you can access them unless you share public links.

## Getting Help

- **Documentation**: Check other documentation files
- **API Documentation**: Visit `/api/docs/` for API reference
- **Architecture**: See `docs/ARCHITECTURE.md` for technical details

## Advanced Features

### RAG Question Answering
Ask questions and get AI-generated answers based on your video content:
1. Use the Enhanced Search interface
2. Enter a question instead of a search query
3. Get comprehensive answers with source citations

### Topic Filtering
Filter search results by topics:
1. Use Enhanced or Advanced Search
2. Specify topic tags in filter_topics
3. Results are filtered to matching topics

### Result Diversification
Get results from different parts of videos:
1. Enable diversification in Enhanced Search
2. Results are spread across different video segments
3. Prevents clustering of similar results

