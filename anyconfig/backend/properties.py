#
# Copyright (C) 2012 - 2015 Satoru SATOH <ssato @ redhat.com>
# License: MIT
#
"""
Java properties file support.

.. versionadded:: 0.2
   Added native Java properties parser instead of a plugin utilizes
   pyjavaproperties module.

- Format to support: Java Properties file, e.g.
  http://docs.oracle.com/javase/1.5.0/docs/api/java/util/Properties.html
- Requirements: None (built-in)
- Limitations: None
- Special options: None
"""
from __future__ import absolute_import

import logging
import re

import anyconfig.backend.base
import anyconfig.compat


LOGGER = logging.getLogger(__name__)
_COMMENT_MARKERS = ("#", "!")


def _parseline(line):
    """
    Parse a line of Java properties file.

    :param line:
        A string to parse, must not start with ' ', '#' or '!' (comment)
    :return: A tuple of (key, value), both key and value may be None

    >>> _parseline("aaa")
    (None, None)
    >>> _parseline("calendar.japanese.type: LocalGregorianCalendar")
    ('calendar.japanese.type', 'LocalGregorianCalendar')
    """
    match = re.match(r"^(\S+)(?:\s+)?(?<!\\)[:=](?:\s+)?(.+)", line)
    if not match:
        LOGGER.warning("Invalid line found: %s", line)
        return (None, None)

    return match.groups()


def _pre_process_line(line, comment_markers=_COMMENT_MARKERS):
    """
    Preprocess a line in properties; strip comments, etc.

    :param line:
        A string not starting w/ any white spaces and ending w/ line breaks.
        It may be empty. see also: :func:`load`.
    :param comment_markers: Comment markers, e.g. '#' (hash)

    >>> _pre_process_line('') is None
    True
    >>> s0 = "calendar.japanese.type: LocalGregorianCalendar"
    >>> _pre_process_line("# " + s0) is None
    True
    >>> _pre_process_line("! " + s0) is None
    True
    >>> _pre_process_line(s0 + "# comment")
    'calendar.japanese.type: LocalGregorianCalendar# comment'
    """
    if not line:
        return None

    if any(c in line for c in comment_markers):
        if line.startswith(comment_markers):
            return None

    return line


def unescape(in_s):
    """
    :param in_s: Input string
    """
    return re.sub(r"\\(.)", r"\1", in_s)


def _escape_char(in_c):
    """
    Escape some special characters in java .properties files.

    :param in_c: Input character

    >>> "\\:" == _escape_char(':')
    True
    >>> "\\=" == _escape_char('=')
    True
    >>> _escape_char('a')
    'a'
    """
    return '\\' + in_c if in_c in (':', '=', '\\') else in_c


def escape(in_s):
    """
    :param in_s: Input string
    """
    return ''.join(_escape_char(c) for c in in_s)


def load(stream, to_container=dict, comment_markers=_COMMENT_MARKERS):
    """
    Load and parse Java properties file given as a fiel or file-like object
    `stream`.

    :param stream: A file or file like object of Java properties files
    :param to_container:
        Factory function to create a dict-like object to store properties
    :param comment_markers: Comment markers, e.g. '#' (hash)
    :return: Dict-like object holding properties

    >>> to_strm = anyconfig.compat.StringIO
    >>> s0 = "calendar.japanese.type: LocalGregorianCalendar"
    >>> load(to_strm(''))
    {}
    >>> load(to_strm("# " + s0))
    {}
    >>> load(to_strm("! " + s0))
    {}
    >>> load(to_strm("calendar.japanese.type:"))
    {}
    >>> load(to_strm(s0))
    {'calendar.japanese.type': 'LocalGregorianCalendar'}
    >>> load(to_strm(s0 + "# ..."))
    {'calendar.japanese.type': 'LocalGregorianCalendar# ...'}
    >>> s1 = r"key=a\\:b"
    >>> load(to_strm(s1))
    {'key': 'a:b'}
    >>> s2 = '''application/postscript: \\
    ...         x=Postscript File;y=.eps,.ps
    ... '''
    >>> load(to_strm(s2))
    {'application/postscript': 'x=Postscript File;y=.eps,.ps'}
    """
    ret = to_container()
    prev = ""

    for line in stream.readlines():
        line = _pre_process_line(prev + line.strip().rstrip(),
                                 comment_markers)
        # I don't think later case may happen but just in case.
        if line is None or not line:
            continue

        if line.endswith("\\"):
            prev += line.rstrip(" \\")
            continue

        prev = ""  # re-initialize for later use.

        (key, val) = _parseline(line)
        if key is None:
            LOGGER.warning("Failed to parse the line: %s", line)
            continue

        ret[key] = unescape(val)

    return ret


class Parser(anyconfig.backend.base.FromStreamLoader,
             anyconfig.backend.base.ToStreamDumper):
    """
    Parser for Java properties files.
    """
    _type = "properties"
    _extensions = ["properties"]

    def load_from_stream(self, stream, to_container, **kwargs):
        """
        Load config from given file like object `stream`.

        :param stream: A file or file like object of Java properties files
        :param to_container: callble to make a container object
        :param kwargs: optional keyword parameters (ignored)

        :return: Dict-like object holding config parameters
        """
        return load(stream, to_container=to_container)

    def dump_to_stream(self, cnf, stream, **kwargs):
        """
        Dump config `cnf` to a file or file-like object `stream`.

        :param cnf: Java properties config data to dump
        :param stream: Java properties file or file like object
        :param kwargs: backend-specific optional keyword parameters :: dict
        """
        for key, val in anyconfig.compat.iteritems(cnf):
            stream.write("%s = %s\n" % (key, escape(val)))

# vim:sw=4:ts=4:et:
