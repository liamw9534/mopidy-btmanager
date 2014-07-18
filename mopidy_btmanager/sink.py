from __future__ import unicode_literals

import gobject

import pygst
pygst.require('0.10')
import gst  # noqa
import bt_manager


class BluetoothAudioSink(gst.Bin):
    def __init__(self, address):
        super(BluetoothAudioSink, self).__init__()
        a2dpsink = gst.element_factory_make('a2dpsink')
        a2dpsink.set_property('device', address)
        a2dpsink.set_property('async-handling', True)
        sbcenc = gst.element_factory_make('sbcenc')
        queue = gst.element_factory_make('queue')
        capsfilter = gst.element_factory_make('capsfilter')
        caps = 'audio/x-raw-int, endianness=(int)1234, channels=(int)2, ' + \
            'width=(int)16, depth=(int)16,signed=(boolean)true, rate=(int)44100'
        capsfilter.set_property('caps', gst.Caps(str(caps)))
        self.add_many(queue, capsfilter, sbcenc, a2dpsink)
        gst.element_link_many(queue, capsfilter, sbcenc, a2dpsink)
        pad = queue.get_pad('sink')
        ghost_pad = gst.GhostPad('sink', pad)
        self.add_pad(ghost_pad)


class BluetoothAudioSinkExperimental(gst.Bin):

    def __init__(self, address):
        super(BluetoothAudioSinkExperimental, self).__init__()
        print 'Creating audio sink...'
        btsink = BTA2DPSink(address)
        print 'Done...'
        queue = gst.element_factory_make('queue')
        self.add_many(queue, btsink)
        gst.element_link_many(queue, btsink)
        pad = queue.get_pad('sink')
        ghost_pad = gst.GhostPad('sink', pad)
        self.add_pad(ghost_pad)


class BTA2DPSink(gst.BaseSink):

    __gstdetails__ = (
        'bta2dpsink',
        'Sink',
        'Bluetooth A2DP audio sink',
        'Liam Wickins <liamw9534@gmail.com>')

    __gsttemplates__ = (
        gst.PadTemplate ('sink',
                         gst.PAD_SINK,
                         gst.PAD_ALWAYS,
                         gst.caps_from_string(b'audio/x-raw-int, endianness=(int)1234, '
                                              'channels=(int)2, '
                                              'width=(int)16, depth=(int)16, '
                                              'signed=(boolean)true, rate=(int)44100')
                         )
                        )

    sink_pad = property(lambda self: self.get_pad('sink'))

    def __init__(self, address):

        super(BTA2DPSink, self).__init__()
        self._buf = b''

        print 'Find adapter...'
        path = bt_manager.BTAdapter().find_device(address)
        print 'Adapter path...', path
        print 'Create media endpoint...'
        ep_path = '/ep/1'
        self.ep = bt_manager.SBCAudioSource(path=ep_path)
        print 'Created media endpoint...', self.ep
        print 'Registering media endpoint...'
        media = bt_manager.BTMedia()
        media.register_endpoint(ep_path, self.ep.get_properties())
        print 'Registering transport ready event handler...'
        self.ep.register_transport_ready_event(self._transport_ready_handler, None)
        self.set_sync(True)
        print 'Done...'

    def _buf_add(self, buf):
        self._buf += buf

    def _buf_remove(self, size):
        if (len(self._buf) >= size):
            buf = self._buf[0:size-1]
            self._buf = self._buf[size:]
            return buf
        return b''

    def _transport_ready_handler(self, user_arg):
        #print 'Received data len:', len(buf.data), "occupancy:", len(self._buf)
        opbuf = self._buf_remove(2560)
        if (len(opbuf)):
            self.ep.write_transport(opbuf)

    def do_render(self, buf):
        #print 'Received data len:', len(buf.data), "occupancy:", len(self._buf)
        self._buf_add(buf.data)
        return gst.FLOW_OK
    
    def do_stop(self):
        self.ep.close_transport()
        self.ep.remove_from_connection()
        media = bt_manager.BTMedia()
        media.unregister_endpoint('/ep/1')


gobject.type_register(BTA2DPSink)
