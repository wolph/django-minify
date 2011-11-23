

import logging
import json
from framework.utils.test import TestCase
from django_minify.minify import MinifyJs
import os
from django_minify.utils import LANGUAGE_ID, replace_lang
from django_minify.utils import expand_on_lang
from django_minify.exceptions import FromCacheException

logger = logging.getLogger(__name__)

from functools import partial

    
class TestLangSupport(TestCase):
    def test_lang_file_minify(self):
        simple, lang = self.get_files()
        lang_minify = MinifyJs(lang)
        combined_filename = lang_minify.get_combined_filename(force_generation=True)
        self.assertLang(combined_filename)
        minified_filename = lang_minify.get_minified_filename(force_generation=True)
        self.assertLang(minified_filename)
        
        self.assertValidLangPath(minified_filename)

    def test_lang_file_minify_with_missing_file(self):
        '''
        Generates, removes one of the files, and subsequently tries again.
        Used for testing failures half way through the script
        '''
        simple, lang = self.get_files()
        lang_minify = MinifyJs(lang)
        combined_filename = lang_minify.get_combined_filename(force_generation=True)
        self.assertLang(combined_filename)
        minified_filename = lang_minify.get_minified_filename(force_generation=True)
        pt_filename = replace_lang(minified_filename, 'pt-br')
        self.assertLang(minified_filename)
        self.assertValidLangPath(minified_filename)
        #remove one of the files and see if things will still work :)
        assert os.path.isfile(pt_filename)
        os.remove(pt_filename)
        
        #try with from cache disabled
        minified_filename = lang_minify.get_minified_filename(force_generation=True)
        pt_filename = replace_lang(minified_filename, 'pt-br')
        #this shouldnt have been regenerated
        #TODO: Maybe it would be desired behaviour to rebuild
        assert not os.path.isfile(pt_filename)
        
        #try with from cache enabled
        from django_minify.conf import settings
        OLD_FROM_CACHE, OLD_DEBUG = settings.FROM_CACHE, settings.DEBUG
        settings.FROM_CACHE = True
        settings.DEBUG = False
        try:
            minified_filename = lang_minify.get_minified_filename(force_generation=True)
            pt_filename = replace_lang(minified_filename, 'pt-br')
            #this shouldnt have been regenerated
            assert not os.path.isfile(pt_filename)
        finally:
            settings.FROM_CACHE = OLD_FROM_CACHE
            settings.DEBUG = OLD_DEBUG
        

    def test_file_minify(self):
        simple, lang = self.get_files()
        lang_minify = MinifyJs(simple)
        combined_filename = lang_minify.get_combined_filename(force_generation=True)
        minified_filename = lang_minify.get_minified_filename(force_generation=True)
        
    def test_failing_minify(self):
        from django_minify.conf import settings
        OLD_FROM_CACHE, OLD_DEBUG = settings.FROM_CACHE, settings.DEBUG
        settings.FROM_CACHE = True
        settings.DEBUG = False
        simple, lang = self.get_files()
        test_files = [simple, lang]
        try:
            for files in test_files:
                try:
                    lang_minify = MinifyJs(files)
                    combined_filename = lang_minify.get_combined_filename(force_generation=True, raise_=True)
                    minified_filename = lang_minify.get_minified_filename(force_generation=True)
                    raise ValueError, "We were expecting a from cache exceptions"
                except FromCacheException, e:
                    pass
        finally:
            settings.FROM_CACHE = OLD_FROM_CACHE
            settings.DEBUG = OLD_DEBUG
        
        
        
    def get_files(self):
        simple = [u'jquery.js']
        lang = [u'fashiolista.js', os.path.join('translated','i18n_<lang>.js')]
        return simple, lang
    
    def assertLang(self, name_or_path):
        assert LANGUAGE_ID in name_or_path, 'Didnt find %s in %s' % (LANGUAGE_ID, name_or_path)
        
    def assertValidLangPath(self, name_or_path):
        self.assertLang(name_or_path)
        language_specific_files = expand_on_lang(name_or_path)
        for language_specific_path in language_specific_files:
            assert os.path.isfile(language_specific_path), 'File %s coudnt be found' % language_specific_path
            f = open(language_specific_path)
            content = f.read()
            assert len(content) > 100
            
        