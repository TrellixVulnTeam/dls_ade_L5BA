#!/bin/env dls-python
# This script comes from the dls_scripts python module

import os
import sys
from argument_parser import ArgParser
from dls_environment import environment
import path_functions as pathf
import vcs_git
import logging

logging.basicConfig(level=logging.DEBUG)

usage = """
Default <area> is 'support'.
Print all the log messages for module <module_name> in the <area> area of svn
from the revision number when <earlier_release> was done, to the revision
when <later_release> was done. If not specified, <earlier_release> defaults to
revision 0, and <later_release> defaults to the head revision. If
<earlier_release> is given an invalid value (like 'latest') if will be set
to the latest release.
"""

BLUE = 34
CYAN = 36
GREEN = 32


def make_parser():

    parser = ArgParser(usage)
    parser.add_argument(
        "module_name", type=str, default=None,
        help="name of module")
    parser.add_argument(
        "earlier_release", type=str, default='0',
        help="start point of log messages")
    parser.add_argument(
        "later_release", type=str, default='1',
        help="end point of log messages")
    parser.add_argument(
        "-v", "--verbose", action="store_true", dest="verbose",
        help="Print lots of log information")
    parser.add_argument(
        "-r", "--raw", action="store_true", dest="raw",
        help="Print raw text (not in colour)")

    return parser


def check_technical_area_valid(args, parser):

    if args.area == "ioc" and not len(args.module_name.split('/')) > 1:
        parser.error("Missing Technical Area Under Beamline")


def colour(word, col, raw):
    if raw:
        return word
    # >>> I have just hard coded the char conversion of %27c in, as I couldn't find the
    # .format equivalent of %c, is anything wrong with this?
    return '\x1b[{col}m{word}\x1b[0m'.format(col=col, word=word)


def create_release_list(repo):

    release_list = []
    for tag in repo.tags:
        release_list.append(str(tag))
    return release_list


def format_message_width(message, line_len):

    if not isinstance(message, list):
        message = [message]
    for i, part in enumerate(message):
        if len(message[i]) > line_len:
            # Find first ' ' before line_len cut-off
            line_end = line_len - message[i][line_len::-1].find(' ')
            # Append second section to separate list entry
            if ' ' in message[i][line_len::-1]:
                # +1 -> without ' '
                message.insert(i+1, message[i][line_end+1:])
            else:
                # Keep string as is if there are no spaces (e.g. long file paths)
                message.insert(i+1, message[i][line_end:])
            # Keep section before cut-off
            message[i] = message[i][:line_end]

    return message


def main():

    parser = make_parser()
    args = parser.parse_args()
    e = environment()

    test_list = e.sortReleases([args.earlier_release, args.later_release])
    if args.later_release == test_list[0] and args.later_release != 'HEAD':
        parser.error("<later_release> must be more recent than <earlier_release>")

    check_technical_area_valid(args, parser)

    # don't write coloured text if args.raw
    if args.raw or \
            (not args.raw and (not sys.stdout.isatty() or os.getenv("TERM") is None or os.getenv("TERM") == "dumb")):
        raw = True
    else:
        raw = False

    source = pathf.devModule(args.module_name, args.area)
    if vcs_git.is_repo_path(source):
        # Get the list of releases from the repo
        if os.path.isdir('./' + args.module_name):
            repo = vcs_git.git.Repo(args.module_name)
            releases = create_release_list(repo)
        else:
            # >>> Use temp_clone once merged
            # repo = vcs_git.temp_clone(source, module)
            vcs_git.clone(source, args.module_name)
            repo = vcs_git.git.Repo(args.module_name)
            # <<<
            releases = create_release_list(repo)

        logging.debug(releases)

        if args.earlier_release in releases:
            start = args.earlier_release
        else:
            parser.error("Module " + args.module_name + " does not have a release " + args.earlier_release)
        if args.later_release in releases or args.later_release == 'HEAD':
            end = args.later_release
        else:
            parser.error("Module " + args.module_name + " does not have a release " + args.later_release)
    else:
        parser.error("Module " + args.module_name + " doesn't exist in " + source)

    # Get logs between start and end releases in a custom format
    # %h: commit hash, %aD: author date, %cn: committer name, %n: line space, %s: commit message subject,
    # >>> %b: commit message body
    logs = repo.git.log(start + ".." + end, "--format=%h %aD %cn %n%s%n%b<END>")
    # Add log for start; end is included in start..end but start is not
    logs = logs + '\n' + repo.git.show(start, "--format=%h %aD %cn %n%s%n%b")
    # There is one extra line space in the split because one is appended to the front of each entry automatically
    logs = logs.split('<END>\n')
    # Sort logs from earliest to latest
    logs.reverse()

    # Add formatting parameters
    if args.verbose:
        max_line_length = 60
        message_padding = 51
    else:
        max_line_length = 80
        message_padding = 30

    # Make list of logs
    formatted_logs = []
    prev_commit = ''
    for entry in logs:
        commit_hash = entry.split()[0]
        name = '{:<20}'.format(entry.split()[7] + ' ' + entry.split()[8])

        # Add commit subject message
        commit_message = filter(None, entry.split('\n')[1])
        if len(commit_message) > max_line_length:
            commit_message = format_message_width(commit_message, max_line_length)
            formatted_message = commit_message[0]
            for line in commit_message[1:]:
                formatted_message += '\n' + '{:<{}}'.format('...', message_padding) + line
        else:
            formatted_message = commit_message

        # Check if there is a commit message body and append it
        if len(filter(None, entry.split('\n'))) > 3:
            commit_body = format_message_width(filter(None, entry.split('\n')[2:]), max_line_length - 5)
            for line in commit_body:
                formatted_message += '\n' + '{:<{}}'.format('>>>', message_padding + 5) + line

        # Add date, time and diff info if verbose
        if args.verbose:
            if len(entry.split()[2]) == 1:
                date = '0' + entry.split()[2] + ' ' + entry.split()[3] + ' ' + entry.split()[4]
            else:
                date = entry.split()[2] + ' ' + entry.split()[3] + ' ' + entry.split()[4]

            time = entry.split()[5]

            formatted_logs.append(colour(commit_hash, BLUE, raw) + ' ' +
                                  colour(date, CYAN, raw) + ' ' +
                                  colour(time, CYAN, raw) + ' ' +
                                  colour(name, GREEN, raw) + ': ' + formatted_message)
            if prev_commit:
                diff = repo.git.diff("--name-status", prev_commit, commit_hash)
                if diff:
                    formatted_logs.append("Changes:\n" + diff + '\n')
            prev_commit = commit_hash
        # Otherwise just add to list
        else:
            formatted_logs.append(colour(commit_hash, BLUE, raw) + ' ' +
                                  colour(name, GREEN, raw) + ': ' + formatted_message)

    print("Log Messages for " + args.module_name + " between releases " + start + " and " + end + ":")

    for log in formatted_logs:
        print(log)


if __name__ == "__main__":
    sys.exit(main())
