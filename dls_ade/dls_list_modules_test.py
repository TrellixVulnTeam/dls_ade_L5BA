#!/bin/env dls-python

from __future__ import print_function
from sys import version_info
if version_info.major == 2:
    import __builtin__ as builtins  # Allows for Python 2/3 compatibility, 'builtins' is namespace for inbuilt functions
else:
    import builtins

import unittest
from pkg_resources import require
require("mock")
from mock import patch, ANY, MagicMock

p = patch('dls_ade.Server')
server_mock = MagicMock()
m = p.start()
m.return_value = server_mock
from dls_ade import dls_list_modules
p.stop()


class ParserTest(unittest.TestCase):

    def setUp(self):
        self.parser = dls_list_modules.make_parser()

    def test_domain_name_has_correct_attributes(self):
        arguments = self.parser._positionals._actions[4]
        self.assertEqual(arguments.type, str)
        self.assertEqual(arguments.dest, 'domain_name')


class PrintModuleListTest(unittest.TestCase):

    def setUp(self):
        self.server_mock = server_mock

    def tearDown(self):
        self.server_mock.reset_mock()

    def test_server_repo_list_called(self):
        source = "test/source"

        dls_list_modules.print_module_list(source)

        self.server_mock.get_server_repo_list.assert_called_once_with()

    def test_given_valid_source_then_print_called(self):
        self.server_mock.get_server_repo_list.return_value =\
            ["test/source/module", "test/source2/module2"]

        source = "test/source"

        with patch.object(builtins, 'print') as mock_print:
            dls_list_modules.print_module_list(source)

        call_args = mock_print.call_args_list
        self.assertEqual(call_args[0][0][0], 'module')
        # Check that module2 from source2 is not printed
        self.assertEqual(len(call_args), 1)

    def test_given_invalid_source_then_print_not_called(self):
        self.server_mock.get_server_repo_list.return_value = \
            ["test/not_source/module"]

        source = "test/source"

        with patch.object(builtins, 'print') as mock_print:
            dls_list_modules.print_module_list(source)

        self.assertFalse(mock_print.call_count)