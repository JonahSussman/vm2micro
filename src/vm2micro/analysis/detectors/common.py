"""Common service detectors (elasticsearch, logstash, kibana)."""

from vm2micro.models import DistroVariant, ServiceDetector

COMMON_DETECTORS: list[ServiceDetector] = [
    ServiceDetector(
        name="elasticsearch",
        category="search",
        variants={
            "rhel": DistroVariant(
                package_names=["elasticsearch"],
                service_names=["elasticsearch.service"],
                config_paths=["/etc/elasticsearch/"],
                data_paths=["/var/lib/elasticsearch/"],
            ),
            "debian": DistroVariant(
                package_names=["elasticsearch"],
                service_names=["elasticsearch.service"],
                config_paths=["/etc/elasticsearch/"],
                data_paths=["/var/lib/elasticsearch/"],
            ),
        },
    ),
    ServiceDetector(
        name="logstash",
        category="pipeline",
        variants={
            "rhel": DistroVariant(
                package_names=["logstash"],
                service_names=["logstash.service"],
                config_paths=["/etc/logstash/"],
                data_paths=["/var/lib/logstash/"],
            ),
            "debian": DistroVariant(
                package_names=["logstash"],
                service_names=["logstash.service"],
                config_paths=["/etc/logstash/"],
                data_paths=["/var/lib/logstash/"],
            ),
        },
    ),
    ServiceDetector(
        name="kibana",
        category="dashboard",
        variants={
            "rhel": DistroVariant(
                package_names=["kibana"],
                service_names=["kibana.service"],
                config_paths=["/etc/kibana/"],
                data_paths=[],
            ),
            "debian": DistroVariant(
                package_names=["kibana"],
                service_names=["kibana.service"],
                config_paths=["/etc/kibana/"],
                data_paths=[],
            ),
        },
    ),
]
