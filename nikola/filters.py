# -*- coding: utf-8 -*-

# Copyright © 2012-2014 Roberto Alsina and others.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Utility functions to help you run filters on files."""

from .utils import req_missing
from functools import wraps
import os
import codecs
import re
import shutil
import subprocess
import tempfile
import shlex

try:
    import typogrify.filters as typo
except ImportError:
    typo = None  # NOQA


def apply_to_binary_file(f):
    """Take a function f that transforms a data argument, and returns
    a function that takes a filename and applies f to the contents,
    in place.  Reads files in binary mode."""
    @wraps(f)
    def f_in_file(fname):
        with open(fname, 'rb') as inf:
            data = inf.read()
        data = f(data)
        with open(fname, 'wb+') as outf:
            outf.write(data)

    return f_in_file


def apply_to_text_file(f):
    """Take a function f that transforms a data argument, and returns
    a function that takes a filename and applies f to the contents,
    in place.  Reads files in UTF-8."""
    @wraps(f)
    def f_in_file(fname):
        with codecs.open(fname, 'r', 'utf-8') as inf:
            data = inf.read()
        data = f(data)
        with codecs.open(fname, 'w+', 'utf-8') as outf:
            outf.write(data)

    return f_in_file


def list_replace(the_list, find, replacement):
    "Replace all occurrences of ``find`` with ``replacement`` in ``the_list``"
    for i, v in enumerate(the_list):
        if v == find:
            the_list[i] = replacement


def runinplace(command, infile):
    """Run a command in-place on a file.

    command is a string of the form: "commandname %1 %2" and
    it will be execed with infile as %1 and a temporary file
    as %2. Then, that temporary file will be moved over %1.

    Example usage:

    runinplace("yui-compressor %1 -o %2", "myfile.css")

    That will replace myfile.css with a minified version.

    You can also supply command as a list.
    """

    if not isinstance(command, list):
        command = shlex.split(command)

    tmpdir = None

    if "%2" in command:
        tmpdir = tempfile.mkdtemp(prefix="nikola")
        tmpfname = os.path.join(tmpdir, os.path.basename(infile))

    try:
        list_replace(command, "%1", infile)
        if tmpdir:
            list_replace(command, "%2", tmpfname)

        subprocess.check_call(command)

        if tmpdir:
            shutil.move(tmpfname, infile)
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir)


def yui_compressor(infile):
    yuicompressor = False
    try:
        subprocess.call('yui-compressor', stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        yuicompressor = 'yui-compressor'
    except Exception:
        pass
    if not yuicompressor:
        try:
            subprocess.call('yuicompressor', stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
            yuicompressor = 'yuicompressor'
        except:
            raise Exception("yui-compressor is not installed.")
            return False

    return runinplace(r'{} --nomunge %1 -o %2'.format(yuicompressor), infile)


def optipng(infile):
    return runinplace(r"optipng -preserve -o2 -quiet %1", infile)


def jpegoptim(infile):
    return runinplace(r"jpegoptim -p --strip-all -q %1", infile)


def tidy(inplace):
    # Google site verifcation files are not HTML
    if re.match(r"google[a-f0-9]+.html", os.path.basename(inplace)) \
            and open(inplace).readline().startswith(
                "google-site-verification:"):
        return

    # Tidy will give error exits, that we will ignore.
    output = subprocess.check_output(
        "tidy -m -w 90 -utf8 --new-blocklevel-tags header,footer,nav,article,aside "
        "--new-inline-tags time --indent no --quote-marks no --keep-time yes --tidy-mark no "
        "--force-output yes '{0}'; exit 0".format(inplace), stderr=subprocess.STDOUT, shell=True)

    output = '\n'.join([l.decode('utf-8') for l in output.split(b'\n')])

    for line in output.split(u"\n"):
        if "Warning:" in line:
            if '<meta> proprietary attribute "charset"' in line:
                # We want to set it though.
                continue
            elif '<meta> lacks "content" attribute' in line:
                # False alarm to me.
                continue
            elif '<div> anchor' in line and 'already defined' in line:
                # Some seeming problem with JavaScript terminators.
                continue
            elif '<img> lacks "alt" attribute' in line:
                # Happens in gallery code, probably can be tolerated.
                continue
            elif '<table> lacks "summary" attribute' in line:
                # Happens for tables, TODO: Check this is normal.
                continue
            elif 'proprietary attribute' in line:
                # for data-* and other html5 additions
                continue
            elif 'is not approved by W3C' in line:
                # it is, in html5.  (--new-blocklevel-tags)
                continue
            elif "'<' + '/' + letter not allowed here" in line:
                # javascript.  It turns it to <\/a>; fortunately JS understands
                # this properly.
                continue
            elif '<script> inserting "type" attribute' in line:
                # That’s what you get for using 2009 tools in 2014
                continue
            elif 'trimming empty' in line:
                # [WARNING] destroys all icons, probably more things.
                continue
            else:
                assert False, (inplace, line)
        elif "Error:" in line:
            if 'is not recognized' in line:
                # False alarm, most such things are HTML5.
                continue
            else:
                assert False, line


@apply_to_text_file
def typogrify(data):
    if typo is None:
        req_missing(['typogrify'], 'use the typogrify filter')

    data = typo.amp(data)
    data = typo.widont(data)
    data = typo.smartypants(data)
    # Disabled because of typogrify bug where it breaks <title>
    # data = typo.caps(data)
    data = typo.initial_quotes(data)
    return data
