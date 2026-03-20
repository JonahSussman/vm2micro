from vm2micro.analysis.detectors import get_all_detectors
from vm2micro.models import ServiceDetector


def test_registry_returns_detectors() -> None:
    detectors = get_all_detectors()
    assert len(detectors) > 0
    assert all(isinstance(d, ServiceDetector) for d in detectors)


def test_registry_has_web_servers() -> None:
    detectors = get_all_detectors()
    names = [d.name for d in detectors]
    assert "nginx" in names
    assert "apache" in names


def test_registry_has_databases() -> None:
    detectors = get_all_detectors()
    names = [d.name for d in detectors]
    assert "postgresql" in names
    assert "mysql" in names


def test_registry_has_app_servers() -> None:
    detectors = get_all_detectors()
    names = [d.name for d in detectors]
    assert "tomcat" in names


def test_registry_has_queues() -> None:
    detectors = get_all_detectors()
    names = [d.name for d in detectors]
    assert "rabbitmq" in names
