from flask import Flask, redirect, render_template, request, Response, session, url_for
from flask_session import Session
import queue
import json
import uuid

app = Flask(__name__)
app.secret_key = uuid.uuid4()
app.config["SESSION_PERMANENT"] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
Session(app)

listeners = {}


def announce(msg, deviceId):
    try:
        listeners[deviceId]['messages'].put_nowait(msg)
    except:
        del listeners[deviceId]


@app.route('/')
@app.route('/index')
def index():
    if not 'deviceId' in session:
        session['deviceId'] = str(uuid.uuid4())
    if not session['deviceId'] in listeners:
        listeners[session['deviceId']] = {
            "control_state": {
                "lights_on": False,
                "blinds_down": False,
                "coffee_on": False
            }
        }
    return render_template('index.html',
                           deviceId=session['deviceId'],
                           control_state=json.dumps(listeners[session['deviceId']]['control_state']))


@app.route('/lights/<deviceId>', methods=['PUT'])
@app.route('/blinds/<deviceId>', methods=['PUT'])
@app.route('/coffee/<deviceId>', methods=['PUT'])
def lights(deviceId):
    if not deviceId in listeners:
        return {}, 404
    listeners[deviceId]['control_state'].update(request.json)
    data = listeners[deviceId]['control_state']
    msg = f'data: { json.dumps(data) }\n\n'
    announce(msg, deviceId)
    return '', 204


@app.route('/events/<deviceId>', methods=['GET'])
def events(deviceId):
    listeners[deviceId]['messages'] = queue.Queue(maxsize=100)

    def stream():
        while True:
            msg = listeners[deviceId]['messages'].get()
            yield msg
    return Response(stream(), mimetype='text/event-stream')
