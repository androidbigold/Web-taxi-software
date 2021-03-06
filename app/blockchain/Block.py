#!/usr/bin/python
# -*- coding: utf-8 -*-

from .Cryptography import signature_verify
import hashlib
import json
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import requests
import time


class Blockchain:
    __is_mine = False
    # __difficult = 5

    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # 创建创世块
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address: str) -> None:
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def remove_node(self, address: str) -> None:
        """
        Remove a existed node in the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """

        parsed_url = urlparse(address)
        self.nodes.discard(parsed_url.netloc)

    def valid_chain(self, chain: List[Dict[str, Any]]) -> bool:
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self, self_node) -> bool:
        """
        共识算法解决冲突
        使用网络中最长的链.
        :return:  如果链被取代返回 True, 否则为False
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            if node == self_node:
                continue
            response = requests.get(f'http://{node}/blockchain/chain_remote')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof: int, previous_hash: Optional[str]) -> Dict[str, Any]:
        """
        生成新块
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)

        return block

    def new_transaction(self, sender: str, recipient: str, amount: float, signature: str) -> int:
        """
        生成新交易信息，信息将加入到下一个待挖的区块中
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :param signature: Signature of the Sender
        :return: The index of the Block that will hold this transaction
        """

        trade_record = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'signature': signature,
        }
        # 验证签名
        if sender == '0' or signature_verify(trade_record) is True:
            self.current_transactions.append(trade_record)
            return self.last_block['index'] + 1
        else:
            return -1

    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]

    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        """
        生成块的 SHA-256 hash值
        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof: int) -> int:
        """
        简单的工作量证明:
         - 查找一个 p' 使得 hash(pp') 以difficult个0开头
         - p 是上一个块的证明,  p' 是当前的证明
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False and self.__is_mine is True:
            proof += 1
        if self.__is_mine is False:
            return -1
        else:
            return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int) -> bool:
        """
        验证证明: 是否hash(last_proof, proof)以difficult个0开头
        :param last_proof: Previous Proof
        :param proof: Current Proof
        :return: True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash.find('00000') == 0

    def mine_start(self):
        self.__is_mine = True

    def mine_stop(self):
        self.__is_mine = False

    def balance(self, wallet):
        balance = 0.0
        trans = []

        for block in self.chain:
            for transaction in block['transactions']:
                if transaction['recipient'] == wallet:
                    balance += transaction['amount']
                    trans.append(transaction)
                    trans[-1].update({'timestamp': block['timestamp']})
                elif transaction['sender'] == wallet:
                    balance -= transaction['amount']
                    trans.append(transaction)
                    trans[-1].update({'timestamp': block['timestamp']})

        return balance, trans

