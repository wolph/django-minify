'''The Django combine library, mostly legacy code which should be replaced
asap when time allows'''

from coffin.template import Library
from django import template
from django.template import Node, Variable, VariableDoesNotExist
from django_minify.conf import settings
from django_minify.minify import minify
import os
import re

register = Library()

URL_PARSE_RE = re.compile('''
    ^
    (?P<admin>|admin/)
    (?P<extension>js|css)
    /(?P<path>|.*/)
    (?P<files>[A-Za-z0-9_.,-]+)
    $''', re.VERBOSE)

ABSOLUTE_URL = 1
ABSOLUTE_FILE = 2
RELATIVE_FILE = 3

def _list_to_string(list_):
    urls = [u.replace('original/', '', 1) for u in list_]
    base_url = urls[0]
    urls = [u.replace('js/', '', 1).replace('css/', '', 1)
        for u in urls[1:]]

    urls.insert(0, base_url)
    return ','.join(urls)

class Combiner(Node):
    def __init__(self, variables=[]):
        self.variables = variables

    def render(self, context):
        self.variables = map(lambda x: get_variable(context, x),
            self.variables)
        
        if isinstance(self.variables[0], basestring):
            old_url = self.variables[0].strip('"').strip("'")
        else:
            old_url = _list_to_string(self.variables[0])

        try:
            request = template.resolve_variable('request', context)
        except VariableDoesNotExist:
            request = None

        url = combine_files(old_url, request)
        return url

@register.tag('combine')
def combine(parser, token):
    tokens = token.contents.split()
    return Combiner(tokens[1:])

def parse_bool(dict_, key, default=False):
    return  dict_.get(key, default) in ('y', 'yes', '1', 'true', True)

@register.filter(jinja2_only=True)
def combine_files(files_string, request=None, output=ABSOLUTE_URL):
    '''Accepts a comma separated list of files, only the first file should
    have the directory added to it

    e.g. css/foo.css,bar.css for the files css/foo.css and css/bar.css
    '''
    match = URL_PARSE_RE.match(files_string)
    if match:
        matches = match.groups()
    else:
        raise ValueError('Unable to parse "%s"' % files_string)
    admin, extension, path, files = matches
    if admin:
        prefix = 'admin'
    else:
        prefix = ''

    files = files.split(',')
    if extension == 'css':
        compress = settings.CSS_COMPRESS
        minimize = settings.CSS_MINIFY
    elif extension == 'js':
        compress = settings.JS_COMPRESS
        minimize = settings.JS_MINIFY

    if request:
        GET = request.GET
    else:
        GET = {}

    minimize = parse_bool(GET, 'minimize', minimize)
    compress = parse_bool(GET, 'compress', compress)

    try:
        cached_file = minify(path, files, extension, minimize, compress,
            prefix)
    except OSError, e:
        e.args = list(e.args) + [
            'prefix: %r' % prefix,
            'extension: %r' % extension,
            'files: %r' % files,
        ]
        raise

    if output == ABSOLUTE_FILE:
        return cached_file.replace('\\', '/')
    else:
        last = cached_file.split('cache')[1].replace('/', '').replace('\\', '')
        media_path = os.path.join(extension, 'cache', last).replace('\\', '/')

        if output == RELATIVE_FILE:
            return media_path
        elif output == ABSOLUTE_URL:
            return settings.MEDIA_URL + media_path
    raise TypeError('Output must be ABSOLUTE_URL, ABSOLUTE_FILE or '
        'RELATIVE_FILE')


def get_variable(context, name):
    '''
    This function will attempt to retrieve the variable and upon failing to do so return the string 
    '''
    template_variable = Variable(name)
    try:
        return template_variable.resolve(context)
    except template.VariableDoesNotExist:
        return name

