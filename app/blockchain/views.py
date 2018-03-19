from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from . import blockchain
from .Cryptography import *
from .Block import *
from .forms import TransactionForm
from config import server_address
import requests
from urllib.error import HTTPError
import json

# IP address of this node
ip = None

# Address of this node for mine
node_identifier = ''

# Instantiate the Blockchain
blockchain_local = Blockchain()


@blockchain.route('/index', methods=['GET'])
def index():
    return render_template('blockchain/index.html')


@blockchain.route('/nodes', methods=['GET', 'POST'])
def nodes():
    global ip
    ip = request.remote_addr
    return render_template('blockchain/nodes.html', ip_address=ip)


@blockchain.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain_local.last_block
    last_proof = last_block['proof']
    proof = blockchain_local.proof_of_work(last_proof)

    # 给工作量证明的节点提供奖励.
    # 发送者为 "0" 表明是新挖出的币
    blockchain_local.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=10,
        signature="0",
    )

    # Forge the new Block by adding it to the chain
    block = blockchain_local.new_block(proof, None)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return render_template('/blockchain/response.html',
                           response=json.dumps(response,
                                               indent=4).replace('\\n',
                                                                 '<br>').replace(',', '<br>'))


@blockchain.route('/transactions', methods=['GET', 'POST'])
def transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        global sender, recipient, amount
        sender = form.sender.data
        recipient = form.recipient.data
        amount = form.amount.data
        private_key = form.private_key.data
        # 对交易信息签名
        message = str(sender) + str(recipient) + str(amount)
        try:
            global signature
            signature = signature_generation(message, private_key)
        except:
            flash('invalid message')
        else:
            try:
                index = blockchain_local.new_transaction(sender, recipient, amount, signature)
            except:
                flash('invalid key')
            else:
                if index == -1:
                    flash('invalid key')
                else:
                    flash('Transaction will be added to Block {0}'.format(index))
                    form.sender.data = ''
                    form.recipient.data = ''
                    form.amount.data = 0.0
                    form.private_key.data = ''
                    return render_template('blockchain/transactions.html', form=form)
    return render_template('blockchain/transactions.html', form=form)


@blockchain.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain_local.chain,
        'length': len(blockchain_local.chain),
    }
    return render_template('/blockchain/response.html',
                           response=json.dumps(response,
                                               indent=4).replace('\\n',
                                                                 '<br>').replace(',', '<br>'))


@blockchain.route('/wallet/obtain', methods=['GET'])
def obtain_wallet():
    key_pair = key_generation()
    response = {
        'private_key': key_pair['private_pem'].decode(),
        'public_key': key_pair['public_pem'].decode(),
    }
    return render_template('/blockchain/response.html',
                           response=json.dumps(response,
                                               indent=4).replace('\\n',
                                                                 '<br>').replace(',', '<br>').replace(':', ':<br>'))


@blockchain.route('/nodes/register_local', methods=['GET', 'POST'])
def register_local_node():
    global ip
    url = 'http://127.0.0.1:5000/blockchain/nodes/register_remote'
    postdict = {
        'nodes': 'http://127.0.0.1:5001'
    }

    blockchain_local.register_node('http://127.0.0.1:5000')

    try:
        requests.post(url, json=postdict)
    except HTTPError as e:
        flash('Error: register failed')
        return render_template('/blockchain/response.html', response=e.read())
    else:
        flash('Your node has been registered')
        return render_template('/blockchain/nodes.html', ip_address=ip)


@blockchain.route('/nodes/register_remote', methods=['GET', 'POST'])
def register_remote_node():
    values = request.get_json()

    node = values.get('nodes')
    if node is None:
        return "Error: Please supply a valid list of nodes", 400

    blockchain_local.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'nodes': list(blockchain_local.nodes),
    }
    return jsonify(response), 201


@blockchain.route('/nodes/get', methods=['GET'])
def get_nodes():
    response = {
        'nodes': list(blockchain_local.nodes),
    }
    return render_template('/blockchain/response.html',
                           response=json.dumps(response,
                                               indent=4).replace('\\n',
                                                                 '<br>').replace(',', '<br>'))


@blockchain.route('/nodes/remove_local', methods=['GET', 'POST'])
def remove_local_node():
    global ip
    url = 'http://127.0.0.1:5000/blockchain/nodes/remove_remote'
    postdict = {
        'nodes': 'http://127.0.0.1:5001'
    }

    blockchain_local.remove_node('http://127.0.0.1:5000')

    try:
        requests.post(url, json=postdict)
    except HTTPError as e:
        flash('Error: remove failed')
        return render_template('/blockchain/response.html', response=e.read())
    else:
        flash('Your node has been removed')
        return render_template('/blockchain/nodes.html', ip_address=ip)


@blockchain.route('/nodes/remove_remote', methods=['GET', 'POST'])
def remove_remote_node():
    values = request.get_json()

    node = values.get('nodes')
    if node is None:
        return "Error: Please supply a valid list of nodes", 400

    blockchain_local.remove_node(node)

    response = {
        'message': 'The nodes have been removed',
        'nodes': list(blockchain_local.nodes),
    }
    return jsonify(response), 201


@blockchain.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain_local.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain_local.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain_local.chain
        }

    return jsonify(response), 200
