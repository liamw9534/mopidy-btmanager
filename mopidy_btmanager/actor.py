from __future__ import unicode_literals

import logging
import pykka
import bt_manager
import dbus
from .sink import BluetoothA2DPSink

from mopidy import exceptions, service
from mopidy.utils.jsonrpc import private_method

logger = logging.getLogger(__name__)

BLUETOOTH_SERVICE_NAME = 'bluetooth'


class BTDeviceManager(pykka.ThreadingActor, service.Service):
    """
    BTDeviceManager implements an autonomous bluetooth device manager that
    is capable of discovering, pairing and connecting with bluetooth devices
    with profiles that are compatible with the Mopidy music player.

    It implements a mopidy Service and posts events to any classes
    mixing in the ServiceListener interface.

    The main use-case of this device manager is to notify when new
    devices are added/connected which allows Audio to commence
    streaming output to them.

    ..note:: This plug-in is not concerned with streaming A2DP audio to
        a device.  This should be dealt with by the Audio subsystem.
    """
    def __init__(self, config, core):
        super(BTDeviceManager, self).__init__()
        self.name = BLUETOOTH_SERVICE_NAME
        self.public = True
        self.config = dict(config['btmanager'])
        self.devices = {}
        self.autoconnect = self.config['autoconnect']
        self.core = core

    def _on_device_created(self, signal_name, user_arg, path):
        bt_device = bt_manager.BTDevice(dev_path=path)
        dev = BTDeviceManager._make_device(bt_device.Name,
                                           bt_device.Address,
                                           bt_device.UUIDs)
        service.ServiceListener.send('bluetooth_device_created',
                                     service=self.name,
                                     device=dev)
        logger.info('BTDeviceManager event=device_created dev=%s', dev)

    def _on_device_removed(self, signal_name, user_arg, path):
        # We can't access the device object from the dbus registry, since
        # it no longer exists.  We therefore have to translate the device
        # path to a device address
        device_addr = path[-17:].replace('_', ':')
        dev = BTDeviceManager._make_device(None, device_addr, [])
        service.ServiceListener.send('bluetooth_device_removed', service=self.name,
                                     device=dev)
        logger.info('BTDeviceManager event=device_removed dev=%s', dev)

    def _on_device_disappeared(self, signal_name, user_arg, device_addr):
        dev = BTDeviceManager._make_device(None, device_addr, [])
        service.ServiceListener.send('bluetooth_device_disappeared',
                                     service=self.name,
                                     device=dev)
        logger.info('BTDeviceManager event=device_disappeared dev=%s', dev)

    def _on_device_found(self, signal_name, user_arg, device_addr, device_info):
        # The device *MAY* not yet be in the dbus registry, so we use the
        # properties we get given in this signal handler to provide the
        # mandatory device fields
        uuids = device_info.get('UUIDs', [])
        name = device_info.get('Name')
        dev = BTDeviceManager._make_device(name,
                                           device_addr,
                                           uuids)
        service.ServiceListener.send('bluetooth_device_found',
                                     service=self.name,
                                     device=dev)
        logger.info('BTDeviceManager event=device_found dev=%s', dev)

        # Try to autoconnect if this is enabled
        if (self.autoconnect):
            self.connect(dev)

    def _on_device_property_changed(self, signal_name, path, prop, value):

        try:
            bt_device = self.devices.get(path)
            dev = BTDeviceManager._make_device(bt_device.Name,
                                               bt_device.Address,
                                               bt_device.UUIDs)
        except:
            device_addr = path[-17:].replace('_', ':')
            dev = BTDeviceManager._make_device(None, device_addr, [])
        property_dict = {}
        property_dict[prop] = value
        logger.info('BTDeviceManager event=device_property_changed dev=%s %s=%s', dev,
                    prop, value)

        # We have dedicated events for the "Connected" property
        if (prop == 'Connected'):
            if (value):
                if (self.config['attach_audio_sink'] and 'AudioSink' in dev['caps']):
                    self._connect_audio_sink(dev['addr'])
                service.ServiceListener.send('bluetooth_device_connected', service=self.name,
                                             device=dev)
            else:
                service.ServiceListener.send('bluetooth_device_disconnected', service=self.name,
                                             device=dev)
        else:
            service.ServiceListener.send('bluetooth_device_property_changed', service=self.name,
                                         device=dev,
                                         property_dict=property_dict)

    @staticmethod
    def _service_to_capability(service):
        if (service.name == 'AudioSource'):
            return service.name
        elif (service.name == 'AudioSink'):
            return service.name
        elif (service.name == 'AVRemoteControl'):
            return 'InputControl'
        elif (service.name == 'HumanInterfaceDeviceService'):
            return 'InputControl'
        else:
            return None

    @staticmethod
    def _make_device(name, addr, uuids):
        capabilities = []
        # Check for supported UUIDs and translate to respective capability
        for i in uuids:
            uuid = bt_manager.BTUUID(i)
            service = bt_manager.SERVICES.get(uuid.uuid16)
            if (service):
                cap = BTDeviceManager._service_to_capability(service)
                if (cap is not None):
                    capabilities.append(cap)
        return { 'addr': addr, 'caps': capabilities }

    @staticmethod
    def _audio_sink_name(address):
        return BLUETOOTH_SERVICE_NAME + ':audio:' + address

    def _connect_audio_sink(self, address):
        self.core.add_audio_sink(BTDeviceManager._audio_sink_name(address),
                                 BluetoothA2DPSink(address)) 

    def _disconnect_audio_sink(self, address):
        self.core.remove_audio_sink(BTDeviceManager._audio_sink_name(address))

    def _on_device_created_ok(self, path):
        logger.info('BTDeviceManager device=%s created ok', path)
        bt_device = bt_manager.BTDevice(dev_path=path)
        bt_device.discover_services()
        bt_device.add_signal_receiver(self._on_device_property_changed,
                                      bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED,
                                      path)
        bt_device.Trusted = True
        self.devices[str(path)] = bt_device

    def _on_device_created_error(self, error):
        logger.error('BTDeviceManager device creation error: %s', error)

    def _on_request_confirmation(self, event, path, pass_key):
        device_addr = path[-17:].replace('_', ':')
        dev = BTDeviceManager._make_device(None, device_addr, [])
        service.ServiceListener.send('bluetooth_pass_key_confirmation',
                                     service=self.name,
                                     device=dev,
                                     pass_key=pass_key)
        logger.info('BTDeviceManager event=device_pass_key_confirmation dev=%s', dev)
        return dbus.UInt32(pass_key)

    def _on_request_pin_code(self, event, path):
        pin_code = self.config['pincode']
        device_addr = path[-17:].replace('_', ':')
        dev = BTDeviceManager._make_device(None, device_addr, [])
        service.ServiceListener.send('bluetooth_pin_code_requested',
                                     device=dev,
                                     pin_code=pin_code)
        logger.info('BTDeviceManager event=device_pin_code_requested dev=%s', dev)
        return dbus.String(pin_code)

    def _on_release(self):
        logger.info('BTDeviceManager agent released')

    @private_method
    def on_start(self):
        """
        Activate the BT adapter
        """
        adapter = bt_manager.BTAdapter()
        self.is_powered_on_start = adapter.Powered
        adapter.Powered = True
        adapter.Name = self.config['name']

        adapter.add_signal_receiver(self._on_device_created,
                                    bt_manager.BTAdapter.SIGNAL_DEVICE_CREATED,
                                    None)
        adapter.add_signal_receiver(self._on_device_removed,
                                    bt_manager.BTAdapter.SIGNAL_DEVICE_REMOVED,
                                    None)
        adapter.add_signal_receiver(self._on_device_disappeared,
                                    bt_manager.BTAdapter.SIGNAL_DEVICE_DISAPPEARED,
                                    None)
        adapter.add_signal_receiver(self._on_device_found,
                                    bt_manager.BTAdapter.SIGNAL_DEVICE_FOUND,
                                    None)

        # Obtain initial list of devices and register for signal events
        bt_devices = adapter.list_devices()
        for i in bt_devices:
            bt_device = bt_manager.BTDevice(dev_path=i)
            bt_device.add_signal_receiver(self._on_device_property_changed,
                                          bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED,
                                          i)
            self.devices[str(i)] = bt_device

        # Enable device discovery
        adapter.start_discovery()

        # Store away adapter for future usage
        self.adapter = adapter

        # Notify listeners
        self.state = service.ServiceState.SERVICE_STATE_STARTED
        service.ServiceListener.send('service_started', service=self.name)
        logger.info('BTDeviceManager started')

    @private_method
    def on_stop(self):
        """
        Put the BT adapter into idle mode.
        """

        # Cleanup device events
        for i in self.devices.keys():
            d = self.devices.pop(i)
            d.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED)

        # Stop discovery
        self.adapter.stop_discovery()

        # Remove adapter events
        self.adapter.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED)
        self.adapter.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_DEVICE_FOUND)
        self.adapter.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_DEVICE_DISAPPEARED)
        self.adapter.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_DEVICE_REMOVED)
        self.adapter.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_DEVICE_CREATED)

        # Restore initial power-up state
        self.adapter.Powered = self.is_powered_on_start
        self.adapter = None

        # Notify listeners
        self.state = service.ServiceState.SERVICE_STATE_STOPPED
        service.ServiceListener.send('service_stopped', service=self.name)
        logger.info('BTDeviceManager stopped')

    @private_method
    def on_failure(self, *args):
        pass

    @private_method
    def stop(self, *args, **kwargs):
        return pykka.ThreadingActor.stop(self, *args, **kwargs)

    def set_property(self, name, value):
        if (name in self.config):
            self.config[name] = value
            service.ServiceListener.send('service_property_changed',
                                         service=self.name,
                                         props={ name: value })
            self.on_stop()
            self.on_start()

    def get_property(self, name):
        if (name is None):
            return self.config
        else:
            try:
                value = self.config[name]
                return { name: value }
            except:
                return None

    def get_devices(self):
        devices = []
        for dev in self.devices.values():
            try:
                devices.append(BTDeviceManager._make_device(dev.Name,
                                                            dev.Address,
                                                            dev.UUIDs))
            except:
                pass
        return devices

    def enable(self):
        """
        Enable the device manager
        """
        if (self.adapter is None):
            self.on_start()
        logger.info('BTDeviceManager enabled')

    def disable(self):
        """
        Disable the device manager
        """
        if (self.adapter):
            self.on_stop()
        logger.info('BTDeviceManager disabled')

    def connect(self, dev):
        """
        Connect device's compatible profiles
        """
        logger.info('BTDeviceManager connecting dev=%s', dev)
        try:
            path = str(self.adapter.find_device(dev['addr']))
            bt_device = self.devices.get(path)
            if (bt_device is not None):
                dev = BTDeviceManager._make_device(bt_device.Name,
                                                   bt_device.Address,
                                                   bt_device.UUIDs)
                if ('AudioSink' in dev['caps']):
                    sink = bt_manager.BTAudioSink(dev_id=dev['addr'])
                    sink.connect()
                if ('AudioSource' in dev['caps']):
                    source = bt_manager.BTAudioSource(dev_id=dev['addr'])
                    source.connect()
                if ('InputControl' in dev['caps']):
                    ip = bt_manager.BTInput(dev_id=dev['addr'])
                    ip.connect()
        except:
            pass

    def disconnect(self, dev):
        """
        Disconnect a device
        """
        logger.info('BTDeviceManager disconnecting dev=%s', dev)
        try:
            if (self.config['attach_audio_sink']):
                self._disconnect_audio_sink(dev['addr'])
            bt_device = bt_manager.BTDevice(dev_id=dev['addr'])
            bt_device.disconnect()
        except:
            pass

    def pair(self, dev):
        """
        Pair a device
        """
        if (not self.is_paired(dev)):
            logger.info('BTDeviceManager pairing dev=%s', dev)
            path = '/mopidy/agent'
            # Register agent for handling device pairing/authentication
            try:
                self.agent.remove_from_connection()
                self.adapter.unregister_agent(path)
            except:
                pass

            try:
                self.agent = bt_manager.BTAgent(path=path,
                                                cb_notify_on_request_pin_code=self._on_request_pin_code,
                                                cb_notify_on_request_confirmation=self._on_request_confirmation,
                                                cb_notify_on_release=self._on_release)
                caps = 'DisplayYesNo'
                self.adapter.create_paired_device(dev['addr'], path, caps,
                                                  self._on_device_created_ok,
                                                  self._on_device_created_error)
            except:
                raise exceptions.ExtensionError('Unable to create paired device')
        else:
            logger.info('BTDeviceManager dev=%s already paired', dev)

    def remove(self, dev):
        """
        Remove a paired device
        """
        logger.info('BTDeviceManager removing dev=%s', dev)
        try:
            path = str(self.adapter.find_device(dev['addr']))
            if (path in self.devices):
                bt_device = self.devices.pop(path)
                bt_device.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED)
                self.adapter.remove_device(path)
        except:
            raise

    def is_connected(self, dev):
        """
        Ascertain if a device is connected
        """
        try:
            path = str(self.adapter.find_device(dev['addr']))
            bt_device = self.devices.get(path)
            if (bt_device.Connected):
                return True
            else:
                return False
        except:
            raise

    def is_paired(self, dev):
        """
        Ascertain if a device is paired
        """
        try:
            path = str(self.adapter.find_device(dev['addr']))
            bt_device = self.devices.get(path)
            if (bt_device.Paired):
                return True
            else:
                return False
        except:
            return False

    def set_device_property(self, dev, name, value):
        """
        Set a device's property
        """
        try:
            path = str(self.adapter.find_device(dev['addr']))
            bt_device = self.devices.get(path)
            bt_device.set_property(name, value)
        except:
            pass

    def get_device_property(self, dev, name=None):
        """
        Get a device's property
        """
        try:
            path = str(self.adapter.find_device(dev['addr']))
            bt_device = self.devices.get(path)
            return bt_device.get_property(name)
        except:
            pass

    def has_device_property(self, dev, name):
        """
        Check if a device has a particular property name
        """
        try:
            path = str(self.adapter.find_device(dev['addr']))
            bt_device = self.devices.get(path)
            if (bt_device):
                return name in bt_device.__dict__
        except:
            pass
