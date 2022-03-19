from flask import Flask, redirect, render_template, request, Response, session, url_for
from flask_session import Session
import json
import redis
import os

TEST = os.getenv('HOME_AUTO_SIM_TEST') == "True"

red = redis.Redis.from_url(
    decode_responses=True,
    url=os.environ.get('REDIS_URL'),
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
app.config['SESSION_REDIS'] = redis.from_url(os.environ.get('REDIS_URL'))
Session(app)

def init_listener(deviceId):
    red.set(deviceId, json.dumps({
        "lights_on": False,
        "blinds_down": False,
        "coffee_on": False
        }),
    ex=app.config['PERMANENT_SESSION_LIFETIME']
    )
    # red.expire(deviceId, app.config['PERMANENT_SESSION_LIFETIME'])


@ app.route('/')
@ app.route('/index')
def index():
    if not 'deviceId' in session:
        session['deviceId'] = session.sid
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
    red.set(deviceId, json.dumps(control_state), ex=app.config['PERMANENT_SESSION_LIFETIME'])
    red.expire(f'session:{deviceId}', app.config['PERMANENT_SESSION_LIFETIME'])
    msg = f'data: { json.dumps(control_state) }\n\n'
    red.publish(deviceId, msg)
    return '', 204


@ app.route('/events/<deviceId>', methods=['GET'])
def events(deviceId):
    if not red.exists(session['deviceId']):
        init_listener(session['deviceId'])
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
