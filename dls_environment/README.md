Intro
=====
This module contains a python object representation of a site enviroment. 
It is primarily used so modules like dls_dependency_tree can be site independant

Dependencies
============
Just python

Modifying the module for your site
==================================
Before using this, you should modify the following in dls_environment.py:
- class environment: change some functions:
 - epicsDir(): location of epics base
 - devArea(): location of the development area
 - prodArea(): location of the production area

It is assumed that the site environment is of a similar structure to dls:
- development of a module is done in a local area or in <devArea>
- modules in devArea have the path <devArea>/<module_name>
- modules are installed in <prodArea>
- modules in prodArea have the path <prodArea>/<module_name>/<module_release>

You should also define the following in Makefile.private:
- INSTALL_DIR: Where to install the module
- PYTHON: Where to find python

Install
=======
To make this module:
- type make to check the build
- type make install to install to $INSTALL_DIR
- type make clean to clean the module

Usage
=====
Once installed, you can use dls_dependency_tree