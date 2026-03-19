"""Database service detectors."""

from vm2micro.models import DistroVariant, ServiceDetector

DATABASE_DETECTORS: list[ServiceDetector] = [
    ServiceDetector(
        name="postgresql",
        category="database",
        variants={
            "rhel": DistroVariant(
                package_names=["postgresql-server", "postgresql"],
                service_names=["postgresql.service"],
                config_paths=["/var/lib/pgsql/data/", "/var/lib/pgsql/data/postgresql.conf"],
                data_paths=["/var/lib/pgsql/data/"],
            ),
            "debian": DistroVariant(
                package_names=["postgresql", "postgresql-14", "postgresql-15", "postgresql-16"],
                service_names=["postgresql.service"],
                config_paths=["/etc/postgresql/"],
                data_paths=["/var/lib/postgresql/"],
            ),
        },
    ),
    ServiceDetector(
        name="mysql",
        category="database",
        variants={
            "rhel": DistroVariant(
                package_names=["mysql-server", "mariadb-server", "mariadb"],
                service_names=["mysqld.service", "mariadb.service"],
                config_paths=["/etc/my.cnf", "/etc/my.cnf.d/"],
                data_paths=["/var/lib/mysql/"],
            ),
            "debian": DistroVariant(
                package_names=["mysql-server", "mariadb-server"],
                service_names=["mysql.service", "mariadb.service"],
                config_paths=["/etc/mysql/", "/etc/mysql/my.cnf"],
                data_paths=["/var/lib/mysql/"],
            ),
        },
    ),
    ServiceDetector(
        name="redis",
        category="cache",
        variants={
            "rhel": DistroVariant(
                package_names=["redis"],
                service_names=["redis.service"],
                config_paths=["/etc/redis/", "/etc/redis.conf"],
                data_paths=["/var/lib/redis/"],
            ),
            "debian": DistroVariant(
                package_names=["redis-server"],
                service_names=["redis-server.service", "redis.service"],
                config_paths=["/etc/redis/"],
                data_paths=["/var/lib/redis/"],
            ),
        },
    ),
    ServiceDetector(
        name="mongodb",
        category="database",
        variants={
            "rhel": DistroVariant(
                package_names=["mongodb-server", "mongodb-org-server"],
                service_names=["mongod.service"],
                config_paths=["/etc/mongod.conf"],
                data_paths=["/var/lib/mongo/"],
            ),
            "debian": DistroVariant(
                package_names=["mongodb-server", "mongodb-org-server"],
                service_names=["mongod.service"],
                config_paths=["/etc/mongod.conf"],
                data_paths=["/var/lib/mongodb/"],
            ),
        },
    ),
]
