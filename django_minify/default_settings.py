'''These are the default settings, DON'T MODIFY THIS FILE!

If (some) of these settings need changing, do that in `settings.py` instead


The global settings prefix can be changed by modifying the `SETTINGS_PREFIX`
variable. These settings can be overwritten by modifying the Django settings
(in that case the `SETTINGS_PREFIX` is used) or by modifying `settings.py`
'''
from os import path as _path

SETTINGS_PREFIX = 'MINIFY_'

MAX_WAIT = 5
JAVA_PATHS = [
    '/bin/java',
    '/usr/bin/java',
    '/usr/local/bin/java',
    'c:/Windows/System32/java.exe',
]

YUI_PATH = _path.join(_path.dirname(__file__), 'yuicompressor-2.4.6.jar')
JS_COMPRESSION_COMMAND = CSS_COMPRESSION_COMMAND = ' '.join([
    '%(JAVA_PATH)s',
    '-jar',
    '%(YUI_PATH)s',
    '-o %%(output_filename)s',
    '%%(input_filename)s',
])

JS_INLINE = '''
<script type="text/javascript" charset="utf-8">
/* <![CDATA[ */
%s
/* ]]> */
</script>
'''

JS_INCLUDE = '''
<script src="%s" type="text/javascript" charset="utf-8"></script>
'''

CSS_INLINE = '''<style media="all">
/* <![CDATA[ */
%s
/* ]]> */
</style>'''

CSS_INCLUDE = '''
<link href="%s" type="text/css" rel="stylesheet" media="all" />
'''

FROM_CACHE = True

DEV_LANGUAGES = (
    ('en', 'English'),
    ('pt-br', 'Portugese (Brazil)'),
)
DEBUG = False
MEDIA_ROOT = 'media/'
LANGUAGE_ID = '<lang>'

