# DISCLAIMER: This lib is based on:
# https://github.com/fpom/snakes/blob/master/snakes/plugins/__init__.py

"""This package implements a plugin system. Plugins
themselves are available as modules within the package.
Examples below are based on plugin `hello` that is distributed with
NoPE to be used as an exemple of how to build a plugin. It extends
class `NopeDispatcher` adding a method `hello` that says hello displaying
the name of the net.
## Loading plugins ##
The first example shows how to load a plugin: we load
`nope.plugins.hello` and plug it into `nope.dispatcher`, which results
in a new module that is actually `nope.dispatcher` extended by
our plugin (`nope.plugins.hello`).
>>> from nope import getLayer
>>> import nope.plugins as plugins
>>> nope_extended = plugins.load('hello', 'nope.dispatcher')
>>> manager = NopeRpcManager({
...     "communicator": await getLayer("event"),
...     "logger": False,
... }, lambda *args: "test", "test")
>>> manager.hello()
Hello from N
"""

import imp
import sys
import inspect
from functools import wraps

from nope.helpers import rsetattr

# apidoc skip


def update(module, objects):
    """Update a module content
    """
    for obj in objects:
        if isinstance(obj, tuple):
            try:
                n, o = obj
            except BaseException:
                raise ValueError("expected (name, object) and got '%r'" % obj)
            setattr(module, n, o)
        elif inspect.isclass(obj) or inspect.isfunction(obj):
            setattr(module, obj.__name__, obj)
        else:
            raise ValueError("cannot plug '%r'" % obj)


def load(lib, name:str, plugins, new_pkg_name: str = None):
    """Load plugins, `plugins` can be a single plugin name, a module
    or a list of such values. If `name` is not `None`, the extended
    module is loaded as `name` in `sys.modules` as well as in the
    global environment from which `load` was called.
    @param plugins: the module that implements the plugin, or its
        name, or a collection (eg, list, tuple) of such values
    @type plugins: `object`
    @param base: the module being extended or its name
    @type base: `object`
    @param name: the name of the created module
    @type name: `str`
    @return: the extended module
    @rtype: `module`
    """
    result = None
    mainLib = None
    mainLibName = None
    deltaPath = None

    if isinstance(lib, str):
        mainLibName = __import__(lib, fromlist=["__name__"])
    else:
        mainLib = lib

    deltaPath = ".".join(name.split(".")[1:])
    mainLibName = name.split(".")[0]


    if isinstance(name, str):
        
        result = __import__(name, fromlist=["__name__"])
    else:
        raise Exception("Please work with a for the module!")
    if isinstance(plugins, str):
        plugins = [plugins]
    else:
        try:
            plugins = list(plugins)
        except TypeError:
            plugins = [plugins]
    # The Following loops will ensure,
    # that we import the plugins.
    for i, p in enumerate(plugins):
        
        if isinstance(p, str) and not p.startswith("nope.plugins."):
            plugins[i] = "nope.plugins." + p
    for plug in plugins:
        if isinstance(plug, str):
            plug = __import__(plug, fromlist=["__name__"])
        
        # Now we need to 
        mainLib, result = plug.extend(mainLib, deltaPath, result)

    sys.modules[mainLibName] = mainLib
    
    if new_pkg_name is not None:
        result.__name__ = new_pkg_name
        sys.modules[new_pkg_name] = result
        inspect.stack()[1][0].f_globals[new_pkg_name] = result
        
    return mainLib


"""## Creating plugins ###
We show now how to develop a plugin that allows instances of
`PetriNet` to say hello: a new method `PetriNet.hello` is added and
the constructor `PetriNet.__init__` is added a keyword argument
`hello` for the message to print when calling method `hello`.
Defining a plugins required to write a module with a function called
`extend` that takes as its single argument the module to be extended.
Inside this function, extensions of the classes in the module are
defined as normal sub-classes. Function `extend` returns the extended
classes. A decorator called `plugin` must be used, it also allows to
resolve plugin dependencies and conflicts.
"""

# apidoc include "hello.py" lang="python"

"""Note that, when extending an existing method like `__init__` above,
we have to take care that you may be working on an already extended
class, consequently, we cannot know how its arguments have been
changed already. So, we must always use those from the unextended
method plus `**args`. Then, we remove from the latter what your plugin
needs and pass the remaining to the method of the base class if we
need to call it (which is usually the case). """


def plugin(base, depends=[], conflicts=[]):
    """ Decorator for extension functions
    @param base: name of base module (usually 'nope') that the
        plugin extends
    @type base: `str`
    @param depends: list of plugin names (as `str`) this one depends
        on, prefix `nope.plugins.` may be omitted
    @type depends: `list`
    @param conflicts: list of plugin names with which this one
        conflicts
    @type conflicts: `list`
    @return: the appropriate decorator
    @rtype: `decorator`
    """
    def wrapper(fun):
        @wraps(fun)
        def extend(mainModule, deltaPath, module):
            print(mainModule, module)
            try:
                loaded = set(module.__plugins__)
            except AttributeError:
                loaded = set()
            for name in depends:
                if name not in loaded:
                    module = load(name, module)
                    loaded.update(module.__plugins__)
            conf = set(conflicts) & loaded
            if len(conf) > 0:
                raise ValueError("plugin conflict (%s)" % ", ".join(conf))
            objects = fun(module)
            if not isinstance(objects, tuple):
                objects = (objects,)

            # Now we use the buid function to update the Module.
            adaptedModule = build(fun.__module__, module, *objects)

            # We now have to update the main lib.
            rsetattr(mainModule, deltaPath, adaptedModule, splitchar=".")

            return mainModule, adaptedModule
        module = sys.modules[fun.__module__]
        module.__test__ = {"extend": extend}
        objects = fun(__import__(base, fromlist=["__name__"]))
        if not isinstance(objects, tuple):
            objects = (objects,)
        update(module, objects)
        return extend
    return wrapper

# apidoc skip


def new_instance(cls, obj):
    """Create a copy of `obj` which is an instance of `cls`
    """
    result = object.__new__(cls)
    result.__dict__.update(obj.__dict__)
    return result

# apidoc skip


def build(name, module, *objects):
    """Builds an extended module.
    The parameter `module` is exactly that taken by the function
    `extend` of a plugin. This list argument `objects` holds all the
    objects, constructed in `extend`, that are extensions of objects
    from `module`. The resulting value should be returned by `extend`.
    @param name: the name of the constructed module
    @type name: `str`
    @param module: the extended module
    @type module: `module`
    @param objects: the sub-objects
    @type objects: each is a class object
    @return: the new module
    @rtype: `module`
    """
    result = imp.new_module(name)
    result.__dict__.update(module.__dict__)
    update(result, objects)
    result.__plugins__ = (module.__dict__.get("__plugins__",
                                              (module.__name__,))
                          + (name,))
    for obj in objects:
        if inspect.isclass(obj):
            obj.__plugins__ = result.__plugins__
    return result
