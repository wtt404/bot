from dataclasses import dataclass, field


@dataclass
class Media:
    url: str
    type: str


@dataclass
class Post:
    platform: str
    text: str
    media: list[Media] = field(default_factory=list)
    author_name: str = None
    author_handle: str = None
    author_avatar: str = None
    url: str = None
