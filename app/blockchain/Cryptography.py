#!/usr/bin/python
# coding=utf-8

import base64
from Crypto import Random
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
from Crypto.PublicKey import RSA
from typing import Dict, Any


def key_generation():
    # 伪随机数生成器
    random_generator = Random.new().read

    # 生成2048比特秘钥对(pk, sk)
    rsa = RSA.generate(2048, random_generator)
    private_pem = rsa.exportKey()
    public_pem = rsa.publickey().exportKey()
    return {'private_pem': private_pem, 'public_pem': public_pem}


def signature_generation(trade_message: str, private_key: str) -> str:
    rsakey = RSA.importKey(private_key)
    signer = Signature_pkcs1_v1_5.new(rsakey)
    digest = SHA.new()
    digest.update(trade_message.encode())
    sign = signer.sign(digest)
    signature = base64.b64encode(sign)
    return signature.decode()


def signature_verify(trade_record: Dict[str, Any]) -> bool:
    key = trade_record['sender']
    signature = trade_record['signature'].encode()
    trade_message = str(trade_record['sender']) + str(trade_record['recipient']) + str(trade_record['amount'])
    rsakey = RSA.importKey(key)
    verifier = Signature_pkcs1_v1_5.new(rsakey)
    digest = SHA.new()
    # Assumes the data is base64 encoded to begin with
    digest.update(trade_message.encode())
    is_verify = verifier.verify(digest, base64.b64decode(signature))
    return is_verify
