from __future__ import with_statement
import os
import subprocess
from django_minify.conf import settings
try:
    from framework.middleware.spaceless import SpacelessMiddleware
except ImportError:
    SpacelessMiddleware = None
import gzip
import portalocker
import logging
from django_minify.utils import has_lang, get_languages_list, expand_on_lang,\
    replace_lang, append_lang
from django_minify.exceptions import FromCacheException

try:
    import cPickle as pickle
except ImportError:
    import pickle
    

# Maximum lock wait time in seconds
MAX_WAIT = 5

logger = logging.getLogger(__name__)

class FileCache(object):
    '''Cache object with file backing

    >>> cache = Cache('/tmp/')
    >>> cache['foo'] = 'bar'
    >>> 'foo' in cache
    True
    '''
    def __init__(self, cache_dir):
        self.cache_file = os.path.join(cache_dir, 'index.pickle')
        self.read()
    
    def read(self):
        if(os.path.isfile(self.cache_file) and settings.FROM_CACHE
                and not settings.DEBUG):
            self._cache = pickle.load(open(self.cache_file))
        else:
            self._cache = {}
    
    def write(self):
        pickle.dump(self._cache, open(self.cache_file, 'w'))
    
    def get(self, *args, **kwargs):
        return self._cache.get(*args, **kwargs)
    
    def __setitem__(self, key, value):
        self._cache[key] = value

    def __contains__(self, key):
        return key in self._cache
    
    def __unicode__(self):
        return unicode(self._cache)
    
    def __repr__(self):
        return repr(self._cache)


class DummyCache(object):
    # Does nothing at all
    def __init__(self, *args, **kwargs):
        pass

    def get(self, key, default=None):
        pass

    def __setitem__(self, key, value):
        pass

    def write(self):
        pass

    def __contains__(self, key):
        return False


if settings.DEBUG:
    Cache = DummyCache
else:
    Cache = FileCache


class Minify(object):
    COMPRESSION_COMMAND = None
    cache_dir = None
    extension = None
    
    def __init__(self, files=None):
        if not self.cache and not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        if files:
            self.files = files
        else:
            self.files = []
    
    def _minimize_file(self, input_filename, output_filename):
        '''
        '''
        if self.COMPRESSION_COMMAND:
            cmd = self.COMPRESSION_COMMAND % dict(
                output_filename=output_filename,
                input_filename=input_filename,
            )
            logger.info('Compressing with %r', cmd)
            p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)
            _, err = p.communicate()
            if p.returncode or err:
                raise RuntimeError, 'Unable to compress %r: %s' % (self.files,
                    err)
        else:
            logger.error('Skipping compression, COMPRESSION_COMMAND not '
                'defined')
            fout = open(output_filename, 'w')
            fin = open(input_filename)
            fout.write(fin.read())
            fout.close()
            fin.close()
        return output_filename
    
    def _gzip_file(self, filename):
        fh = open(filename)
        with portalocker.Lock(filename + '.gz', timeout=MAX_WAIT):
            gzfh = gzip.open(filename + '.gz', 'wb')
            gzfh.writelines(fh)
        fh.close()
    
    def get_combined_filename(self, force_generation=False, raise_=False):
        cached_file_path = self.cache.get(tuple(self.files))
        if settings.DEBUG:
            # Always continue when DEBUG is enabled
            pass
        elif settings.FROM_CACHE:
            if cached_file_path:
                return cached_file_path
            else:
                logging.error('Unable to generate cache because '
                    '`MINIFY_FROM_CACHE` is enabled was trying to compile %s', self.files)
                if raise_:
                    raise FromCacheException('When FROM CACHE is enabled you cannot access the file system, was trying to compile %s' % self.files)
        
        timestamp = 0
        digest = abs(hash(','.join(self.files)))
        
        files = []
        language_specific = has_lang(self.files)
        # the filename will be max(timestamp
        for file_ in self.files:
            simple_fullpath = os.path.join(settings.MEDIA_ROOT, self.extension,
                'original', file_)
            fullpaths = expand_on_lang(simple_fullpath)
            #expand to language specific versions, because if they changed we need to redirect
            for fullpath in fullpaths:
                stat = os.stat(fullpath)
                timestamp = max(timestamp, stat.st_mtime, stat.st_ctime)
            #simple fullpath is the version with <lang> still in there
            files.append(simple_fullpath)
        
        cached_file_path = os.path.join(self.cache_dir, '%d_debug_%d.%s' % 
            (digest, timestamp, self.extension))
        
        
        if not os.path.isfile(cached_file_path) or force_generation:
            if not os.path.isdir(self.cache_dir):
                os.makedirs(self.cache_dir)
            cached_file_path = self._generate_combined_file(cached_file_path, files)
        elif language_specific:
            cached_file_path = append_lang(cached_file_path)
            
        self.cache[tuple(self.files)] = cached_file_path
        
        return cached_file_path

    def _generate_combined_file(self, filename, files):
        '''
        Generate the combined file
        If there is a <lang> param used we support is by generating multiple versions
        And returning a combined filename with <lang> in it
        
        filename = the file we are writing to
        files = the list of files we are compiling
        
        Generates a stripped version of each file. Expanding language_specific files where needed
        Subsequently gets a combined file per locale
        Finally it writes a file per locale with this output 
        '''
        name = os.path.splitext(os.path.split(filename)[1])[0]
        language_specific = has_lang(files)
        
        #combined output per locale
        combined_per_locale = dict()
        #store the stripped file per path
        stripped_files_dict = dict()
        
        #loop through all files and combine them, expand if there is a <lang>
        for file_path in files:
            localized_paths = expand_on_lang(file_path)
            for localized_path in localized_paths:
                read_fh = open(localized_path)
                # Add the spaceless version to the output
                if SpacelessMiddleware:
                    data = SpacelessMiddleware.strip_content_safe(read_fh.read())
                else:
                    data = read_fh.read()
                stripped_files_dict[localized_path] = data
                read_fh.close()
                
        #generate the combined file for each locale
        locales = get_languages_list(language_specific)
        for locale in locales:
            #get the language_specific versions of the files and combine them
            combined_output = ''
            for file_path in files:
                file_path = replace_lang(file_path, locale)
                content = stripped_files_dict[file_path]
                combined_output += content
                combined_output += '\n'
            
            #postfix some debug info to ensure we can check for the file's validity
            if self.extension == 'js':
                js = 'var file_%s = true;' % name
                combined_output += js
                js = 'var file_%s = true;' % name.replace('debug', 'mini')
                combined_output += js
            elif self.extension == 'css':
                css = '#file_%s{color: #FF00CC;}' % name
                combined_output += css
                css = '#file_%s{color: #FF00CC;}' % name.replace('debug', 'mini')
                combined_output += css
            else:
                raise TypeError('Extension %r is not supported'
                    % self.extension)
                
            combined_per_locale[locale] = combined_output
            
        #write the combined version per locale to temporary files and then move them
        #to their locale specific file
        for locale in locales:
            combined_output = combined_per_locale[locale]
            postfix = '%s.tmp' % locale
            temp_file_path = filename + postfix
            
            path, ext = os.path.splitext(filename)
            final_file_path = filename.replace(ext, '%s%s' % (locale, ext)) if locale else filename
            
            #be atomic!
            with portalocker.Lock(temp_file_path, timeout=MAX_WAIT) as fh:
                fh.write(combined_output)
    
            
            if os.path.isfile(final_file_path):
                os.remove(final_file_path)
            os.rename(filename + postfix, final_file_path)
        
        if language_specific:
            filename = append_lang(filename)
            
        return filename
    
    def get_minified_filename(self, force_generation=False):
        '''
        Returns the minified filename, for language specific files it will return
        filename_<lang>.js
        '''
        input_filename = self.get_combined_filename()
        output_filename = input_filename.replace('_debug_', '_mini_')
        if output_filename in self.cache:
            #if the output is cached, immediatly return it without checking the filesystem
            return output_filename
        else:
            error_message = 'There is no file cache available, but we arent allowed to build the files. Searching for %s in %s' % (output_filename, self.cache)
            assert not settings.FROM_CACHE, error_message
            #see if all the files we need are actually there
            compiled_files_available = True
            output_filenames = expand_on_lang(output_filename)
            for lang_specific_filename in output_filenames:
                if not os.path.isfile(lang_specific_filename):
                    compiled_files_available = False
            
            if not compiled_files_available or force_generation:
                #loop over the various locales
                input_filenames = expand_on_lang(input_filename)
                for input_filename in input_filenames:
                    lang_specific_output_path = input_filename.replace('_debug_', '_mini_')
                    tmp_filename = lang_specific_output_path + '.tmp'
                    #compile towards a temporary file, which only this process and its children can touch
                    if os.name == 'nt':
                        #child processes cant access things we lock under windows like environments
                        self._minimize_file(input_filename, tmp_filename)
                    else:
                        with portalocker.Lock(tmp_filename, timeout=MAX_WAIT):
                            self._minimize_file(input_filename, tmp_filename)
                    #raise an error if the file exist, or remove it if rebuilding
                    if os.path.isfile(lang_specific_output_path):
                        os.remove(lang_specific_output_path)
                        if not force_generation:
                            logger.warn('%r already exists', lang_specific_output_path)
                    os.rename(tmp_filename, lang_specific_output_path)
                    assert os.path.isfile(lang_specific_output_path)

            self.cache[output_filename] = True
            
        return output_filename
    
    @classmethod
    def _filename_to_url(cls, filename):
        filename = os.path.abspath(filename).replace('\\', '/')
        media_root = os.path.abspath(settings.MEDIA_ROOT).replace('\\', '/')
        relative_filename = filename.replace(media_root, '').strip('/')
        return settings.MEDIA_URL + relative_filename
    
    def get_combined_url(self):
        return self._filename_to_url(self.get_combined_filename())
    
    def get_minified_url(self):
        return self._filename_to_url(self.get_minified_filename())

class MinifyCss(Minify):
    extension = 'css'
    COMPRESSION_COMMAND = settings.CSS_COMPRESSION_COMMAND
    root_dir = os.path.join(settings.MEDIA_ROOT, extension)
    cache_dir = os.path.join(root_dir, 'cache')
    cache = Cache(cache_dir)


class MinifyJs(Minify):
    extension = 'js'
    COMPRESSION_COMMAND = settings.JS_COMPRESSION_COMMAND
    root_dir = os.path.join(settings.MEDIA_ROOT, extension)
    cache_dir = os.path.join(root_dir, 'cache')
    cache = Cache(cache_dir)

    
def minify(path, files, extension, minimize=True, compress=True, prefix='',
        force=False):
    if extension == 'js':
        Minifier = MinifyJs
    elif extension == 'css':
        Minifier = MinifyCss
    else:
        raise TypeError, 'unknown extension %r' % extension
    
    if path:
        files = [os.path.join(path + f) for f in files]
    
    minifier = Minifier(files)
    if minimize:
        return minifier.get_minified_filename()
    else:
        return minifier.get_combined_filename()

if __name__ == '__main__':
    import doctest
    doctest.runtest()


