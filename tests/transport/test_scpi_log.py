"""Тесты ScpiLogger — TDD, RED-first.

Приёмочные кейсы:
  - start пишет заголовок; is_active меняется корректно
  - log_tx формат "[ЧЧ:ММ:СС.mmm] TX: ..."
  - log_rx_text формат "RX:", rstrip newlines
  - log_rx_bytes #9-пакет -> "<#9 pkt_len=.. total=.. up=.. bytes=N>"
  - log_rx_bytes произвольные байты -> "<N bytes: xx xx...>"
  - callback маршрутизирует TX/RX и молчит если не активен
  - ротация при малом max_bytes: создаётся '{path}.1', основной файл усечён
  - stop идемпотентен (двойной вызов не бросает)
"""
from __future__ import annotations

import os
import re

import pytest

from hantek_dso2d15.transport.scpi_log import ScpiLogger


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _read(path: str) -> str:
    return open(path, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# 1. start / is_active
# ---------------------------------------------------------------------------

class TestStart:
    def test_not_active_before_start(self):
        lg = ScpiLogger()
        assert lg.is_active is False

    def test_active_after_start(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        try:
            assert lg.is_active is True
        finally:
            lg.stop()

    def test_start_writes_header_line(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.stop()
        content = _read(log_path)
        assert "=== SCPI log started" in content
        # Должна быть временна́я метка ISO
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", content)

    def test_start_creates_file(self, tmp_path):
        log_path = str(tmp_path / "new.log")
        assert not os.path.exists(log_path)
        lg = ScpiLogger()
        lg.start(log_path)
        lg.stop()
        assert os.path.exists(log_path)


# ---------------------------------------------------------------------------
# 2. log_tx
# ---------------------------------------------------------------------------

class TestLogTx:
    def test_log_tx_contains_tx_marker(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_tx(":CHAN1:DISP ON")
        lg.stop()
        content = _read(log_path)
        assert "TX: :CHAN1:DISP ON" in content

    def test_log_tx_has_timestamp(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_tx(":TRIG:MODE EDGE")
        lg.stop()
        content = _read(log_path)
        # Формат [ЧЧ:ММ:СС.mmm]
        assert re.search(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]", content)

    def test_log_tx_ends_with_newline(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_tx("CMD")
        lg.stop()
        content = _read(log_path)
        lines = [l for l in content.splitlines() if "TX:" in l]
        assert len(lines) == 1
        # Каждая строка корректно разделена (splitlines работает — значит '\n' есть)

    def test_log_tx_multiple(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_tx("CMD_A")
        lg.log_tx("CMD_B")
        lg.stop()
        content = _read(log_path)
        assert "TX: CMD_A" in content
        assert "TX: CMD_B" in content


# ---------------------------------------------------------------------------
# 3. log_rx_text
# ---------------------------------------------------------------------------

class TestLogRxText:
    def test_log_rx_text_contains_rx_marker(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_text("ON")
        lg.stop()
        content = _read(log_path)
        assert "RX: ON" in content

    def test_log_rx_text_strips_trailing_newlines(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_text("ON\r\n")
        lg.stop()
        content = _read(log_path)
        # Должно быть "RX: ON", НЕ "RX: ON\r\n"
        assert "RX: ON" in content
        # Не должно быть пустой строки после ON (следствие lstrip)
        lines = [l for l in content.splitlines() if "RX:" in l]
        assert lines[0].endswith("ON")

    def test_log_rx_text_strips_only_trailing(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_text("Hantek,DSO2D15,CN21034,1.0\n")
        lg.stop()
        content = _read(log_path)
        assert "RX: Hantek,DSO2D15,CN21034,1.0" in content


# ---------------------------------------------------------------------------
# 4. log_rx_bytes
# ---------------------------------------------------------------------------

class TestLogRxBytes:
    def test_log_rx_bytes_pkt9_format(self, tmp_path):
        """#9-пакет -> <#9 pkt_len=.. total=.. up=.. bytes=N>"""
        # Сконструировать валидный #9-пакет:
        # b'#9' + pkt_len(9) + total(9) + uploaded(9) + payload(100 байт)
        pkt = b"#9" + b"000000100" + b"000016000" + b"000000000" + bytes(100)
        # len(pkt) = 2 + 9 + 9 + 9 + 100 = 129
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_bytes(pkt)
        lg.stop()
        content = _read(log_path)
        assert "<#9 pkt_len=100 total=16000 up=0 bytes=129>" in content

    def test_log_rx_bytes_pkt9_with_nonzero_up(self, tmp_path):
        """uploaded != 0 тоже корректно отображается."""
        pkt = b"#9" + b"000000500" + b"000016000" + b"000002000" + bytes(500)
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_bytes(pkt)
        lg.stop()
        content = _read(log_path)
        assert "up=2000" in content
        assert "bytes=529" in content

    def test_log_rx_bytes_generic_short(self, tmp_path):
        """Менее 29 байт -> generic hex."""
        data = b"\xDE\xAD\xBE\xEF"
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_bytes(data)
        lg.stop()
        content = _read(log_path)
        assert "<4 bytes:" in content
        assert "de ad be ef" in content

    def test_log_rx_bytes_generic_no_pkt9_prefix(self, tmp_path):
        """Байты без '#9' -> generic hex."""
        data = bytes(range(20))
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_bytes(data)
        lg.stop()
        content = _read(log_path)
        assert f"<{len(data)} bytes:" in content
        assert data[:16].hex(" ") in content

    def test_log_rx_bytes_generic_long_shows_first16(self, tmp_path):
        """Более 16 байт без #9 -> только первые 16 в hex."""
        data = bytes(range(32))
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_bytes(data)
        lg.stop()
        content = _read(log_path)
        assert "<32 bytes:" in content
        # Первые 16 байт в hex через пробел
        assert data[:16].hex(" ") in content
        # Байты 16-31 не должны быть в hex (нет полного списка)
        assert data[16:].hex(" ") not in content

    def test_log_rx_bytes_empty(self, tmp_path):
        """Пустые байты -> generic."""
        data = b""
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.log_rx_bytes(data)
        lg.stop()
        content = _read(log_path)
        assert "<0 bytes:" in content


# ---------------------------------------------------------------------------
# 5. callback — маршрутизация
# ---------------------------------------------------------------------------

class TestCallback:
    def test_callback_tx_routes_to_log_tx(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.callback("TX", ":CHAN1:DISP ON")
        lg.stop()
        content = _read(log_path)
        assert "TX: :CHAN1:DISP ON" in content

    def test_callback_rx_str_routes_to_log_rx_text(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.callback("RX", "ON")
        lg.stop()
        content = _read(log_path)
        assert "RX: ON" in content

    def test_callback_rx_bytes_routes_to_log_rx_bytes(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.callback("RX", b"\x01\x02\x03")
        lg.stop()
        content = _read(log_path)
        assert "RX: <3 bytes:" in content

    def test_callback_silent_when_not_active(self):
        """callback до start() не бросает и ничего не делает."""
        lg = ScpiLogger()
        # Не должно упасть
        lg.callback("TX", ":CHAN1:DISP ON")
        lg.callback("RX", "ON")
        lg.callback("RX", b"\x00")

    def test_callback_silent_after_stop(self, tmp_path):
        """callback после stop() не бросает."""
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.stop()
        # Не должно упасть — is_active=False, быстрый выход
        lg.callback("TX", "CMD")

    def test_callback_rx_bytes_pkt9(self, tmp_path):
        """callback('RX', bytes) корректно сворачивает #9-пакет."""
        pkt = b"#9" + b"000000200" + b"000008000" + b"000000000" + bytes(200)
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.callback("RX", pkt)
        lg.stop()
        content = _read(log_path)
        assert "<#9 pkt_len=200 total=8000 up=0 bytes=229>" in content


# ---------------------------------------------------------------------------
# 6. Ротация
# ---------------------------------------------------------------------------

class TestRotation:
    def test_rotation_creates_backup_file(self, tmp_path):
        """При переполнении max_bytes создаётся '{path}.1'."""
        log_path = str(tmp_path / "test.log")
        # max_bytes=50: заголовок (~52 байта) уже превысит лимит,
        # поэтому первый же _write вызовет ротацию.
        lg = ScpiLogger(max_bytes=50)
        lg.start(log_path)
        # Несколько записей для надёжного срабатывания
        for i in range(5):
            lg.log_tx(f"cmd_{i:03d}")
        lg.stop()
        assert os.path.exists(log_path + ".1"), "Резервная копия .1 не создана"

    def test_rotation_backup_is_nonempty(self, tmp_path):
        """'{path}.1' содержит данные (не пустой)."""
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger(max_bytes=50)
        lg.start(log_path)
        for i in range(5):
            lg.log_tx(f"cmd_{i:03d}")
        lg.stop()
        backup_size = os.path.getsize(log_path + ".1")
        assert backup_size > 0, "Резервный файл .1 пуст"

    def test_rotation_main_file_is_truncated(self, tmp_path):
        """После ротации основной файл мельче суммарного объёма записанных данных."""
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger(max_bytes=50)
        lg.start(log_path)
        # Пишем 10 строк по ~28 символов = ~280 байт суммарно
        for i in range(10):
            lg.log_tx(f"cmd_{i:03d}")
        lg.stop()
        main_size = os.path.getsize(log_path)
        # Основной файл не может вместить всё (280 >> 50)
        assert main_size < 280, "Основной файл не усечён после ротации"

    def test_no_rotation_without_overflow(self, tmp_path):
        """При достаточном max_bytes ротация не происходит."""
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger(max_bytes=10 * 1024 * 1024)
        lg.start(log_path)
        lg.log_tx("CMD")
        lg.stop()
        # '.1' не должно появиться
        assert not os.path.exists(log_path + ".1"), ".1 появился без ротации"


# ---------------------------------------------------------------------------
# 7. stop — идемпотентность
# ---------------------------------------------------------------------------

class TestStop:
    def test_stop_deactivates(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.stop()
        assert lg.is_active is False

    def test_stop_is_idempotent(self, tmp_path):
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.stop()
        lg.stop()  # повторный stop не должен падать

    def test_stop_before_start_is_noop(self):
        """stop() без предшествующего start() безопасен."""
        lg = ScpiLogger()
        lg.stop()  # не должно упасть

    def test_stop_writes_footer(self, tmp_path):
        """stop() дописывает строку-футер."""
        log_path = str(tmp_path / "test.log")
        lg = ScpiLogger()
        lg.start(log_path)
        lg.stop()
        content = _read(log_path)
        # Ожидаем строку с 'stopped'
        assert "=== SCPI log stopped" in content
