from abc import ABC, abstractmethod
from models.post import Post

class Fetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> Post:
        ...