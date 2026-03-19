"""Message queue service detectors."""

from vm2micro.models import DistroVariant, ServiceDetector

QUEUE_DETECTORS: list[ServiceDetector] = [
    ServiceDetector(
        name="rabbitmq",
        category="queue",
        variants={
            "rhel": DistroVariant(
                package_names=["rabbitmq-server"],
                service_names=["rabbitmq-server.service"],
                config_paths=["/etc/rabbitmq/"],
                data_paths=["/var/lib/rabbitmq/"],
            ),
            "debian": DistroVariant(
                package_names=["rabbitmq-server"],
                service_names=["rabbitmq-server.service"],
                config_paths=["/etc/rabbitmq/"],
                data_paths=["/var/lib/rabbitmq/"],
            ),
        },
    ),
    ServiceDetector(
        name="kafka",
        category="queue",
        variants={
            "rhel": DistroVariant(
                package_names=[],
                service_names=["kafka.service"],
                config_paths=["/etc/kafka/", "/opt/kafka/config/"],
                data_paths=["/var/lib/kafka/"],
            ),
            "debian": DistroVariant(
                package_names=[],
                service_names=["kafka.service"],
                config_paths=["/etc/kafka/", "/opt/kafka/config/"],
                data_paths=["/var/lib/kafka/"],
            ),
        },
    ),
]
