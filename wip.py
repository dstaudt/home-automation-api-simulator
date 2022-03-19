from flask import Flask, redirect, render_template, request, Response, session, url_for
from flask_session import Session
# import queue
import json
import uuid
import os
import pika

app = Flask(__name__)
app.secret_key = "7fc2b780-6852-4e8c-9332-f869dc940b78"
app.config["SESSION_PERMANENT"] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
Session(app)

# listeners = {}

mq_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
mq_channel = mq_connection.channel()

@ app.route('/')
@ app.route('/index')
def index():
    if not 'deviceId' in session:
        session['deviceId'] = str(uuid.uuid4())
    if not session['deviceId'] in listeners:
        init_listener(session['deviceId'])
    return render_template('index.html',
                           deviceId=session['deviceId'],
                           control_state=json.dumps(listeners[session['deviceId']]['control_state']))


@ app.route('/lights/<deviceId>', methods=['PUT'])
@ app.route('/blinds/<deviceId>', methods=['PUT'])
@ app.route('/coffee/<deviceId>', methods=['PUT'])
def lights(deviceId):
    if not deviceId in listeners:
        return {}, 404
    listeners[deviceId]['control_state'].update(request.json)
    data = listeners[deviceId]['control_state']
    msg = f'data: { json.dumps(data) }\n\n'
    try:
        listeners[deviceId]['messages'].put_nowait(msg)
    except Exception as err:
        del listeners[deviceId]
        return f'Listener {listeners[deviceId]} unreachable: deleted\n{err}', 502
    return '', 204


@ app.route('/events/<deviceId>', methods=['GET'])
def events(deviceId):
    if not session['deviceId'] in listeners:
        init_listener(session['deviceId'])

    def stream():
        listeners[deviceId]['messages'] = Queue(connection=redis_conn)
        while True:
            try:
                msg = listeners[deviceId]['messages'].get()
                yield msg
            except GeneratorExit:
                del listeners[deviceId]
    return Response(stream(), mimetype='text/event-stream')
