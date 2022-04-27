from concurrent.futures import thread
from email import message
from flask import Flask, render_template, request, send_from_directory, session
from flask_cors import CORS
from flask_sock import Sock
from simple_websocket import ConnectionClosed
import json
import redis
import os
import uuid
from queue import SimpleQueue, Empty
from threading import Event
import logging

TEST = os.getenv('HOME_AUTO_SIM_TEST') == "True"
LOG_LEVEL = os.getenv('HOME_AUTO_SIM_LOG')
logging.basicConfig(format='%(asctime)s %(message)s', level=LOG_LEVEL if LOG_LEVEL else logging.WARN)

red = redis.Redis.from_url(
    decode_responses=True,
    url=os.environ.get('REDIS_URL'),
    db=0
)

thread_queues = {}
thread_commands = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('HOME_AUTO_SECRET_KEY')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app)
sock = Sock(app)


@app.route('/')
@app.route('/index')
def index():
    if 'deviceId' not in session:
        session['deviceId'] = str(uuid.uuid4())
    return render_template('index.html', deviceId=session['deviceId'], TEST=TEST)


@app.route('/downloads/<filename>')
def downloads(filename):
    return send_from_directory(
        'downloads',
        filename,
        as_attachment=True,
        attachment_filename=filename,
        mimetype='application/octet-stream')


@app.route('/lights/<deviceId>', methods=['PUT'])
@app.route('/blinds/<deviceId>', methods=['PUT'])
@app.route('/coffee/<deviceId>', methods=['PUT'])
def control_device(deviceId):
    messageId = str(uuid.uuid4())
    msg = {
        'messageId': messageId,
        'deviceId': deviceId,
        'control_status': request.json
    }
    thread_commands[messageId]=Event()
    red.publish('messages', json.dumps(msg))
    thread_commands[messageId].wait(timeout=5)
    resp = ('',204) if thread_commands[messageId].is_set() else ('Timed out sending command', 504)
    thread_commands.pop(messageId, None)
    return resp


@sock.route('/events/<deviceId>')
def ws_connect(ws, deviceId):
    session['deviceId'] = deviceId
    logging.debug(f'REGISTER pid:{os.getpid()} deviceId:{deviceId}')
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    if deviceId in thread_queues:
        thread_queues[deviceId].put('kill')
    thread_queues[deviceId] = SimpleQueue()

    while True:
        messageId=None
        try:
            msg = thread_queues[deviceId].get(timeout=40)
            if msg == 'kill': break
        except Empty:
            ws.send('keepalive')
            continue
        message = f'{json.dumps(msg["control_status"])}'
        logging.debug(f'SEND pid:{os.getpid()} deviceId:{deviceId} Data: {message}')
        try:
            ws.send(message)
            red.publish('responses', json.dumps(msg))
        except ConnectionClosed as e:
            thread_queues.pop(deviceId, None)
            logging.debug(f'CLOSED pid:{os.getpid()} deviceId:{deviceId}')
            raise e


if TEST:
    @app.route('/deviceIds', methods=['GET'])
    def deviceIds():
        with open('device_ids.log', 'r') as file:
            return file.read(), 200

    @app.route('/startTest', methods=['GET'])
    def startTest():
        with open('device_ids.log', 'w') as file:
            pass
        return '', 200


def process_queue_messages(message):
    if message['type'] != 'message': return
    msg = json.loads(message['data'])
    logging.debug(f'pid: {os.getpid()} {msg["deviceId"]}: got message Data: {msg}')
    if msg['deviceId'] in thread_queues:
        logging.debug(f'pid: {os.getpid()} {msg["deviceId"]}: dispatched data:{msg["control_status"]}')
        thread_queues[msg['deviceId']].put(msg)

def process_queue_responses(message):
    if message['type'] != 'message': return
    msg = json.loads(message['data'])
    logging.debug(f'pid: {os.getpid()} {msg["deviceId"]}: got response Data: {msg}')
    if msg['messageId'] in thread_commands:
        logging.debug(f'pid: {os.getpid()} {msg["deviceId"]}: ack for messageId: {msg["messageId"]}')
        thread_commands[msg['messageId']].set()

process_queue = red.pubsub()
process_queue.subscribe(**{'messages': process_queue_messages})
process_queue.subscribe(**{'responses': process_queue_responses})
process_queue.run_in_thread(sleep_time=0.1)

