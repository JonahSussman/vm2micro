"""Web server service detectors."""

from vm2micro.models import DistroVariant, ServiceDetector

WEB_SERVER_DETECTORS: list[ServiceDetector] = [
    ServiceDetector(
        name="nginx",
        category="web-server",
        variants={
            "rhel": DistroVariant(
                package_names=["nginx"],
                service_names=["nginx.service"],
                config_paths=["/etc/nginx/", "/etc/nginx/nginx.conf", "/etc/nginx/conf.d/"],
                data_paths=["/usr/share/nginx/html/"],
            ),
            "debian": DistroVariant(
                package_names=["nginx", "nginx-full", "nginx-light"],
                service_names=["nginx.service"],
                config_paths=["/etc/nginx/", "/etc/nginx/nginx.conf", "/etc/nginx/sites-enabled/"],
                data_paths=["/var/www/html/"],
            ),
            "alpine": DistroVariant(
                package_names=["nginx"],
                service_names=["nginx"],
                config_paths=["/etc/nginx/", "/etc/nginx/nginx.conf"],
                data_paths=["/var/www/"],
            ),
        },
    ),
    ServiceDetector(
        name="apache",
        category="web-server",
        variants={
            "rhel": DistroVariant(
                package_names=["httpd"],
                service_names=["httpd.service"],
                config_paths=["/etc/httpd/", "/etc/httpd/conf/httpd.conf"],
                data_paths=["/var/www/html/"],
            ),
            "debian": DistroVariant(
                package_names=["apache2"],
                service_names=["apache2.service"],
                config_paths=["/etc/apache2/", "/etc/apache2/apache2.conf", "/etc/apache2/sites-enabled/"],
                data_paths=["/var/www/html/"],
            ),
        },
    ),
]
