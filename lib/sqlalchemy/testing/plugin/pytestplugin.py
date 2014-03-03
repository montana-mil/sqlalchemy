import pytest
import argparse
import inspect
py_unittest = None
from . import plugin_base

def pytest_addoption(parser):
    group = parser.getgroup("sqlalchemy")

    def make_option(name, **kw):
        callback_ = kw.pop("callback", None)
        if callback_:
            class CallableAction(argparse.Action):
                def __call__(self, parser, namespace, values, option_string=None):
                    callback_(option_string, values, parser)
            kw["action"] = CallableAction

        group.addoption(name, **kw)

    plugin_base.setup_options(make_option)
    plugin_base.read_config()

def pytest_configure(config):
    plugin_base.pre_begin(config.option)
    plugin_base.post_begin()

    # because it feels icky importing from "_pytest"..
    global py_unittest
    py_unittest = config.pluginmanager.getplugin('unittest')


def pytest_pycollect_makeitem(collector, name, obj):
    if inspect.isclass(obj) and plugin_base.want_class(obj):
        return [
            py_unittest.UnitTestCase(sub_obj.__name__, parent=collector)
            for sub_obj in plugin_base.generate_sub_tests(obj, collector.module)
        ]

_current_class = None

from pytest import Item
def pytest_runtest_setup(item):
    # I'd like to get module/class/test level calls here
    # but I don't quite see the pattern.

    # not really sure what determines if we're called
    # here with pytest.Class, pytest.Module, does not seem to be
    # consistent

    global _current_class

    # ... so we're doing a little dance here to figure it out...
    if item.parent is not _current_class:

        class_setup(item.parent)
        _current_class = item.parent
        item.parent.addfinalizer(lambda: class_teardown(item.parent))

    item.addfinalizer(lambda: test_teardown(item))
    test_setup(item)

def test_setup(item):
    id_ = "%s.%s:%s" % (item.parent.module.__name__, item.parent.name, item.name)
    plugin_base.before_test(item, id_)

def test_teardown(item):
    plugin_base.after_test(item)

def class_setup(item):
    try:
        plugin_base.start_test_class(item.cls)
    except plugin_base.GenericSkip as gs:
        print(gs.message)
        pytest.skip(gs.message)

def class_teardown(item):
    plugin_base.stop_test_class(item.cls)
