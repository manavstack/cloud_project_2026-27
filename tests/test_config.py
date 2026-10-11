import os
import unittest
from unittest.mock import patch

from src.config import database_dsn


class DatabaseConfigurationTests(unittest.TestCase):
    def test_builds_required_local_database_target(self):
        env = {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "cloud_project",
            "POSTGRES_USER": "student1",
            "POSTGRES_PASSWORD": "test@password",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                database_dsn(),
                "postgresql://student1:test%40password@127.0.0.1:5432/cloud_project",
            )

    def test_database_url_has_priority(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://example"}, clear=True):
            self.assertEqual(database_dsn(), "postgresql://example")


if __name__ == "__main__":
    unittest.main()
