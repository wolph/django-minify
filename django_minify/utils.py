import os
from django_minify.conf import settings


def has_lang(iterable):
    has_lang = False
    for item in iterable:
        if settings.LANGUAGE_ID in unicode(item):
            has_lang = True
            break
    return has_lang

def get_language_codes():
    language_codes = [k for k, v in settings.DEV_LANGUAGES if k != 'ka']
    return language_codes

def get_languages_list(has_lang):
    '''
    Returns locales or a nice list with None if there are no locales
    '''

    locales = [None]
    if has_lang:
        locales = get_language_codes()
    return locales
        
def expand_on_lang(name_or_path):
    '''
    Expands something like
    my_file_<trans>.js
    to
    my_file_en.js
    my_file_pt-br.js
    ....
    '''
    expanded = []
    if settings.LANGUAGE_ID in name_or_path:
        language_codes = get_language_codes()
        for lang in language_codes:
            localized_path = name_or_path.replace(settings.LANGUAGE_ID, lang)
            expanded.append(localized_path)
    else:
        expanded.append(name_or_path)
        
    return expanded

def replace_lang(name_or_path, locale):
    '''
    Replaces something like
    my_file<trans>.js
    to
    my_file_en.js
    or if no locale is given
    my_file.js
    '''
    return name_or_path.replace(settings.LANGUAGE_ID, unicode(locale))
    
def append_lang(name_or_path):
    assert settings.LANGUAGE_ID not in name_or_path
    path, ext = os.path.splitext(name_or_path)
    path_with_lang = path + settings.LANGUAGE_ID + ext
    return path_with_lang
    
    
    
        
