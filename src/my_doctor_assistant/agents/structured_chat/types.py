"""Agent type definitions for the structured chat agent."""

from enum import Enum


class AgentType(str, Enum):
    """Enum for structured chat agent types."""

    STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION = "structured-chat-zero-shot-react-description"
    """An zero-shot react agent optimized for chat models.
    
    This agent is capable of invoking tools that have multiple inputs.
    """