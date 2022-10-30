from ..helpers import ensureDottedAccess


def _class_decorator_factory(storing_type: str):

    def func(options):

        options = ensureDottedAccess(options)

        class class_decorator:
            """ A Simple Decorator for classes
                This will store the decorated element in an list
                named "decoratedItems"

                You can provide options etc.
            """

            def __init__(self, item):
                nonlocal storing_type
                self._type = storing_type

            def __set_name__(self, owner, name):
                # We want to store the item.
                if not hasattr(owner, "decoratedItems"):
                    setattr(owner, "decoratedItems", [])

                # Store item
                owner.decoratedItems.append(
                    ensureDottedAccess({
                        "accessor": name,
                        "options": options,
                        "type": self._type,
                    })
                )

        return class_decorator

    return func


exportAsNopeService = _class_decorator_factory("method")
exportAsNopeProperty = _class_decorator_factory("property")
exportAsNopeEvent = _class_decorator_factory("event")
