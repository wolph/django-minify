
'''
The global settings prefix can be changed by modifying the `SETTINGS_PREFIX`
variable. These settings can be overwritten by modifying the Django settings
(in that case the `SETTINGS_PREFIX` is used) or by modifying this file.
'''
#SETTINGS_PREFIX = 'MINIFY_'

'''The maximum time to wait (in seconds) for a lock on the files'''
#MAX_WAIT = 5

'''The possible Java locations'''
#JAVA_PATHS = [
#    '/bin/java',
#    '/usr/bin/java',
#    '/usr/local/bin/java',
#]

'''Change this if you want to use some other compression tool''' 
#JS_COMPRESSION_COMMAND = CSS_COMPRESSION_COMMAND = ' '.join([
#    '%(JAVA_PATH)s',
#    '-jar',
#    '%(YUI_PATH)s',
#    '-o %%(output_filename)s',
#    '%%(input_filename)s',
#])

'''The inline javascript template to use'''
#JS_INLINE = '''%s'''

'''The linked javascript template to use'''
#JS_INCLUDE = '''
#<script src="%s" type="text/javascript" charset="utf-8"></script>
#'''

'''The inline css template to use'''
#CSS_INLINE = '''%s'''

'''The linked css template to use'''
#CSS_INCLUDE = '''
#<link href="%s" type="text/css" rel="stylesheet" media="all" />
#'''
