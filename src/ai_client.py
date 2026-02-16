import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class AssistantModelNotConfiguredError(RuntimeError):
    default_message = "OpenAI assistant model is not configured"

    def __init__(self) -> None:
        super().__init__(self.default_message)


class AIClient:
    def __init__(self, token: str, assistant_id: str):
        self.client = AsyncOpenAI(api_key=token)
        self.assistant_id = assistant_id
        self._assistant_loaded = False
        self._model: str | None = None
        self._instructions: str | None = None
        self._temperature: float | None = None
        self._top_p: float | None = None
        self._tools: list[dict[str, object]] = []

    async def delete_conversation(self, conversation_id: str) -> None:
        await self.client.conversations.delete(conversation_id)

    async def new_conversation(self) -> str:
        conversation = await self.client.conversations.create()
        logger.debug("Created new conversation %s", conversation)
        return conversation.id

    async def get_response(self, conversation_id: str, text: str, *, user_id: str | None = None) -> str | None:
        await self._ensure_assistant_loaded()
        if not self._model:
            raise AssistantModelNotConfiguredError

        request_params: dict[str, object] = {
            "conversation": conversation_id,
            "model": self._model,
            "input": text,
            "store": True,
        }
        if self._instructions:
            request_params["instructions"] = self._instructions
        if self._tools:
            request_params["tools"] = self._tools
        if self._temperature is not None:
            request_params["temperature"] = self._temperature
        if self._top_p is not None:
            request_params["top_p"] = self._top_p
        if user_id:
            request_params["user"] = user_id

        response = await self.client.responses.create(**request_params)
        output_text = response.output_text
        if output_text:
            return output_text

        return None

    async def _ensure_assistant_loaded(self) -> None:
        if self._assistant_loaded:
            return

        assistant = await self.client.beta.assistants.retrieve(self.assistant_id)
        self._model = assistant.model
        self._instructions = assistant.instructions
        self._temperature = assistant.temperature
        self._top_p = assistant.top_p
        self._tools = self._assistant_to_responses_tools(assistant)
        self._assistant_loaded = True

    @staticmethod
    def _assistant_to_responses_tools(assistant) -> list[dict[str, object]]:
        tools: list[dict[str, object]] = []
        if not assistant.tools:
            return tools

        file_search_vector_store_ids = []
        if assistant.tool_resources and assistant.tool_resources.file_search:
            file_search_vector_store_ids = assistant.tool_resources.file_search.vector_store_ids or []

        code_interpreter_file_ids = []
        if assistant.tool_resources and assistant.tool_resources.code_interpreter:
            code_interpreter_file_ids = assistant.tool_resources.code_interpreter.file_ids or []

        for tool in assistant.tools:
            match tool.type:
                case "file_search":
                    if not file_search_vector_store_ids:
                        logger.warning(
                            "Assistant %s has file_search tool but no vector_store_ids configured", assistant.id
                        )
                        continue
                    payload: dict[str, object] = {
                        "type": "file_search",
                        "vector_store_ids": file_search_vector_store_ids,
                    }
                    if tool.file_search and tool.file_search.max_num_results is not None:
                        payload["max_num_results"] = tool.file_search.max_num_results
                    tools.append(payload)
                case "code_interpreter":
                    tools.append(
                        {
                            "type": "code_interpreter",
                            "container": {"type": "auto", "file_ids": code_interpreter_file_ids},
                        }
                    )
                case "function":
                    definition = tool.function
                    payload = {
                        "type": "function",
                        "name": definition.name,
                        "description": definition.description,
                        "parameters": definition.parameters,
                        "strict": definition.strict,
                    }
                    tools.append({key: value for key, value in payload.items() if value is not None})
                case _:
                    logger.warning("Unsupported assistant tool type: %s", tool.type)

        return tools
