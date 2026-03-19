# src/vm2micro/analysis/patterns.py
"""Stack pattern matching — identify common multi-service stacks."""

from __future__ import annotations

from vm2micro.models import ServiceFingerprint, StackPattern

_PATTERNS: list[StackPattern] = [
    StackPattern(
        name="LAMP",
        services=["apache", "mysql"],
        relationships=[("apache", "connects_to", "mysql")],
        decomposition_hint="Separate web/app tier (apache+PHP) from database tier (mysql). Consider using Red Hat UBI base images.",
    ),
    StackPattern(
        name="LEMP",
        services=["nginx", "mysql"],
        relationships=[("nginx", "connects_to", "mysql")],
        decomposition_hint="Separate web/proxy tier (nginx) from database tier (mysql). Nginx config needs review for upstream backends.",
    ),
    StackPattern(
        name="LENP",
        services=["nginx", "postgresql"],
        relationships=[("nginx", "connects_to", "postgresql")],
        decomposition_hint="Separate web/proxy tier (nginx) from database tier (postgresql).",
    ),
    StackPattern(
        name="Rails",
        services=["nginx", "redis", "postgresql"],
        relationships=[
            ("nginx", "proxies_to", "rails"),
            ("rails", "connects_to", "postgresql"),
            ("rails", "connects_to", "redis"),
        ],
        decomposition_hint="Separate into web proxy (nginx), app server (rails/puma), background workers (sidekiq), cache (redis), database (postgresql).",
    ),
    StackPattern(
        name="Java/Tomcat",
        services=["tomcat"],
        relationships=[],
        decomposition_hint="Tomcat app server with embedded WAR. Consider building a container from the WAR directly using a JBoss/Tomcat base image.",
    ),
    StackPattern(
        name="Django",
        services=["nginx", "postgresql"],
        relationships=[
            ("nginx", "proxies_to", "gunicorn"),
            ("gunicorn", "connects_to", "postgresql"),
        ],
        decomposition_hint="Separate web proxy (nginx), app server (gunicorn), task queue (celery if present), database (postgresql).",
    ),
    StackPattern(
        name="ELK",
        services=["elasticsearch", "logstash", "kibana"],
        relationships=[
            ("logstash", "sends_to", "elasticsearch"),
            ("kibana", "reads_from", "elasticsearch"),
        ],
        decomposition_hint="Each component is already designed to run independently. Deploy as separate containers with shared network.",
    ),
    StackPattern(
        name="Single Database",
        services=["postgresql"],
        relationships=[],
        decomposition_hint="Single database server. Containerize with persistent volume for data directory.",
    ),
    StackPattern(
        name="Single Database (MySQL)",
        services=["mysql"],
        relationships=[],
        decomposition_hint="Single MySQL/MariaDB server. Containerize with persistent volume for /var/lib/mysql.",
    ),
    StackPattern(
        name="Single Web Server",
        services=["nginx"],
        relationships=[],
        decomposition_hint="Static web server. Simple containerization with config and document root mounted.",
    ),
    StackPattern(
        name="Single Web Server (Apache)",
        services=["apache"],
        relationships=[],
        decomposition_hint="Static web server. Simple containerization with config and document root mounted.",
    ),
]


def get_all_patterns() -> list[StackPattern]:
    """Return all known stack patterns."""
    return list(_PATTERNS)


def detect_stack_patterns(
    fingerprints: list[ServiceFingerprint],
) -> list[StackPattern]:
    """Match fingerprints against known stack patterns. Returns matching patterns sorted by specificity (most services matched first)."""
    found_names = {fp.name for fp in fingerprints}
    matches: list[tuple[int, StackPattern]] = []

    for pattern in _PATTERNS:
        required = set(pattern.services)
        if required.issubset(found_names):
            matches.append((len(required), pattern))

    # Sort by number of services matched (most specific first)
    matches.sort(key=lambda x: x[0], reverse=True)
    return [pattern for _, pattern in matches]
