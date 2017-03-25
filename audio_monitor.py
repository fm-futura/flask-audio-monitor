import sys

import time
from threading import Thread

from flask import Flask, render_template
from flask_socketio import SocketIO


import gi, gi.repository

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject

GObject.threads_init()
Gst.init(sys.argv)

from devices import DeviceMonitor, AudioLevelMonitor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

device_monitor = DeviceMonitor(socket=socketio)

@app.route('/')
def index():
    return render_template('index.html')


def glib_loop (*args, **kwargs):
    loop = GLib.MainLoop.new(None, False)
    ctx = loop.get_context()
    while True:
        while ctx.pending():
            ctx.iteration()
        socketio.sleep()

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    audio_monitors = []
    audio_monitors_map = {}

    glib_task = socketio.start_background_task(target=glib_loop)

    def on_device_added(monitor, device):
        monitor = AudioLevelMonitor(device=device, socket=socketio)
        audio_monitors.append(monitor)
        audio_monitors_map[device.internal_name] = monitor

    def on_device_removed(monitor, device):
        monitor = audio_monitors_map.get(device.internal_name, None)
        if monitor:
            del audio_monitors_map[device.internal_name]
            monitor.stop()

    for device in device_monitor.get_devices():
        monitor = AudioLevelMonitor(device=device, socket=socketio)
        audio_monitors.append(monitor)

    device_monitor.connect('device-added',   on_device_added)
    device_monitor.connect('device-removed', on_device_removed)
    device_monitor.start()

    socketio.run(app)
