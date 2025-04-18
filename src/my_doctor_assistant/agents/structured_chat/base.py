"""Implementation of the Structured Chat Agent."""

import re
from typing import Any, List, Optional, Sequence, Tuple

from langchain_core.agents import AgentAction
from langchain_core.callbacks import BaseCallbackManager
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import BasePromptTemplate
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.tools import BaseTool
from pydantic import Field

from langchain.agents.agent import Agent, AgentOutputParser
from langchain.chains.llm import LLMChain
from my_doctor_assistant.agents.structured_chat.output_parser import (
    StructuredChatOutputParserWithRetries,
)
from my_doctor_assistant.agents.structured_chat.prompt import FORMAT_INSTRUCTIONS, HUMAN_MESSAGE_TEMPLATE, PREFIX, SUFFIX


class StructuredChatAgent(Agent):
    """Structured Chat Agent for handling tools with complex inputs."""

    output_parser: AgentOutputParser = Field(
        default_factory=StructuredChatOutputParserWithRetries
    )
    """Output parser for the agent."""

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "Observation: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Thought:"

    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[AgentAction, str]]
    ) -> str:
        """Construct the scratchpad that serves as the agent's working memory.
        
        Args:
            intermediate_steps: Steps the LLM has taken to date
            
        Returns:
            A string representing the scratchpad for the agent
        """
        agent_scratchpad = super()._construct_scratchpad(intermediate_steps)
        if not isinstance(agent_scratchpad, str):
            raise ValueError("agent_scratchpad should be of type string.")
        if agent_scratchpad:
            return (
                f"This was your previous work "
                f"(but I haven't seen any of it! I only see what "
                f"you return as final answer):\n{agent_scratchpad}"
            )
        else:
            return agent_scratchpad

    @classmethod
    def _validate_tools(cls, tools: Sequence[BaseTool]) -> None:
        """Validate that the tools are valid for this agent.
        
        Args:
            tools: The tools to be used by the agent
        """
        pass  # No validation needed for this agent type

    @classmethod
    def _get_default_output_parser(
        cls, llm: Optional[BaseLanguageModel] = None, **kwargs: Any
    ) -> AgentOutputParser:
        """Get the default output parser for this agent.
        
        Args:
            llm: The LLM to use for output parsing
            
        Returns:
            The default output parser
        """
        return StructuredChatOutputParserWithRetries.from_llm(llm=llm)

    @property
    def _stop(self) -> List[str]:
        """Return the default stop sequences for the agent."""
        return ["Observation:"]

    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        prefix: str = PREFIX,
        suffix: str = SUFFIX,
        human_message_template: str = HUMAN_MESSAGE_TEMPLATE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
        memory_prompts: Optional[List[BasePromptTemplate]] = None,
    ) -> BasePromptTemplate:
        """Create a prompt for this agent.
        
        Args:
            tools: The tools the agent will have access to
            prefix: The prefix for the prompt
            suffix: The suffix for the prompt
            human_message_template: The template for human messages
            format_instructions: Instructions for formatting agent responses
            input_variables: The input variables for the prompt
            memory_prompts: Prompts for agent memory
            
        Returns:
            A prompt template for the agent
        """
        # Format tool descriptions and names
        tool_strings = []
        for tool in tools:
            args_schema = re.sub("}", "}}", re.sub("{", "{{", str(tool.args)))
            tool_strings.append(f"{tool.name}: {tool.description}, args: {args_schema}")
        formatted_tools = "\n".join(tool_strings)
        tool_names = ", ".join([tool.name for tool in tools])
        format_instructions = format_instructions.format(tool_names=tool_names)
        
        # Build the full template
        template = "\n\n".join([prefix, formatted_tools, format_instructions, suffix])
        if input_variables is None:
            input_variables = ["input", "agent_scratchpad"]
        
        # Create chat message templates
        _memory_prompts = memory_prompts or []
        messages = [
            SystemMessagePromptTemplate.from_template(template),
            *_memory_prompts,
            HumanMessagePromptTemplate.from_template(human_message_template),
        ]
        
        return ChatPromptTemplate(input_variables=input_variables, messages=messages)

    @classmethod
    def from_llm_and_tools(
        cls,
        llm: BaseLanguageModel,
        tools: Sequence[BaseTool],
        callback_manager: Optional[BaseCallbackManager] = None,
        output_parser: Optional[AgentOutputParser] = None,
        prefix: str = PREFIX,
        suffix: str = SUFFIX,
        human_message_template: str = HUMAN_MESSAGE_TEMPLATE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
        memory_prompts: Optional[List[BasePromptTemplate]] = None,
        **kwargs: Any,
    ) -> Agent:
        """Create an agent from an LLM and tools.
        
        Args:
            llm: The LLM to use for the agent
            tools: The tools the agent will have access to
            callback_manager: The callback manager to use
            output_parser: The output parser to use
            prefix: The prefix for the prompt
            suffix: The suffix for the prompt
            human_message_template: The template for human messages
            format_instructions: Instructions for formatting agent responses
            input_variables: The input variables for the prompt
            memory_prompts: Prompts for agent memory
            
        Returns:
            A configured agent
        """
        cls._validate_tools(tools)
        
        # Create prompt
        prompt = cls.create_prompt(
            tools,
            prefix=prefix,
            suffix=suffix,
            human_message_template=human_message_template,
            format_instructions=format_instructions,
            input_variables=input_variables,
            memory_prompts=memory_prompts,
        )
        
        # Create LLM chain
        llm_chain = LLMChain(
            llm=llm,
            prompt=prompt,
            callback_manager=callback_manager,
        )
        
        # Configure agent
        tool_names = [tool.name for tool in tools]
        _output_parser = output_parser or cls._get_default_output_parser(llm=llm)
        
        return cls(
            llm_chain=llm_chain,
            allowed_tools=tool_names,
            output_parser=_output_parser,
            **kwargs,
        )

    @property
    def _agent_type(self) -> str:
        """Return the type of agent."""
        return "structured-chat-zero-shot-react-description"