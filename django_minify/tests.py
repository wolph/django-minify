

import logging
import json
from framework.utils.test import TestCase
from django_minify.minify import MinifyJs


logger = logging.getLogger(__name__)

from functools import partial
    
class TestLangSupport(TestCase):
    def get_files(self):
        simple = [u'jquery.js']
        lang = [u'fashiolista.js', u'translated/i18n_<lang>.js']
        return simple, lang
    
    def test_file_combination(self):
        simple, lang = self.get_files()
        lang_minify = MinifyJs(lang)
        lang_minify.get_combined_filename(force_generation=True)
    
