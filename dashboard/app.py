from datetime import datetime
import json, os, threading, time

import docker
from confluent_kafka.admin import AdminClient
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
NETWORK = "selfcoder_net"

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*")
client = docker.from_env()
admin = AdminClient({"bootstrap.servers": BOOTSTRAP})

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def handle_connect():
    emit("snapshot", _snapshot())

def _snapshot():
    containers = client.containers.list()
    data = []
    for c in containers:
        if not c.name.startswith("agent_"):
            continue
        stats = c.stats(stream=False)
        cpu = stats["cpu_stats"]["cpu_usage"]["total_usage"]
        mem = stats["memory_stats"]["usage"]
        data.append({"name": c.name, "cpu": cpu, "mem": mem,
                     "created": c.attrs["Created"]})
    return {"ts": datetime.utcnow().isoformat(), "agents": data}

def background():
    while True:
        socketio.emit("snapshot", _snapshot())
        time.sleep(5)

threading.Thread(target=background, daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000) 