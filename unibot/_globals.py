"""
This module holds global variables across the package to avoid circular imports.
"""

from typing import *

if TYPE_CHECKING:
    from unibot import Bot

bot: Optional["Bot"] = None
