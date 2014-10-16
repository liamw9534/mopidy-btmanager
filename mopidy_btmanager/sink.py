from __future__ import unicode_literals

import gobject

import pygst
pygst.require('0.10')
import gst  # noqa


class BluetoothA2DPSink(gst.Bin):
    def __init__(self, address):
        super(BluetoothA2DPSink, self).__init__()
        queue = gst.element_factory_make('queue')
        sbcenc = gst.element_factory_make('sbcenc')
        a2dpsink = gst.element_factory_make('a2dpsink')
        a2dpsink.set_property('device', address)
        a2dpsink.set_property('async-handling', True)
        self.add_many(queue, sbcenc, a2dpsink)
        gst.element_link_many(queue, sbcenc, a2dpsink)
        pad = queue.get_pad('sink')
        ghost_pad = gst.GhostPad('sink', pad)
        self.add_pad(ghost_pad)
