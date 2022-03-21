from flask import Flask, render_template, request, Response, session, stream_with_context
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

listeners = {}

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())


@ app.route('/')
@ app.route('/index')
def index():
    if 'deviceId' not in session:
        session['deviceId'] = str(uuid.uuid4())
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
    session['deviceId'] = deviceId
    print('reg '+deviceId+' '+session['deviceId'])
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    if not deviceId in listeners:
        listeners[deviceId] = SimpleQueue()
        print('listener added: '+str(len(listeners)))

    def stream():
        try:
            yield 'data: reconnected\n\n'
            while True:
                try:
                    if deviceId in listeners:
                        msg = listeners[deviceId].get(timeout=10)
                        yield f'data: {json.dumps(msg["control_status"])}\n\n'
                except Empty:
                    print('keepalive')
                    yield 'data: keepalive\n\n'
        except GeneratorExit:
            print('exited')
    return Response(stream_with_context(stream()), mimetype='text/event-stream')


@ app.route('/deviceIds', methods=['GET'])
def deviceIds():
    if TEST:
        with open('device_ids.log', 'r') as file:
            return file.read(), 200
    else:
        return '', 404


@ app.route('/startTest', methods=['GET'])
def startTest():
    if TEST:
        with open('device_ids.log', 'w') as file:
            pass
        return '', 200
    else:
        return '', 404


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
