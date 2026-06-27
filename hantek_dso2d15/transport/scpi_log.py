"""Файловый логгер SCPI-обмена с прибором.

Пишет все TX/RX-строки в текстовый файл с ротацией по размеру.
Потокобезопасен: все файловые операции защищены threading.Lock.
Хук ``callback`` передаётся в VisaTransport и вызывается из воркер-потока.

Использование::

    logger = ScpiLogger(max_bytes=10 * 1024 * 1024)
    logger.start("/tmp/scpi.log")
    transport.set_io_logger(logger.callback)
    ...
    logger.stop()
"""
from __future__ import annotations

import os
import threading
from datetime import datetime


class ScpiLogger:
    """Файловый логгер SCPI-обмена с ротацией файла по размеру.

    Parameters
    ----------
    max_bytes:
        Примерный максимальный размер лог-файла (в символах текстового режима).
        При превышении — ротация: текущий файл сохраняется как ``<path>.1``,
        открывается новый пустой файл. Хранится только одна резервная копия.
        Default: 10 МБ.
    """

    def __init__(self, max_bytes: int = 10 * 1024 * 1024) -> None:
        self._max_bytes: int = max_bytes
        self._lock: threading.Lock = threading.Lock()
        self._file = None          # открытый файловый объект или None
        self._path: str | None = None
        self._current_size: int = 0
        self._active: bool = False

    # ------------------------------------------------------------------
    # Публичные свойства
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """``True`` если логгер запущен (``start()`` вызван, ``stop()`` — нет)."""
        return self._active

    # ------------------------------------------------------------------
    # Управление жизненным циклом
    # ------------------------------------------------------------------

    def start(self, path: str) -> None:
        """Открыть файл и начать логирование.

        Файл открывается в режиме записи (truncate). Записывает строку-заголовок
        с текущей временно́й меткой.

        Parameters
        ----------
        path:
            Путь к файлу лога.
        """
        with self._lock:
            self._path = path
            self._file = open(path, "w", encoding="utf-8")
            header = f"=== SCPI log started {datetime.now().isoformat()} ===\n"
            self._file.write(header)
            self._file.flush()
            self._current_size = len(header)
            self._active = True

    def stop(self) -> None:
        """Остановить логирование и закрыть файл.

        Идемпотентен: повторный вызов безопасен.
        """
        with self._lock:
            if not self._active:
                return
            footer = f"=== SCPI log stopped {datetime.now().isoformat()} ===\n"
            self._file.write(footer)
            self._file.flush()
            self._file.close()
            self._file = None
            self._active = False

    # ------------------------------------------------------------------
    # Методы логирования
    # ------------------------------------------------------------------

    def log_tx(self, text: str) -> None:
        """Записать исходящую SCPI-команду.

        Формат строки: ``[ЧЧ:ММ:СС.mmm] TX: <text>``
        """
        ts = self._timestamp()
        self._write(f"[{ts}] TX: {text}\n")

    def log_rx_text(self, text: str) -> None:
        """Записать входящий текстовый ответ.

        Формат строки: ``[ЧЧ:ММ:СС.mmm] RX: <text>``

        Ведущие переводы строк из ``text`` обрезаются (rstrip).
        """
        ts = self._timestamp()
        # rstrip убирает только trailing CR/LF — не трогает тело ответа
        self._write(f"[{ts}] RX: {text.rstrip(chr(13) + chr(10))}\n")

    def log_rx_bytes(self, data: bytes) -> None:
        """Записать входящий бинарный пакет.

        Формат строки: ``[ЧЧ:ММ:СС.mmm] RX: <summary>``

        Для ``#9``-пакетов осциллограммы summary имеет вид::

            <#9 pkt_len=.. total=.. up=.. bytes=N>

        Для прочих байт::

            <N bytes: xx xx xx ...>  (первые 16 байт в hex)
        """
        ts = self._timestamp()
        summary = self._bytes_summary(data)
        self._write(f"[{ts}] RX: {summary}\n")

    def callback(self, direction: str, payload: object) -> None:
        """Хук для передачи в VisaTransport.

        Вызывается из воркер-потока при каждой операции I/O.

        Маршрутизация:

        - ``"TX"``               → :meth:`log_tx`
        - ``"RX"`` + ``bytes``   → :meth:`log_rx_bytes`
        - ``"RX"`` + ``str``     → :meth:`log_rx_text`

        Быстрый выход без блокировки если логгер не активен.
        """
        # Быстрый выход — не захватываем Lock; _active — bool, чтение атомарно в CPython
        if not self._active:
            return
        if direction == "TX":
            self.log_tx(str(payload))
        elif direction == "RX":
            if isinstance(payload, bytes):
                self.log_rx_bytes(payload)
            else:
                self.log_rx_text(str(payload))

    # ------------------------------------------------------------------
    # Приватные вспомогательные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp() -> str:
        """Текущее время в формате ``ЧЧ:ММ:СС.mmm``."""
        now = datetime.now()
        return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"

    @staticmethod
    def _bytes_summary(data: bytes) -> str:
        """Свернуть бинарные данные в короткое текстовое описание.

        Пытается распознать ``#9``-пакет (WAVeform:DATA:ALL?).
        При ошибке парса или неверном префиксе — generic hex.
        """
        if data[:2] == b"#9" and len(data) >= 29:
            try:
                pkt_len = int(data[2:11])
                total = int(data[11:20])
                up = int(data[20:29])
                return (
                    f"<#9 pkt_len={pkt_len} total={total} up={up} bytes={len(data)}>"
                )
            except (ValueError, IndexError):
                pass
        first16hex = data[:16].hex(" ")
        return f"<{len(data)} bytes: {first16hex}>"

    def _write(self, line: str) -> None:
        """Записать строку в файл под Lock с проверкой ротации.

        Не делает ничего если логгер не активен (защита от гонки
        между callback и stop).
        """
        with self._lock:
            if not self._active or self._file is None:
                return
            # Ротация при превышении лимита
            if self._current_size + len(line) > self._max_bytes:
                self._rotate()
            self._file.write(line)
            self._file.flush()
            self._current_size += len(line)

    def _rotate(self) -> None:
        """Ротация лог-файла.

        Закрывает текущий файл, сохраняет его как ``<path>.1`` (один резервный
        слой), открывает ``<path>`` заново (truncate), сбрасывает счётчик.

        ВАЖНО: вызывается только из :meth:`_write`, которая уже удерживает
        ``self._lock``. Повторно Lock не захватывать.
        """
        self._file.close()
        os.replace(self._path, self._path + ".1")
        self._file = open(self._path, "w", encoding="utf-8")
        self._current_size = 0
