"""Application server service detectors."""

from vm2micro.models import DistroVariant, ServiceDetector

APP_SERVER_DETECTORS: list[ServiceDetector] = [
    ServiceDetector(
        name="tomcat",
        category="app-server",
        variants={
            "rhel": DistroVariant(
                package_names=["tomcat"],
                service_names=["tomcat.service"],
                config_paths=["/etc/tomcat/", "/opt/tomcat/conf/"],
                data_paths=["/var/lib/tomcat/webapps/", "/opt/tomcat/webapps/"],
            ),
            "debian": DistroVariant(
                package_names=["tomcat9", "tomcat10"],
                service_names=["tomcat9.service", "tomcat10.service"],
                config_paths=["/etc/tomcat9/", "/etc/tomcat10/", "/opt/tomcat/conf/"],
                data_paths=["/var/lib/tomcat9/webapps/", "/var/lib/tomcat10/webapps/"],
            ),
        },
    ),
    ServiceDetector(
        name="gunicorn",
        category="app-server",
        variants={
            "rhel": DistroVariant(
                package_names=["python3-gunicorn"],
                service_names=["gunicorn.service"],
                config_paths=["/etc/gunicorn/"],
                data_paths=[],
            ),
            "debian": DistroVariant(
                package_names=["gunicorn", "python3-gunicorn"],
                service_names=["gunicorn.service"],
                config_paths=["/etc/gunicorn/"],
                data_paths=[],
            ),
        },
    ),
    ServiceDetector(
        name="puma",
        category="app-server",
        variants={
            "rhel": DistroVariant(
                package_names=[],
                service_names=["puma.service"],
                config_paths=[],
                data_paths=[],
            ),
            "debian": DistroVariant(
                package_names=[],
                service_names=["puma.service"],
                config_paths=[],
                data_paths=[],
            ),
        },
    ),
    ServiceDetector(
        name="pm2",
        category="app-server",
        variants={
            "rhel": DistroVariant(
                package_names=[],
                service_names=["pm2-root.service"],
                config_paths=["/etc/pm2/"],
                data_paths=[],
            ),
            "debian": DistroVariant(
                package_names=[],
                service_names=["pm2-root.service"],
                config_paths=["/etc/pm2/"],
                data_paths=[],
            ),
        },
    ),
]
