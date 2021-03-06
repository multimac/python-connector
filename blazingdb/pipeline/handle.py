"""
Defines the Handle class for tracking messages within the pipeline
"""

import asyncio


class Handle(object):
    """ Represents a handle which can be waited upon to see when a message is completed """

    def __init__(self, loop=None, parent=None, track_children=False):
        loop = loop if loop is not None else asyncio.get_event_loop()

        self.children = [] if track_children else None
        self.future = loop.create_future()
        self.parent = parent
        self.loop = loop

    def __await__(self):
        yield from self.future.__await__()

        while self.children:
            self.children, pending = [], self.children
            yield from asyncio.wait(pending, loop=self.loop)

    def add_child(self, follower):
        """ Adds a follower to the handle """
        if self.children is not None:
            self.children.append(follower)
        elif self.parent is not None:
            self.parent.add_child(follower)

    def create_child(self, track_children=False):
        """ Creates a new follower from the handle """
        handle = Handle(loop=self.loop, parent=self,
            track_children=track_children)

        self.add_child(handle)
        return handle

    def complete(self):
        self.future.set_result(None)

    def cancelled(self):
        return self.future.cancelled()

    def done(self):
        return self.future.done()
