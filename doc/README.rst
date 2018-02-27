========================
Qinling Development Docs
========================

Files under this directory tree are used for generating the documentation
for the qinling source code.

Developer documentation is built to:
https://docs.openstack.org/qinling/latest/

Tools
=====

Sphinx
  The Python Sphinx package is used to generate the documentation output.
  Information on Sphinx, including formatting information for RST source
  files, can be found in the `Sphinx online documentation
  <http://www.sphinx-doc.org/en/stable/>`_.

Building Documentation
======================

Doc builds are performed using tox with the ``docs`` target::

 % cd ..
 % tox -e docs

