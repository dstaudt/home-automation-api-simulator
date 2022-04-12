from flask import Flask, render_template, request, send_from_directory, session
from flask_cors import CORS
from flask_sock import Sock
from simple_websocket import ConnectionClosed
import json
import redis
import os
import uuid
from threading import Timer
from queue import SimpleQueue, Empty

TEST = os.getenv('HOME_AUTO_SIM_TEST') == "True"

red = redis.Redis.from_url(
    decode_responses=True,
    url=os.environ.get('REDIS_URL'),
    db=0
)

process_queue = red.pubsub()
process_queue.subscribe('messages')

thread_queues = {}

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
    msg = {
        'deviceId': deviceId,
        'control_status': request.json
    }
    red.publish('messages', json.dumps(msg))
    return '', 204


@sock.route('/events/<deviceId>')
def ws_connect(ws, deviceId):
    session['deviceId'] = deviceId
    print(f'REGISTER pid:{os.getpid()} deviceId:{deviceId}')
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    if deviceId in thread_queues:
        thread_queues[deviceId].put('kill')
    thread_queues[deviceId] = SimpleQueue()

    while True:
        try:
            msg = thread_queues[deviceId].get(timeout=55)
            if msg == 'kill': break
            msg = f'{json.dumps(msg["control_status"])}'
        except Empty:
            msg = 'keepalive'
        print(f'SEND pid:{os.getpid()} deviceId:{deviceId} Data: {msg}')
        try:
            ws.send(msg)
        except ConnectionClosed as e:
            thread_queues.pop('deviceId', None)
            print(f'CLOSED pid:{os.getpid()} deviceId:{deviceId}')
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


def check_messages():
    while True:
        message = process_queue.get_message()
        if not message:
            break
        if message['type'] == 'message':
            msg = json.loads(message['data'])
            print(f'pid: {os.getpid()} {msg["deviceId"]}: got message Data: {msg}')
            if msg['deviceId'] in thread_queues:
                print(f'pid: {os.getpid()} {msg["deviceId"]}: dispatched data:{msg["control_status"]}')
                thread_queues[msg['deviceId']].put(msg)


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


message_timer = RepeatTimer(0.1, check_messages)
message_timer.start()
