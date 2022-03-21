from flask import Flask, render_template, request, Response, session, stream_with_context
import json
import redis
import os
import uuid
from threading import Timer
from queue import SimpleQueue

def secho(text, file=None, nl=None, err=None, color=None, **styles):
    pass

def echo(text, file=None, nl=None, err=None, color=None, **styles):
    pass

TEST = os.getenv('HOME_AUTO_SIM_TEST') == "True"

red = redis.Redis.from_url(
    decode_responses=True,
    url=os.environ.get('REDIS_URL'),
    db=0
)

listeners = {}

app = Flask(__name__)
app.secret_key = "7fc2b780-6852-4e8c-9332-f869dc940b78"

@ app.route('/')
@ app.route('/index')
def index():
    if 'deviceId' not in session:
        session['deviceId']=str(uuid.uuid4())
    return render_template('index.html', deviceId=session['deviceId'])

@ app.route('/lights/<deviceId>', methods=['PUT'])
@ app.route('/blinds/<deviceId>', methods=['PUT'])
@ app.route('/coffee/<deviceId>', methods=['PUT'])
def lights(deviceId):
    msg = {
        'deviceId': deviceId,
        'control_status': request.json
    }
    red.publish('messages', json.dumps(msg))
    return '', 204


@ app.route('/events/<deviceId>', methods=['GET'])
def events(deviceId):
    print('reg '+deviceId+' '+session['deviceId'])
    session['deviceId']=deviceId
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    listeners[deviceId] = SimpleQueue()
    def stream():
        yield 'data: reconnected\n\n'
        while True:
            msg = listeners[deviceId].get()
            yield f'data: {json.dumps(msg["control_status"])}\n\n'
    return Response(stream(), mimetype='text/event-stream')

@ app.route('/deviceIds', methods=['GET'])
def deviceIds():
    if TEST:
        try:
            with open('device_ids.log', 'r') as file:
                return file.read(), 200
        except Exception as err:
            return err, 500

@ app.route('/startTest', methods=['GET'])
def startTest():
    if TEST:
        with open('device_ids.log', 'w') as file: pass
    return '', 200

process_queue = red.pubsub()
process_queue.subscribe('messages')

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def check_messages():
    message = process_queue.get_message()
    if message and message['type'] == 'message':
        msg = json.loads(message['data'])
        if msg['deviceId'] in listeners:
            listeners[msg['deviceId']].put(msg)

message_timer = RepeatTimer(0.01, check_messages)
message_timer.start()

