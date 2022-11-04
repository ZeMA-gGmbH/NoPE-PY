#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ...modules import BaseModule
from ...observable import NopeObservable


class HelloWorldModule(BaseModule):

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

        await self.registerMethod('hello', self.hello, {
            "schema": {
                "type": "string",
                "name": "greetings_to",
                "description": "The person how receives the greeting"
            }
        })

        def _callback(data, reset):
            if (rest.sender != self.prop.id):
                self._logger.warn("External-Update. Data= " + str(data))

        self.prop.subscribe(_callback)

    async def hello(self, greetings_to: str):
        return 'hello ' + greetings_to + ' from ' + self.identifier

    async def dispose(self):
        await super().dispose()
        print(self.identifier, "as helloworld is getting removed")
