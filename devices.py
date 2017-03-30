from munch import Munch

import gi, gi.repository

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject


def Device(raw_device):
    return Munch(
        internal_name=raw_device.props.internal_name,
        display_name=raw_device.props.display_name
    )

class DeviceMonitor(GObject.GObject):
    __gsignals__ = {
       "device-added":   (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
       "device-removed": (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.monitor = Gst.DeviceMonitor.new()
        self.monitor.add_filter('Audio/Source')

        self.bus = self.monitor.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.bus_element_cb)

    def start(self):
        self.monitor.start()

    def _get_devices(self):
        return self.monitor.get_devices()

    def get_devices(self):
        devices = [Device(d) for d in self._get_devices()]
        return devices

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

        raw_device = s.get_value('device')
        device = Device(raw_device)

        self.emit(action, device)

        return True


class AudioLevelMonitor(GObject.GObject):
    __gsignals__ = {
       "level":   (GObject.SIGNAL_RUN_FIRST, None, [GObject.TYPE_PYOBJECT]),
    }

    def __init__(self, device):
        GObject.GObject.__init__(self)

        self.stopped = False
        self.device = device
        self.payload = {
            'display_name':  device.display_name,
            'internal_name': device.internal_name,
        }

        pipe = self.pipe = Gst.parse_launch('pulsesrc name=source device="{0}" ! level post-messages=true name=level ! fakesink sync=true'.format(device.internal_name))

        bus = pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message::element", self.bus_element_cb)
        pipe.set_state(Gst.State.PLAYING)

    def stop(self):
        self.stopped = True
        self.pipe.set_state(Gst.State.NULL)

    def bus_element_cb (self, bus, msg, arg=None):
        if self.stopped:
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

        return True

