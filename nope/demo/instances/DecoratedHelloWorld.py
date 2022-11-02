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
        self.setAuthor("martin", "karkowski", "m.karkowski@zema.de")
        self.setVersion("1.0", "01.11.2022")
        self.description = "A Simple Hello World Module. It contains a Property and a Function."

        # Generate the Observable
        self.prop = NopeObservable()

    async def init(self):

        await super().init()

        await self.registerProperty('prop', self.prop, {
            'topic': 'prop',
            'mode': ['publish', 'subscribe']
        })

        def _callback(data, sender, *args):
            if (sender != self.prop.id):
                self._logger.warn("External-Update. Data= " + str(data))

        self.prop.subscribe(_callback)

    @exportAsNopeService({
        "schema": {
            "type": "string",
            "name": "greetings_to",
            "description": "The person how receives the greeting"
        }
    })
    async def hello(self, greetings_to: str):
        return 'hello ' + greetings_to + ' from ' + self.identifier

    async def dispose(self):
        await super().dispose()

        print(self.identifier, "as helloworld is getting removed")
