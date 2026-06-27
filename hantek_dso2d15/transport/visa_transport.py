"""VisaTransport — обёртка PyVISA для Hantek DSO2D15.

Импортируй напрямую:
    from hantek_dso2d15.transport.visa_transport import VisaTransport

Зависит только от абстрактного Transport; PyVISA используется через инъекцию
resource_manager, что позволяет тестировать без железа.
"""

from __future__ import annotations

from hantek_dso2d15.transport.base import Transport


class VisaTransport(Transport):
    """Конкретная реализация Transport поверх PyVISA.

    Parameters
    ----------
    resource:
        Строка VISA-ресурса, например ``"USB0::0x0483::0x5740::CN21034::INSTR"``.
    timeout_ms:
        Таймаут операций ввода-вывода в миллисекундах (default 5000).
    read_termination:
        Символ(ы) конца строки для чтения (default ``None``). Для USBTMC чтение
        завершается по биту EOM пакета, а не по символу-терминатору; DSO2D15 не
        добавляет ``\\n`` к ответам (подтверждено на железе). ``None`` также не
        даёт оборвать бинарный блок ``WAVeform:DATA:ALL?`` на байте ``0x0A``.
    write_termination:
        Символ(ы) конца строки для записи (default ``"\\n"``).
    resource_manager:
        Готовый ``pyvisa.ResourceManager`` (или фейковый RM для тестов).
        Если ``None`` — будет создан через ``pyvisa.ResourceManager()`` при первом
        вызове ``open()`` или ``list_resources()``.
    """

    def __init__(
        self,
        resource: str,
        *,
        timeout_ms: int = 5000,
        read_termination: str | None = None,
        write_termination: str | None = "\n",
        resource_manager=None,
        io_logger=None,
    ) -> None:
        self._resource_str = resource
        self._timeout_ms = timeout_ms
        self._read_termination = read_termination
        self._write_termination = write_termination
        self._rm = resource_manager  # может быть None; создаётся при open()
        self._res = None  # pyvisa-ресурс; None пока не открыт
        # Опциональный хук логгера: callable(direction: str, payload) | None.
        # Вызывается при каждом TX/RX; ошибки в хуке глушатся (не ломают I/O).
        self._io_logger = io_logger

    # ------------------------------------------------------------------
    # Статический метод: список доступных ресурсов
    # ------------------------------------------------------------------

    @staticmethod
    def list_resources(resource_manager=None) -> tuple[str, ...]:
        """Вернуть кортеж строк VISA-ресурсов, найденных RM.

        Parameters
        ----------
        resource_manager:
            Готовый RM или ``None`` (тогда будет создан ``pyvisa.ResourceManager()``).
        """
        if resource_manager is None:
            import pyvisa  # импорт отложен, чтобы не валиться при отсутствии pyvisa
            rm = pyvisa.ResourceManager()
        else:
            rm = resource_manager
        return tuple(rm.list_resources())

    # ------------------------------------------------------------------
    # Открытие / закрытие
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Открыть соединение с прибором.

        Если ``resource_manager`` не был передан в конструктор, создаёт
        ``pyvisa.ResourceManager()`` и сохраняет его в ``self._rm``.
        """
        if self._rm is None:
            import pyvisa
            self._rm = pyvisa.ResourceManager()
        self._res = self._rm.open_resource(self._resource_str)
        self._res.timeout = self._timeout_ms
        self._res.read_termination = self._read_termination
        self._res.write_termination = self._write_termination

    def close(self) -> None:
        """Закрыть соединение с прибором.

        Безопасно вызывать на уже закрытом транспорте.
        """
        if self._res is not None:
            self._res.close()
            self._res = None

    @property
    def is_open(self) -> bool:
        """``True`` если соединение установлено."""
        return self._res is not None

    # ------------------------------------------------------------------
    # Хук логгера
    # ------------------------------------------------------------------

    def set_io_logger(self, cb) -> None:
        """Установить или снять хук логгера I/O.

        Parameters
        ----------
        cb:
            callable(direction: str, payload) или ``None`` для отключения.
            Безопасно вызывать из любого потока (замена атомарна в CPython).
        """
        self._io_logger = cb

    def _log(self, direction: str, payload) -> None:
        """Вызвать хук логгера, поглощая все исключения из него."""
        if self._io_logger is not None:
            try:
                self._io_logger(direction, payload)
            except Exception:
                # Ошибка логгера не должна прерывать I/O с прибором
                pass

    # ------------------------------------------------------------------
    # I/O — делегируют pyvisa-ресурсу
    # ------------------------------------------------------------------

    def _assert_open(self) -> None:
        if self._res is None:
            raise RuntimeError(
                "VisaTransport: попытка I/O на закрытом соединении. "
                "Вызовите open() перед использованием."
            )

    def write(self, cmd: str) -> None:
        """Отправить команду SCPI прибору без ожидания ответа."""
        self._assert_open()
        self._log("TX", cmd)
        self._res.write(cmd)

    def query(self, cmd: str) -> str:
        """Отправить запрос SCPI и вернуть ответ в виде строки."""
        self._assert_open()
        self._log("TX", cmd)
        resp = self._res.query(cmd)
        self._log("RX", resp)
        return resp

    def read_raw(self) -> bytes:
        """Прочитать сырые байты из буфера прибора."""
        self._assert_open()
        data = self._res.read_raw()
        self._log("RX", data)
        return data

    # ------------------------------------------------------------------
    # Переподключение
    # ------------------------------------------------------------------

    def reconnect(self) -> None:
        """Закрыть и снова открыть соединение."""
        self.close()
        self.open()

    # ------------------------------------------------------------------
    # repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        state = "open" if self.is_open else "closed"
        return f"VisaTransport({self._resource_str!r}, {state})"
