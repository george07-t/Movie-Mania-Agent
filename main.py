from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import logging
from contextlib import asynccontextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

# Import your agent
from agent import graph
from langchain_core.messages import HumanMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory session storage (use Redis/Database in production)
chat_sessions: Dict[str, Dict] = {}

# Thread pool for running synchronous agent
executor = ThreadPoolExecutor(max_workers=4)

# Rate limiter configuration with Redis URL for production
REDIS_URL = os.getenv('REDIS_URL', None)
if REDIS_URL:
    from slowapi.middleware import SlowAPIMiddleware
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=REDIS_URL,
        default_limits=["1000/hour", "100/minute"]
    )
else:
    # Fallback to in-memory for development
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000/hour", "100/minute"]
    )

# FastAPI Configuration from Environment Variables
FASTAPI_HOST = os.getenv('FASTAPI_HOST', '0.0.0.0')
FASTAPI_PORT = int(os.getenv('FASTAPI_PORT', '8000'))
FASTAPI_RELOAD = os.getenv('FASTAPI_RELOAD', 'True').lower() in ('true', '1', 'yes', 'on')
FASTAPI_DEBUG = os.getenv('FASTAPI_DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
FASTAPI_LOG_LEVEL = os.getenv('FASTAPI_LOG_LEVEL', 'info').lower()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🎬 Movie Assistant API Starting...")
    logger.info(f"🌐 Host: {FASTAPI_HOST}")
    logger.info(f"🔌 Port: {FASTAPI_PORT}")
    logger.info(f"🔄 Reload: {FASTAPI_RELOAD}")
    logger.info(f"🐛 Debug: {FASTAPI_DEBUG}")
    yield
    logger.info("🎬 Movie Assistant API Shutting down...")
    executor.shutdown(wait=True)

# Initialize FastAPI app
app = FastAPI(
    title="Movie Assistant API",
    description="AI-powered movie recommendation and information API using TMDB",
    version="1.0.0",
    debug=FASTAPI_DEBUG,
    lifespan=lifespan
)

# Add rate limiting to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for mobile app
# Production: Replace "*" with specific domains
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # In production: ["https://yourdomain.com", "https://app.yourdomain.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Restrict methods
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation continuity")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    message_id: str = Field(..., description="Unique message ID")
    timestamp: datetime = Field(default_factory=datetime.now)

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    environment: dict

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime

class RateLimitResponse(BaseModel):
    error: str
    message: str
    limit: str
    retry_after: int
    timestamp: datetime

# Utility functions
def create_session_id() -> str:
    """Generate unique session ID"""
    return str(uuid.uuid4())

def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one"""
    if session_id and session_id in chat_sessions:
        # Update last activity
        chat_sessions[session_id]['last_activity'] = datetime.now()
        return session_id
    
    # Create new session
    new_session_id = create_session_id()
    chat_sessions[new_session_id] = {
        'messages': [],
        'created_at': datetime.now(),
        'last_activity': datetime.now(),
        'state': {'messages': []}
    }
    return new_session_id

async def run_agent_async(state: Dict) -> Dict:
    """Run the agent in a thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(executor, graph.invoke, state)
        return result
    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent processing failed: {str(e)}")

# Custom rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    response = RateLimitResponse(
        error="Rate limit exceeded",
        message=f"Too many requests. Limit: {exc.detail}",
        limit=exc.detail,
        retry_after=60,  # seconds
        timestamp=datetime.now()
    )
    return HTTPException(status_code=429, detail=response.dict())

# Security and validation
def validate_environment():
    """Validate required environment variables"""
    required_vars = ['tmdb_api_key']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

# Validate environment on startup
validate_environment()

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# API Endpoints

@app.get("/", response_model=HealthResponse)
@limiter.limit("100/minute")
async def root(request: Request):
    """Health check endpoint with environment info"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        environment={
            "host": FASTAPI_HOST,
            "port": FASTAPI_PORT,
            "reload": FASTAPI_RELOAD,
            "debug": FASTAPI_DEBUG,
            "log_level": FASTAPI_LOG_LEVEL
        }
    )

@app.get("/health", response_model=HealthResponse)
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Detailed health check"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        environment={
            "host": FASTAPI_HOST,
            "port": FASTAPI_PORT,
            "reload": FASTAPI_RELOAD,
            "debug": FASTAPI_DEBUG,
            "log_level": FASTAPI_LOG_LEVEL,
            "active_sessions": len(chat_sessions),
            "total_messages": sum(len(session['messages']) for session in chat_sessions.values())
        }
    )

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")  # 10 chat messages per minute per IP
async def chat_with_agent(request: Request, chat_request: ChatRequest):
    """
    Main chat endpoint for movie recommendations and information
    Rate limited to 10 requests per minute to prevent abuse of AI processing
    """
    try:
        # Get or create session
        session_id = get_or_create_session(chat_request.session_id)
        session = chat_sessions[session_id]
        
        # Add user message to session
        user_message = ChatMessage(role="user", content=chat_request.message)
        session['messages'].append(user_message.dict())
        
        # Prepare agent state
        agent_state = session['state'].copy()
        agent_state['messages'].append(HumanMessage(content=chat_request.message))
        
        # Run agent
        logger.info(f"Processing message for session {session_id}: {chat_request.message[:50]}...")
        result = await run_agent_async(agent_state)
        
        # Extract AI response
        ai_response = result['messages'][-1].content
        
        # Update session state
        session['state'] = result
        
        # Add AI response to session history
        ai_message = ChatMessage(role="assistant", content=ai_response)
        session['messages'].append(ai_message.dict())
        session['last_activity'] = datetime.now()
        
        message_id = str(uuid.uuid4())
        
        logger.info(f"Response generated for session {session_id}")
        
        return ChatResponse(
            response=ai_response,
            session_id=session_id,
            message_id=message_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/sessions", response_model=List[SessionInfo])
@limiter.limit("20/minute")
async def get_sessions(request: Request):
    """Get all active sessions (for debugging/monitoring)"""
    sessions = []
    for session_id, session_data in chat_sessions.items():
        sessions.append(SessionInfo(
            session_id=session_id,
            created_at=session_data['created_at'],
            last_activity=session_data['last_activity'],
            message_count=len(session_data['messages'])
        ))
    return sessions

@app.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
@limiter.limit("30/minute")
async def get_session_messages(request: Request, session_id: str):
    """Get conversation history for a session"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return [ChatMessage(**msg) for msg in chat_sessions[session_id]['messages']]

@app.delete("/sessions/{session_id}")
@limiter.limit("10/minute")
async def delete_session(request: Request, session_id: str):
    """Delete a chat session"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del chat_sessions[session_id]
    return {"message": f"Session {session_id} deleted successfully"}

@app.delete("/sessions")
@limiter.limit("5/minute")  # More restrictive for clearing all sessions
async def clear_all_sessions(request: Request):
    """Clear all chat sessions (for debugging)"""
    chat_sessions.clear()
    return {"message": "All sessions cleared"}

@app.post("/sessions/{session_id}/reset")
@limiter.limit("15/minute")
async def reset_session(request: Request, session_id: str):
    """Reset a session's conversation history"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    chat_sessions[session_id]['messages'] = []
    chat_sessions[session_id]['state'] = {'messages': []}
    chat_sessions[session_id]['last_activity'] = datetime.now()
    
    return {"message": f"Session {session_id} reset successfully"}

# Movie endpoints with appropriate rate limits
@app.get("/movies/search/{query}")
@limiter.limit("30/minute")  # Search is commonly used, allow more requests
async def search_movies_endpoint(request: Request, query: str):
    """Quick movie search endpoint"""
    try:
        from tools import search_movies
        result = search_movies.invoke({"query": query})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/popular")
@limiter.limit("60/minute")  # Popular movies can be cached, allow more requests
async def get_popular_movies(request: Request):
    """Get popular movies"""
    try:
        from tools import get_movie_lists
        result = get_movie_lists.invoke({"list_type": "popular"})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/top-rated")
@limiter.limit("60/minute")
async def get_top_rated_movies(request: Request):
    """Get top rated movies"""
    try:
        from tools import get_movie_lists
        result = get_movie_lists.invoke({"list_type": "top_rated"})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/now-playing")
@limiter.limit("60/minute")
async def get_now_playing_movies(request: Request):
    """Get now playing movies"""
    try:
        from tools import get_movie_lists
        result = get_movie_lists.invoke({"list_type": "now_playing"})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/upcoming")
@limiter.limit("60/minute")
async def get_upcoming_movies(request: Request):
    """Get upcoming movies"""
    try:
        from tools import get_movie_lists
        result = get_movie_lists.invoke({"list_type": "upcoming"})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/{movie_id}/details")
@limiter.limit("50/minute")  # Movie details are specific lookups
async def get_movie_details_endpoint(request: Request, movie_id: int):
    """Get detailed movie information"""
    try:
        from tools import get_movie_details
        result = get_movie_details.invoke({"movie_id": movie_id})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/{movie_id}/watch-providers")
@limiter.limit("40/minute")  # Watch providers involve external API calls
async def get_watch_providers_endpoint(request: Request, movie_id: int, region: str = "US"):
    """Get streaming/watch providers for a movie"""
    try:
        from tools import get_watch_providers
        result = get_watch_providers.invoke({"movie_id": movie_id, "region": region})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/{movie_id}/recommendations")
@limiter.limit("30/minute")
async def get_movie_recommendations_endpoint(request: Request, movie_id: int):
    """Get movie recommendations"""
    try:
        from tools import get_movie_recommendations
        result = get_movie_recommendations.invoke({"movie_id": movie_id})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/trending/{time_window}")
@limiter.limit("50/minute")
async def get_trending_movies_endpoint(request: Request, time_window: str = "day"):
    """Get trending movies (day/week)"""
    try:
        from tools import get_trending_movies
        result = get_trending_movies.invoke({"time_window": time_window})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/movies/discover")
@limiter.limit("40/minute")
async def discover_movies_endpoint(
    request: Request, 
    genre_id: Optional[int] = None, 
    sort_by: str = "popularity.desc"
):
    """Discover movies by genre and sorting"""
    try:
        from tools import discover_movies
        result = discover_movies.invoke({"genre_id": genre_id, "sort_by": sort_by})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoint
@app.get("/config")
@limiter.limit("10/minute")
async def get_config(request: Request):
    """Get API configuration information"""
    return {
        "server_config": {
            "host": FASTAPI_HOST,
            "port": FASTAPI_PORT,
            "reload": FASTAPI_RELOAD,
            "debug": FASTAPI_DEBUG,
            "log_level": FASTAPI_LOG_LEVEL
        },
        "rate_limits": {
            "chat": "10/minute - AI chat processing",
            "search": "30/minute - Movie search",
            "popular_movies": "60/minute - Popular/trending lists",
            "movie_details": "50/minute - Detailed movie info",
            "watch_providers": "40/minute - Streaming availability",
            "recommendations": "30/minute - Movie recommendations",
            "sessions": "20/minute - Session management",
            "health": "100/minute - Health checks"
        },
        "note": "Rate limits are per IP address per minute",
        "android_app_tips": [
            "Cache popular movies locally",
            "Implement retry logic with exponential backoff",
            "Show loading states during API calls",
            "Handle 429 errors gracefully"
        ]
    }

# Rate limiting info endpoint (kept for backward compatibility)
@app.get("/rate-limits")
@limiter.limit("10/minute")
async def get_rate_limits(request: Request):
    """Get information about current rate limits"""
    return {
        "rate_limits": {
            "chat": "10/minute - AI chat processing",
            "search": "30/minute - Movie search",
            "popular_movies": "60/minute - Popular/trending lists",
            "movie_details": "50/minute - Detailed movie info",
            "watch_providers": "40/minute - Streaming availability",
            "recommendations": "30/minute - Movie recommendations",
            "sessions": "20/minute - Session management",
            "health": "100/minute - Health checks"
        },
        "note": "Rate limits are per IP address per minute",
        "android_app_tips": [
            "Cache popular movies locally",
            "Implement retry logic with exponential backoff",
            "Show loading states during API calls",
            "Handle 429 errors gracefully"
        ]
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": "HTTP Exception",
        "message": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    
    # Log startup configuration
    logger.info("🚀 Starting Movie Assistant API...")
    logger.info(f"🌐 Host: {FASTAPI_HOST}")
    logger.info(f"🔌 Port: {FASTAPI_PORT}")
    logger.info(f"🔄 Reload: {FASTAPI_RELOAD}")
    logger.info(f"🐛 Debug: {FASTAPI_DEBUG}")
    logger.info(f"📝 Log Level: {FASTAPI_LOG_LEVEL}")
    
    uvicorn.run(
        "main:app", 
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        reload=FASTAPI_RELOAD,
        log_level=FASTAPI_LOG_LEVEL
    )