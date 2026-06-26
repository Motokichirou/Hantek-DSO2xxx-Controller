"""AcquisitionController — чистое ядро сбора данных (Task E2).

Тянет один кадр с прибора через WaveformReader, читает scale/offset из Scope,
декодирует через decode_frame и возвращает DecodedFrame.
Не импортирует Qt. Полностью тестируется через FakeTransport без железа.
"""
from __future__ import annotations

from hantek_dso2d15.waveform.decode import decode_frame, DecodedFrame
from hantek_dso2d15.waveform.reader import RawFrame


class AcquisitionController:
    """Чистое ядро сбора: читает кадр, декодирует, возвращает DecodedFrame.

    Parameters
    ----------
    scope:
        Экземпляр :class:`~hantek_dso2d15.scpi.scope.Scope` (или совместимый
        объект). Используется для чтения scale/offset каналов и управления
        триггером.
    reader:
        Экземпляр :class:`~hantek_dso2d15.waveform.reader.WaveformReader`
        (или совместимый объект с методом ``read_frame()``).
    decoder:
        Callable ``(frame, scales, offsets) -> DecodedFrame``.
        По умолчанию — :func:`~hantek_dso2d15.waveform.decode.decode_frame`.
        Можно заменить для тестирования.
    """

    def __init__(self, scope, reader, decoder=decode_frame) -> None:
        self._scope = scope
        self._reader = reader
        self._decoder = decoder

    def read_decoded_frame(self) -> DecodedFrame:
        """Прочитать один кадр с прибора и вернуть декодированный DecodedFrame.

        1. Читает сырой кадр через ``reader.read_frame()``.
        2. Определяет включённые каналы из заголовка кадра.
        3. Запрашивает scale и offset для каждого канала через Scope.
        4. Декодирует через ``decoder(frame, scales, offsets)``.

        Returns
        -------
        DecodedFrame
            Декодированный кадр с напряжениями и временной осью.
        """
        frame: RawFrame = self._reader.read_frame()
        chans = frame.header.enabled_channels
        scales = {n: self._scope.channel[n].scale for n in chans}
        offsets = {n: self._scope.channel[n].offset for n in chans}
        return self._decoder(frame, scales, offsets)

    def force(self) -> None:
        """Отправить принудительный триггер (:TRIGger:FORCe).

        Делегирует в ``scope.trigger.force()``.
        """
        self._scope.trigger.force()

    def set_sweep(self, mode: str) -> None:
        """Установить режим развёртки триггера (:TRIGger:SWEep {mode}).

        Parameters
        ----------
        mode:
            Один из ``"AUTO"``, ``"NORMal"``, ``"SINGle"``.
            Валидация производится в :class:`~hantek_dso2d15.scpi.trigger.Trigger`.

        Raises
        ------
        ValueError
            Если ``mode`` не является допустимым режимом развёртки.
        """
        self._scope.trigger.sweep = mode
