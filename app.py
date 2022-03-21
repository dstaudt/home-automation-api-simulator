from flask import Flask, render_template, request, Response, session
import json
import redis
import os
import uuid

TEST = os.getenv('HOME_AUTO_SIM_TEST') == "True"

red = redis.Redis.from_url(
    decode_responses=True,
    url=os.environ.get('REDIS_URL'),
    db=0
)

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
    msg = f'data: {json.dumps(request.json)}\n\n'
    try:
        red.publish(deviceId, msg)
    except:
        return '', 404
    return '', 204


@ app.route('/events/<deviceId>', methods=['GET'])
def events(deviceId):
    session['deviceId']=deviceId
    if TEST:
        with open('device_ids.log', 'a') as file:
            file.write(f'{deviceId}\n')
    def stream():
        queue = red.pubsub()
        queue.subscribe(deviceId)
        while True:
            red.publish(deviceId, f'data: reconnected\n\n')
            for msg in queue.listen():
                if msg and (msg['type'] == 'message'):
                    yield msg.get('data')

    return Response(stream(), mimetype='text/event-stream')
    return {}, 200
