
""" An example how to modify the Behavior of multiple elements using a Plugin.

    In This case the Plugin allows the implementation of an ackknowledgement
    message if required.
"""

from nope.plugins import plugin
from nope.helpers import generateId, EXECUTOR, ensureDottedAccess, formatException
from nope.eventEmitter import NopeEventEmitter


@plugin([
    "nope.communication.bridge",
    "nope.dispatcher.connectivityManager"
],
    name="ackMessages")
def extend(bridgeMod, conManagerMod):
    "Extends the Bridge and adds the functionality of ack knowlededing messages."
    class Bridge(bridgeMod.Bridge):
        def __init__(self, *args, **kwargs):
            bridgeMod.Bridge.__init__(self, *args, **kwargs)

            # Define
            self.defaultTargets = kwargs.get("defaultTargets", list())
            self.ackReplyId = kwargs.get("ackReplyId", None)
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

            # Subscribe to Errors:
            def onTransportError(err, *args):
                if self._logger:
                    self._logger.error(
                        "Failed to receive an acknowledge message!")
                    self._logger.error(formatException(err))
                else:
                    print(formatException(err))
            self.onTransportError.subscribe(onTransportError)

        async def emit(self, eventName, data, target=None, timeout=0, **kwargs):
            promise = None

            if eventName != "ackMessage" and self.ackReplyId is not None:
                messageId = generateId()
                data["messageId"] = messageId

                # Now lets define the Target:

                if target is None or target == True:
                    if self.defaultTargets:
                        target = set(self.defaultTargets)
                    else:
                        target = set()
                else:
                    if isinstance(target, str):
                        target = set([target])
                    elif target == False:
                        target = set()
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

            await bridgeMod.Bridge.emit(self, eventName, data, **kwargs)

            if promise:
                await promise

            return eventName, data, None

        async def on(self, eventName, cb):
            # In here we will define a custom callback,
            # which will send an "ackMessage" after
            # performing the original callback.

            if eventName == "ackMessage":
                return await bridgeMod.Bridge.on(self, eventName, cb)

            def callback(msg):
                cb(msg)

                if "messageId" in msg and self.ackReplyId is not None:

                    EXECUTOR.callParallel(
                        self.emit,
                        "ackMessage",
                        ensureDottedAccess({
                            "messageId": msg["messageId"],
                            "dispatcher": self.ackReplyId
                        })
                    )

            return await bridgeMod.Bridge.on(self, eventName, callback)

    class NopeConnectivityManager(conManagerMod.NopeConnectivityManager):
        def __init__(self, *args, **kwargs):
            conManagerMod.NopeConnectivityManager.__init__(
                self, *args, **kwargs)

            self._communicator.ackReplyId = self._id
            self.forceAckMessage = True

            # To extend

            def cb(dispatchers: list, *args):
                if self.forceAckMessage:
                    self._communicator.defaultTargets = dispatchers

            self.dispatchers.data.subscribe(cb)

        def _info(self):

            ret = conManagerMod.NopeConnectivityManager._info(self)

            if "plugins" not in ret:
                ret.plugins = []

            ret.plugins.append("ackMessages")

            return ret

    return Bridge, NopeConnectivityManager
