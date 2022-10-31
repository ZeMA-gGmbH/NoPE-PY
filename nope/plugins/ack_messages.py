
""" An example how to modify the
"""

from nope.plugins import plugin
from nope.helpers import generateId, Promise, EXECUTOR, ensureDottedAccess
from nope.eventEmitter import NopeEventEmitter


@plugin("nope.communication.bridge")
def extend(module):
    "Extends the Bridge and adds the functionality of ack knowlededing messages."
    class Bridge(module.Bridge):
        def __init__(self, *args, **kwargs):
            module.Bridge.__init__(self, *args, **kwargs)

            # Define
            self.onTransportError = NopeEventEmitter()
            self._onMessageReceived = NopeEventEmitter()

            # Dict containing the Messages, that have been send as key and containign the
            # still open respones (dispatcher ids) as set as value
            self._openMessages = {}

            # Make shure to forward ackknowledge messages.
            EXECUTOR.callParallel(
                self.on,
                "ackMessage",
                lambda msg: self._onMessageReceived.emit(msg))

        async def emit(self, eventName, data, target=None, timeout=0, **kwargs):
            promise = None

            if eventName != "ackMessage":
                messageId = generateId()
                data["messageId"] = messageId

                # Now lets define the Target:

                if target is None:
                    target = set()
                else:
                    if isinstance(target, str):
                        target = set([target])
                    else:
                        target = set(target)

                # Only if we expect a target,
                # we will wait for the message.
                if len(target) > 0:

                    def callback(msg, *args):
                        nonlocal messageId

                        if msg.get(
                                "messageId", False) == messageId and messageId in self._openMessages:

                            data = self._openMessages.get(
                                messageId, False)

                            # Mark the Dispatcher as ready:
                            data["received"].add(msg["dispatcher"])

                            if len(data["target"] - data["received"]) == 0:

                                # Remove the Message, becaus it is finished
                                self._openMessages.pop(messageId)

                                return True

                        return False

                    promise = self._onMessageReceived.waitFor(
                        callback, options={"timeout": timeout})

                    # Store the Message
                    self._openMessages[messageId] = {
                        "received": set(),
                        "target": target,
                        "promise": promise
                    }

            res = await module.Bridge.emit(self, eventName, data, **kwargs)

            if promise:
                await promise

            return eventName, data, None

        async def on(self, eventName, cb):
            # In here we will define a custom callback,
            # which will send an "ackMessage" after
            # performing the original callback.

            if eventName == "ackMessage":
                return await module.Bridge.on(self, eventName, cb)

            def callback(msg):
                cb(msg)

                if "messageId" in msg:

                    EXECUTOR.callParallel(
                        self.emit,
                        "ackMessage",
                        ensureDottedAccess({
                            "messageId": msg["messageId"],
                            "dispatcher": self._id
                        })
                    )

            return await module.Bridge.on(self, eventName, callback)

    return Bridge
