import requests
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.getenv('tmdb_api_key')
MOVIE_LIST_TYPES = {
    'popular': 'popular',
    'top_rated': 'top_rated',
    'now_playing': 'now_playing',
    'upcoming': 'upcoming'
}

GENRE_MAPPING = {
    # Action & Adventure
    'action': 28,
    'adventure': 12,
    'thriller': 53,

    # Comedy & Drama
    'comedy': 35,
    'funny': 35,
    'drama': 18,

    # Horror & Mystery
    'horror': 27,
    'scary': 27,
    'mystery': 9648,

    # Romance & Family
    'romance': 10749,
    'romantic': 10749,
    'family': 10751,

    # Sci-Fi & Fantasy
    'science fiction': 878,
    'sci-fi': 878,
    'fantasy': 14,

    # Other
    'documentary': 99,
    'animation': 16,
    'crime': 80,
    'war': 10752,
    'western': 37
}


@tool(parse_docstring=True)
def get_movie_details(movie_id: int, append_credits: bool = True) -> dict:
    """
    Get detailed information about a specific movie including cast, crew, and ratings.

    Args:
        movie_id (int): The TMDB movie ID to get details for.
        append_credits (bool): Whether to include cast and crew information, defaults to True.

    Returns:
        dict: JSON response containing detailed movie information including title, overview,
              cast, crew, runtime, budget, revenue, and ratings.

    Example:
        >>> get_movie_details(157336)
        {'title': 'Interstellar', 'runtime': 169, 'vote_average': 8.4, ...}
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        'api_key': API_KEY,
        'language': 'en-US'
    }

    if append_credits:
        params['append_to_response'] = 'credits'

    response = requests.get(url, params=params).json()

    # Filter to essential fields only
    filtered_response = {
        'id': response.get('id'),
        'title': response.get('title'),
        'overview': response.get('overview'),
        'release_date': response.get('release_date'),
        'runtime': response.get('runtime'),
        'vote_average': response.get('vote_average'),
        'vote_count': response.get('vote_count'),
        'budget': response.get('budget'),
        'revenue': response.get('revenue'),
        'genres': [genre['name'] for genre in response.get('genres', [])],
    }

    # Add cast and crew if credits are included
    if 'credits' in response:
        credits = response['credits']
        filtered_response['cast'] = [
            {
                'name': person['name'],
                'character': person['character']
            }
            for person in credits.get('cast', [])[:10]  # Limit to top 10 cast
        ]

        # Get director from crew
        crew = credits.get('crew', [])
        directors = [person['name']
                     for person in crew if person['job'] == 'Director']
        filtered_response['director'] = directors[0] if directors else None

    return filtered_response


@tool(parse_docstring=True)
def search_movies(query: str, page: int = 1) -> dict:
    """
    Search for movies by title or name using TMDB API.

    Args:
        query (str): The movie title or name to search for (e.g., "Interstellar", "Oppenheimer").
        page (int): Page number for pagination, defaults to 1.

    Returns:
        dict: JSON response containing search results with movie information including title, 
              release date, overview, rating, and poster path.

    Example:
        >>> search_movies("Interstellar")
        {'results': [{'title': 'Interstellar', 'release_date': '2014-11-07', ...}]}
    """
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        'api_key': API_KEY,
        'query': query,
        'page': page,
        'language': 'en-US'
    }
    response = requests.get(url, params=params).json()

    # Filter to only essential fields
    if 'results' in response:
        filtered_results = []
        for movie in response['results'][:5]:  # Limit to top 5 results
            filtered_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview', '')[:200] + '...' if len(movie.get('overview', '')) > 200 else movie.get('overview', '')
            }
            filtered_results.append(filtered_movie)

        return {
            'results': filtered_results,
            'total_results': min(response.get('total_results', 0), 5)
        }

    return response


@tool(parse_docstring=True)
def discover_movies(genre_id: int = None, sort_by: str = 'popularity.desc', page: int = 1) -> dict:
    """
    Discover movies by genre, popularity, ratings, and year.

    Args:
        genre_id (int, optional): The genre ID to filter movies by (e.g., 28 for Action).
        sort_by (str): Sort criteria for results, defaults to 'popularity.desc'.
        page (int): Page number for pagination, defaults to 1.

    Returns:
        dict: JSON response containing discovered movies matching the specified criteria.

    Example:
        >>> discover_movies(genre_id=28, page=1)
        {'results': [{'title': 'Action Movie', 'genre_ids': [28], ...}]}
    """
    url = f"https://api.themoviedb.org/3/discover/movie"
    params = {
        'api_key': API_KEY,
        'language': 'en-US',
        'sort_by': sort_by,
        'page': page,
        'include_adult': False
    }

    if genre_id:
        params['with_genres'] = genre_id

    response = requests.get(url, params=params).json()

    # Filter to only essential fields
    if 'results' in response:
        filtered_results = []
        for movie in response['results'][:5]:  # Limit to top 5 results
            filtered_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview', '')[:150] + '...' if len(movie.get('overview', '')) > 150 else movie.get('overview', '')
            }
            filtered_results.append(filtered_movie)

        return {
            'results': filtered_results,
            'total_results': min(response.get('total_results', 0), 5)
        }

    return response


@tool(parse_docstring=True)
def get_movie_lists(list_type: str = 'popular', page: int = 1) -> dict:
    """
    Get popular, top-rated, now-playing, or upcoming movies from TMDB.

    Args:
        list_type (str): Type of movie list to retrieve. Options: 'popular', 'top_rated', 
                        'now_playing', 'upcoming'. Defaults to 'popular'.
        page (int): Page number for pagination, defaults to 1.

    Returns:
        dict: JSON response containing list of movies with details like title, release date,
              overview, rating, and poster path.

    Example:
        >>> get_movie_lists('popular')
        {'results': [{'title': 'Popular Movie', 'vote_average': 8.5, ...}]}
    """
    url = f"https://api.themoviedb.org/3/movie/{list_type}"
    params = {
        'api_key': API_KEY,
        'language': 'en-US',
        'page': page
    }
    response = requests.get(url, params=params).json()

    # Filter to only essential fields
    if 'results' in response:
        filtered_results = []
        for movie in response['results'][:5]:  # Limit to top 5 results
            filtered_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview', '')[:150] + '...' if len(movie.get('overview', '')) > 150 else movie.get('overview', '')
            }
            filtered_results.append(filtered_movie)

        return {
            'results': filtered_results,
            'total_results': min(response.get('total_results', 0), 5)
        }

    return response


@tool(parse_docstring=True)
def get_trending_movies(time_window: str = 'day', page: int = 1) -> dict:
    """
    Get trending movies for a specified time window from TMDB.

    Args:
        time_window (str): Time period for trending movies. Options: 'day', 'week'. 
                          Defaults to 'day'.
        page (int): Page number for pagination, defaults to 1.

    Returns:
        dict: JSON response containing trending movies for the specified time period.

    Example:
        >>> get_trending_movies('day')
        {'results': [{'title': 'Trending Movie', 'vote_average': 8.2, ...}]}
    """
    url = f"https://api.themoviedb.org/3/trending/movie/{time_window}"
    params = {
        'api_key': API_KEY,
        'page': page
    }
    response = requests.get(url, params=params).json()

    # Filter to only essential fields
    if 'results' in response:
        filtered_results = []
        for movie in response['results'][:5]:  # Limit to top 5 results
            filtered_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview', '')[:150] + '...' if len(movie.get('overview', '')) > 150 else movie.get('overview', '')
            }
            filtered_results.append(filtered_movie)

        return {
            'results': filtered_results,
            'total_results': min(response.get('total_results', 0), 5)
        }

    return response


@tool(parse_docstring=True)
def get_movie_recommendations(movie_id: int, page: int = 1) -> dict:
    """
    Get similar or recommended movies based on a specific movie from TMDB.

    Args:
        movie_id (int): The TMDB movie ID to get recommendations for.
        page (int): Page number for pagination, defaults to 1.

    Returns:
        dict: JSON response containing recommended movies similar to the input movie.

    Example:
        >>> get_movie_recommendations(157336)
        {'results': [{'title': 'Similar Movie', 'vote_average': 7.8, ...}]}
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
    params = {
        'api_key': API_KEY,
        'language': 'en-US',
        'page': page
    }
    response = requests.get(url, params=params).json()

    # Filter to only essential fields
    if 'results' in response:
        filtered_results = []
        for movie in response['results'][:5]:  # Limit to top 5 results
            filtered_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview', '')[:150] + '...' if len(movie.get('overview', '')) > 150 else movie.get('overview', '')
            }
            filtered_results.append(filtered_movie)

        return {
            'results': filtered_results,
            'total_results': min(response.get('total_results', 0), 5)
        }

    return response

@tool(parse_docstring=True)
def get_watch_providers(movie_id: int, region: str = 'US') -> dict:
    """
    Get streaming availability and watch options for a movie by region.

    Args:
        movie_id (int): The TMDB movie ID to get watch providers for.
        region (str): Country code for regional availability (e.g., 'US', 'GB', 'CA'). 
                     Defaults to 'US'.

    Returns:
        dict: JSON response containing streaming, rental, and purchase options for the movie
              in the specified region.

    Example:
        >>> get_watch_providers(550)
        {'streaming': ['Netflix', 'Hulu'], 'rent': ['Amazon Video'], 'buy': ['iTunes']}
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
    params = {
        'api_key': API_KEY,
        'language': 'en-US'
    }
    
    response = requests.get(url, params=params).json()
    
    # Extract and format providers for specific region
    if 'results' in response and region in response['results']:
        providers_data = response['results'][region]
        
        formatted_response = {
            'movie_id': movie_id,
            'region': region,
            'streaming': [],
            'rent': [],
            'buy': [],
            'link': providers_data.get('link', '')
        }
        
        # Streaming services (flatrate/subscription)
        if 'flatrate' in providers_data:
            formatted_response['streaming'] = [
                provider['provider_name'] for provider in providers_data['flatrate']
            ]
        
        # Rental options
        if 'rent' in providers_data:
            formatted_response['rent'] = [
                provider['provider_name'] for provider in providers_data['rent']
            ]
        
        # Purchase options
        if 'buy' in providers_data:
            formatted_response['buy'] = [
                provider['provider_name'] for provider in providers_data['buy']
            ]
        
        return formatted_response
    
    else:
        return {
            'movie_id': movie_id,
            'region': region,
            'streaming': [],
            'rent': [],
            'buy': [],
            'message': f'No streaming information available for this movie in {region}',
            'link': ''
        }

# # Test cases for the movie API functions
# if __name__ == "__main__":
#     print("Testing Movie API Functions...")
#     print("=" * 50)

#     # Test 1: Search Movies
#     print("\n1. Testing search_movies('Interstellar'):")
#     try:
#         result = search_movies.invoke({"query": "Interstellar"})
#         if result.get('results'):
#             movie = result['results'][0]
#             print(f"✓ Found: {movie['title']} ({movie.get('release_date', 'N/A')})")
#         else:
#             print("✗ No results found")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 2: Get Movie Details
#     print("\n2. Testing get_movie_details(157336):")  # Interstellar movie ID
#     try:
#         result = get_movie_details.invoke({"movie_id": 157336})
#         print(f"✓ Title: {result.get('title', 'N/A')}")
#         print(f"✓ Runtime: {result.get('runtime', 'N/A')} minutes")
#         print(f"✓ Rating: {result.get('vote_average', 'N/A')}/10")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 3: Discover Movies by Genre
#     print("\n3. Testing discover_movies with action genre:")
#     try:
#         result = discover_movies.invoke({"genre_id": 28, "page": 1})  # Action genre
#         if result.get('results'):
#             movie = result['results'][0]
#             print(f"✓ Found action movie: {movie['title']}")
#         else:
#             print("✗ No results found")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 4: Get Popular Movies
#     print("\n4. Testing get_movie_lists('popular'):")
#     try:
#         result = get_movie_lists.invoke({"list_type": "popular"})
#         if result.get('results'):
#             movie = result['results'][0]
#             print(f"✓ Popular movie: {movie['title']}")
#         else:
#             print("✗ No results found")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 5: Get Movie Recommendations
#     print("\n5. Testing get_movie_recommendations(157336):")  # Interstellar
#     try:
#         result = get_movie_recommendations.invoke({"movie_id": 157336})
#         if result.get('results'):
#             movie = result['results'][0]
#             print(f"✓ Recommended: {movie['title']}")
#         else:
#             print("✗ No recommendations found")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 6: Get Trending Movies
#     print("\n6. Testing get_trending_movies('day'):")
#     try:
#         result = get_trending_movies.invoke({"time_window": "day"})
#         if result.get('results'):
#             movie = result['results'][0]
#             print(f"✓ Trending: {movie['title']}")
#         else:
#             print("✗ No trending movies found")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 7: Get Watch Providers
#     print("\n7. Testing get_watch_providers(550):")  # Fight Club movie ID
#     try:
#         result = get_watch_providers.invoke({"movie_id": 550, "region": "US"})
#         print(f"✓ Movie ID: {result.get('movie_id')}")
#         print(f"✓ Region: {result.get('region')}")
#         if result.get('streaming'):
#             print(f"✓ Streaming on: {', '.join(result['streaming'])}")
#         else:
#             print("✗ No streaming options found")
#         if result.get('rent'):
#             print(f"✓ Rent from: {', '.join(result['rent'])}")
#         if result.get('buy'):
#             print(f"✓ Buy from: {', '.join(result['buy'])}")
#         if result.get('message'):
#             print(f"ℹ {result['message']}")
#     except Exception as e:
#         print(f"✗ Error: {e}")

#     # Test 8: Watch Providers for Different Regions
#     print("\n8. Testing get_watch_providers(157336) for different regions:")
#     regions_to_test = ['US', 'GB', 'CA']
#     for region in regions_to_test:
#         try:
#             result = get_watch_providers.invoke({"movie_id": 157336, "region": region})  # Interstellar
#             print(f"  {region}: ", end="")
#             if result.get('streaming') or result.get('rent') or result.get('buy'):
#                 available = []
#                 if result.get('streaming'):
#                     available.append(f"Stream: {', '.join(result['streaming'])}")
#                 if result.get('rent'):
#                     available.append(f"Rent: {', '.join(result['rent'])}")
#                 if result.get('buy'):
#                     available.append(f"Buy: {', '.join(result['buy'])}")
#                 print(" | ".join(available))
#             else:
#                 print("No providers available")
#         except Exception as e:
#             print(f"{region}: Error - {e}")

#     # Test 9: Genre Mapping Test
#     print("\n9. Testing GENRE_MAPPING:")
#     test_genres = ['action', 'comedy', 'horror', 'romance']
#     for genre in test_genres:
#         if genre in GENRE_MAPPING:
#             print(f"✓ {genre}: {GENRE_MAPPING[genre]}")
#         else:
#             print(f"✗ {genre}: Not found")

#     print("\n" + "=" * 50)
#     print("Testing complete!")