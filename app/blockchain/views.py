from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from . import blockchain
from .Cryptography import *
from .Block import *
from .forms import TransactionForm, BindWalletForm
import requests
from urllib.error import HTTPError
import json
from config import server_address
import threading
import socket


def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


ip = ''
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
    ip = get_host_ip()
    return render_template('blockchain/nodes.html', ip_address=ip)


@blockchain.route('/mine', methods=['GET', 'POST'])
def mine():
    global node_identifier
    form = BindWalletForm()

    if form.validate_on_submit():
        node_identifier = form.wallet_address.data
        flash('wallet binded')

    # 检查是否绑定挖矿钱包
    if node_identifier == '':
        flash('Please bind a wallet firstly')
        return render_template('blockchain/mine.html', form=form)

    form.wallet_address.data = node_identifier
    return render_template('blockchain/mine.html', form=form)


class MineThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while True:
            blockchain_local.mine_start()
            # We run the proof of work algorithm to get the next proof...
            last_block = blockchain_local.last_block
            last_proof = last_block['proof']
            proof = blockchain_local.proof_of_work(last_proof)

            if proof == -1:
                break

            # 给工作量证明的节点提供奖励.
            # 发送者为 "0" 表明是新挖出的币
            blockchain_local.new_transaction(
                sender="0",
                recipient=node_identifier,
                amount=10,
                signature="0",
            )

            # Forge the new Block by adding it to the chain
            blockchain_local.new_block(proof, None)

            # response = {
            #     'message': "New Block Forged",
            #     'index': block['index'],
            #     'transactions': block['transactions'],
            #     'proof': block['proof'],
            #     'previous_hash': block['previous_hash'],
            # }


@blockchain.route('/mine/start', methods=['GET', 'POST'])
def mine_start():
    mine_thread = MineThread()
    mine_thread.start()
    flash('mine start')

    global node_identifier
    form = BindWalletForm()
    form.wallet_address.data = node_identifier
    return render_template('blockchain/mine.html', form=form)


@blockchain.route('/mine/stop', methods=['GET', 'POST'])
def mine_stop():
    blockchain_local.mine_stop()
    flash('mine stop')

    global node_identifier
    form = BindWalletForm()
    form.wallet_address.data = node_identifier
    return render_template('blockchain/mine.html', form=form)


@blockchain.route('/transactions_local', methods=['GET', 'POST'])
def transaction_local():
    form = TransactionForm()
    if form.validate_on_submit():
        sender = form.sender.data
        recipient = form.recipient.data
        amount = form.amount.data
        private_key = form.private_key.data
        # 对交易信息签名
        message = str(sender) + str(recipient) + str(amount)
        try:
            signature = signature_generation(message, private_key)
        except ValueError:
            flash('invalid message')
        else:
            url = f'http://{server_address}/blockchain/transactions_remote'
            postdict = {
                'sender': sender,
                'recipient': recipient,
                'amount': amount,
                'signature': signature
            }
            try:
                requests.post(url, json=postdict)
            except ValueError:
                flash('invalid transaction')
            else:
                for node in blockchain_local.nodes:
                    url = f'http://{node}/blockchain/transactions_remote'
                    try:
                        requests.post(url, json=postdict)
                    except HTTPError:
                        flash('connect to {0} failed'.format(node))
                        continue
                    except ValueError:
                        flash('invalid transaction')
                        continue

                flash('Transaction will be added to Block {0}'.format(index))
                form.sender.data = ''
                form.recipient.data = ''
                form.amount.data = 0.0
                form.private_key.data = ''
                return render_template('blockchain/transactions.html', form=form)
    return render_template('blockchain/transactions.html', form=form)


@blockchain.route('/transactions_remote', methods=['GET', 'POST'])
def transaction_remote():
    values = request.get_json()

    # 检查POST数据
    required = ['sender', 'recipient', 'amount', 'signature']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # 验证签名
    try:
        block_index = blockchain_local.new_transaction(values['sender'], values['recipient'],
                                                       values['amount'], values['signature'])
    except HTTPError:
        return 'Error: add transaction failed', 400
    else:
        if block_index == -1:
            raise ValueError('invalid transaction')
        else:
            return jsonify(values), 200


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
    get_url = f'http://{server_address}/blockchain/nodes/get_remote'
    post_url = f'http://{server_address}/blockchain/nodes/register_remote'
    postdict = {
        'nodes': f'http://{ip}:5000'
    }

    # blockchain_local.register_node(postdict['nodes'])
    try:
        r = requests.get(get_url)
    except HTTPError as e:
        flash('Error: get remote nodes failed')
        return render_template('/blockchain/response.html', response=e.read())
    else:
        node_list = r.json().get('nodes')
        for node in node_list:
            blockchain_local.register_node('http://' + node)
            url = f'http://{node}/blockchain/nodes/register_remote_node'
            try:
                requests.post(url, json=postdict)
            except HTTPError:
                flash('connect to {0} failed'.format(node))
                continue

    try:
        requests.post(post_url, json=postdict)
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


@blockchain.route('/nodes/get_local', methods=['GET'])
def get_local_nodes():
    response = {
        'nodes': list(blockchain_local.nodes),
    }
    return render_template('/blockchain/response.html',
                           response=json.dumps(response,
                                               indent=4).replace('\\n',
                                                                 '<br>').replace(',', '<br>'))


@blockchain.route('/nodes/get_remote', methods=['GET'])
def get_remote_nodes():
    response = {
        'nodes': list(blockchain_local.nodes),
    }
    return jsonify(response), 200


@blockchain.route('/nodes/remove_local', methods=['GET', 'POST'])
def remove_local_node():
    global ip
    post_url = f'http://{server_address}/blockchain/nodes/remove_remote'
    postdict = {
        'nodes': f'http://{ip}:5000'
    }

    # blockchain_local.remove_node(postdict['nodes'])
    for node in blockchain_local.nodes:
        url = f'http://{node}/blockchain/nodes/remove_remote'
        try:
            requests.post(url, postdict)
        except HTTPError:
            flash('connect to {0} failed'.format(node))
            continue
    blockchain_local.nodes.clear()

    try:
        requests.post(post_url, json=postdict)
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


@blockchain.route('/chain_local', methods=['GET'])
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

    return render_template('/blockchain/response.html',
                           response=json.dumps(response,
                                               indent=4).replace('\\r\\n',
                                                                 '<br>').replace(',', '<br>'))


@blockchain.route('/chain_remote', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain_local.chain,
        'length': len(blockchain_local.chain),
    }
    return jsonify(response), 200
