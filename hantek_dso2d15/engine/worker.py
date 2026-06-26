"""EngineWorker — тонкий Qt-слой поверх AcquisitionController (Task E3).

Переносится в QThread слоем GUI. Управление кадентностью опроса — host-side:
  - Run  → таймер тикает с interval_ms, каждый тик вызывает capture_once().
  - Stop → таймер остановлен.
  - Single → один synchronous захват, затем автоматически STOPPED.

Не блокирует UI-поток: вся VISA-I/O происходит в том потоке, куда перемещён worker.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from hantek_dso2d15.engine.states import RunState


class EngineWorker(QObject):
    """Qt-обёртка вокруг AcquisitionController.

    Сигналы
    -------
    frameReady(object)
        Испускается при успешном получении декодированного кадра.
        Передаёт объект :class:`~hantek_dso2d15.waveform.decode.DecodedFrame`.
    errorOccurred(str)
        Испускается при любом исключении в ``capture_once()``.
        Передаёт строку ``str(exception)``.
    stateChanged(object)
        Испускается при каждом изменении состояния. Передаёт
        значение :class:`~hantek_dso2d15.engine.states.RunState`.

    Parameters
    ----------
    controller:
        Объект с методом ``read_decoded_frame() -> DecodedFrame``.
        Обычно :class:`~hantek_dso2d15.engine.controller.AcquisitionController`.
    interval_ms:
        Интервал таймера непрерывного сбора в миллисекундах. По умолчанию 50 мс
        (~20 fps).
    parent:
        Родительский QObject (опционально).
    """

    frameReady = Signal(object)
    errorOccurred = Signal(str)
    stateChanged = Signal(object)

    def __init__(self, controller, interval_ms: int = 50, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._state: RunState = RunState.STOPPED

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.capture_once)

    # ------------------------------------------------------------------
    # Public property
    # ------------------------------------------------------------------

    @property
    def state(self) -> RunState:
        """Текущее состояние цикла сбора."""
        return self._state

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def start(self) -> None:
        """Перевести в режим непрерывного сбора (RUNNING) и запустить таймер."""
        self._state = RunState.RUNNING
        self._timer.start()
        self.stateChanged.emit(self._state)

    @Slot()
    def stop(self) -> None:
        """Остановить сбор (STOPPED) и остановить таймер."""
        self._state = RunState.STOPPED
        self._timer.stop()
        self.stateChanged.emit(self._state)

    @Slot()
    def single(self) -> None:
        """Одиночный захват: SINGLE → capture_once() → STOPPED."""
        self._state = RunState.SINGLE
        self.stateChanged.emit(self._state)
        self.capture_once()

    @Slot()
    def capture_once(self) -> None:
        """Тянет один кадр с контроллера и испускает frameReady или errorOccurred.

        После захвата (успешного ИЛИ ошибочного), если текущее состояние SINGLE,
        автоматически вызывает :meth:`stop` — чтобы одиночный режим не залипал в
        SINGLE при ошибке контроллера.
        """
        try:
            frame = self._controller.read_decoded_frame()
            self.frameReady.emit(frame)
        except Exception as exc:  # noqa: BLE001
            self.errorOccurred.emit(str(exc))
        finally:
            # Одиночный режим всегда завершается в STOPPED, даже после ошибки.
            if self._state is RunState.SINGLE:
                self.stop()
