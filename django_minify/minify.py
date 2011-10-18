from __future__ import with_statement
import os
import subprocess
from django_minify.conf import settings
from framework.middleware.spaceless import SpacelessMiddleware
import gzip
import portalocker
import logging

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


class DummyCache(object):
    # Does nothing at all
    def __init__(self, *args, **kwargs):
        pass

    def get(self, key, default=None):
        pass

    def __setitem__(self, key, value):
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
    
    def _gzip_file(self, filename):
        fh = open(filename)
        with portalocker.Lock(filename + '.gz', timeout=MAX_WAIT):
            gzfh = gzip.open(filename + '.gz', 'wb')
            gzfh.writelines(fh)
        fh.close()
    
    def get_combined_filename(self):
        cached_file = self.cache.get(tuple(self.files))

        if settings.DEBUG:
            # Always continue when DEBUG is enabled
            pass
        elif settings.FROM_CACHE:
            if cached_file:
                return cached_file
            else:
                import logging
                logging.error('Unable to generate cache because '
                    '`MINIFY_FROM_CACHE` is enabled')
        
        timestamp = 0
        digest = abs(hash(','.join(self.files)))
        
        files = []
        # the filename will be max(timestamp
        for file_ in self.files:
            fullpath = os.path.join(settings.MEDIA_ROOT, self.extension,
                'original', file_)
            stat = os.stat(fullpath)
            timestamp = max(timestamp, stat.st_mtime, stat.st_ctime)
            files.append(fullpath)
        
        cached_file = os.path.join(self.cache_dir, '%d_debug_%d.%s' % 
            (digest, timestamp, self.extension))
        
        if not os.path.isfile(cached_file):
            if not os.path.isdir(self.cache_dir):
                os.makedirs(self.cache_dir)

            cached_file = self._generate_combined_file(cached_file, files)
        
        self.cache[tuple(self.files)] = cached_file
        return cached_file

    def _generate_combined_file(self, filename, files):
        with portalocker.Lock(filename + '.tmp', timeout=MAX_WAIT) as fh:
            for file_ in files:
                read_fh = open(file_)

                # Add the spaceless version to the output
                data = SpacelessMiddleware.strip_content_safe(read_fh.read())
                print >>fh, data
                read_fh.close()

            name = os.path.splitext(os.path.split(filename)[1])[0]
            if self.extension == 'js':
                js = 'var file_%s = true;' % name
                print >>fh, js
                js = 'var file_%s = true;' % name.replace('debug', 'mini')
                print >>fh, js
            elif self.extension == 'css':
                css = '#file_%s{color: #FF00CC;}' % name
                print >>fh, css
                css = '#file_%s{color: #FF00CC;}' % name.replace('debug', 'mini')
                print >>fh, css
            else:
                raise TypeError('Extension %r is not supported'
                    % self.extension)

        os.rename(filename + '.tmp', filename)
        return filename
    
    def get_minified_filename(self):
        input_filename = self.get_combined_filename()
        filename = input_filename.rpartition('_debug_')
        output_filename = ''.join([filename[0], '_mini_', filename[2]])
        if output_filename in self.cache:
            return output_filename

        else:
            if not os.path.isfile(output_filename):
                tmp_filename = output_filename + '.tmp'
                with portalocker.Lock(tmp_filename, timeout=MAX_WAIT):
                    self._minimize_file(input_filename, tmp_filename)

                os.rename(tmp_filename, output_filename)

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


