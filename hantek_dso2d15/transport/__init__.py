"""Транспортный слой: абстрактный интерфейс + реализации (PyVISA, fake для тестов)."""

from .base import Transport
from .fake_transport import FakeTransport
from .visa_transport import VisaTransport

__all__ = ["Transport", "FakeTransport", "VisaTransport"]
