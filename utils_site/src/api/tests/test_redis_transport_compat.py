"""kombu and redis-py must agree, or every Celery broker connection dies.

kombu is a transitive dependency of celery; when it floated to 5.7.0 the prod
image shipped with redis-py 5.2.0 and kombu refused to open any Redis
connection (VersionMismatch in _get_client), so all async conversions failed.
"""

from django.test import SimpleTestCase
from kombu.transport.redis import Channel


class RedisTransportCompatTests(SimpleTestCase):
    def test_kombu_accepts_installed_redis_py(self):
        Channel._get_client(object.__new__(Channel))
