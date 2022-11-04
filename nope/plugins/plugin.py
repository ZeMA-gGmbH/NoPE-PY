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
>>> nope_extended = plugins.load('nope.plugins.hello', 'nope.dispatcher')
>>> manager = NopeRpcManager({
...     "communicator": await getLayer("event"),
...     "logger": False,
... }, lambda *args: "test", "test")
>>> manager.hello()
"Hello from the Plugin"
"""

import imp
import importlib
import inspect
import sys
from functools import wraps

from nope.logger import getNopeLogger, DEBUG

_LOGGER = getNopeLogger("plugin-system", DEBUG)

_PLUGIN_COUNTER = 0
_PLUGINS = dict()
_LOADED = list()


def _set(obj, accessor: str, value):
    """ Helper to set items.

    Args:
        obj: Object to manipulate
        accessor (str): The Attribute to change
        value (_type_): The value to use.
    """
    try:
        obj[accessor] = value
    except BaseException as E:
        try:
            setattr(obj, accessor, value)
        except BaseException as E:
            raise E


def _get(obj, accessor: str, prevent_to_load: str):
    ret = None
    additional_module = False
    try:
        ret = obj[accessor]
    except BaseException as E:
        try:
            ret = getattr(obj, accessor)
        except BaseException as E:
            raise E

    if inspect.isfunction(ret):
        # Wir haben eine funktion als attribute
        # D.h. damit wir die funktion manipulieren
        # können => wir müssen den definitions file
        # laden
        src = inspect.getsourcefile(ret)

        if src == prevent_to_load:
            # Wir laden unser addon.
            # Das wenn wir dies erneut laden ==>
            # wir können den File öfters.
            return ret, additional_module

        spec = importlib.util.spec_from_file_location(ret.__module__, src)
        ret = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ret)

        # Wir geben jetzt noch an, dass wir
        # ein zusätzl. modul manipulieren.
        additional_module = True

    return ret, additional_module


def _rsetattr(data, path: str, value, prevent_to_load: str):
    """ Function to Set recursely a Attribute of an Object/Module

    Args:
        data (any):  The Object, where the data should be stored
        path (str): The Path of the Attribute. All are seprated by a the "."
        value (any): The Value which should be Stored in the Attribute.
    """

    obj = data

    # Wir unterteilen den Pfad in segmente
    # Über diesen wercen wir im Anschluss iterieren
    # und auf die entsprechenden items zugreifen.
    ptrs = path.split(".")
    last_path_segment = ptrs[len(ptrs) - 1]

    # Helfer, die sicherstellen wenn funktionen geladen
    # werden, dass diese Anpassungen dabei auch erfolgen.
    loaded_extra = []

    # Schleife die über die einzlenen Segmente iteriert.
    for idx, accessor in enumerate(ptrs[0:-1]):

        # Wir bekommen das submodul. Wenn der accessor
        # eine "funktion" beinhaltet -> wird dynamisch
        # das modul geladen, welches die funktion enthält.
        # Diese wird dann über "loaded_module" angezeigt
        sub, loaded_module = _get(obj, accessor, prevent_to_load)

        if loaded_module:
            # Wenn wir dyn. das modul welches die funktion
            # definiert lädt, stellen wir sicher, dass dieses
            # modul die änderung erhalten wird. später nehmen
            # wir dann die neue definition der methode und weisen
            # sie dem aktuellen modul zu.
            loaded_extra.append((obj, accessor, sub))

        # Falls wir neue elemente Anlegen => erstelle ein dotted-dict.
        # darüber können wir dann darauf zugreifen.
        if sub is None:
            # Define a dict.
            _set(obj, accessor, dict())
            # Now extract the dict.
            sub = obj[accessor]
            _LOGGER.warn(
                "Watchout. You are using the plugin-system. The code reached an untested code-sections. Please contact m.karkowski@zema.de")

        # Nun gehen wir mit dem nächsten segment des pfades
        # genau so vor.
        obj = sub

    # Wir haben unser ziel erreicht und weisen nur noch
    # das element zu.
    _set(obj, last_path_segment, value)

    # Falls wir funktionen geändert haben nehmen wir dann die neue
    # definition der methode und weisen sie den aktuellen modulen zu.
    # Sicherheitshalber machen wir dies in negativer reihenfolge.
    for o, a, v in reversed(loaded_extra):
        _set(o, a, getattr(v, a))


def _update(module, objects):
    """ Update the module based on the given adapted items. This might be

    Args:
        module: The module to update.
        objects: The changed elements.

    Raises:
        ValueError: If we cannot extend the behavior.
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
        elif isinstance(obj, dict):
            for k, v in obj.items():
                setattr(module, k, v)
        else:
            raise ValueError("cannot plug '%r'" % obj)


def _getOccurence(lib, lib_name: str, occurence=None, orignal_srcs=None, refs=None, func=False,
                  pre_path: str = "", max_recursion=100, current_depth=0):
    """ Goal of this function is to determine the occurence of the all items, provided in the lib.

    Args:
        lib (_type_): _description_
        ret (_type_, optional): _description_. Defaults to None.
        pre_path (str, optional): _description_. Defaults to "".

    Returns:
        _type_: _description_
    """
    if occurence is None:
        occurence = dict()
    if orignal_srcs is None:
        orignal_srcs = dict()
    if refs is None:
        refs = dict()

    if current_depth > max_recursion:
        raise Exception(
            "Max Recursion reached. Propably you import the package inside of a subpackage!")

    path_segment = pre_path + "." if pre_path else ""
    libName = lib.name if hasattr(lib, "name") else lib.__name__

    # The trick to determine if we only reexport the original stuff,
    # is to check the lib name and the path:
    if pre_path and lib_name + "." + pre_path != libName and not func:
        # We mark the item as reexport.
        refs[lib_name + "." + pre_path] = libName
    elif func:
        pass

    if not libName.startswith(lib_name):
        return occurence, orignal_srcs, refs

    l = inspect.getmembers(lib)

    for name, obj in inspect.getmembers(lib):

        if name == "getTimestamp":
            pass

        if name.startswith("_"):
            continue

        elif inspect.ismodule(obj) or inspect.isfunction(obj):

            obj_to_use = obj
            _is_func = False

            if inspect.isfunction(obj) and obj.__module__.startswith(lib_name):

                if obj.__module__ != libName:

                    # Magic:
                    # Wenn wir mit einer funktion arbeiten ->
                    # dann müssen wir das dazu gehörige module laden
                    # in dem die funktion definiert wird.

                    # Dies ist aber nur erforderlich, falls wir nicht
                    # schon das selbe modul betrachten, ansonsten werden
                    # die darin definierten Funktionen erkannt und das modul
                    # wieder geladen --> Endlos schleife. (Dies fangen wir
                    # über die If-condition ab)

                    src = inspect.getsourcefile(obj)
                    spec = importlib.util.spec_from_file_location(
                        obj.__module__, src)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)

                    # Das modul ist nun geladen -> wir werden dieses
                    # analysieren.
                    obj_to_use = mod

                    _is_func = True

                else:
                    # Wir haben das modul schon offen -> Vergesse es.
                    obj_to_use = False

                # Wir speichern noch das vorkommen der Nutzung.
                if name not in occurence:
                    occurence[name] = set()
                occurence[name].add(pre_path)

                # Wir stellen zudem sicher, dass wir das original gespeicher
                # haben.
                orignal_srcs[name] = obj.__module__

            if not obj_to_use or inspect.isbuiltin(obj_to_use):
                # Falls es sich um ein builtin handel oder
                # wir vorher gesagt haben dass das modul
                # uninteressant ist --> Wir skippen den nächsten
                # schritt
                continue
            try:
                src = inspect.getsourcefile(obj_to_use)

                if lib_name not in src:
                    # Mit dieser Funktion fangen wir
                    # andere Libraries ab, die wir hier
                    # nicht betrachten wollen
                    continue

                # Wir haben nun eine relevante library analysiere diese
                # rekursiv.
                occurence, orignal_srcs, refs = _getOccurence(
                    obj_to_use,
                    lib_name,
                    occurence,
                    orignal_srcs,
                    refs,
                    _is_func,
                    path_segment + name,
                    max_recursion,
                    current_depth + 1
                )
            except BaseException:
                # Wenn dabei was schief läuft
                # logge den error.
                pass

        else:
            if name not in occurence:
                occurence[name] = set()
            occurence[name].add(pre_path)

            if inspect.isclass(obj) or inspect.isfunction(obj):
                orignal_srcs[name] = obj.__module__

    return occurence, orignal_srcs, refs


def _getPluginInfo(plugin):
    if isinstance(plugin, str):
        plugin = __import__(plugin, fromlist=["__name__"])

    return plugin.name, plugin.base, plugin.depends, plugin.conflicts


def install(lib, plugins, new_pkg_name: str = None):
    """ installiert ein Plugin in der Library.

    Args:
        lib (module): Die Library die betrachtet wird
        plugins (str | list<str> | func | list<func>): Die Plugins die geladen werden sollen. Siehe Beispiele.
        new_pkg_name (str, optional): Name unterdem das Update gespeicher werden soll (nur partial die Änderung). Defaults to None.

    Returns:
        (module, list(str), list(str)): Die angepasste lib (Inline edit -> wird nicht benötigt), Liste mit geupdaten Referenzen, Liste mir dem originalen Elementen.
    """
    # Damit wir nicht unseren eigene datei laden,
    # extrahieren wir diese.
    prevent_to_load = inspect.stack()[1].filename

    _LOGGER.info(f"Using plugin installed started at '{prevent_to_load}'")

    # Nun laden wir das main module was wir anpassen werden.
    if isinstance(lib, str):
        mainModule = __import__(lib, fromlist=["__name__"])
    else:
        mainModule = lib

    mainModuleName = mainModule.__name__

    # Wir ermitteln das Auftreten aller Klassen.
    occourenceDict, srcs, refs = _getOccurence(mainModule, mainModuleName)

    plugins_to_use = []
    to_be_plugged = dict()

    # Wir stellen sicher, dass wir immer eine liste von Plugins
    # betrachten.
    if not isinstance(plugins, (list, tuple)):
        plugins = [plugins]

    # In dieser schleife stellen wir sicher, dass wir immer
    # die funktion des Plugin ladens und später verwenden.
    for plugin in plugins:
        if isinstance(plugin, str):
            if plugin not in _PLUGINS:
                # Unser Plugin muss "nachgeladen werden"
                plugin = __import__(plugin, fromlist=["__name__"])

        # Basierend auf dem Typ (dynamisch / statisch)
        # speichern wir das Plugin / die Methode.
        if hasattr(plugin, "extend"):
            plugin = plugin.extend

        if not inspect.isfunction(plugin):
            raise Exception("Failed to load the Plugin")

        # Wir speicher das Plugin.
        plugins_to_use.append(plugin)

    rpr_start = "Plugins used!\n\n" + "-" * 50 + "\nPLUGIN INSTALLTION REPORT:\n" + \
        "-" * 50 + \
        f"\n\nInstalled the following plugins in '{mainModuleName}':"
    rpr_bases = "\n\nThe following source have been modified:"
    rpr_plugins = ""
    rpr_end = f"\n\nReturning modified library '{mainModuleName}'. Watchout this may change the default behavior of '{mainModuleName}'!"

    # In dieser schleife ermitteln wir nun, welche
    # Basis module für die Plugins benötigt werden.
    # Dazu unterscheiden wir in einfache Strings
    # und listen. Je nachdem laden wir die Basis module
    # und speichern diese in "to_be_plugged"
    for plugin in plugins_to_use:
        if isinstance(plugin.base, str):
            if plugin.base not in to_be_plugged:
                to_be_plugged[plugin.base] = __import__(
                    plugin.base, fromlist=["__name__"])

                rpr_plugins += f"\n\t- {plugin.name}"
                rpr_bases += f"\n\t- {plugin.base}"

            # Sicherstellen, dass wir mit einer Liste arbeiten
            plugin.base = [plugin.base]

        elif isinstance(plugin.base, (list, tuple)):
            for item in plugin.base:
                if item not in to_be_plugged:
                    to_be_plugged[item] = __import__(
                        item, fromlist=["__name__"])

                    for base in plugin.base:
                        rpr_bases += f"\n\t- {base}"
                    rpr_plugins += f"\n\t- {plugin.name}"

    changes = dict()

    # In dieser schleife nehmen wir nun die plugins und wenden diese an.
    # Durch die Anwendung dieser in einer schleife können wir verschiedene
    # Plugins kombinieren.
    for plugin in plugins_to_use:

        modules = [to_be_plugged[item] for item in plugin.base]

        mainModule, adapted_modules, changes = plugin(
            mainModule, modules, changes)

        # Jetzt spiegeln wir die Änderungen zurück in die module.
        for idx, item in enumerate(plugin.base):
            to_be_plugged[item] = adapted_modules[idx]

    updated = []
    skipped = []

    for module, changed in changes.items():

        # Wir speichern noch den Namen des originalen Element
        # Dieses darf NICHT überschrieben werden, das sonst die
        # Vererbung nicht klappt.
        destPath = module.__name__

        # Nun wissen wir was sich geändert hat und wir müssen diese
        # Änderungen im Modul implementieren:
        for name, adapted in changed.items():

            if name not in srcs:
                # Das Element ist noch nicht vorhanden (bspw. eine neue funktion)
                # daher definieren wir einen Namen zum zuweisen der Variable.
                set_path = name

                if destPath != mainModuleName:
                    set_path = destPath[len(mainModuleName) + 1:] + "." + name

                _rsetattr(mainModule, set_path, adapted, prevent_to_load)

            else:
                # We are adding an alread existing item.
                occourence = occourenceDict.get(name, set())

                for path in occourence:
                    path_to_use = mainModuleName + "." + path if path else mainModuleName
                    set_path = path + "." + name if path else name

                    # if we working with a reference like here:
                    # we skip adapting the item:
                    if path_to_use in refs:
                        skipped.append(set_path)
                        continue
                    # We have to maintain the original item.
                    elif name in srcs and path_to_use == srcs[name]:
                        skipped.append(set_path)
                        continue
                    # We already updated our destination. we dont need that.
                    # otherwise we cannot access updated plugins.
                    elif destPath == path_to_use:
                        skipped.append(set_path)
                        continue

                    # We now update the lib item.
                    _rsetattr(mainModule, set_path, adapted, prevent_to_load)
                    updated.append(set_path)

    sys.modules[mainModuleName] = mainModule

    if new_pkg_name is not None:
        to_be_plugged.__name__ = new_pkg_name
        sys.modules[new_pkg_name] = to_be_plugged
        inspect.stack()[1][0].f_globals[new_pkg_name] = to_be_plugged

    _LOGGER.warn(rpr_start + rpr_plugins + rpr_bases + rpr_end)

    return mainModule, updated, skipped


def plugin(base, name: str = None, depends=[], conflicts=[]):
    """ Helper to create a plugin. Used as decorator for the extending function.

        The base defines the bases of the module.
    Args:
        base (str, list<str>): The base that has to be adapted.
        depends (list, optional): Dependencies. Defaults to [].
        conflicts (list, optional): Conflicts. Defaults to [].
    """

    def wrapper(fun):
        @wraps(fun)
        def extend(mainModule, modules: list, changes: dict):
            try:
                loaded = set(modules.__plugins__)
            except AttributeError:
                loaded = set()
            for name in depends:
                if name not in loaded:
                    modules = install(name, modules)
                    loaded.update(modules.__plugins__)

            conf = set(conflicts) & loaded
            if len(conf) > 0:
                raise ValueError("plugin conflict (%s)" % ", ".join(conf))

            # Aufrufen des eigentlichen Plugins.
            adaptions = fun(*modules)

            if len(modules) == 1:
                adaptions = [adaptions]

            if len(modules) > 1 and len(adaptions) != len(modules):
                raise Exception(
                    "Can not assign the adaped items. Please make shure you are providing the correct length!")

            adapted_modules = list()

            for idx, changes_per_module in enumerate(adaptions):

                module = modules[idx]

                if module not in changes:
                    changes[module] = dict()

                if not isinstance(changes_per_module, (tuple, list)):
                    changes_per_module = [changes_per_module]

                for obj in changes_per_module:

                    if inspect.isclass(obj) or inspect.isfunction(obj):
                        if obj.__name__ in changes[module]:
                            raise Exception("Adapted name used twice")
                        changes[module][obj.__name__] = obj
                    elif isinstance(obj, dict):
                        for varname, v in obj.items():
                            if varname in changes[module]:
                                raise Exception("Adapted name used twice")
                            changes[module][varname] = v

                changes[module].update()

                adapted_modules.append(
                    _build(
                        fun.__module__,
                        module,
                        *changes_per_module))

            return mainModule, adapted_modules, changes

        module = sys.modules[fun.__module__]
        module.__test__ = {"extend": extend}

        extend.base = base
        extend.depends = depends
        extend.conflicts = conflicts
        extend.name = name

        # We will define a custom Pluginname if required.
        if extend.name is None:
            global _PLUGIN_COUNTER
            extend.name = f"anymousPlugin{_PLUGIN_COUNTER}@{inspect.getsourcefile(inspect.stack()[1][0])}"
            _PLUGIN_COUNTER += 1
        else:
            _PLUGINS[extend.__name__] = extend

        _PLUGINS[extend] = extend

        return extend

    return wrapper


def _build(name, module, *objects):
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
    _update(result, objects)
    result.__plugins__ = (module.__dict__.get("__plugins__",
                                              (module.__name__,))
                          + (name,))
    for obj in objects:
        if inspect.isclass(obj):
            obj.__plugins__ = result.__plugins__
    return result
