# SPDX-License-Identifier: MPL-2.0
import socket
import unittest

from vela.core.api_router import ApiRouter
from vela.core.api_server import ApiServer


class DynamicApiPortTests(unittest.TestCase):
    HOST = "127.0.0.1"

    def _free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.HOST, 0))
            return sock.getsockname()[1]

    def test_keeps_configured_port_when_it_is_free(self):
        port = self._free_port()

        resolved = ApiServer.resolve_port(
            host=self.HOST,
            preferred_port=port,
            auto_port=True,
        )

        self.assertEqual(resolved, port)

    def test_allocates_another_port_when_configured_port_is_busy(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_socket:
            busy_socket.bind((self.HOST, 0))
            busy_socket.listen(1)

            busy_port = busy_socket.getsockname()[1]

            resolved = ApiServer.resolve_port(
                host=self.HOST,
                preferred_port=busy_port,
                auto_port=True,
            )

            self.assertNotEqual(resolved, busy_port)
            self.assertTrue(ApiServer.is_port_available(self.HOST, resolved))

    def test_raises_when_auto_port_is_disabled(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_socket:
            busy_socket.bind((self.HOST, 0))
            busy_socket.listen(1)

            busy_port = busy_socket.getsockname()[1]

            with self.assertRaises(RuntimeError):
                ApiServer.resolve_port(
                    host=self.HOST,
                    preferred_port=busy_port,
                    auto_port=False,
                )

    def test_port_zero_always_requests_dynamic_allocation(self):
        resolved = ApiServer.resolve_port(
            host=self.HOST,
            preferred_port=0,
            auto_port=False,
        )

        self.assertGreater(resolved, 0)
        self.assertTrue(ApiServer.is_port_available(self.HOST, resolved))

    def test_waitress_start_uses_dynamic_port_when_preferred_port_is_busy(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_socket:
            busy_socket.bind((self.HOST, 0))
            busy_socket.listen(1)
            busy_port = busy_socket.getsockname()[1]

            server = ApiServer(
                ApiRouter(),
                host=self.HOST,
                port=busy_port,
                auto_port=True,
                server="waitress",
            )
            actual_port = server.start()
            try:
                self.assertNotEqual(actual_port, busy_port)
                self.assertGreater(actual_port, 0)
                self.assertTrue(server.wait_until_ready(timeout=2))
            finally:
                server.stop()

    def test_waitress_start_raises_when_preferred_port_is_busy_and_auto_port_disabled(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_socket:
            busy_socket.bind((self.HOST, 0))
            busy_socket.listen(1)
            busy_port = busy_socket.getsockname()[1]

            server = ApiServer(
                ApiRouter(),
                host=self.HOST,
                port=busy_port,
                auto_port=False,
                server="waitress",
            )
            with self.assertRaises(RuntimeError):
                server.start()


if __name__ == "__main__":
    unittest.main()
