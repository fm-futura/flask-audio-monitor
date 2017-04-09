# flask-audio-monitor

Simple audio monitor made with GStreamer, Flask and websockets.


## Installation

Besides the dependencies listed in the requirements.txt file you need the
GI Instrospection packages for GStreamer, GLib and Python.

If installing under a virtualenv you may need to use the '--system-site-packages'
flag so it picks the GI bindings.


## Usage

Running *audio_monitor.py* will start an http server on port 5000 displaying the
levels for all the detected interfaces. It detects new devices and handles
disconnections gracefully.

There's another tool, *list_devices.py* that only lists the detected audio devices
and, optionally, can keep monitoring for changes.
