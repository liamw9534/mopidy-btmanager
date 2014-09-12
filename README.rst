****************************
Mopidy-BTManager
****************************

.. image:: https://pypip.in/version/Mopidy-BTManager/badge.png?latest
    :target: https://pypi.python.org/pypi/Mopidy-BTManager/
    :alt: Latest PyPI version

.. image:: https://pypip.in/download/Mopidy-BTManager/badge.png
    :target: https://pypi.python.org/pypi/Mopidy-BTManager/
    :alt: Number of PyPI downloads

.. image:: https://travis-ci.org/liamw9534/mopidy-btmanager.png?branch=master
    :target: https://travis-ci.org/liamw9534/mopidy-btmanager
    :alt: Travis CI build status

.. image:: https://coveralls.io/repos/liamw9534/mopidy-btmanager/badge.png?branch=master
   :target: https://coveralls.io/r/liamw9534/mopidy-btmanager?branch=master
   :alt: Test coverage

`Mopidy <http://www.mopidy.com/>`_ extension for bluetooth device management.

Installation
============

Install by running::

    pip install Mopidy-BTManager

Or, if available, install the Debian/Ubuntu package from `apt.mopidy.com
<http://apt.mopidy.com/>`_.


Configuration
=============

Dbus
----

Before starting Mopidy, you must ensure the 'audio' user group has dbus permissions
for managing bluetooth devices.  This can be done by adding the following policy
section into the file /etc/dbus-1/system.d/bluetooth.conf:

	<!-- allow users of audio group to communicate with bluetoothd -->
	<policy group="audio">
		<allow send_destination="org.bluez"/>
	</policy>

Extension
---------

Add the following section to your Mopidy configuration file following installation:

	[btmanager]
	enabled = true
	name = mopidy
	pincode = 1111
	autoconnect = true

The ``pincode`` setting is required when pairing devices with a keypad (e.g., AV remote control).
The same ``pincode`` value must be entered during the pairing process.

The ``name`` setting is the bluetooth network name that is announced to devices wishing to
connect to Mopidy.  You can change it to anything you wish.

The ``autoconnect`` setting tells the extension to automatically connect paired devices
as soon as they are discovered.  This can be useful if you have already paired a device
and don't wish to use the HTTP API to connect it each time you start Mopidy.


Bluetooth Audio
---------------

You need a ``/etc/bluetooth/audio.conf`` file setup for `mopidy-btmanager` to work
correctly.  This file tells the bluetooth daemon how you want your audio connections
to be setup.  Here's the required content::

    [General]
    Enable=Source,Sink,Control,Media
    Master=true
    Disable=
    SCORouting=HCI
    AutoConnect=false

    [Headset]
    HFP=false
    MaxConnected=1
    FastConnectable=false

    [A2DP]
    SBCSources=1
    MPEG12Sources=0
    MaxConnected=1

Note: If you wish to use the gstreamer bluetooth plugin then you also need to add
``Socket`` to the ``Enable`` option list.  Do not add this option unless you plan
to use the gstreamer bluetooth plugin.


Audio Rendering
---------------

The `mopidy-btmanager` extension will allow the user to establish bluetooth connections
to A2DP audio sources and sinks.  However, in order to route audio to an audio sink,
you will require a separate entity that is able to push Mopidy audio onto the
available bluetooth media (A2DP) transport.  There are a number of different ways
of doing this:

1. Use the `mopidy-pulseaudio` extension

The main advantage of using `mopidy-pulseaudio` is that it can dynamically render
audio from Mopidy directly to newly connected audio sinks without any changes being
require to the Mopidy audio configuration subsystem.  Moreover, it can be configured
also to attach audio sources to audio sinks without user intervention e.g., you wish
to play music from your iPhone over bluetooth rather than playing from Mopidy.

Refer to <https://github.com/liamw9534/mopidy-pulseaudio> for more details about
using PulseAudio with Mopidy.

2. Create a configuration entry in your `asound.rc` ALSA configuration file for
each bluetooth device you have e.g.,

    pcm.bluetooth_speaker_1 {
        type bluetooth
        device "XX:XX:XX:XX:XX:XX"
        profile "auto"
    }

[(XX:XX:XX:XX:XX:XX should be substituted for the bluetooth device address]

And then set ``output`` as follows in your Mopidy audio configuration:

    output = alsasink device=bluetooth_speaker_1

3. Use the gstreamer bluetooth plugin and set your audio ``output`` configuration
in mopidy to the following:

    output = sbcenc ! a2dpsink device=XX:XX:XX:XX:XX:XX async-handling=true

[(XX:XX:XX:XX:XX:XX should be substituted for the bluetooth device address]


Note: At present mopidy does not support dynamic audio sink selection in its
audio subsystem.  This means that any sink must be chosen 'a priori'
as part of the audio ``output`` configuration, when using the ALSA sink or gstreamer
audio rendering methods.


Input Control
-------------

This `mopidy-btmanager` extension will allow the user to establish bluetooth
connections to AVRCP compatible devices designed for music players.  There are
many such devices on the market e.g.,
http://www.amazon.co.uk/Trust-Wireless-Remote-Control-iPad/dp/B005F5CK26

However, the AVRCP commands issued by an input device are not intercepted by the
`mopidy-btmanager` extension.  A separate extension is used for this called
`mopidy-evtdev` which is designed to intercept any keypress events from virtual input
devices that attach to the OS.

Refer to <https://github.com/liamw9534/mopidy-evtdev> for more details about
using virtual input devices with Mopidy.


Project resources
=================

- `Source code <https://github.com/liamw9534/mopidy-btmanager>`_
- `Issue tracker <https://github.com/liamw9534/mopidy-btmanager/issues>`_
- `Download development snapshot <https://github.com/liamw9534/mopidy-btmanager/archive/master.tar.gz#egg=mopidy-evtdev-dev>`_


Changelog
=========


v0.1.0 (UNRELEASED)
----------------------------------------

- Initial release.
