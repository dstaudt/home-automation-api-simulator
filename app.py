from flask import Flask, redirect, render_template, request, Response, session, url_for
from flask_session import Session
import json
import uuid
import redis
import os

red = redis.Redis(
    decode_responses=True,
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=os.getenv("REDIS_PORT", "6379"),
    password=os.getenv("REDIS_PASSWORD", ""),
    db=0
)

app = Flask(__name__)
app.secret_key = "7fc2b780-6852-4e8c-9332-f869dc940b78"
app.config["SESSION_PERMANENT"] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
Session(app)

def init_listener(deviceId):
    red.set(deviceId, json.dumps({
        "lights_on": False,
        "blinds_down": False,
        "coffee_on": False
        })
    )


@ app.route('/')
@ app.route('/index')
def index():
    if not 'deviceId' in session:
        session['deviceId'] = str(uuid.uuid4())
    if not red.exists(session['deviceId']):
        init_listener(session['deviceId'])
    return render_template('index.html',
                           deviceId=session['deviceId'],
                           control_state=red.get(session['deviceId']))


@ app.route('/lights/<deviceId>', methods=['PUT'])
@ app.route('/blinds/<deviceId>', methods=['PUT'])
@ app.route('/coffee/<deviceId>', methods=['PUT'])
def lights(deviceId):
    if not red.exists(deviceId):
        return {}, 404
    control_state = json.loads(red.get(deviceId))
    control_state.update(request.json)
    red.set(deviceId, json.dumps(control_state))
    msg = f'data: { json.dumps(control_state) }\n\n'
    red.publish(deviceId, msg)
    return '', 204


@ app.route('/events/<deviceId>', methods=['GET'])
def events(deviceId):
    if not red.exists(session['deviceId']):
        init_listener(session['deviceId'])

    def stream():
        queue = red.pubsub()
        queue.subscribe(deviceId)
        while True:
            for msg in queue.listen():
                # print(msg.get('data'))
                if msg and (msg['type'] == 'message'):
                    yield msg.get('data')

    return Response(stream(), mimetype='text/event-stream')
    return {}, 200
