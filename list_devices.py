import sys

import argparse

import gi, gi.repository

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject

GObject.threads_init()
Gst.init(sys.argv)

DEVICE_NAME_WIDTH = 74
DISPLAY_FORMAT = '{0:%i} {1}' % DEVICE_NAME_WIDTH

monitor = Gst.DeviceMonitor.new()
monitor.add_filter('Audio/Source')

def bus_element_cb (bus, msg, arg=None):
    s = msg.get_structure()
    if s is None:
        return True

    name = s.get_name()
    if name not in ['GstMessageDeviceAdded', 'GstMessageDeviceRemoved']:
        return True

    name_map = {
        'GstMessageDeviceAdded':   'Device added:',
        'GstMessageDeviceRemoved': 'Device removed:'
    }
    device = s.get_value('device')
    print(name_map[name], DISPLAY_FORMAT.format(device.props.internal_name, device.props.display_name))
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--monitor', action='store_true', help='Keep listening for device changes')

    devices = monitor.get_devices()
    for device in devices:
        print(DISPLAY_FORMAT.format(device.props.internal_name, device.props.display_name))

    args = parser.parse_args()
    if args.monitor:
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        bus = monitor.get_bus()
        bus.add_signal_watch()
        bus.connect("message", bus_element_cb)
        monitor.start()

        loop = GLib.MainLoop()
        loop.run()
