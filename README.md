# 🎬 Movie Assistant AI - API Backend

A powerful AI-powered movie recommendation and information system built with FastAPI, LangGraph, and TMDB API integration. Features intelligent conversational AI for movie discovery, detailed information retrieval, and streaming availability.

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Setup & Installation](#-setup--installation)
- [Environment Configuration](#-environment-configuration)
- [API Endpoints](#-api-endpoints)
- [Rate Limiting](#-rate-limiting)
- [AI Agent Architecture](#-ai-agent-architecture)
- [Usage Examples](#-usage-examples)
- [Android Integration](#-android-integration)
- [Testing](#-testing)
- [Production Deployment](#-production-deployment)
- [Contributing](#-contributing)

## 🚀 Features

### Core Functionality
- **🤖 Conversational AI**: Natural language movie queries and recommendations
- **🔍 Movie Search**: Find movies by title, genre, or keywords
- **📊 Movie Details**: Cast, crew, ratings, runtime, and plot information
- **📺 Streaming Info**: Where to watch movies (Netflix, Hulu, Amazon Prime, etc.)
- **🎯 Recommendations**: Personalized movie suggestions based on preferences
- **📈 Trending**: Current popular and trending movies

### Technical Features
- **⚡ FastAPI Backend**: High-performance async API
- **🛡️ Rate Limiting**: Production-grade request limiting
- **💬 Session Management**: Persistent conversation history
- **🔄 Real-time Processing**: Async AI agent execution
- **📱 Mobile Ready**: CORS-enabled for Android apps
- **🔧 Comprehensive Logging**: Full request/response monitoring

## 🛠️ Tech Stack

- **Backend Framework**: FastAPI 0.104.1
- **AI Framework**: LangChain + LangGraph
- **Language Model**: Qwen2.5:14b (via Ollama)
- **Movie Data**: The Movie Database (TMDB) API
- **Rate Limiting**: SlowAPI
- **Server**: Uvicorn ASGI
- **Language**: Python 3.11+

## 📁 Project Structure

```
Movie App/
├── agent.py              # AI agent configuration and graph
├── tools.py              # TMDB API integration tools
├── main.py               # FastAPI application with rate limiting
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (API keys)
├── .gitignore           # Git ignore patterns
├── README.md            # This file
└── __pycache__/         # Python cache (auto-generated)
```

## 🔧 Setup & Installation

### Prerequisites
- Python 3.11 or higher
- Ollama (for local LLM)
- TMDB API account

### 1. Clone Repository
```bash
git clone <repository-url>
cd "Movie App"
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Ollama & Model
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the required model
ollama pull qwen2.5:14b
```

### 5. Get TMDB API Key
1. Visit [TMDB API](https://www.themoviedb.org/settings/api)
2. Create account and request API key
3. Copy your API key

## 🔐 Environment Configuration

Create a `.env` file in the project root:

```env
# TMDB API Configuration
tmdb_api_key=your_tmdb_api_key_here

#FastAPI Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_RELOAD=True
```

## 🌐 API Endpoints

### Chat & AI Endpoints

#### `POST /chat`
**Main conversational AI endpoint**
- **Rate Limit**: 10 requests/minute
- **Purpose**: Natural language movie queries
- **Request**:
```json
{
    "message": "Tell me about Interstellar",
    "session_id": "optional-session-id"
}
```
- **Response**:
```json
{
    "response": "Interstellar is a 2014 sci-fi epic...",
    "session_id": "abc-123-def-456",
    "message_id": "msg-789-xyz",
    "timestamp": "2025-01-12T10:30:00"
}
```

### Session Management

#### `GET /sessions`
- **Rate Limit**: 20/minute
- **Purpose**: List all active chat sessions
- **Response**: Array of session info objects

#### `GET /sessions/{session_id}/messages`
- **Rate Limit**: 30/minute
- **Purpose**: Get conversation history for a session
- **Response**: Array of chat messages

#### `POST /sessions/{session_id}/reset`
- **Rate Limit**: 15/minute
- **Purpose**: Clear conversation history

#### `DELETE /sessions/{session_id}`
- **Rate Limit**: 10/minute
- **Purpose**: Delete a specific session

#### `DELETE /sessions`
- **Rate Limit**: 5/minute
- **Purpose**: Clear all sessions (debugging)

### Movie Data Endpoints

#### `GET /movies/search/{query}`
- **Rate Limit**: 30/minute
- **Purpose**: Search movies by title
- **Example**: `/movies/search/Inception`

#### `GET /movies/popular`
- **Rate Limit**: 60/minute
- **Purpose**: Get popular movies

#### `GET /movies/top-rated`
- **Rate Limit**: 60/minute
- **Purpose**: Get top-rated movies

#### `GET /movies/now-playing`
- **Rate Limit**: 60/minute
- **Purpose**: Get currently playing movies

#### `GET /movies/upcoming`
- **Rate Limit**: 60/minute
- **Purpose**: Get upcoming movies

#### `GET /movies/{movie_id}/details`
- **Rate Limit**: 50/minute
- **Purpose**: Get detailed movie information
- **Example**: `/movies/157336/details`

#### `GET /movies/{movie_id}/watch-providers`
- **Rate Limit**: 40/minute
- **Purpose**: Get streaming availability
- **Parameters**: `region` (default: "US")
- **Example**: `/movies/157336/watch-providers?region=US`

#### `GET /movies/{movie_id}/recommendations`
- **Rate Limit**: 30/minute
- **Purpose**: Get movie recommendations

#### `GET /movies/trending/{time_window}`
- **Rate Limit**: 50/minute
- **Purpose**: Get trending movies
- **Parameters**: `time_window` ("day" or "week")

#### `GET /movies/discover`
- **Rate Limit**: 40/minute
- **Purpose**: Discover movies by genre
- **Parameters**: `genre_id`, `sort_by`

### System Endpoints

#### `GET /health`
- **Rate Limit**: 100/minute
- **Purpose**: Health check and system status

#### `GET /rate-limits`
- **Rate Limit**: 10/minute
- **Purpose**: Get current rate limiting information

## ⚡ Rate Limiting

### Rate Limit Configuration

| Endpoint Category | Limit | Reasoning |
|------------------|--------|-----------|
| **AI Chat** (`/chat`) | 10/minute | AI processing is expensive |
| **Movie Search** | 30/minute | Common browsing activity |
| **Movie Lists** | 60/minute | Cacheable data, high frequency |
| **Movie Details** | 50/minute | Specific lookups |
| **Streaming Info** | 40/minute | External API dependency |
| **Session Management** | 20/minute | User management |
| **Health Checks** | 100/minute | Monitoring needs |

### Rate Limit Headers
All responses include rate limiting headers:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1642012345
```

### Rate Limit Exceeded Response
```json
{
    "error": "Rate limit exceeded",
    "message": "Too many requests. Limit: 10/minute",
    "limit": "10/minute",
    "retry_after": 60,
    "timestamp": "2025-01-12T10:30:00"
}
```

## 🤖 AI Agent Architecture

### LangGraph Workflow

```mermaid
graph TD
    A[User Input] --> B[LLM Node]
    B --> C{Tool Calls?}
    C -->|Yes| D[Tool Execution]
    C -->|No| E[Final Response]
    D --> F[Search Movies]
    D --> G[Get Details]
    D --> H[Get Providers]
    D --> I[Other Tools]
    F --> B
    G --> B
    H --> B
    I --> B
    E --> J[Response to User]
```

### Available Tools

1. **search_movies**: Find movies by title
2. **get_movie_details**: Detailed movie information
3. **discover_movies**: Browse by genre/criteria
4. **get_movie_lists**: Popular/trending lists
5. **get_movie_recommendations**: Similar movie suggestions
6. **get_trending_movies**: Current trends
7. **get_watch_providers**: Streaming availability

### System Prompt
The AI agent uses a comprehensive system prompt that:
- Defines available tools and their purposes
- Provides genre ID mappings
- Sets conversation guidelines
- Includes example interaction patterns

## 📱 Usage Examples

### Basic Movie Search
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about Interstellar"
  }'
```

### Where to Watch Query
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Where can I watch The Dark Knight?",
    "session_id": "your-session-id"
  }'
```

### Genre Recommendations
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Recommend me some action movies"
  }'
```

### Direct Movie Search
```bash
curl "http://localhost:8000/movies/search/Inception"
```

### Get Movie Details
```bash
curl "http://localhost:8000/movies/157336/details"
```

### Check Streaming Availability
```bash
curl "http://localhost:8000/movies/157336/watch-providers?region=US"
```

## 📱 Android Integration

### Retrofit Setup
Add to your Android `build.gradle`:
```kotlin
dependencies {
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.12.0'
    implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'
}
```

### API Service Interface
```kotlin
interface MovieApiService {
    @POST("chat")
    suspend fun sendChatMessage(@Body request: ChatRequest): Response<ChatResponse>
    
    @GET("movies/popular")
    suspend fun getPopularMovies(): Response<MovieSearchResult>
    
    @GET("movies/{movie_id}/details")
    suspend fun getMovieDetails(@Path("movie_id") movieId: Int): Response<MovieDetails>
}
```

### Base URL Configuration
```kotlin
private const val BASE_URL = "http://10.0.2.2:8000/" // Android emulator
// For real device: "http://your-server-ip:8000/"
```

### Error Handling
```kotlin
try {
    val response = apiService.sendChatMessage(request)
    if (response.isSuccessful) {
        // Handle success
    } else if (response.code() == 429) {
        // Handle rate limiting
    }
} catch (e: Exception) {
    // Handle network errors
}
```

## 🧪 Testing

### Run the Server
```bash
python main.py
```

### Test Endpoints with cURL

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Chat Test
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are some good sci-fi movies?"}'
```

#### Movie Search Test
```bash
curl http://localhost:8000/movies/search/Avatar
```

### Interactive Testing
Visit `http://localhost:8000/docs` for Swagger UI documentation and interactive testing.

### Test Movie Tools
```bash
python tools.py
```

### Test AI Agent
```bash
python agent.py
```

## 🚀 Production Deployment

### Environment Variables
```env
# Production settings
tmdb_api_key=your_production_api_key
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_RELOAD=False

# Redis for session storage (recommended)
REDIS_URL=redis://localhost:6379

# Database for persistent storage
DATABASE_URL=postgresql://user:pass@localhost/moviedb
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use Redis for session storage instead of in-memory
- Implement database for persistent data
- Add authentication/authorization
- Set up monitoring and logging
- Use HTTPS in production
- Configure proper CORS origins
- Implement caching for TMDB responses
- Add request/response validation
- Set up backup and recovery

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

### Code Style
- Follow PEP 8 for Python code
- Use type hints where applicable
- Add docstrings for functions
- Keep functions focused and small
- Use meaningful variable names

### Testing Guidelines
- Test all new endpoints
- Verify rate limiting works
- Test error handling
- Check AI agent responses
- Validate API integrations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the rate limiting info at `/rate-limits`

## 🔄 API Versions

**Current Version**: v1.0.0
- Initial release with full movie AI functionality
- Rate limiting implementation
- Session management
- TMDB integration
- Android-ready endpoints

---

**Built with ❤️ for movie enthusiasts and developers**