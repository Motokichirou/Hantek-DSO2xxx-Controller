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
        # Кэш масштабов/смещений по каналам. Пустой → значения запрашиваются с
        # прибора при каждом кадре (исходное поведение). Заполняется через
        # refresh_scaling(); используется live-циклом, чтобы не слать
        # :SCALe?/:OFFSet? на каждый кадр (ускорение fps).
        self._scale_cache: dict[int, float] = {}
        self._offset_cache: dict[int, float] = {}

    @property
    def scope(self):
        """Драйвер прибора (для управляющих записей из потока воркера)."""
        return self._scope

    def refresh_scaling(self, channels=(1, 2, 3, 4)) -> None:
        """Запросить и закэшировать scale/offset указанных каналов.

        Вызывать после connect и при смене вертикальных настроек. После этого
        ``read_decoded_frame()`` берёт масштабы из кэша, не дёргая прибор
        каждый кадр.
        """
        for n in channels:
            self._scale_cache[n] = self._scope.channel[n].scale
            self._offset_cache[n] = self._scope.channel[n].offset

    def clear_scaling_cache(self) -> None:
        """Сбросить кэш масштабов (следующий кадр снова запросит с прибора)."""
        self._scale_cache.clear()
        self._offset_cache.clear()

    def _scale_for(self, n: int) -> float:
        if n in self._scale_cache:
            return self._scale_cache[n]
        return self._scope.channel[n].scale

    def _offset_for(self, n: int) -> float:
        if n in self._offset_cache:
            return self._offset_cache[n]
        return self._scope.channel[n].offset

    def read_decoded_frame(self) -> DecodedFrame:
        """Прочитать один кадр с прибора и вернуть декодированный DecodedFrame.

        1. Читает сырой кадр через ``reader.read_frame()``.
        2. Определяет включённые каналы из заголовка кадра.
        3. Берёт scale/offset из кэша (если заполнен через refresh_scaling),
           иначе запрашивает с прибора.
        4. Декодирует через ``decoder(frame, scales, offsets)``.

        Returns
        -------
        DecodedFrame
            Декодированный кадр с напряжениями и временной осью.
        """
        frame: RawFrame = self._reader.read_frame()
        chans = frame.header.enabled_channels
        scales = {n: self._scale_for(n) for n in chans}
        offsets = {n: self._offset_for(n) for n in chans}
        return self._decoder(frame, scales, offsets)

    def read_measurements(self, requests: list) -> list:
        """Опросить автоизмерения для заданных пар (channel, item).

        Вызывает ``scope.measure.read_item(channel, item)`` для каждой пары.
        При исключении (I/O-ошибка, таймаут и т.п.) подставляет ``None``
        вместо значения — цикл продолжается.

        Parameters
        ----------
        requests:
            Список пар ``(channel: int, item: str)``.

        Returns
        -------
        list[dict]
            Параллельный список словарей
            ``{"channel": int, "item": str, "value": float | None}``.
            Порядок совпадает с ``requests``. Если ``requests`` пуст — ``[]``.
        """
        if not requests:
            return []
        result = []
        for channel, item in requests:
            try:
                value: float | None = self._scope.measure.read_item(channel, item)
            except Exception:  # noqa: BLE001
                value = None
            result.append({"channel": channel, "item": item, "value": value})
        return result

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
