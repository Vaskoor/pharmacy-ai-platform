"""
Base agent class for all AI agents in the pharmacy system.
"""
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class AgentInput(BaseModel):
    """Base input schema for all agents."""
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    """Base output schema for all agents."""
    success: bool = True
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    escalation_needed: bool = False


class AgentTool:
    """Tool that an agent can use."""
    
    def __init__(self, name: str, description: str, handler: callable, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        return await self.handler(**kwargs)
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class BaseAgent(ABC):
    """Base class for all pharmacy AI agents."""
    
    def __init__(
        self,
        agent_type: str,
        system_prompt: str,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: Optional[List[AgentTool]] = None
    ):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.model = model or settings.OPENAI_MODEL
        self.temperature = temperature or settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self.tools = tools or []
        self.logger = logger.bind(agent_type=agent_type)
        
        # Initialize OpenAI client
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process the input and return output."""
        pass
    
    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[AgentTool]] = None,
        response_format: Optional[Dict[str, str]] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Call the LLM with the given messages."""
        try:
            all_tools = self.tools + (tools or [])
            
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            if all_tools:
                params["tools"] = [t.to_openai_function() for t in all_tools]
            
            if response_format:
                params["response_format"] = response_format
            
            response = await self.client.chat.completions.create(**params)
            
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "tool_calls": response.choices[0].message.tool_calls,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            self.logger.error("llm_call_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
    
    async def execute_tool(self, tool_call: Any) -> str:
        """Execute a tool call from LLM."""
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            return json.dumps({"error": f"Tool {tool_name} not found"})
        
        try:
            result = await tool.execute(**arguments)
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def create_system_message(self, additional_context: Optional[str] = None) -> Dict[str, str]:
        """Create system message with prompt."""
        content = self.system_prompt
        if additional_context:
            content += f"\n\nAdditional Context:\n{additional_context}"
        return {"role": "system", "content": content}
    
    async def log_action(
        self,
        input_data: AgentInput,
        output_data: AgentOutput,
        latency_ms: int,
        tokens: Dict[str, int]
    ):
        """Log agent action for auditing."""
        # This would write to the agent_logs table
        self.logger.info(
            "agent_action",
            agent_type=self.agent_type,
            user_id=input_data.user_id,
            conversation_id=input_data.conversation_id,
            success=output_data.success,
            latency_ms=latency_ms,
            tokens=tokens
        )


class AgentRegistry:
    """Registry for managing agent instances."""
    
    _instance = None
    _agents: Dict[str, BaseAgent] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, agent_type: str, agent: BaseAgent):
        """Register an agent."""
        self._agents[agent_type] = agent
    
    def get(self, agent_type: str) -> Optional[BaseAgent]:
        """Get an agent by type."""
        return self._agents.get(agent_type)
    
    def list_agents(self) -> List[str]:
        """List all registered agent types."""
        return list(self._agents.keys())


# Global registry instance
agent_registry = AgentRegistry()
