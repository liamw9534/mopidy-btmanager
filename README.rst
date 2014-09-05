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

The 'pincode' setting is required when pairing devices with a keypad (e.g., AV remote control).
The same 'pincode' value must be entered during the pairing process.

The 'name' setting is the bluetooth network name that is announced to devices wishing to connect
to your network.  You can change it to anything you wish.

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
