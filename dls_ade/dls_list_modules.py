#!/bin/env dls-python
# This script comes from the dls_scripts python module
"""
List the modules of an area or ioc domain on the repository
"""

from __future__ import print_function
import sys
from dls_ade.argument_parser import ArgParser
from dls_ade import path_functions as pathf
from dls_ade import vcs_git
usage = """
Default <area> is 'support'.
List all modules in the <area> area.
If <dom_name> given and <area> = 'ioc', list the subdirectories of <dom_name>.
e.g. %prog -p prints: converter, cothread, dls_nsga, etc.
"""


def make_parser():
    """
    Takes ArgParse instance with default arguments and adds

    Flags:
        * -d (domain) :class:`argparse.ArgumentParser`

    Returns:
        :class:`argparse.ArgumentParser`: Parser instance
    """
    parser = ArgParser(usage)
    parser.add_argument("-d", "--domain", action="store",
                        type=str, dest="domain_name",
                        help="domain of ioc to list")
    return parser


def print_module_list(source, area):
    """
    Prints the modules in the area of the repository specified by source.

    Args:
        source(str): Suffix of URL to list from
        area(str): Area of repository to list

    """
    split_list = vcs_git.get_server_repo_list()
    print("Modules in " + area + ":\n")
    for module_path in split_list:
        if module_path.startswith(source + '/'):
            # Split module path by slashes twice and print what remains after that, i.e. after 'controls/<area>/'
            print(module_path.split('/', 2)[-1])


def main():

    parser = make_parser()
    args = parser.parse_args()
    
    if args.area == "ioc" and args.domain_name:
        source = pathf.dev_module_path(args.domain_name, args.area)
    else:
        source = pathf.dev_area_path(args.area)

    print_module_list(source, args.area)


if __name__ == "__main__":
    sys.exit(main())
