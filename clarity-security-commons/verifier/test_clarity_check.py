import unittest

from clarity_check import address_to_parts, decode, encode_arg, parts_to_address

ADDRS = [
    "SP2ZNGJ85ENDY6QRHQ5P2D4FXKGZWCKTB2T0Z55KS",
    "SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG",
    "SP102V8P0F7JX67ARQ77WEA3D3CFB5XW39REDT0AM",
    "SPQC38PW542EQJ5M11CR25P7BS1CA6QT4TBXGB3M",
    "SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR",
]


class AddressTest(unittest.TestCase):
    def test_round_trip_real_mainnet_addresses(self):
        for a in ADDRS:
            self.assertEqual(parts_to_address(*address_to_parts(a)), a)

    def test_bad_checksum_rejected(self):
        bad = ADDRS[0][:-1] + ("T" if ADDRS[0][-1] != "T" else "V")
        with self.assertRaises(ValueError):
            address_to_parts(bad)


class ValueTest(unittest.TestCase):
    def round_trip(self, literal):
        v, end = decode(encode_arg(literal))
        self.assertEqual(end, len(encode_arg(literal)))
        return v

    def test_scalars(self):
        self.assertEqual(self.round_trip("u100"), 100)
        self.assertEqual(self.round_trip("-5"), -5)
        self.assertIs(self.round_trip("true"), True)
        self.assertIsNone(self.round_trip("none"))
        self.assertEqual(self.round_trip('"abc"'), "abc")

    def test_uint_wire_format(self):
        self.assertEqual(encode_arg("u1").hex(), "01" + "00" * 15 + "01")

    def test_principals(self):
        self.assertEqual(self.round_trip("'" + ADDRS[0]), ADDRS[0])
        self.assertEqual(self.round_trip("'" + ADDRS[1] + ".token-ststx"),
                         ADDRS[1] + ".token-ststx")

    def test_response_tuple(self):
        # (ok { a: u1, b: false })
        raw = bytes.fromhex(
            "07" "0c" "00000002"
            "01" "61" "01" + "00" * 15 + "01"
            "01" "62" "04")
        self.assertEqual(decode(raw)[0], {"a": 1, "b": False})

    def test_err(self):
        raw = bytes.fromhex("08" "01" + "00" * 15 + "65")
        self.assertEqual(decode(raw)[0], {"err": 101})


if __name__ == "__main__":
    unittest.main()
