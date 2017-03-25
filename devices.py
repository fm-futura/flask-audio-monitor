import gi, gi.repository

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject

class DeviceMonitor(GObject.GObject):
    __gsignals__ = {
       "device-added":   (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
       "device-removed": (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self, socket=None):
        GObject.GObject.__init__(self)

        self.socket = socket
        self.monitor = Gst.DeviceMonitor.new()
        self.monitor.add_filter('Audio/Source')

        self.bus = self.monitor.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.bus_element_cb)

    def start(self):
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

        if self.socket is not None:
            self.socket.emit(action, {
                'display_name': device.props.display_name,
                'internal_name': device.props.internal_name,
            }, broadcast=True)

        return True


class AudioLevelMonitor(GObject.GObject):
    __gsignals__ = {
       "level":   (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self, device, socket):
        GObject.GObject.__init__(self)

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

            self.emit('level', self.payload)

            if self.socket is not None:
                self.socket.emit('level', self.payload, broadcast=False)
                self.socket.emit('peak', peak, broadcast=False)
                self.socket.emit('rms',  rms,  broadcast=False)

            self.emit('level', self.payload)

        return True




