from typing import Any, Dict
import cbors
import base64
from pycoin.encoding.hexbytes import b2h, h2b
from pycoin.satoshi.der import sigdecode_der
from cryptos.main import encode_sig, decode_sig, ecdsa_raw_recover, encode_pubkey
import hashlib
import binascii
from secp256k1 import PrivateKey

cid_prefix = bytes([0x01, 0x71, 0xa0, 0xe4, 0x02, 0x20])


def sign(ft, pri_key, pub_key):
    digest_cbor = hashlib.blake2b(digest_size=32, key=b"", salt=b"", person=b"")
    digest_cbor.update(ft.cbor_serial())
    digest_sign = hashlib.blake2b(digest_size=32, key=b"", salt=b"", person=b"")
    digest_sign.update(cid_prefix.__add__(digest_cbor.digest()))
    tx_decode = binascii.hexlify(digest_sign.digest()).decode()
    privkey = PrivateKey(bytes(bytearray.fromhex(pri_key)), raw=True)
    sig_check = privkey.ecdsa_sign(bytes(bytearray.fromhex(tx_decode)), raw=True)
    sig_ser = privkey.ecdsa_serialize(sig_check)
    sign_str = sig_ser.hex()
    v, r, s = get_signature(sign_str, tx_decode, pub_key)
    sign_str_h = handle_vrs(v, r, s)
    sign_msg = ft.signed_tx(sign_str_h)
    return sign_msg


def get_signature(sign_hex, unsign_hex, pubkey):
    rs = sigdecode_der(h2b(sign_hex))
    r, s = rs
    bin_pubkey = b2h(encode_pubkey(h2b(pubkey), 'bin'))
    for v in [27, 28, 29, 30, 31]:
        v, r, s = decode_sig(encode_sig(v, r, s))
        Q = ecdsa_raw_recover(h2b(unsign_hex), (v, r, s))
        pubkey = encode_pubkey(Q, 'hex_compressed' if v >= 30 else 'hex')
        if pubkey != bin_pubkey:
            continue
        else:
            return v, r, s
    return v, r, s


def handle_vrs(v, r, s):
    r_hex = hex(r)[2:]
    s_hex = hex(s)[2:]
    r_hex_h = r_hex + "0" if len(r_hex) != 64 else r_hex
    s_hex_h = "0" + s_hex if len(s_hex) != 64 else s_hex
    r_s_hex = r_hex_h + s_hex_h
    v_hex = '0' + str(v - 27)
    return r_s_hex + v_hex


class FilTransaction:
    From: str
    To: str
    Nonce: int
    Value: int
    GasLimit: int
    GasFeeCap: int
    GasPremium: int
    Method: int
    Params: str
    Version: int

    def __init__(
            self,
            From: str,
            To: str,
            Nonce: int,
            Value: int,
            GasLimit: int,
            GasFeeCap: int,
            GasPremium: int,
            Method: int,
            Params: any,
            Version: int):
        self.From = From
        self.To = To
        self.Nonce = Nonce
        self.Value = Value
        self.GasLimit = GasLimit
        self.GasFeeCap = GasFeeCap
        self.GasPremium = GasPremium
        self.Method = Method
        self.Params = Params
        self.Version = Version

    def signed_tx(self, sign_dt):
        tx_msg: Dict[str, Any] = {
            'From': self.From,
            'To': self.To,
            'Nonce': self.Nonce,
            'Value': str(self.Value),
            'GasLimit': self.GasLimit,
            'GasFeeCap': str(self.GasFeeCap),
            'GasPremium': str(self.GasPremium),
            'Method': self.Method,
            'Params': self.Params,
            'Version': self.Version
        }

        sign_msg: Dict[str, Any] = {
            "Type": 1,
            "Data": base64.b64encode(binascii.unhexlify(sign_dt)).decode('utf-8')
        }
        signed_tx_data: Dict[str, Any] = {
            "Message": tx_msg,
            "Signature": sign_msg
        }
        return signed_tx_data

    def _b32_padding(self, s: str):
        return s + ("=" * (8 - (len(s) % 8)))

    def addr2base32(self, address: str):
        b = bytearray.fromhex("01")
        sub_address = address[2:]
        padd_addrr = self._b32_padding(sub_address.upper())
        b32_address = base64.b32decode(padd_addrr)
        valid_addr = b32_address[0:20]
        return b.__add__(valid_addr)

    def cbor_encode(self, data):
        return cbors.dumpb(data)

    def cbor_clong2b(self, data):
        data2hex = hex(data).replace('0x', '')
        if len(data2hex) % 2 == 0:
            data2hex = "00" + data2hex
        else:
            data2hex = "000" + data2hex
        return h2b(data2hex)

    def cbor_serial(self):
        f_c = self.addr2base32(self.From)
        t_c = self.addr2base32(self.To)
        return bytearray.fromhex("8a") \
            .__add__(self.cbor_encode(self.Version))\
            .__add__(self.cbor_encode(h2b(t_c.hex())))\
            .__add__(self.cbor_encode(h2b(f_c.hex())))\
            .__add__(self.cbor_encode(self.Nonce)) \
            .__add__(self.cbor_encode(self.cbor_clong2b(self.Value))) \
            .__add__(self.cbor_encode(self.GasLimit)) \
            .__add__(self.cbor_encode(self.cbor_clong2b(self.GasFeeCap))) \
            .__add__(self.cbor_encode(self.cbor_clong2b(self.GasPremium))) \
            .__add__(self.cbor_encode(self.Method))\
            .__add__(self.cbor_encode(bytearray.fromhex("")))

    def tx_data(self):
        return {
            'From': self.From,
            'To': self.To,
            'Nonce': self.Nonce,
            'Value': str(self.Value),
            'GasLimit': self.GasLimit,
            'GasFeeCap': str(self.GasFeeCap),
            'GasPremium': str(self.GasPremium),
            'Method': self.Method,
            'Params': self.Params,
            'Version': self.Version
        }