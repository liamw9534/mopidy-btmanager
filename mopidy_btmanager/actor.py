from __future__ import unicode_literals

import logging
import pykka
import bt_manager
import dbus

from mopidy import device, exceptions

logger = logging.getLogger(__name__)

BLUETOOTH_DEVICE_TYPE = 'bluetooth'

class BTDeviceManager(pykka.ThreadingActor, device.DeviceManager):
    """
    BTDeviceManager implements an autonomous bluetooth device manager that
    is capable of discovering, pairing and connecting with bluetooth devices
    with profiles that are compatible with the Mopidy music player.

    It implements a mopidy DeviceManager and posts events to any classes
    mixing in the DeviceListener interface.
    
    The main use-case of this device manager is to notify when new
    devices are added/connected which allows Audio to commence
    streaming output to them.
    
    ..note:: This plug-in is not concerned with streaming A2DP audio to
        a device.  This should be dealt with by the Audio subsystem.
    """
    def __init__(self, config):
        super(BTDeviceManager, self).__init__()
        self.device_types = [BLUETOOTH_DEVICE_TYPE]
        self.config = config

    def _on_device_created(self, signal_name, user_arg, path):
        bt_device = bt_manager.BTDevice(dev_path=path)
        bt_device.add_signal_receiver(self._on_device_property_changed,
                                      bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED,
                                      path)
        dev = BTDeviceManager._make_device(bt_device.Name,
                                           bt_device.Address,
                                           bt_device.UUIDs)
        device.DeviceListener.send('device_created', device=dev)
        logger.info('BTDeviceManager event=device_created dev=%s', dev)

    def _on_device_removed(self, path):
        # We can't access the device object from the dbus registry, since
        # it no longer exists.  We therefore have to translate the device
        # path to a device address
        device_addr = path[-17:].replace('_', ':')
        dev = BTDeviceManager._make_device(None, device_addr, [])
        device.DeviceListener.send('device_removed', device=dev)
        logger.info('BTDeviceManager event=device_removed dev=%s', dev)

    def _on_device_disappeared(self, signal_name, user_arg, device_addr):
        dev = BTDeviceManager._make_device(None, device_addr, [])
        device.DeviceListener.send('device_disappeared', device=dev)
        logger.info('BTDeviceManager event=device_disappeared dev=%s', dev)

    def _on_device_found(self, signal_name, user_arg, device_addr, device_info):
        # The device *MAY* not yet be in the dbus registry, so we use the
        # properties we get given in this signal handler to provide the
        # mandatory device fields
        uuids = device_info.get('UUIDs', [])
        dev = BTDeviceManager._make_device(device_info['Name'],
                                           device_addr,
                                           uuids)
        device.DeviceListener.send('device_found', device=dev)
        logger.info('BTDeviceManager event=device_found dev=%s', dev)

    def _on_device_property_changed(self, signal_name, path, prop, value):
        bt_device = bt_manager.BTDevice(dev_path=path)
        dev = BTDeviceManager._make_device(bt_device.Name,
                                           bt_device.Address,
                                           bt_device.UUIDs)
        property_dict = {}
        property_dict[prop] = value
        logger.info('BTDeviceManager event=device_property_changed dev=%s %s=%s', dev,
                    prop, value)

        # We have dedicated events for the "Connected" property
        if (prop == 'Connected'):
            if (value):
                device.DeviceListener.send('device_connected', device=dev)
            else:
                device.DeviceListener.send('device_disconnected', device=dev)
        else:
            device.DeviceListener.send('device_property_changed', device=dev,
                                       property_dict=property_dict)

    @staticmethod
    def _service_to_capability(service):
        if (service.name == 'AudioSource'):
            return device.DeviceCapability.DEVICE_AUDIO_SOURCE
        elif (service.name == 'AudioSink'):
            return device.DeviceCapability.DEVICE_AUDIO_SINK
        elif (service.name == 'AVRemoteControl'):
            return device.DeviceCapability.DEVICE_INPUT_CONTROL
        else:
            return None

    @staticmethod
    def _make_device(name, addr, uuids):
        dev = BluetoothDevice()
        dev.name = name
        dev.address = addr
        dev.capability = []
        # Check for supported UUIDs and translate to respective capability
        for i in uuids:
            uuid = bt_manager.BTUUID(i)
            service = bt_manager.SERVICES.get(uuid.uuid16)
            if (service):
                cap = BTDeviceManager._service_to_capability(service)
                if (cap is not None):
                    dev.capability.append(cap)
        return dev

    def _device_created_ok(self, path):
        # Mark device is trusted to allow future connections
        bt_device = bt_manager.BTDevice(dev_path=path)
        bt_device.Trusted = True
        dev = BTDeviceManager._make_device(bt_device.Name,
                                           bt_device.Address,
                                           bt_device.UUIDs)
        device.DeviceListener.send('device_created', device=dev)
        logger.info('BTDeviceManager event=device_created dev=%s', dev)

    def _device_created_error(self, error):
        logger.error('BTDeviceManager device creation error:%s', error)

    def _request_confirmation(self, path, pass_key):
        bt_device = bt_manager.BTDevice(dev_path=path)
        dev = BTDeviceManager._make_device(bt_device.Name,
                                              bt_device.Address,
                                              bt_device.UUIDs)
        device.DeviceListener.send('device_pass_key_confirmation',
                                   device=dev,
                                   pass_key=pass_key)
        logger.info('BTDeviceManager event=device_pass_key_confirmation dev=%s', dev)

    def _request_pin_code(self, path):
        bt_device = bt_manager.BTDevice(dev_path=path)
        dev = BTDeviceManager._make_device(bt_device.Name,
                                           bt_device.Address,
                                           bt_device.UUIDs)
        device.DeviceListener.send('device_pin_code_requested',
                                   device=dev,
                                   pin_code=self.config['btmanager']['pincode'])
        logger.info('BTDeviceManager event=device_pin_code_requested dev=%s', dev)
        return dbus.String(self.config['btmanager']['pincode'])

    def on_start(self):
        """
        Activate the BT adapter
        """
        adapter = bt_manager.BTAdapter()
        self.is_powered_on_start = adapter.Powered
        adapter.Powered = True
        adapter.Name = self.config['btmanager']['name']

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

        # Enable device discovery
        adapter.start_discovery()

        # Store away adapter for future usage
        self.adapter = adapter

        # Register agent for handling device pairing/authentication
        try:
            path = '/mopidy/agent'
            caps = 'DisplayYesNo'
            pin_code = self.config['btmanager']['pincode']
            self.agent = bt_manager.BTAgent(path=path,
                                            default_pin_code=pin_code,
                                            cb_notify_on_request_pin_code=self._request_pin_code,
                                            cb_notify_on_request_confirmation=self._request_confirmation)
            self.adapter.register_agent(path, caps)
        except:
            raise exceptions.ExtensionError('Unable to register agent')

        logger.info('BTDeviceManager started')

    def on_stop(self):
        """
        Put the BT adapter into idle mode.
        """

        # Unregister bluetooth agent
        try:
            self.adapter.unregister_agent('/mopidy/agent')
        except:
            pass

        # Remove device events
        bt_devices = self.adapter.list_devices()
        for i in bt_devices:
            bt_device = bt_manager.BTDevice(dev_path=i)
            bt_device.remove_signal_receiver(bt_manager.BTAdapter.SIGNAL_PROPERTY_CHANGED)

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
        logger.info('BTDeviceManager stopped')

    def get_devices(self):
        bt_devices = self.adapter.list_devices()
        return [BTDeviceManager._make_device(bt_device.Name,
                                             bt_device.Address,
                                             bt_device.UUIDs) for bt_device in bt_devices]

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
        if (device.DeviceCapability.DEVICE_AUDIO_SINK in dev.capabilities):
            bt_manager.BTAudioSink(dev_id=dev.address).connect()
        if (device.DeviceCapability.DEVICE_AUDIO_SOURCE in dev.capabilities):
            bt_manager.BTAudioSource(dev_id=dev.address).connect()
        if (device.DeviceCapability.DEVICE_AUDIO_SOURCE in dev.capabilities):
            bt_manager.BTInput(dev_id=dev.address).connect()

    def disconnect(self, dev):
        """
        Disconnect a device
        """
        logger.info('BTDeviceManager disconnecting dev=%s', dev)
        bt_device = bt_manager.BTDevice(dev_id=dev.address)
        bt_device.disconnect()

    def pair(self, dev):
        """
        Pair a device
        """
        logger.info('BTDeviceManager pairing dev=%s', dev)
        if (self.is_paired(device) is False):
            path = '/mopidy/agent'

            try:
                caps = 'DisplayYesNo'
                self.adapter.create_paired_device(dev.address, path, caps,
                                                  self._device_created_ok,
                                                  self._device_created_error)
            except:
                raise exceptions.ExtensionError('Unable to create paired device')

    def remove(self, dev):
        """
        Remove a paired device
        """
        logger.info('BTDeviceManager removing dev=%s', dev)
        path = self.adapter.find_device(dev.address)
        self.adapter.remove_device(path)

    def is_connected(self, dev):
        """
        Ascertain if a device is connected
        """
        try:
            bt_device = bt_manager.BTDevice(dev_id=dev.address)
            return bt_device.Connected
        except:
            return False

    def is_paired(self, dev):
        """
        Ascertain if a device is paired
        """
        try:
            bt_device = bt_manager.BTDevice(dev_id=dev.address)
            return bt_device.Paired
        except:
            return False

    def set_property(self, dev, name, value):
        """
        Set a device's property
        """
        bt_device = bt_manager.BTDevice(dev_id=dev.address)
        bt_device.set_property(name, value)

    def get_property(self, dev, name=None):
        """
        Get a device's property
        """
        bt_device = bt_manager.BTDevice(dev_id=dev.address)
        return bt_device.get_property(name)

    def has_property(self, dev, name):
        """
        Check if a device has a particular property name
        """
        bt_device = bt_manager.BTDevice(dev_id=dev.address)
        return name in bt_device.__dict__


class BluetoothDevice(device.Device):

    device_type = BLUETOOTH_DEVICE_TYPE

    def __str__(self):
        return '{type:' + \
            self.device_type + ' name:' + str(self.name) + ' addr:' + str(self.address) + \
            ' caps:' + str(self.capability) + '}'

    def __repr__(self):
        return self.__str__
