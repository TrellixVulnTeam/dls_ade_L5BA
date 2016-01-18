#! /bin/env dls-python
from __future__ import print_function
import os
import subprocess
import tempfile
import shutil
from pkg_resources import require
require('nose')
from nose.tools import assert_equal, assert_true, assert_false


# Make sure env var is set.(PYTHONPATH must also be set, but cannot
# easily test it is correct)
try:
    os.environ['GIT_ROOT_DIR']
except KeyError:
    raise EnvironmentError("GIT_ROOT_DIR must be set")

try:
    from dls_ade import vcs_git
except ImportError:
    vcs_git = None
    raise ImportError("PYTHONPATH must contain the dls_ade package")


class Error(Exception):
    """Class for exceptions relating to systems_testing module."""
    pass


def get_input(message):
    """Get input from the user with the given message.

    Args:
        message: The message to be shown to the user.

    Returns:
        str: The raw input given by the user.

    """
    return raw_input(message)


def get_local_temp_clone(server_repo_path):
    """Obtain the root directory for a temporary clone of the given repository.

    Args:
        server_repo_path: The repository path for the server.

    Returns:
        str: The root directory of the cloned server repository.
            This will always be located in a temporary folder.

    Raises:
        vcs_git.Error: From vcs_git.temp_clone.

    """
    repo = vcs_git.temp_clone(server_repo_path)

    tempdir = repo.working_tree_dir

    return tempdir


def delete_temp_repo(local_repo_path):
    """Delete a repository in a temporary directory.

    Args:
        local_repo_path: The path to the temporary directory.

    Raises:
        Error: If the path given is not a temporary folder.
        Error: If the path given is not for a git repository.

    """
    if not os.path.realpath(local_repo_path).startswith(tempfile.gettempdir()):
        err_message = ("{local_repo_path:s} is not a temporary folder, cannot "
                       "delete.")
        raise Error(err_message.format(local_repo_path=local_repo_path))

    if not vcs_git.is_git_root_dir(local_repo_path):
        err_message = ("{local_repo_path:s} is not a git root directory, "
                       "cannot delete.")
        raise Error(err_message.format(local_repo_path=local_repo_path))

    shutil.rmtree(local_repo_path)


def check_if_folders_equal(path_1, path_2):
    """Check if the two local paths given are equivalent.

    This involves all files and folders (plus names) being identical. The
    names of the folders themselves are ignored.

    Args:
        path_1: The first path for comparison.
        path_2: The second path for comparison.

    Returns:
        bool: True if the directories are equal, False otherwise.

    Raises:
        Error: If either of the two paths are blank.

    """
    if not (path_1 and path_2):
        err_message = ("Two paths must be given to compare folders.\n"
                       "path 1: {path_1:s}, path 2: {path_2:s}.")
        raise Error(err_message.format(path_1=path_1, path_2=path_2))

    command_format = "diff -rq {path1:s} {path2:s}"
    call_args = command_format.format(path1=path_1, path2=path_2).split()

    out = subprocess.check_output(call_args)

    return not out


class SystemsTest(object):
    """Class for the automatic generation of systems tests using nosetests.

    Attributes:
        _script: The script to be tested.
        description: The test description as used by nosetests.

        _std_out: The standard output of the script called.
        _std_err: The standard error of the script called.
        _return_code: The return code of the script called.

        _server_repo_clone_path: The path to a clone of the server repo.

        _exception_type: The exception type to test for in standard error.
        _exception_string: The exception string to test for in standard error.
        _std_out_compare_string: The string for standard output comparisons.
        _arguments: A string containing the arguments for the given script.
        _attributes_dict: A dictionary of all git attributes to check for.

        _local_repo_path: A local path, used for attribute checking.

        _local_comp_path_one: A local path used for directory comparisons.
        _local_comp_path_two: A local path used for directory comparisons.

        _server_repo_path: The remote repository path.
            This is used for both git attribute checking as well as directory
            comparisons (after being cloned to _server_repo_clone_path)

    Raises:
        Error: Indicates error in this class or in the settings dict.
        vcs_git.Error: Indicates error in this class or in the settings dict.
        AssertionError: Indicates a failure of the script being tested.

    """

    def __init__(self, script, description):
        """Initialises attributes."""
        self._script = script
        self.description = description

        self._std_out = ""
        self._std_err = ""
        self._return_code = None

        # Used for attribute checking and comparisons
        self._server_repo_clone_path = ""

        self._exception_type = ""
        self._exception_string = ""
        self._std_out_compare_method = ""
        """string: Specifies the mechanism ny which the standard out is tested.
        This can be either 'string_comp' to test _std_out against
        _std_out_compare_string or 'manual_comp' to get a printed output of the
        script for the user to manually compare with."""

        self._std_out_compare_string = ""
        self._arguments = ""
        self._attributes_dict = {}

        # Used for attribute checking
        self._local_repo_path = ""

        # Used for comparisons
        self._repo_comp_method = ""
        """string: Specifies the mechanism ny which the standard out is tested.
        This can be: 'local_comp' to test _local_comp_path_one against
        _local_comp_path_two. 'server_comp' to test _local_comp_path_one
        against _server_repo_clone_path (cloned from _server_repo_path) or
        'all_comp' to compare all three paths against each other."""

        self._local_comp_path_one = ""
        self._local_comp_path_two = ""

        # Used for attribute checking and comparisons
        self._server_repo_path = ""
        """The remote repository path.
        This is used for both git attribute checking as well as directory
        comparisons (after being cloned to _server_repo_clone_path)"""

        self._settings_list = [  # List of valid variables to update.
            'exception_type',
            'exception_string',
            'std_out_compare_method',
            'std_out_compare_string',
            'arguments',
            'attributes_dict',
            'server_repo_path'
            'local_repo_path'
            'repo_comp_method'
            'local_comp_path_one'
            'local_comp_path_two'
        ]
        """A list of all attributes that may be changed.
        This is done by the settings dictionary passed to load_settings."""

    def load_settings(self, settings):
        """Loads the given settings dictionary into the relevant variables.

        Note: This will only load the following variables:
            - exception_type
            - exception_string
            - std_out_compare_method
            - std_out_compare_string
            - arguments
            - attributes_dict
            - server_repo_path
            - local_repo_path
            - repo_comp_method
            - local_comp_path_one
            - local_comp_path_two

        """
        self.__dict__.update({("_" + key): value for (key, value)
                              in settings.items()
                              if key in self._settings_list})

    def setup(self):
        """Performs any setup routine required.
        """
        pass

    def call_script(self):
        """Call the script and store output, error and return code.
        """
        call_args = (self._script + " " + self._arguments).split()

        # It appears that we cannot use 'higher-level' subprocess functions,
        # eg. check_output here. This is because stderr cannot be obtained
        # separately to stdout in these functions.
        process = subprocess.Popen(call_args, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)

        self._std_out, self._std_err = process.communicate()

        self._return_code = process.returncode

    def check_std_err_for_exception(self):
        """Check the standard error for the exception information.

        Raises:
            Error: If either the exception type or string is blank.
            AssertionError: If the test does not pass.

        """
        if not self._exception_type or not self._exception_string:
            if not self._exception_type and not self._exception_string:
                return
            raise Error("Both exception_type and exception_string must "
                        "be provided.")

        assert_false(self._return_code == 0)

        expected_string = "\n{exc_t:s}: {exc_s:s}\n"
        expected_string = expected_string.format(exc_t=self._exception_type,
                                                 exc_s=self._exception_string)

        assert_true(self._std_err.endswith(expected_string))

    def compare_std_out_to_string(self):
        """Compare the standard output to std_out_compare_string.

        Raises:
            Error: If the comparison string is not provided.
            AssertionError: If the test does not pass.

        """
        if not self._std_out_compare_string:
            raise Error("A std_out comparison string must be provided.")

        assert_equal(self._std_out, self._std_out_compare_string)

    def compare_std_out_manually(self):
        """Compare the standard output with the correct value manually.

        Raises:
            AssertionError: If the test does not pass.
                This triggers if the user presses anything but 'y' or 'Y'.

        """
        print("The following content is the direct output of the script:\n")
        print(self._std_out)
        response = get_input("Does this match the expected output? (y/n)")

        assert_true(response.lower() == "y")

    def check_remote_repo_exists(self):
        """Check that the server_repo_path exists on the server.

        Raises:
            AssertionError: If the test does not pass.

        """
        assert_true(vcs_git.is_repo_path(self._server_repo_path))

    def clone_server_repo(self):
        """Clone the server_repo_path to a temp dir and return the path.

        Raises:
            vcs_git.Error: From vcs_git.temp_clone()
        """
        repo = vcs_git.temp_clone(self._server_repo_path)
        self._server_repo_clone_path = repo.working_tree_dir

    def run_git_attributes_tests(self):
        """Perform the git attributes tests.

        Raises:
            AssertionError: If the test does not pass.

        """
        if not self._attributes_dict:
            return

        if self._server_repo_clone_path:
            return_value = vcs_git.check_git_attributes(
                    self._server_repo_clone_path,
                    self._attributes_dict
            )
            assert_true(return_value)

        if self._local_repo_path:
            return_value = vcs_git.check_git_attributes(self._local_repo_path,
                                                        self._attributes_dict)
            assert_true(return_value)

    def run_comparison_tests(self):
        """Run the local path comparison tests.

        The repo_comp_method must be one of the following:
            - local_comp: compares the two local paths, named with
            local_comp_path_one and local_comp_path_two.
            - server_comp: compares local_comp_path_one with the
            server_repo_clone_path.
            - all_comp: compares all three paths against one another.

        Raises:
            Error: From check_if_folders_equal
            Error: If the repo_comp_method has an unexpected value.
            AssertionError: If the test does not pass.

        """
        if not self._repo_comp_method:
            return

        if self._repo_comp_method == "local_comp":
            equal = check_if_folders_equal(self._local_comp_path_one,
                                           self._local_comp_path_two)
            assert_true(equal)

        elif self._repo_comp_method == "server_comp":
            equal = check_if_folders_equal(self._local_comp_path_one,
                                           self._server_repo_clone_path)
            assert_true(equal)

        elif self._repo_comp_method == "all_comp":
            equal_1 = check_if_folders_equal(self._local_comp_path_one,
                                             self._local_comp_path_two)
            equal_2 = check_if_folders_equal(self._local_comp_path_one,
                                             self._server_repo_clone_path)
            assert_true(equal_1 and equal_2)

        else:
            err_message = ("The repo_comp_method must be called using one of "
                           "the following:"
                           "\nlocal_comp, server_comp, all_comp."
                           "\nCurrently got: {repo_comp_method:s}")
            raise Error(err_message.format(
                    repo_comp_method=self._repo_comp_method)
            )

    def check_std_out_and_exceptions(self):
        """Performs all the standard out and error comparisons.

        This includes exception testing.

        Raises:
            Error: From the comparison tests.
            AssertionError: From the comparison tests.
            vcs_git.Error: From the comparison tests.

        """
        self.check_std_err_for_exception()

        if self._std_out_compare_method == "string_comp":
            self.compare_std_out_to_string()
        elif self._std_out_compare_method == "manual_comp":
            self.compare_std_out_manually()

    def run_tests(self):
        """Performs the entire test suite.

        Raises:
            Error: From the tests.
            AssertionError: From the tests.
            vcs_git.Error: From the tests.

        """
        self.check_std_out_and_exceptions()

        if not self._server_repo_path:
            self.check_remote_repo_exists()

            self.clone_server_repo()
            # And adds path to server_clone_path.

        self.run_git_attributes_tests()
        # This should check local_repo and server_repo_path for attributes_dict

        self.run_comparison_tests()
        # Filesystem equality checks

    def __call__(self):
        """Defined for the use of nosetests.

        This is considered the test function.

        Raises:
            Error: From run_tests().
            AssertionError: From run_tests().
            vcs_git.Error: From run_tests().

        """
        raise Error("Remove when script fully tested")
        self.setup()
        self.call_script()
        self.run_tests()


def generate_tests_from_dicts(script, systems_test_cls, test_settings):
    """Generator for the automatic construction of systems tests.

    Args:
        script: The script for testing.
        systems_test_cls: The SystemsTest class (or subclass) to use.
        test_settings: The settings for each individual test.

    """
    for settings in test_settings:
        if 'script' in settings:
            script = settings.pop('script')
        description = settings.pop('description')
        systems_test = systems_test_cls(script, description)
        systems_test.load_settings(settings)
        yield systems_test
