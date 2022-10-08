#!/usr/bin/env python
# @author Martin Karkowski
# @email m.karkowski@zema.de

from ...helpers import max_of_array, min_of_array


def generate_selector(selector, core):
    """ A Helper Function, to generate the Basic selector Functions.

    params

    """

    if selector == 'master':

        # Define a function, which will select the same master.
        async def master_selector(opts):
            master_id = core.connectivity_manager.master.id
            data = core.rpc_manager.services.key_mapping_reverse
            if opts.service_name in data:
                arr = list(data[opts.service_name])
                if master_id in arr:
                    return master_id
            raise Exception('No matching dispatcher present.')

        return master_selector

    elif selector == 'first':

        async def first_found(opts):
            data = core.rpc_manager.services.key_mapping_reverse
            if opts.service_name in data:
                arr = list(data[opts.service_name])
                if len(arr) > 0:
                    return arr[0]
            raise Exception('No matching dispatcher present.')

        return first_found

    elif selector == 'dispatcher':

        async def own_dispatcher(opts):
            ids = core.connectivity_manager.dispatchers.data.get_content()
            if core.id in ids:
                return core.id
            raise Exception('No matching dispatcher present.')

        return own_dispatcher

    elif selector == 'host':

        host = core.connectivity_manager.info.host.name

        async def same_host(opts):
            data = core.rpc_manager.services.key_mapping_reverse
            if opts.service_name in data:
                items = list(data[opts.service_name])
                hosts = list(
                    map(
                        lambda item: core.connectivity_manager.dispatchers.original_data[item].host.name,
                        items
                    )
                )

                if host in hosts:
                    return items[hosts.index(host)]

            raise Exception('No matching dispatcher present.')

        return same_host

    elif selector == 'cpu-usage':

        async def cpu_usage():
            dispatchers = core.connectivity_manager.dispatchers.data.get_content()
            best_option = min_of_array(dispatchers, 'host.cpu.usage')
            if best_option.index >= 0:
                return dispatchers[best_option.index]
            raise Exception('No matching dispatcher present.')

        return cpu_usage

    elif selector == 'free-ram':

        async def ram_usage():
            dispatchers = core.connectivity_manager.dispatchers.data.get_content()
            best_option = max_of_array(dispatchers, 'host.ram.free')
            if best_option.index >= 0:
                return dispatchers[best_option.index]

            raise Exception('No matching dispatcher present.')

        return ram_usage

    else:
        raise Exception('Please use a valid selector')
