from abc import ABC, abstractmethod


class Tool(ABC):
    name: str
    description: str
    parameters_json_schema: dict = {"type": "object", "properties": {}}

    @abstractmethod
    async def execute(self, *args, **kwargs):
        pass