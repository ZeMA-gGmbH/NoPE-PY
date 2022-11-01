#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ...modules import BaseModule
from ...decorators.classes import exportAsNopeEvent, exportAsNopeProperty, exportAsNopeService
from ...observable import NopeObservable


class DecoratedHelloWorldModule(BaseModule):

    def __init__(self, core):
        super().__init__(core)

        # Define the Description:
        self.set_author("martin", "karkowski", "m.karkowski@zema.de")
        self.set_version("1.0", "01.11.2022")
        self.description = "A Simple Hello World Module. It contains a Property and a Function."

        # Generate the Observable
        self.test_prop = NopeObservable()

    async def init(self):

        await super().init()

        await self.register_property('test_prop', self.test_prop, {
            'topic': 'test_prop',
            'mode': ['publish', 'subscribe']
        })

        def _callback(data, sender, *args):
            if (sender != self.test_prop.id):
                self._logger.warn("External-Update. Data= " + str(data))

        self.test_prop.subscribe(_callback)

    @exportAsNopeService({
        'delete_after_calling': True,
        "schema": {
            "type": "string",
            "name": "greetings_to",
            "description": "The person how receives the greeting"
        }
    })
    async def hello_world(self, greetings_to: str):
        return 'hello ' + greetings_to + ' from ' + self.identifier

    async def dispose(self):
        await super().dispose()

        print(self.identifier, "as helloworld is getting removed")
