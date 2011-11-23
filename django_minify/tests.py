

import logging
import json
from framework.utils.test import TestCase
from django_minify.minify import MinifyJs
import os
from django_minify.utils import LANGUAGE_ID
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
        
        try:
            try:
                simple, lang = self.get_files()
                lang_minify = MinifyJs(simple)
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
            
        