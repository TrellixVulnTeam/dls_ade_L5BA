#!/bin/env dls-python
# This script comes from the dls_scripts python module
"""
List the releases that have been made for a module in prod or on the repository.
Default epics version and rhel version are the set from you environment,
to specify different versions the epics version or rhel version flags can be used.
The git flag will list releases from the repository.
"""

import os
import sys
import shutil
import platform
import logging

from dls_ade.dls_environment import environment
from dls_ade.argument_parser import ArgParser
from dls_ade import path_functions as pathf
from dls_ade import vcs_git, Server

env = environment()
logging.basicConfig(level=logging.DEBUG)


usage = """
Default <area> is 'support'.

List the releases of <module_name> in the <area> area of prod or the repository if -g is true.
By default uses the epics release number from your environment to work out the area on disk to
look for the module, this can be overridden with the -e flag.
"""


def get_rhel_version():
    """
    Checks if platform is Linux redhat, if so returns base version number from
    environment (e.g. returns 6 if 6.7), if not returns default of 6.
    
    Returns:
        str: Rhel version number
    """

    default_rhel_version = "6"
    if platform.system() == 'Linux' and platform.dist()[0] == 'redhat':
        dist, release_str, name = platform.dist()
        release = release_str.split(".")[0]
        return release
    else:
        return default_rhel_version


def make_parser():
    """
    Takes ArgParse instance with default arguments and adds

    Positional Arguments:
        * module_name

    Flags:
        * -b (branch)
        * -l (latest)
        * -g (git)
        * -e (epics_version)
        * -r (rhel_version)

    Returns:
        :class:`argparse.ArgumentParser`:  ArgParse instance
    """

    parser = ArgParser(usage)
    parser.add_module_name_arg()
    parser.add_epics_version_flag()
    parser.add_git_flag(
        help_msg="Print releases available in git")

    parser.add_argument(
        "-l", "--latest", action="store_true", dest="latest",
        help="Only print the latest release")
    parser.add_argument(
        "-r", "--rhel_version", action="store", type=int, dest="rhel_version",
        default=get_rhel_version(),
        help="Change the rhel version of the environment, default is " +
             get_rhel_version() + " (from your system)")

    return parser


def main():

    parser = make_parser()
    args = parser.parse_args()

    env.check_epics_version(args.epics_version)
    pathf.check_technical_area(args.area, args.module_name)

    # Force check of repo, not file system, for tools, etc and epics
    # (previous releases are only stored on repo)
    if args.area in ["etc", "tools", "epics"]:
        args.git = True

    # Check for the existence of releases of this module/IOC    
    releases = []
    if args.git:

        server = Server()

        # List branches of repository
        target = "the repository"
        source = server.dev_module_path(args.module_name, args.area)

        vcs = server.temp_clone(source)
        releases = vcs_git.list_module_releases(vcs.repo)
        shutil.rmtree(vcs.repo.working_tree_dir)

    else:
        # List branches from prod
        target = "prod"
        source = env.prodArea(args.area)
        if args.area == 'python' and args.rhel_version >= 6:
            source = os.path.join(source,
                                  "RHEL{0}-{1}".format(args.rhel_version,
                                                       platform.machine()))
            logging.debug(source)
        release_dir = os.path.join(source, args.module_name)

        if os.path.isdir(release_dir):
            for p in os.listdir(release_dir):
                if os.path.isdir(os.path.join(release_dir, p)):
                    releases.append(p)

    # Check some releases have been made
    if len(releases) == 0:
        if args.git:
            print(args.module_name + ": No releases made in git")
        else:
            print(args.module_name + ": No releases made for " +
                  args.epics_version)
        return 1

    releases = env.sortReleases(releases)

    if args.latest:
        print("The latest release for " + args.module_name + " in " + target +
              " is: " + releases[-1])
    else:
        print("Previous releases for " + args.module_name + " in " +
              target + ":")
        for release in releases:
            print(release)

if __name__ == "__main__":
    sys.exit(main())