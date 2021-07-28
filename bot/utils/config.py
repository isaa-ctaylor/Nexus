from os import PathLike, path
from typing import Optional, Union

from aiofile import async_open
from yaml import safe_dump as yamldump
from yaml import safe_load as yamlload

from .helpers import DotDict

CONFIG_PATH = path.join(path.dirname(__file__), "../config.yaml")

if not path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "w") as f:
        print(f"Config file created: {CONFIG_PATH}")


class Config:
    def __init__(self, path: Optional[Union[str, PathLike]] = None):
        path = path or CONFIG_PATH

        with open(path, "r") as f:
            self._raw_data = yamlload(f)

        self.data = DotDict(self._raw_data)

    async def load(self, *, path: Union[str, PathLike] = CONFIG_PATH) -> None:
        """
        Load the config from the file. Useful for re-loading the config without
        stopping the bot.
        """
        async with async_open(path, "r") as f:
            self._raw_data = await f.read()

            self.data = DotDict(self._raw_data)

    async def dump(self, *, path: Union[str, PathLike] = CONFIG_PATH) -> None:
        """
        Dump the current loaded config
        """
        async with async_open(path, "w") as f:
            await f.write(yamldump(self._raw_data, default_flow_style=False))
