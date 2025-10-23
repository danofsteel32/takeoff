from datetime import date as Date

import instructor
from pydantic import BaseModel

client = instructor.from_provider("openai/gpt-5-mini")


class TitleBlock(BaseModel):
    scale: str
    date: Date
    named_entities: list[str]


class BlueprintSheet(BaseModel):
    title_block: TitleBlock
