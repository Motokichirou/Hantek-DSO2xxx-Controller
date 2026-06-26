"""Tests for Scope facade and ChannelCollection — Task 8.5.

Все тесты используют FakeTransport; реального железа не требуется.
"""

from __future__ import annotations

import pytest

from hantek_dso2d15.transport.fake_transport import FakeTransport
from hantek_dso2d15.scpi.scope import ChannelCollection, Scope
from hantek_dso2d15.scpi.channel import Channel
from hantek_dso2d15.scpi.timebase import Timebase
from hantek_dso2d15.scpi.acquire import Acquire
from hantek_dso2d15.scpi.trigger import Trigger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_transport(*, open: bool = True) -> FakeTransport:
    """Создать FakeTransport, опционально открытый."""
    t = FakeTransport()
    if open:
        t.open()
    return t


# ---------------------------------------------------------------------------
# ChannelCollection
# ---------------------------------------------------------------------------

class TestChannelCollection:
    def test_getitem_returns_channel_instance(self):
        t = make_transport()
        cc = ChannelCollection(t)
        ch = cc[1]
        assert isinstance(ch, Channel)

    def test_cache_same_object_for_same_index(self):
        """scope.channel[1] is scope.channel[1] — кэш работает."""
        t = make_transport()
        cc = ChannelCollection(t)
        assert cc[1] is cc[1]

    def test_different_indices_return_different_objects(self):
        """channel[1] != channel[2]."""
        t = make_transport()
        cc = ChannelCollection(t)
        assert cc[1] is not cc[2]

    def test_all_valid_channels(self):
        """Все допустимые каналы 1-4 создаются без ошибок."""
        t = make_transport()
        cc = ChannelCollection(t)
        for n in (1, 2, 3, 4):
            ch = cc[n]
            assert isinstance(ch, Channel)

    def test_invalid_channel_raises(self):
        """channel[9] — должна быть ошибка (KeyError или ValueError)."""
        t = make_transport()
        cc = ChannelCollection(t)
        with pytest.raises((KeyError, ValueError)):
            _ = cc[9]

    def test_invalid_channel_zero_raises(self):
        """channel[0] — не входит в {1,2,3,4}, должна быть ошибка."""
        t = make_transport()
        cc = ChannelCollection(t)
        with pytest.raises((KeyError, ValueError)):
            _ = cc[0]

    def test_invalid_channel_5_raises(self):
        """channel[5] — не входит в {1,2,3,4}."""
        t = make_transport()
        cc = ChannelCollection(t)
        with pytest.raises((KeyError, ValueError)):
            _ = cc[5]


# ---------------------------------------------------------------------------
# Scope — lifecycle
# ---------------------------------------------------------------------------

class TestScopeLifecycle:
    def test_connect_opens_transport(self):
        """scope.connect() → transport.is_open is True."""
        t = FakeTransport()
        assert not t.is_open
        scope = Scope(t)
        scope.connect()
        assert t.is_open is True

    def test_is_connected_true_after_connect(self):
        """scope.is_connected is True после connect()."""
        t = FakeTransport()
        scope = Scope(t)
        scope.connect()
        assert scope.is_connected is True

    def test_disconnect_closes_transport(self):
        """scope.disconnect() → transport.is_open is False."""
        t = FakeTransport()
        scope = Scope(t)
        scope.connect()
        scope.disconnect()
        assert t.is_open is False

    def test_is_connected_false_after_disconnect(self):
        """scope.is_connected is False после disconnect()."""
        t = FakeTransport()
        scope = Scope(t)
        scope.connect()
        scope.disconnect()
        assert scope.is_connected is False

    def test_is_connected_initially_false(self):
        """До connect() is_connected == False."""
        t = FakeTransport()
        scope = Scope(t)
        assert scope.is_connected is False


# ---------------------------------------------------------------------------
# Scope — idn
# ---------------------------------------------------------------------------

class TestScopeIdn:
    def test_idn_returns_stripped_string(self):
        """scope.idn() = stripped ответ на *IDN?."""
        t = make_transport()
        t.set_response("*IDN?", "Hantek,DSO2D15,CN21034,V1.2.3\n")
        scope = Scope(t)
        result = scope.idn()
        assert result == "Hantek,DSO2D15,CN21034,V1.2.3"

    def test_idn_sends_correct_command(self):
        """scope.idn() отправляет именно '*IDN?'."""
        t = make_transport()
        t.set_response("*IDN?", "Hantek,DSO2D15,CN21034,V1.2.3")
        scope = Scope(t)
        scope.idn()
        assert t.queries[-1] == "*IDN?"

    def test_idn_already_stripped(self):
        """Если ответ без пробелов — всё равно возвращается как есть."""
        t = make_transport()
        t.set_response("*IDN?", "Hantek,DSO2D15,CN21034,V1.2.3")
        scope = Scope(t)
        assert scope.idn() == "Hantek,DSO2D15,CN21034,V1.2.3"


# ---------------------------------------------------------------------------
# Scope — атрибуты-подсистемы
# ---------------------------------------------------------------------------

class TestScopeSubsystems:
    def test_channel_is_channel_collection(self):
        t = make_transport()
        scope = Scope(t)
        assert isinstance(scope.channel, ChannelCollection)

    def test_timebase_is_timebase(self):
        t = make_transport()
        scope = Scope(t)
        assert isinstance(scope.timebase, Timebase)

    def test_acquire_is_acquire(self):
        t = make_transport()
        scope = Scope(t)
        assert isinstance(scope.acquire, Acquire)

    def test_trigger_is_trigger(self):
        t = make_transport()
        scope = Scope(t)
        assert isinstance(scope.trigger, Trigger)


# ---------------------------------------------------------------------------
# Сквозная проверка: scope.channel[n].scale записывает правильную SCPI-строку
# ---------------------------------------------------------------------------

class TestScopePassthrough:
    def test_channel1_scale_set_writes_correct_scpi(self):
        """scope.channel[1].scale = 1.0 → ':CHANnel1:SCALe 1'."""
        t = make_transport()
        scope = Scope(t)
        scope.channel[1].scale = 1.0
        assert t.writes[-1] == ":CHANnel1:SCALe 1"

    def test_channel2_scale_set_writes_correct_scpi(self):
        """scope.channel[2].scale = 0.5 → ':CHANnel2:SCALe 0.5'."""
        t = make_transport()
        scope = Scope(t)
        scope.channel[2].scale = 0.5
        assert t.writes[-1] == ":CHANnel2:SCALe 0.5"

    def test_channel_cache_after_write(self):
        """После write — объект канала тот же (кэш не сбрасывается)."""
        t = make_transport()
        scope = Scope(t)
        ch_before = scope.channel[1]
        scope.channel[1].scale = 2.0
        ch_after = scope.channel[1]
        assert ch_before is ch_after

    def test_channel9_raises_on_scope(self):
        """scope.channel[9] → ошибка (сквозная)."""
        t = make_transport()
        scope = Scope(t)
        with pytest.raises((KeyError, ValueError)):
            _ = scope.channel[9]
