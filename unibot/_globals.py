"""
This module holds global variables across the package to avoid circular imports.
It must be imported before any other modules in the package
"""

from typing import *

from unibot.config import Config

if TYPE_CHECKING:
    from unibot import Bot

bot: Optional["Bot"] = None
config: Optional["Config"] = Config()
credentials: Optional["Config"] = Config()
