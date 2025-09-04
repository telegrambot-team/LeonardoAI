import logging

from openai import AsyncOpenAI, BadRequestError

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self, token: str, assistant_id: str):
        self.client = AsyncOpenAI(api_key=token)
        self.assistant_id = assistant_id

    async def delete_thread(self, thread_id: str):
        await self.client.beta.threads.delete(thread_id)

    async def new_thread(self) -> str:
        thread = await self.client.beta.threads.create()
        logger.debug("Created new thread %s", thread)
        return thread.id

    async def get_response(self, ai_thread_id: str, text: str) -> str | None:
        with suppress(BadRequestError):
            await self.client.beta.threads.messages.create(thread_id=ai_thread_id, role="user", content=text)
        run = await self.client.beta.threads.runs.create_and_poll(
            thread_id=ai_thread_id, assistant_id=self.assistant_id
        )
        logger.info("Run completed: %s", run.status)
        if run.status == "completed":
            messages = await self.client.beta.threads.messages.list(thread_id=ai_thread_id)
            return messages.data[0].content[0].text.value

        return None
