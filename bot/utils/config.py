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


path = CONFIG_PATH

with open(path, "r") as f:
    _raw_data = yamlload(f)

CONFIG = DotDict(self._raw_data)
