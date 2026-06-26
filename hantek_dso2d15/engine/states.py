"""Engine run-state enumeration for the acquisition controller."""

import enum


class RunState(enum.Enum):
    """Состояние цикла сбора данных.

    STOPPED — сбор остановлен.
    RUNNING — непрерывный сбор (Run).
    SINGLE  — одиночный захват (Single).
    """

    STOPPED = "stopped"
    RUNNING = "running"
    SINGLE = "single"
