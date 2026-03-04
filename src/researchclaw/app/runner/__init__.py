"""Runner package – manages agent lifecycle, chat sessions, and chat CRUD.

Provides:
- AgentRunnerManager: Top-level runner lifecycle management
- AgentRunner: Core agent wrapper for async web usage
- ChatManager: Chat specification CRUD operations
- Chat models (ChatSpec, ChatHistory, ChatsFile)
- Chat repository (BaseChatRepository, JsonChatRepository)
- API router for chat endpoints
- Utility functions (build_env_context, query_error_dump)
"""
from .manager import AgentRunnerManager
from .runner import AgentRunner
from .chat_manager import ChatManager
from .api import router
from .models import ChatSpec, ChatHistory, ChatsFile
from .repo import BaseChatRepository, JsonChatRepository

__all__ = [
    # Core classes
    "AgentRunnerManager",
    "AgentRunner",
    "ChatManager",
    # API
    "router",
    # Models
    "ChatSpec",
    "ChatHistory",
    "ChatsFile",
    # Chat Repository
    "BaseChatRepository",
    "JsonChatRepository",
]
