from django.urls import include, path

from . import views

urlpatterns = [
    # Main interfaces
    path("", views.search_interface_view, name="home"),
    path("search/", views.search_videos, name="search_videos"),
    
    # Enhanced Search Interfaces
    path("enhanced/", views.enhanced_search_interface, name="enhanced_search"),
    path("public/enhanced/", views.public_enhanced_search_interface, name="public_enhanced_search"),
    
    # Public User-Specific Search (No authentication required, but searches specific user's videos)
    path("search/<str:username>/", views.public_user_search_interface, name="public_user_search"),
    path("search/<str:username>/enhanced/", views.public_user_enhanced_search_interface, name="public_user_enhanced_search"),
    
    # API endpoints for search functionality
    path("api/search/", views.api_search, name="api_search"),
    path("api/enhanced-search/", views.api_enhanced_search, name="api_enhanced_search"),
    path("api/advanced-search/", views.api_advanced_search, name="api_advanced_search"),
    path("api/rag-qa/", views.api_rag_qa, name="api_rag_qa"),
    
    # Teams API endpoints (for frontend compatibility)
    path("api/teams/summary/", views.api_teams_summary, name="api_teams_summary"),
    path("api/teams/", views.api_teams_list, name="api_teams_list"),
    
    # Health Check for load balancers
    path("health/", views.health_check, name="health_check"),
    path("api/health/", views.api_health_check, name="api_health_check"),
    
    # API endpoints for admin functionality
    path("api/search-status/", views.api_search_status, name="api_search_status"),
    path("api/pending-jobs/", views.api_pending_jobs, name="api_pending_jobs"),
    path("api/detailed-stats/", views.api_detailed_stats, name="api_detailed_stats"),
    path("api/rebuild-search-index/", views.api_rebuild_search_index, name="api_rebuild_search_index"),
    path("api/rebuild-enhanced-search-index/", views.api_rebuild_enhanced_search_index, name="api_rebuild_enhanced_search_index"),
    path("api/cleanup-youtube/", views.api_cleanup_youtube, name="api_cleanup_youtube"),
    path("api/process-job/", views.api_process_job, name="api_process_job"),
    path("api/video/<str:job_id>/", views.api_video_details, name="api_video_details"),
    path('api/video/<uuid:job_id>/update-metadata/', views.api_update_video_metadata, name='api_update_video_metadata'),
    
    # Hybrid processing endpoints
    path("api/hybrid/status/", views.api_hybrid_status, name="api_hybrid_status"),
    path("api/hybrid/processed/", views.api_hybrid_processed_status, name="api_hybrid_processed_status"),
    path("api/hybrid/process/", views.process_hybrid_batch, name="process_hybrid_batch"),
    
    # Authentication
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/register/", views.register_view, name="register"),
    path("register/", views.register_view, name="register_old"),  # Redirect for old URL
    
    # Private interfaces (Authentication required)
    path("library/", views.VideoLibraryView.as_view(), name="video_library"),
    
    # Video upload and processing 
    path("upload/", views.upload_video, name="upload_video"),
    
    # Video management
    path("delete/<str:job_id>/", views.delete_video, name="delete_video"),
    path("video-file/<str:job_id>/", views.video_file_serve, name="video_file_serve"),
    
    # Transcript editor
    path("transcript/<str:job_id>/", views.transcript_editor, name="transcript_editor"),
]
