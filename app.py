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

process_queue = red.pubsub()
process_queue.subscribe('messages')

thread_queue = {}

app = Flask(__name__)
app.secret_key = "3ba9baf4-1e1b-42d4-b8bd-e18c0a329300"
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


@ app.route('/')
@ app.route('/index')
def index():
    if 'deviceId' not in session:
        session['deviceId'] = str(uuid.uuid4())
    return render_template('index.html', deviceId=session['deviceId'], TEST=TEST)


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
    print(f'REGISTER pid:{os.getpid()} did:{deviceId}')
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    if deviceId in thread_queue:
        thread_queue[deviceId].put('kill')
    thread_queue[deviceId] = SimpleQueue()
    def stream():
        try:
            streaming = True
            yield 'data: reconnected\n\n'
            while streaming:
                try:
                    if deviceId in thread_queue:
                        msg = thread_queue[deviceId].get(timeout=7)
                        if msg == 'kill':
                            streaming = False
                            print(f'KILL pid:{os.getpid()} did:{deviceId}')
                            break
                        print(f'STREAM pid:{os.getpid()} did:{deviceId}')
                        yield f'data: {json.dumps(msg["control_status"])}\n\n'
                except Empty:
                    print(f'KEEPALIVE pid:{os.getpid()} did:{deviceId}')
                    yield 'data: keepalive\n\n'
        except GeneratorExit:
            thread_queue.pop('deviceId', None)
            print(f'EXITED pid:{os.getpid()} did:{deviceId}')
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

def check_messages():
    message = process_queue.get_message()
    if message and message['type'] == 'message':
        msg = json.loads(message['data'])
        print(f'pid: {os.getpid()} {msg["deviceId"]}: got message')
        if msg['deviceId'] in thread_queue:
            print(f'pid: {os.getpid()} {msg["deviceId"]}: dispatched data:{msg["control_status"]}')
            thread_queue[msg['deviceId']].put(msg)

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
message_timer = RepeatTimer(0.01, check_messages)
message_timer.start()
