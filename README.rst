############################
 DNF Offline Upgrade Plugin
############################

Experimental plugin to use with `DNF package manager <https://github.com/rpm-software-management/dnf>`_.

======================
 Building from source
======================

From the DNF git checkout directory::

    mkdir build;
    pushd build;
    cmake .. && make;
    popd;

Then to run DNF::

    PYTHONPATH=`readlink -f .` bin/dnf <arguments>

===============
 Running tests
===============

From the DNF git checkout directory::

    mkdir build;
    pushd build;
    cmake .. && make ARGS="-V" test;
    popd;
