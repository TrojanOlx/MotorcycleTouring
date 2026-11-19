import unittest
from unittest.mock import Mock, call

from obd_rpm import OBDResponseError, UnsupportedPID, read_rpm


SUPPORTED = "41 00 00 10 00 00\r>"


class ReadRPMTest(unittest.TestCase):
    def test_checks_support_then_reads_rpm(self):
        exchange = Mock(side_effect=[f"0100\rSEARCHING...\r{SUPPORTED}", "410C1AF8\r>"])
        self.assertEqual(read_rpm(exchange), 1726)
        self.assertEqual(exchange.call_args_list, [call("0100"), call("010C")])

    def test_unsupported_rpm_is_not_queried(self):
        exchange = Mock(return_value="41 00 00 00 00 00\r>")
        with self.assertRaises(UnsupportedPID):
            read_rpm(exchange)
        exchange.assert_called_once_with("0100")

    def test_zero_rpm_is_valid(self):
        self.assertEqual(read_rpm(Mock(side_effect=[SUPPORTED, "410C0000>"])), 0)

    def test_preserves_fractional_rpm(self):
        self.assertEqual(read_rpm(Mock(side_effect=[SUPPORTED, "410C1AF9>"])), 1726.25)

    def test_rejects_unusable_adapter_responses(self):
        for reply in ("NO DATA\r>", "STOPPED\r>", "41 0C 1A F8", "410C1AZ8>",
                      "410D1AF8>", "410C1AF8\r410C1AF9\r>", "SEARCHING...\r>"):
            with self.subTest(reply=reply), self.assertRaises(OBDResponseError):
                read_rpm(Mock(side_effect=[SUPPORTED, reply]))

    def test_invalid_support_reply_never_queries_rpm(self):
        exchange = Mock(return_value="41000010>")
        with self.assertRaises(OBDResponseError):
            read_rpm(exchange)
        exchange.assert_called_once_with("0100")

    def test_timeout_does_not_reuse_previous_rpm(self):
        exchange = Mock(side_effect=[SUPPORTED, "410C1AF8>", SUPPORTED, TimeoutError()])
        self.assertEqual(read_rpm(exchange), 1726)
        with self.assertRaises(TimeoutError):
            read_rpm(exchange)


if __name__ == "__main__":
    unittest.main()
