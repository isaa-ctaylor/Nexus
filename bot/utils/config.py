from os import PathLike, path
from typing import Any, Optional, Union

from yaml import load

from .helpers import DotDict

CONFIG_DIR = path.join(path.dirname(__file__), '../config.yaml')

if not path.exists(CONFIG_DIR):
    with open(CONFIG_DIR, "w") as f:
        print(f"Config file created: {CONFIG_DIR}")

class Config:
    def __init__(self, path: Optional[Union[str, PathLike]] = None):
        path = path or CONFIG_DIR
        
        with open(path, "r") as f:
            self._raw_data = load(f)
            
        self.data = DotDict(self._raw_data)
        
    def __getattr__(self, key: str) -> Any:
        return self.data.__getattr__(key)
    
    def __setattr__(self, key: str, value: Any) -> Any:
        return self.data.__setattr__(key, value)
    
    def __delattr__(self, key: str) -> Any:
        return self.data.__delattr__(key)
