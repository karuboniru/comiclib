from pydantic import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    skip_exits: bool = True
    content: str = '.'
    thumb: str = './thumb'


settings = Settings()

if settings.debug:
    print(settings)
