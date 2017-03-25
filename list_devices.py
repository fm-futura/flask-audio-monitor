import sys

import argparse

import gi, gi.repository

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib, GObject

GObject.threads_init()
Gst.init(sys.argv)

from devices import DeviceMonitor

DEVICE_NAME_WIDTH = 74
DISPLAY_FORMAT = '{0:%i} {1}' % DEVICE_NAME_WIDTH

def display_device(device):
    print(DISPLAY_FORMAT.format(device.internal_name, device.display_name))

def on_device_added(monitor, device):
    print('Device added:')
    display_device(device)

def on_device_removed(monitor, device):
    print('Device removed:')
    display_device(device)


if __name__ == '__main__':
    device_monitor = DeviceMonitor()

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--monitor', action='store_true', help='Keep listening for device changes')

    devices = device_monitor.get_devices()
    for device in devices:
        display_device(device)

    args = parser.parse_args()
    if args.monitor:
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        device_monitor.connect('device-added',   on_device_added)
        device_monitor.connect('device-removed', on_device_removed)
        device_monitor.start()

        loop = GLib.MainLoop()
        loop.run()
