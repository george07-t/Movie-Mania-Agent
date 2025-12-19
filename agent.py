from typing import TypedDict, Annotated, Sequence
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
import requests
from tools import get_watch_providers, search_movies, get_movie_details, discover_movies, get_movie_lists, get_movie_recommendations, get_trending_movies
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
load_dotenv()
# Replace your current LLM setup with:
GROQ_API_KEY = os.getenv('groq_api_key')
system_prompt = SystemMessage(content="""You are a Movie Assistant AI with access to TMDB movie database tools.

Available Tools:
- search_movies: Find movies by title
- get_movie_details: Get full movie info (cast, crew, ratings)  
- discover_movies: Find movies by genre/popularity
- get_movie_lists: Get popular/top-rated/trending lists
- get_movie_recommendations: Get similar movies
- get_trending_movies: Get current trending films
- get_watch_providers: Find where to watch/stream movies

Genres: Action(28), Comedy(35), Drama(18), Horror(27), Romance(10749), Sci-Fi(878), etc.

Guidelines:
- Use multiple tools for complete answers if needed
- Be conversational and engaging
- Provide cast, ratings, and plot when relevant
- Offer recommendations when appropriate
- Format responses clearly with key details
- For "where to watch" queries: search_movies → get_watch_providers
- Don't answer if not related to your task, then explain why you can't answer this.

Examples: 1. "popular/ trending movies?" → get_trending_movies. 2. For "Where can I watch Inception?" → search_movies → get_watch_providers""")


class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


#CHAT_MODEL = 'qwen2.5:14b'
chat_model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
#chat_model='llama-3.1-8b-instant'
#llm = init_chat_model(CHAT_MODEL, model_provider='ollama')
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=chat_model,  # Excellent for tool calling
    temperature=0.1,
    max_tokens=2048
)
llm = llm.bind_tools([get_watch_providers, search_movies, get_movie_details,
                     discover_movies, get_movie_lists, get_movie_recommendations, get_trending_movies])

#raw_llm = init_chat_model(CHAT_MODEL, model_provider='ollama')


def llm_node(state: ChatState) -> ChatState:
    response = llm.invoke([system_prompt]+state['messages'])
    return {'messages': [response]}


def should_continue(state: ChatState):
    last_message = state['messages'][-1]
    # print(f"should_continue last message: {last_message}")
    if not last_message.tool_calls:
        return 'end'
    else:
        return 'continue'


def router(state: ChatState) -> ChatState:
    last_message = state['messages'][-1]
    # print(f"Router last message: {last_message}")
    return 'tools' if getattr(last_message, 'tool_calls', None) else 'end'


tool_node = ToolNode([get_watch_providers,  search_movies, get_movie_details, discover_movies,
                     get_movie_lists, get_movie_recommendations, get_trending_movies])


def tools_node(state):

    result = tool_node.invoke(state)
    print(f"tools_node result: {result}")
    return {
        'messages': state['messages'] + result['messages']
    }


builder = StateGraph(ChatState)
builder.add_node('llm', llm_node)
builder.add_node('tools', tool_node)
builder.add_edge(START, 'llm')
builder.add_edge('tools', 'llm')
builder.add_conditional_edges('llm', should_continue, {
                              'continue': 'tools', 'end': END})

graph = builder.compile()


def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()


if __name__ == '__main__':
    state = {'messages': []}

    print('Type an instruction or "quit".\n')

    while True:
        user_message = input('> ')

        if user_message.lower() == 'quit':
            break

        # Fix: Use proper HumanMessage format
        from langchain_core.messages import HumanMessage
        state['messages'].append(HumanMessage(content=user_message))

        # Get response and update state
        result = graph.invoke(state)
        state = result  # Update state with the complete result

        # Print only the last message (AI response)
        print(state['messages'][-1].content, '\n')
