import logging

from openai import AsyncOpenAI


class AIClient:
    def __init__(self, token: str, assistant_id: str):
        self.client = AsyncOpenAI(api_key=token)
        self.assistant_id = assistant_id

    async def new_thread(self) -> str:
        thread = await self.client.beta.threads.create()
        logging.debug(f"Created new thread {thread}")
        return thread.id

    async def get_response(self, ai_thread_id: str, text: str):
        await self.client.beta.threads.messages.create(thread_id=ai_thread_id, role="user", content=text)
        async with self.client.beta.threads.runs.stream(
            thread_id=ai_thread_id, assistant_id=self.assistant_id
        ) as stream:
            async for response in stream:
                if response.event == "thread.message.completed":
                    return response.data.content[0].text.value
