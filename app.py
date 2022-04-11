from ssl import ALERT_DESCRIPTION_CERTIFICATE_EXPIRED
from flask import Flask, render_template, request, Response, send_from_directory, session, stream_with_context
from flask_cors import CORS
from flask_sock import Sock
import json
import redis
import os
import uuid
from threading import Timer
from queue import SimpleQueue, Empty
from time import time

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
CORS(app)
app.secret_key = "3ba9baf4-1e1b-42d4-b8bd-e18c0a329300"
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
sock = Sock(app)


@ app.route('/')
@ app.route('/index')
def index():
    if 'deviceId' not in session:
        session['deviceId'] = str(uuid.uuid4())
    return render_template('index.html', deviceId=session['deviceId'], TEST=TEST)

@ app.route('/downloads/<filename>')
def downloads(filename):
    return send_from_directory(
        'downloads', 
        filename, 
        as_attachment=True,
        attachment_filename=filename,
        mimetype='application/octet-stream')

@ app.route('/lights/<deviceId>', methods=['PUT'])
@ app.route('/blinds/<deviceId>', methods=['PUT'])
@ app.route('/coffee/<deviceId>', methods=['PUT'])
def control_device(deviceId):
    if not deviceId:
        return 'deviceId missing', 400
    msg = {
        'deviceId': deviceId,
        'control_status': request.json
    }
    red.publish('messages', json.dumps(msg))
    return '', 204

@sock.route('/events/<deviceId>')
def ws_connect(ws, deviceId):
    session['deviceId'] = deviceId
    print(f'REGISTER pid:{os.getpid()} did:{deviceId}')
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    if deviceId in thread_queues:
        thread_queues[deviceId].put('kill')
    thread_queues[deviceId] = SimpleQueue()

    lastTimeStamp = time()
    def pong():
        ws.send('pong')
        lastTimeStamp = time()
        
    try:
        ws.send('connected')
        while True:
            if deviceId in thread_queues:
                try:
                    msg = thread_queues[deviceId].get(timeout=7)
                    # msg = thread_queues[deviceId].get()
                    if msg == 'kill':
                        connected = False
                        print(f'KILL pid:{os.getpid()} did:{deviceId}')
                        break
                    print(f'SEND pid:{os.getpid()} did:{deviceId}')
                    ws.send(f'{json.dumps(msg["control_status"])}')
                except Empty:
                    ws.send('keepalive')
    except ConnectionError:
        thread_queues.pop('deviceId', None)
        print(f'EXITED pid:{os.getpid()} did:{deviceId}')
    print('exited?')


# @ app.route('/events/<deviceId>', methods=['GET'])
# def events(deviceId):
#     if not deviceId:
#         return 'deviceId missing', 400    
#     session['deviceId'] = deviceId
#     print(f'REGISTER pid:{os.getpid()} did:{deviceId}')
#     if TEST:
#         with open('device_ids.log', 'a') as file:
#             file.write(f'{deviceId}\n')
#     if deviceId in thread_queues:
#         thread_queues[deviceId].put('kill')
#     thread_queues[deviceId] = SimpleQueue()
#     def stream():
#         try:
#             streaming = True
#             yield 'data: reconnected\n\n'
#             while streaming:
#                 try:
#                     if deviceId in thread_queues:
#                         msg = thread_queues[deviceId].get(timeout=7)
#                         if msg == 'kill':
#                             streaming = False
#                             print(f'KILL pid:{os.getpid()} did:{deviceId}')
#                             break
#                         print(f'STREAM pid:{os.getpid()} did:{deviceId}')
#                         yield f'data: {json.dumps(msg["control_status"])}\n\n'
#                 except Empty:
#                     print(f'KEEPALIVE pid:{os.getpid()} did:{deviceId}')
#                     yield 'data: keepalive\n\n'
#         except GeneratorExit:
#             thread_queues.pop('deviceId', None)
#             print(f'EXITED pid:{os.getpid()} did:{deviceId}')
#     return Response(stream_with_context(stream()), mimetype='text/event-stream')

if TEST:
    @ app.route('/deviceIds', methods=['GET'])
    def deviceIds():
        with open('device_ids.log', 'r') as file:
            return file.read(), 200

    @ app.route('/startTest', methods=['GET'])
    def startTest():
        with open('device_ids.log', 'w') as file:
            pass
        return '', 200

def check_messages():
    while True:
        message = process_queue.get_message()
        if not message: break
        if message and message['type'] == 'message':
            msg = json.loads(message['data'])
            print(f'pid: {os.getpid()} {msg["deviceId"]}: got message')
            if msg['deviceId'] in thread_queues:
                print(f'pid: {os.getpid()} {msg["deviceId"]}: dispatched data:{msg["control_status"]}')
                thread_queues[msg['deviceId']].put(msg)

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)
message_timer = RepeatTimer(0.1, check_messages)
message_timer.start()
