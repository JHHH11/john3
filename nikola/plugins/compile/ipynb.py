# -*- coding: utf-8 -*-

# Copyright © 2013-2015 Damián Avila and others.

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

"""Implementation of compile_html based on nbconvert."""

from __future__ import unicode_literals, print_function
import io
import os

try:
    import IPython
    from IPython.nbconvert.exporters import HTMLExporter
    if IPython.version_info[0] >= 3:     # API changed with 3.0.0
        from IPython import nbformat
        current_nbformat = nbformat.current_nbformat
    else:
        import IPython.nbformat.current as nbformat
        current_nbformat = 'json'

    from IPython.config import Config
    flag = True
except ImportError:
    flag = None

from nikola.plugin_categories import PageCompiler
from nikola.utils import makedirs, req_missing


class CompileIPynb(PageCompiler):
    """Compile IPynb into HTML."""

    name = "ipynb"
    demote_headers = True

    def compile_html(self, source, dest, is_two_file=True):
        if flag is None:
            req_missing(['ipython>=1.1.0'], 'build this site (compile ipynb)')
        makedirs(os.path.dirname(dest))
        HTMLExporter.default_template = 'basic'
        c = Config(self.site.config['IPYNB_CONFIG'])
        exportHtml = HTMLExporter(config=c)
        with io.open(dest, "w+", encoding="utf8") as out_file:
            with io.open(source, "r", encoding="utf8") as in_file:
                nb_json = nbformat.read(in_file, current_nbformat)
            (body, resources) = exportHtml.from_notebook_node(nb_json)
            out_file.write(body)

    def read_metadata(self, post, file_metadata_regexp=None, unslugify_titles=False, lang=None):
        """read metadata directly from ipynb file.

        As ipynb file support arbitrary metadata as json, the metadata used by Nikola
        will be assume to be in the 'nikola' subfield.
        """
        source = post.source_path
        with io.open(source, "r", encoding="utf8") as in_file:
            nb_json = nbformat.read(in_file, current_nbformat)
        # metadata should always exist, but we never know if
        # the user crafted the ipynb by hand and did not add it.
        return nb_json.get('metadata', {}).get('nikola', {})

    def create_post(self, path, **kw):
        content = kw.pop('content', None)
        onefile = kw.pop('onefile', False)
        kernel = kw.pop('ipython_kernel', None)
        # is_page is not needed to create the file
        kw.pop('is_page', False)

        metadata = {}
        metadata.update(self.default_metadata)
        metadata.update(kw)

        makedirs(os.path.dirname(path))

        if IPython.version_info[0] >= 3:
            nb = nbformat.v4.new_notebook()
            nb["cells"] = [nbformat.v4.new_code_cell(content)]
        else:
            nb = nbformat.v3.nbbase.new_notebook()
            nb["cells"] = [nbformat.v3.nbbase.new_code_cell(content)]

        if onefile:
            nb["metadata"]["nikola"] = metadata

        if kernel is not None:
            nb["metadata"]["kernelspec"] = ipython_kernel_spec[kernel]
            nb["metadata"]["language_info"] = ipython_language_info[kernel]

        with io.open(path, "w+", encoding="utf8") as fd:
            if IPython.version_info[0] >= 3:
                nbformat.write(nb, fd, 4)
            else:
                nbformat.write(nb, fd, 'ipynb')

# python2 nb metadata info

python2_kernelspec = {
    "display_name": "Python 2",
    "language": "python",
    "name": "python2"
}

python2_codemirror_mode = {
    "name": "ipython",
    "version": 2
}

python2_language_info = {
    "codemirror_mode": python2_codemirror_mode,
    "file_extension": ".py",
    "mimetype": "text/x-python",
    "name": "python",
    "nbconvert_exporter": "python",
    "pygments_lexer": "ipython2",
    "version": "2.7.10"
}

# python3 nb metadata info

python3_kernelspec = {
    "display_name": "Python 3",
    "language": "python",
    "name": "python3"
}

python3_codemirror_mode = {
    "name": "ipython",
    "version": 3
}

python3_language_info = {
    "codemirror_mode": python3_codemirror_mode,
    "file_extension": ".py",
    "mimetype": "text/x-python",
    "name": "python",
    "nbconvert_exporter": "python",
    "pygments_lexer": "ipython3",
    "version": "3.4.3"
}

# julia nb metadata info

julia_kernelspec = {
    "display_name": "Julia 0.3.2",
    "language": "julia",
    "name": "julia-0.3"
}

julia_language_info = {
    "name": "julia",
    "version": "0.3.2"
}

# r nb metadata info

r_kernelspec = {
    "display_name": "R",
    "language": "R",
    "name": "ir"
}

r_language_info = {
    "codemirror_mode": "r",
    "file_extension": ".r",
    "mimetype": "text/x-r-source",
    "name": "R",
    "pygments_lexer": "r",
    "version": "3.1.3"
}

# main ipython_kernel_spec dict to map the correct metadata
# with the kernel name from the markup defined by the user

ipython_kernel_spec = {}
ipython_kernel_spec["python2"] = python2_kernelspec
ipython_kernel_spec["python3"] = python3_kernelspec
ipython_kernel_spec["julia"] = julia_kernelspec
ipython_kernel_spec["r"] = r_kernelspec

ipython_language_info = {}
ipython_language_info["python2"] = python2_language_info
ipython_language_info["python3"] = python3_language_info
ipython_language_info["julia"] = julia_language_info
ipython_language_info["r"] = r_language_info
