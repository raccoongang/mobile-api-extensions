======================
 Mobile API extensions
======================


Features
########

Place your plugin features list.

Installation
############

Open edX devstack
*****************

- Clone this repo in the src folder of your devstack.
- Open a new Lms/Devstack shell.
- Install the plugin as follows: pip install -e /path/to/your/src/folder
- Restart Lms/Studio services.

Usage
#####

Include a usage description for your plugin.

Testing and code quality
#####

For running tests locally use the following command:
.. code-block::
    make python-test

For running python style checkers use the following command:
.. code-block::
    make quality

Pre-commit hooks
#####

Run :code:`pre-commit install` to install pre-commit into your git hooks. pre-commit will now run on every commit. Every time you clone a project using pre-commit running :code:`pre-commit install` should always be the first thing you do.

If you want to manually run all pre-commit hooks on a repository, run :code:`pre-commit run --all-files`. To run individual hooks use :code:`pre-commit run <hook_id>`.


Contributing
############

Add your contribution policy. (If required)
