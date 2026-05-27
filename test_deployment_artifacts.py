import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock

PROJECT_DIR = Path('/mnt/c/Users/fhani/Documents/MyNextBestHome/myNBHBackend')
SETTINGS_PATH = PROJECT_DIR / 'backend_config' / 'settings.py'
DOCKERFILE_PATH = PROJECT_DIR / 'Dockerfile'
COMPOSE_PATH = PROJECT_DIR / 'docker-compose.yml'


def load_settings_with_env(env_overrides, module_name='backend_settings_test'):
    with mock.patch.dict(os.environ, env_overrides, clear=False):
        spec = importlib.util.spec_from_file_location(module_name, SETTINGS_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class DeploymentArtifactTests(unittest.TestCase):
    def test_settings_use_sqlite_when_use_postgres_false(self):
        settings = load_settings_with_env({
            'USE_POSTGRES': 'False',
            'POSTGRES_DB': 'ignored_db',
            'POSTGRES_USER': 'ignored_user',
            'POSTGRES_PASSWORD': 'ignored_pw',
            'POSTGRES_HOST': 'ignored_host',
            'POSTGRES_PORT': '5432',
        }, module_name='settings_sqlite_case')
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')
        self.assertTrue(str(settings.DATABASES['default']['NAME']).endswith('db.sqlite3'))

    def test_settings_use_postgres_env_when_use_postgres_true(self):
        settings = load_settings_with_env({
            'USE_POSTGRES': 'True',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pw',
            'POSTGRES_HOST': 'db',
            'POSTGRES_PORT': '5433',
        }, module_name='settings_postgres_case')
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(settings.DATABASES['default']['NAME'], 'test_db')
        self.assertEqual(settings.DATABASES['default']['USER'], 'test_user')
        self.assertEqual(settings.DATABASES['default']['PASSWORD'], 'test_pw')
        self.assertEqual(settings.DATABASES['default']['HOST'], 'db')
        self.assertEqual(settings.DATABASES['default']['PORT'], '5433')

    def test_dockerfile_uses_gunicorn_instead_of_runserver(self):
        dockerfile = DOCKERFILE_PATH.read_text(encoding='utf-8')
        self.assertIn('gunicorn', dockerfile)
        self.assertNotIn('runserver', dockerfile)

    def test_docker_compose_exists_with_web_and_db_services(self):
        self.assertTrue(COMPOSE_PATH.exists())
        compose = COMPOSE_PATH.read_text(encoding='utf-8')
        self.assertIn('web:', compose)
        self.assertIn('db:', compose)
        self.assertIn('gunicorn', compose)


if __name__ == '__main__':
    unittest.main()
