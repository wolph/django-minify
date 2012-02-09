from coffin.template import Library
from django_minify import minify
from django_minify.conf import settings
from django_minify.templatetags import combine
from jinja2 import Markup, contextfunction, ext, nodes
import urlparse

register = Library()


class MinifyExtension(ext.Extension):
    tags = None
    template = None
    extension = None
    Minifier = None
    
    def __init__(self, *args, **kwargs):
        super(MinifyExtension, self).__init__(*args, **kwargs)
        assert self.tags, 'Extensions should be linked to one or more tags'
        assert self.template, ('MinifyExtensions require a template to '
            'render (even "%s" works)')
        assert self.extension, ('An extension for the output files is '
            'required')
        assert self.Minifier, 'The extension requires a minifying module'

    def parse(self, parser):
        lineno = parser.stream.next().lineno
        includes = parser.parse_statements(['name:%s' % self.tags[-1]],
            drop_needle=True)

        return nodes.CallBlock(
            self.call_method('_render', [], [], None, None),
            [], [], includes,
        ).set_lineno(lineno)

    def _get_setting(self, request, key):
        setting = ('%s_%s' % (self.extension, key)).upper()
        if request:
            get_var = request.GET.get(key, '').lower()
        else:
            get_var = None

        if get_var in ('1', 'true'):
            out = True
        elif get_var in ('0', 'false'):
            out = False
        else:
            out = getattr(settings, setting, True)

        return out

    def _get_minify_setting(self, request):
        return self._get_setting(request, 'minify')

    def _get_compress_setting(self, request):
        return self._get_setting(request, 'compress')

    @contextfunction
    def _render(self, context, caller=None):
        code = unicode(caller()).strip()
        return Markup(self.template % code)

def flatten_nodes(nodes_):
    output = []
    for node in nodes_:
        if isinstance(node, nodes.Output):
            output += flatten_nodes(node.nodes)
        elif isinstance(node, nodes.TemplateData):
            output += node.data.strip().split()
        else:
            raise TypeError('Node %r has unknown type %s' %
                (node, type(node)))
    
    # Return only non-zero strings and strip the whitespace
    return [y for x in output for y in [x.strip()] if y]

class IncludeExtension(MinifyExtension):
    '''
    Responsible for parsing the template syntax.
    Based on settings.DEBUG either calls the specified minifier or simply outputs the files
    Returns html including the script tags
    '''
    def parse(self, parser):
        lineno = parser.stream.next().lineno
        includes = flatten_nodes(parser.parse_statements(
            ['name:%s' % self.tags[-1]],
            drop_needle=True,
        ))

        base_path = '/'.join([settings.MEDIA_URL, self.extension, 'original'])
        
        output_nodes = []
        if settings.DEBUG and not getattr(settings, 'TEST_COMPILE', False):
            for include in includes:
                html = self.template % '/'.join([base_path, include])
                output_nodes.append(nodes.Const(html))

        else:
            minifier = self.Minifier(includes)
            html = self.template % minifier.get_minified_url()
            output_nodes.append(nodes.Const(html))
            
        #args seems to be the parsed bit of template, not stadnard python args :(
        callable = self.call_method('_render', [nodes.List(output_nodes)])
        block = nodes.CallBlock(callable, [], [], [])
        block = block.set_lineno(lineno)
        
        return block
    
    def _join_nodes(self, context, nodes, separator=''):
        html = separator.join(nodes)
        html = html.replace('<lang>', context['LANGUAGE_CODE'])
	return html

    @contextfunction
    def _render(self, context, output_nodes, *args, **kwargs):
        '''
        Replace the language code in order to access the different files, either
        combined or single files (on debug)
        '''
        html = self._join_nodes(context, output_nodes)
        markup = Markup(html)
        return markup


class CssExtension(MinifyExtension):
    Minifier = minify.MinifyCss
    extension = 'css'


class JsExtension(MinifyExtension):
    Minifier = minify.MinifyJs
    extension = 'js'

class JsIncludeExtension(JsExtension, IncludeExtension):
    tags = ['jsinclude', 'endjsinclude']
    template = settings.JS_INCLUDE

    def _get_filename(self, request, include, minify):
        if minify or len(include) != 1:
            url = IncludeExtension._get_filename(self, request, include, minify)
        else:
            url = settings.MEDIA_URL + include[0]
        
        return url

register.tag(JsIncludeExtension)

class JsHeadIncludeExtension(JsIncludeExtension):
    """
    wraps all nodes with a template 
    <head>...</head> or head.js(...);
    """
    tags = ['js_head_include', 'endjs_head_include']
    template = settings.JS_HEAD_INCLUDE
    js_head_template = settings.JS_HEAD_CONTAINER

    @contextfunction
    def _join_nodes(self, context, nodes):
        html = super(JsHeadIncludeExtension, self)._join_nodes(context, nodes, separator=',')
        return self.js_head_template % html

register.tag(JsHeadIncludeExtension)


class CssIncludeExtension(CssExtension, IncludeExtension):
    tags = ['cssinclude', 'endcssinclude']
    template = settings.CSS_INCLUDE
register.tag(CssIncludeExtension)


class JsMinifyExtension(JsExtension, MinifyExtension):
    tags = ['js', 'endjs']
    template = settings.JS_INLINE
register.tag(JsMinifyExtension)


class CssMinifyExtension(CssExtension, MinifyExtension):
    tags = ['css', 'endcss']
    template = settings.CSS_INLINE
    
register.tag(CssMinifyExtension)


class Combine(ext.Extension):
    # TODO: Deprecated, the `combine tag should be replaced by
    # `js`/`css`/`jsinclude` or `cssinclude`
    tags = set(['combine'])

    def parse(self, parser):
        tag = parser.stream.next()
        lineno = tag.lineno
        body = parser.parse_primary()

        if isinstance(body, nodes.Const):
            files = body.value
        else:
            files = combine._list_to_string([x.value for x in body.items])
        combine.combine_files(files)

        return nodes.Output([
            self.call_method('_combine_files', args=[body], kwargs=[]),
        ]).set_lineno(lineno=lineno)

    @contextfunction
    def _combine_files(self, context, files):
        if not isinstance(files, basestring):
            files = combine._list_to_string(files)
        return combine.combine_files(files, context.get('request'))

register.tag(Combine)
