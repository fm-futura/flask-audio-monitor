import time
from threading import Thread

from flask import Flask, render_template
from flask_socketio import SocketIO


import gi, gi.repository

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject

GObject.threads_init()
Gst.init(None)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

class DeviceMonitor(GObject.GObject):
    __gsignals__ = {
       "device-added":   (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
       "device-removed": (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self, socket):
        GObject.GObject.__init__(self)

        self.socket = socket
        self.monitor = Gst.DeviceMonitor.new()
        self.monitor.add_filter('Audio/Source')

        self.bus = self.monitor.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.bus_element_cb)
        self.monitor.start()

    def get_devices(self):
        return self.monitor.get_devices()

    def bus_element_cb (self, bus, msg, arg=None):
        s = msg.get_structure()
        if s is None:
            return True

        name = s.get_name()
        if name not in ['GstMessageDeviceAdded', 'GstMessageDeviceRemoved']:
            return True

        action_name_map = {
            'GstMessageDeviceAdded':   'device-added',
            'GstMessageDeviceRemoved': 'device-removed'
        }
        action = action_name_map[name]

        device = s.get_value('device')

        self.emit(action, device)

        self.socket.emit(action, {
            'display_name': device.props.display_name,
            'internal_name': device.props.internal_name,
        }, broadcast=True)

        return True


class AudioMonitor(object):

    def __init__(self, device, socket):

        self.stopped = False
        self.device = device
        self.socket = socket
        self.payload = {
            'display_name': device.props.display_name,
            'internal_name': device.props.internal_name,
        }

        pipe = self.pipe = Gst.parse_launch('pulsesrc name=source device="{0}" ! level post-messages=true name=level ! fakesink sync=true'.format(device.props.internal_name))

        bus = pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message::element", self.bus_element_cb)
        pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.stopped = True

    def bus_element_cb (self, bus, msg, arg=None):
        if self.stopped:
            self.pipe.set_state(Gst.State.NULL)
            return False

        s = msg.get_structure()
        if s is None:
            return True

        if s.get_name() == "level":
            rms = s.get_value('rms')
            peak = s.get_value('peak')
            self.payload.update({
                'peak': peak,
                'rms':  rms,
            })

            socketio.emit('level', self.payload, broadcast=False)
            socketio.emit('peak', peak, broadcast=False)
            socketio.emit('rms',  rms,  broadcast=False)

        return True


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

    device_monitor = DeviceMonitor(socket=socketio)
    glib_task = socketio.start_background_task(target=glib_loop)

    def on_device_added(monitor, device):
        monitor = AudioMonitor(device=device, socket=socketio)
        audio_monitors.append(monitor)
        audio_monitors_map[device.props.internal_name] = monitor

    def on_device_removed(monitor, device):
        monitor = audio_monitors_map.get(device.props.internal_name, None)
        if monitor:
            del audio_monitors_map[device.props.internal_name]
            monitor.stop()

    for device in device_monitor.get_devices():
        monitor = AudioMonitor(device=device, socket=socketio)
        audio_monitors.append(monitor)

    device_monitor.connect('device-added', on_device_added)
    device_monitor.connect('device-removed', on_device_removed)

    socketio.run(app)
