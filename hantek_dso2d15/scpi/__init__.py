"""Типизированный SCPI-драйвер: фасад Scope + подсистемы (frozen reference)."""

from .scope import Scope, ChannelCollection
from .channel import Channel
from .timebase import Timebase, TimebaseWindow
from .acquire import Acquire
from .trigger import Trigger, TriggerEdge

__all__ = [
    "Scope",
    "ChannelCollection",
    "Channel",
    "Timebase",
    "TimebaseWindow",
    "Acquire",
    "Trigger",
    "TriggerEdge",
]
