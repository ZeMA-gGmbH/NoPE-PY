#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de


def generate_assignment_checker(selector, core):
    # Generate a function which will return true.
    async def generate_true():
        return True

    if selector == 'first':
        return generate_true
    elif selector == 'cpu-usage':
        return generate_true
    elif selector == 'free-ram':
        return generate_true

    elif selector == 'dispatcher':
        async def dispatcher_matching(_module, used_dispatcher):
            return used_dispatcher.id == core.id

        return dispatcher_matching

    elif selector == 'host':
        host = core.connectivity_manager.info.host.name

        async def host_matching(_module, used_dispatcher):
            return used_dispatcher.host.name == host

        return host_matching

    else:
        raise Exception('Please provide an valid selector')
