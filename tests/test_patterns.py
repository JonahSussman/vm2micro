# tests/test_patterns.py
from vm2micro.analysis.patterns import detect_stack_patterns, get_all_patterns
from vm2micro.models import ServiceFingerprint, StackPattern


def test_get_all_patterns() -> None:
    patterns = get_all_patterns()
    assert len(patterns) > 0
    names = [p.name for p in patterns]
    assert "LAMP" in names
    assert "LEMP" in names


def test_detect_lamp_stack() -> None:
    fingerprints = [
        ServiceFingerprint(name="apache", category="web-server", version=None,
                          config_paths=[], data_paths=[], ports=[], evidence=[]),
        ServiceFingerprint(name="mysql", category="database", version=None,
                          config_paths=[], data_paths=[], ports=[], evidence=[]),
    ]
    matches = detect_stack_patterns(fingerprints)
    names = [m.name for m in matches]
    assert "LAMP" in names


def test_detect_lemp_stack() -> None:
    fingerprints = [
        ServiceFingerprint(name="nginx", category="web-server", version=None,
                          config_paths=[], data_paths=[], ports=[], evidence=[]),
        ServiceFingerprint(name="mysql", category="database", version=None,
                          config_paths=[], data_paths=[], ports=[], evidence=[]),
    ]
    matches = detect_stack_patterns(fingerprints)
    names = [m.name for m in matches]
    assert "LEMP" in names


def test_no_match_single_service() -> None:
    fingerprints = [
        ServiceFingerprint(name="redis", category="cache", version=None,
                          config_paths=[], data_paths=[], ports=[], evidence=[]),
    ]
    matches = detect_stack_patterns(fingerprints)
    names = [m.name for m in matches]
    assert "LAMP" not in names
    assert "LEMP" not in names


def test_pattern_has_decomposition_hint() -> None:
    patterns = get_all_patterns()
    for p in patterns:
        assert p.decomposition_hint, f"Pattern {p.name} missing decomposition_hint"
