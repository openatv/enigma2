# 2013.05.22 08:35:18 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/AirPlayer/httputil.py
"""HTTP utility code shared by clients and servers."""
import re

class HTTPHeaders(dict):
    """A dictionary that maintains Http-Header-Case for all keys.
    
    Supports multiple values per key via a pair of new methods,
    add() and get_list().  The regular dictionary interface returns a single
    value per key, with multiple values joined by a comma.
    
    >>> h = HTTPHeaders({"content-type": "text/html"})
    >>> h.keys()
    ['Content-Type']
    >>> h["Content-Type"]
    'text/html'
    
    >>> h.add("Set-Cookie", "A=B")
    >>> h.add("Set-Cookie", "C=D")
    >>> h["set-cookie"]
    'A=B,C=D'
    >>> h.get_list("set-cookie")
    ['A=B', 'C=D']
    
    >>> for (k,v) in sorted(h.get_all()):
    ...    print '%s: %s' % (k,v)
    ...
    Content-Type: text/html
    Set-Cookie: A=B
    Set-Cookie: C=D
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self)
        self._as_list = {}
        self.update(*args, **kwargs)

    def add(self, name, value):
        """Adds a new value for the given key."""
        norm_name = HTTPHeaders._normalize_name(name)
        if norm_name in self:
            dict.__setitem__(self, norm_name, self[norm_name] + ',' + value)
            self._as_list[norm_name].append(value)
        else:
            self[norm_name] = value

    def get_list(self, name):
        """Returns all values for the given header as a list."""
        norm_name = HTTPHeaders._normalize_name(name)
        return self._as_list.get(norm_name, [])

    def get_all(self):
        """Returns an iterable of all (name, value) pairs.
        
        If a header has multiple values, multiple pairs will be
        returned with the same name.
        """
        for name, list in self._as_list.iteritems():
            for value in list:
                yield (name, value)

    def parse_line(self, line):
        """Updates the dictionary with a single header line.
        
        >>> h = HTTPHeaders()
        >>> h.parse_line("Content-Type: text/html")
        >>> h.get('content-type')
        'text/html'
        """
        name, value = line.split(':', 1)
        self.add(name, value.strip())

    @classmethod
    def parse(cls, headers):
        r"""Returns a dictionary from HTTP header text.
        
        >>> h = HTTPHeaders.parse("Content-Type: text/html\r\nContent-Length: 42\r\n")
        >>> sorted(h.iteritems())
        [('Content-Length', '42'), ('Content-Type', 'text/html')]
        """
        h = cls()
        for line in headers.splitlines():
            if line:
                h.parse_line(line)

        return h

    def __setitem__(self, name, value):
        norm_name = HTTPHeaders._normalize_name(name)
        dict.__setitem__(self, norm_name, value)
        self._as_list[norm_name] = [value]

    def __getitem__(self, name):
        return dict.__getitem__(self, HTTPHeaders._normalize_name(name))

    def __delitem__(self, name):
        norm_name = HTTPHeaders._normalize_name(name)
        dict.__delitem__(self, norm_name)
        del self._as_list[norm_name]

    def get(self, name, default = None):
        return dict.get(self, HTTPHeaders._normalize_name(name), default)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

    _NORMALIZED_HEADER_RE = re.compile('^[A-Z0-9][a-z0-9]*(-[A-Z0-9][a-z0-9]*)*$')

    @staticmethod
    def _normalize_name(name):
        """Converts a name to Http-Header-Case.
        
        >>> HTTPHeaders._normalize_name("coNtent-TYPE")
        'Content-Type'
        """
        if HTTPHeaders._NORMALIZED_HEADER_RE.match(name):
            return name
        return '-'.join([ w.capitalize() for w in name.split('-') ])


def doctests():
    import doctest
    return doctest.DocTestSuite()


if __name__ == '__main__':
    import doctest
    doctest.testmod()