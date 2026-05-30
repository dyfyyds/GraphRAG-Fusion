from pydantic import BaseModel


class ConfigOut(BaseModel):
    id: int
    config_key: str
    config_value: str
    description: str | None = None

    class Config:
        from_attributes = True


class ConfigUpdate(BaseModel):
    config_value: str


class ConfigBatchUpdate(BaseModel):
    configs: dict[str, str]


class ConfigSectionOut(BaseModel):
    section: str
    items: list[ConfigOut]
