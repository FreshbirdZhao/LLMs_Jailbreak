import unittest
from unittest.mock import patch
from urllib import error

from Analyze.llm_clients import ExternalAPIClient, build_llm_client


class _Resp:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'{"choices":[{"message":{"content":"ok"}}]}'


class ExternalClientTest(unittest.TestCase):
    def test_external_client_retries_transient_errors(self):
        client = ExternalAPIClient(model="x", timeout=1, max_retries=1, retry_backoff=0.0)
        responses = [error.URLError("timeout"), _Resp()]

        def _fake_urlopen(req, timeout):
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        with patch("Analyze.llm_clients.request.urlopen", side_effect=_fake_urlopen):
            self.assertEqual(client.complete("p"), "ok")


class BuildClientTest(unittest.TestCase):
    def test_build_llm_client_passes_retry_settings_to_external_client(self):
        client = build_llm_client(
            {
                "provider": "external",
                "model": "m",
                "timeout": 12,
                "max_retries": 3,
                "retry_backoff": 2.5,
            }
        )
        self.assertIsInstance(client, ExternalAPIClient)
        self.assertEqual(client.timeout, 12)
        self.assertEqual(client.max_retries, 3)
        self.assertEqual(client.retry_backoff, 2.5)


if __name__ == "__main__":
    unittest.main()
