"""
ECN 通知总线单元测试。
"""
from app.services.ecn import ECNNotifier


def test_initial_empty():
    n = ECNNotifier()
    assert n.get() == []
    assert n.has_notifications is False


def test_publish_overwrites():
    n = ECNNotifier()
    n.publish(["a", "b"])
    assert n.get() == ["a", "b"]
    assert n.has_notifications is True
    n.publish(["c"])
    assert n.get() == ["c"]


def test_clear():
    n = ECNNotifier()
    n.publish(["a"])
    n.clear()
    assert n.get() == []
    assert n.has_notifications is False
