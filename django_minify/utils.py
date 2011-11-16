from django.conf import settings


LANGUAGE_ID = '<lang>'

def has_lang(iterable):
    has_lang = False
    for item in iterable:
        print item
        if LANGUAGE_ID in unicode(item):
            has_lang = True
            break
    return has_lang

def get_language_codes():
    language_codes = [x for x in settings.DEV_LANGUAGES if x != 'ka']
    return language_codes

def get_locales(has_lang):
    '''
    Returns locales or a nice list with None if there are no locales
    '''

    locales = [None]
    if has_lang:
        locales = get_language_codes()
    return locales
        
def expand_on_locale(name_or_path):
    '''
    Expands something like
    my_file_<trans>.js
    to
    my_file_en.js
    my_file_pt-br.js
    ....
    '''
    expanded = []
    if LANGUAGE_ID in name_or_path:
        language_codes = get_language_codes()
        for l in language_codes:
            expanded.append(name_or_path.replace(LANGUAGE_ID, l))
    else:
        expanded.append(name_or_path)
        
    return expanded

def replace_locale(name_or_path, locale):
    '''
    Replaces something like
    my_file<trans>.js
    to
    my_file_en.js
    or if no locale is given
    my_file.js
    '''
    return name_or_path.replace(LANGUAGE_ID, unicode(locale))
    
def append_lang(name_or_path):
    return name_or_path + LANGUAGE_ID
    
    
    
        