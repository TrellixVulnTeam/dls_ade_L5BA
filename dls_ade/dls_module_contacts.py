#!/bin/env dls-python
# This script comes from the dls_scripts python module

"""
Check or set the contact information for a module on the repository. By default
the contacts of the module are printed in a basic format. The CSV flag will
print the contacts in CSV format. To set a contact and/or cc, the contact and
cc flags can be used. To set a contact/cc for one or many modules the import
flag can be used with a valid CSV file. If one contact is changed the other
will be left as it was.
"""

import os
import sys
import shutil
import logging
import csv
from pkg_resources import require
require("python_ldap>=2.3.12")
import ldap

from dls_ade.argument_parser import ArgParser
from dls_ade import path_functions as pathf
from dls_ade import Server

# logging.basicConfig(level=logging.DEBUG)

usage = """
Default <area> is 'support'.
Set or get primary contact (contact) and secondary contact (cc) properties
for <modules> (can just give one module)

e.g.
%prog ip autosave calc
# View the contacts for the ip, autosave and calc modules in support area

%prog -s
# View all the module contacts and ccs in the support area in csv format

%prog -c tmc43 -d jr76 -p pysvn
# Set the python module pysvn to have contact tmc43 and cc jr76

%prog -m /tmp/module_contacts_backup.csv
# Import the module contact and cc from /tmp/module_contacts_backup.csv
# and set them in svn. The csv file must be in the same format as produced
# by the -s command, but any specified contact and cc names are ignored,
# only fed-ids are used.
"""


def make_parser():
    """
    Takes ArgParse instance with default arguments and adds

    Positional Arguments:
        * modules

    Flags:
        * -c (contact)
        * -d (cc)
        * -s (csv)
        * -m (import)

    Returns:
        :class:`argparse.ArgumentParser`: ArgParse instance

    """

    parser = ArgParser(usage)
    # nargs='*' makes <modules> an optional positional argument; a list of N
    # entries
    parser.add_argument(
        "modules", nargs='*', type=str, default=None,
        help="Name(s) of module(s) to list/set contacts for")
    parser.add_argument(
        "-c", "--contact", action="store", type=str, metavar="FED_ID",
        dest="contact", help="Set the contact property to FED_ID")
    parser.add_argument(
        "-d", "--cc", action="store", type=str, metavar="FED_ID", dest="cc",
        help="Set the cc property to FED_ID")
    parser.add_argument(
        "-s", "--csv", action="store_true", dest="csv",
        help="Print output as csv file")
    parser.add_argument(
        "-m", "--import", action="store", type=str, metavar="CSV_FILE",
        dest="imp", help="Import a CSV_FILE with header and rows of format:" +
                         "\nModule, Contact, Contact Name, CC, CC Name")

    return parser


def check_parsed_args_compatible(imp, modules, contact, cc, parser):
    """
    Check that the combination of arguments are compatible.

    Args:
        imp(str): CSV import specifier
        modules(str): Modules argument
        contact(str): Contact argument
        cc(str): CC argument
        parser(:class:`argparse.ArgumentParser`): Parser instance

    Raises:
        :class:`argparse.ArgumentParser` error:
            * --import cannot be used with --contact or --cc
            * You cannot set all modules in an area to one contact/cc, enter a
                specific module.
    """

    if imp and (contact or cc):
        parser.error("--import cannot be used with --contact or --cc")

    # Stop user from setting all modules in an area to one contact/cc
    if not modules and (contact or cc):
        parser.error("You cannot set all modules in an area to one contact/cc,"
                     " enter a specific module.")
        # Just in case parser.error doesn't stop the script
        return 1


def lookup_contact_name(fed_id):
    """
    Perform an LDAP search to find the Name and Surname corresponding to a
    FED-ID.

    Args:
        fed_id(str): FED-ID to search for

    Returns:
        str: Contact name

    """

    # Set up ldap search parameters
    l = ldap.initialize('ldap://altfed.cclrc.ac.uk')
    basedn = "dc=fed,dc=cclrc,dc=ac,dc=uk"
    search_filter = "(&(cn={}))".format(fed_id)
    search_attribute = ["givenName", "sn"]
    search_scope = ldap.SCOPE_SUBTREE

    # Perform search, print message so user knows where program hangs
    # The lookup can hang at l.result() if the FED-ID does not exist.
    print("Performing search for " + fed_id + "...")
    l.simple_bind_s()
    ldap_result_id = l.search(basedn, search_scope, search_filter,
                              search_attribute)
    ldap_output = l.result(ldap_result_id, 0)
    logging.debug(ldap_output)
    # ldap_output has the form:
    # (100, [('CN=<FED-ID>,OU=DLS,DC=fed,DC=cclrc,DC=ac,DC=uk',
    # {'givenName': ['<FirstName>'], 'sn': ['<Surname>']})])

    if ldap_output[0] == 115:
        # If the FED-ID does not exist, ldap_output will look like:
        # (115, [(None,
        # ['ldap://res02.fed.cclrc.ac.uk/DC=res02,DC=fed,DC=cclrc,DC=ac,DC=uk'])])
        raise Exception(fed_id + " is not an existing contact")

    # Extract contact name from output
    name_info_dict = ldap_output[1][0][1]
    # name_info_dict: {'givenName': ['<FirstName>'], 'sn': ['<Surname>']}
    contact_name = \
        name_info_dict['givenName'][0] + ' ' + name_info_dict['sn'][0]

    return contact_name


def output_csv_format(contact, cc_contact, module):
    """
    Print out contact info in CSV format.

    Args:
        contact(str): Contact FED-ID
        cc_contact(str): Contact FED-ID
        module(str): Module name

    Returns:
        str: Formatted output
    """

    # Check if <FED-ID>s are specified in repo, if not don't run lookup
    # function
    if contact != 'unspecified':
        contact_name = lookup_contact_name(contact)
    else:
        contact_name = contact
    if cc_contact != 'unspecified':
        cc_name = lookup_contact_name(cc_contact)
    else:
        cc_name = cc_contact

    output = "{module},{contact},{contact_name},{cc},{cc_name}".format(
        module=module, contact=contact, contact_name=contact_name,
        cc=cc_contact, cc_name=cc_name)

    return output


def import_from_csv(modules, area, imp):
    """
    Extract contact info from a given CSV file.

    Args:
        modules(list): List of valid modules
        area(str): Area of modules that are having contacts changed
        imp(str): File path for CSV to get info from

    Returns:
        A list of tuples containing module, contact and cc

    """

    reader = csv.reader(open(imp, "r"))
    # Extract data from reader object
    csv_file = []
    for row in reader:
        csv_file.append(row)
    logging.debug(csv_file)

    if not csv_file:
        raise Exception("CSV file is empty")

    contacts = []
    for row in csv_file:
        # Check for header row and skip
        if row[0] != "Module":
            # CSV file format should be: Module,Contact,Contact Name,CC,CC Name
            if len(row) > 1:
                module = row[0].strip()
                contact = row[1].strip()
            else:
                raise Exception("Module {} has no corresponding contact in"
                                " CSV file".format(row[0]))

            if len(row) > 3:
                cc = row[3].strip()
            else:
                cc = ""

            if module not in modules:
                raise Exception("Module {module} not in {area} area".format(
                    module=module, area=area))
            if module in [x[0] for x in contacts]:
                raise Exception("Module {} defined twice in"
                                " CSV file".format(module))

            contacts.append((module, contact, cc))

    return contacts


def edit_contact_info(repo, contact='', cc=''):
    """
    Write to .gitattributes file to change contacts of repo.

    Args:
        repo(:class:`~git.repo.base.Repo`): Repository instance of module
        contact(str): Contact FED-ID
        cc(str): CC FED-ID

    Returns:
        str: Commit message summarising changes made

    """

    current_contact = repo.git.check_attr("module-contact", ".").split(' ')[-1]
    current_cc = repo.git.check_attr("module-cc", ".").split(' ')[-1]

    if contact in [current_contact, ''] and cc in [current_cc, '']:
        print("Leaving contacts unchanged")
        return 0

    # Check that FED-IDs exist,
    # if they don't lookup...() will (possibly) hang and raise an exception
    if contact:
        contact = contact.strip()
        lookup_contact_name(contact)
    else:
        contact = current_contact

    if cc:
        cc = cc.strip()
        lookup_contact_name(cc)
    else:
        cc = current_cc

    module = repo.working_tree_dir.split('/')[-1]

    with open(os.path.join(
            repo.working_tree_dir, '.gitattributes'), 'w') as git_attr_file:

        commit_message = ''
        if contact:
            print("{0}: Setting contact to {1}".format(module, contact))
            commit_message += "Set contact to {}. ".format(contact)
            git_attr_file.write("* module-contact={}\n".format(contact))
        if cc:
            print("{0}: Setting cc to {1}".format(module, cc))
            commit_message += "Set cc to {}.".format(cc)
            git_attr_file.write("* module-cc={}\n".format(cc))

    return commit_message


def main():

    parser = make_parser()
    args = parser.parse_args()

    check_parsed_args_compatible(args.imp, args.modules, args.contact, args.cc,
                                 parser)

    server = Server()

    # Create the list of modules from args, or the server if none provided
    modules = []
    if args.modules:
        for module in args.modules:
            modules.append(module)
    else:
        repo_list = server.get_server_repo_list()

        modules = []
        for path in repo_list:
            if args.area in path and path.split('/')[-1] not in modules:
                modules.append(path.split('/')[-1])

    # If no contacts or csv file provided to edit, use default script
    # operation: print contacts
    if not (args.contact or args.cc or args.imp):

        print_out = []
        for module in modules:
            source = server.dev_module_path(module, args.area)
            vcs = server.temp_clone(source)

            # Retrieve contact info
            contact = vcs.repo.git.check_attr(
                "module-contact", ".").split(' ')[-1]
            cc_contact = vcs.repo.git.check_attr(
                "module-cc", ".").split(' ')[-1]

            if args.csv:
                print_out.append(output_csv_format(
                    contact, cc_contact, module))
            else:
                print_out.append("Contact: " + contact +
                                 " (CC: " + cc_contact + ")")

            shutil.rmtree(vcs.repo.working_tree_dir)

        if args.csv:
            print("Module,Contact,Contact Name,CC,CC Name")
        for entry in print_out:
            print(entry)

        return 0

    # If we get to this point, we are assigning contacts

    if args.imp:
        contacts = import_from_csv(modules, args.area, args.imp)
    else:
        # If no csv file provided, retrieve contacts from args
        contacts = []
        for module in modules:
            contacts.append((module, args.contact, args.cc))

    # Checkout modules and change contacts
    for module, contact, cc in contacts:

        print("Cloning " + module + " from " + args.area + " area...")
        source = server.dev_module_path(module, args.area)
        vcs = server.temp_clone(source)
        repo = vcs.repo

        edit_summary = edit_contact_info(repo, contact, cc,)

        if edit_summary != 0:
            index = repo.index
            index.add(['.gitattributes'])
            index.commit(edit_summary)

            origin = repo.remotes.origin
            origin.push(repo.active_branch)

        shutil.rmtree(repo.working_tree_dir)


if __name__ == "__main__":
    sys.exit(main())