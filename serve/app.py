import os
import cgi
import re

from datetime import timedelta, datetime

import logging
log = logging.getLogger(__name__)

class CGIApplication(object):

    def __init__(self, path, config):
        try:
            log.debug('Application started')

            self.config = config
            self.web_path = os.path.join(path, 'web')
            self.resources_path = os.path.join(path, 'resources')

        except:
            log.error('Exception intializing application', exc_info=True)

    def handle_request(self, environ, response):
        method = environ['REQUEST_METHOD']
        log.debug('Handling method %s' % method)
        def do_return(value):
            if type(value) is str:
                return bytes(value, 'UTF-8')
            return value

        try:
            return_value = ''
            if method == 'GET':
                return_value = self.do_get(environ, response)
                yield do_return(return_value)

            elif method == 'POST':
                params = self.parse_post(environ)
                if params is None:
                    log.debug('No parameters in POST method')
                decoded_params = {}
                for key in params:
                    decoded_params[key.decode('UTF-8')] = [value.decode('UTF-8') for value in params[key]]
                return_value = self.do_post(environ, decoded_params, response)
                yield do_return(return_value)

            else:
                self.send_error(
                    500,
                    '%s Not implemented' % method,
                    response)

        except Exception as e:
            log.error('Exception handling request', exc_info=True)
            yield self.send_error(
                 500,
                 '%s Unknown exception' % e,
                 response)

    def parse_post(self, environ):
        log.debug('Parsing post parameters')
        if 'CONTENT_TYPE' in environ:
            length = -1
            if 'CONTENT_LENGTH' in environ:
                length = int(environ['CONTENT_LENGTH'])
            if environ['CONTENT_TYPE'] == 'application/x-www-form-urlencoded':
                return cgi.parse_qs(environ['wsgi.input'].read(length))
            if environ['CONTENT_TYPE'] == 'multipart/form-data':
                return cgi.parse_multipart(environ['wsgi.input'].read(length))
            else:
                return cgi.parse_qs(environ['wsgi.input'].read(length))
        return None

    def do_get(self, environ, response):
        log.debug('Invoking get method')
        return self.handle_method('get', environ, response)

    def do_post(self, environ, params, response):
        log.debug('Invoking post method')
        log.debug('POST parameters:')
        if params:
            for param in params:
                log.debug("   %s = %s" % (param, params[param]))
        return self.handle_method('post', environ, response, params)


    def get_resource_path(self, environ):
        theme_key = 'theme'
        if 'HTTP_USER_AGENT' in environ:
            agent = environ['HTTP_USER_AGENT']
            if re.search('(Android|iPhone)', agent):
                theme_key = 'theme.mobile'
        theme = self.config.get_string(theme_key)
        resource_path = os.path.join(self.resources_path, theme)
        return resource_path

    def handle_method(self, request_method, environ, response, params=None):
        log.debug('-------------------------------------')
        log.debug('ENVIRONMENT for method %s: ' % request_method)
        for e in sorted(environ):
            log.debug('   %s = %s' % (e, environ[e]))
        log.debug('-------------------------------------')
        request_path = environ['PATH_INFO']
        if not request_path or request_path == '/':
            request_path = '/index.html'
        if not request_path.startswith('/'):
            request_path = '/' + request_path
        log.debug('handling %s method - path: %s' % (request_method.upper(), request_path))

        resource_path = self.get_resource_path(environ)
        web_path = self.web_path

        path_options = str(request_path).split('/')
        walked_path = ''
        try:
            for name in path_options:
                if not name:
                    continue

                walked_path += '/' + name
                resource_path = os.path.join(resource_path, name)
                web_path = os.path.join(web_path, name)

                if self.is_python_file(web_path):
                    log.debug('Found file %s, loading "Page" class' % web_path)

                    path_params = request_path.replace(walked_path, '')
                    environ['PATH_PARAMS'] = path_params

                    instance = self.create_instance(web_path)
                    the_method = 'do_' + request_method
                    if not hasattr(instance, the_method):
                        raise ServerException(501, \
                                              'Object %s does not have a %s method' % \
                                                (instance, request_method))
                        # NOT IMPLEMENTED

                    try:
                        method = getattr(instance, the_method)
                        if params is None:
                            return method(environ, response)
                        else:
                            return method(environ, params, response)

                    except Exception as e:
                        raise ServerException(500, '%s ERROR - %s' %
                                              (request_method, e.message))

                elif self.is_resource_file(web_path):
                    log.debug('Handling web resource %s' % web_path)
                    resource = self.get_resource_handler(web_path)
                    return resource.handle(response, environ)

                elif self.is_resource_file(resource_path):
                    log.debug('Handling file resource %s' % resource_path)
                    resource = self.get_resource_handler(resource_path)
                    return resource.handle(response, environ)

                else:
                    continue

            log.debug('404 - Could not find resource %s' % request_path)
            raise ServerException(404, 'Could not find resource %s' % request_path)
            # NOT FOUND

        except ServerException as e:
            log.error('Exception handling method %s' % request_method, exc_info=True)
            return self.send_error(e.code, e.message, response)

        except Exception as e:
            log.error('Exception handling method %s' % request_method, exc_info=True)
            return self.send_error(500, e.message, response)
            # UNKNOWN ERROR

    def is_python_file(self, file):
        basename = os.path.basename(file)
        basepath = os.path.dirname(file)
        (filename, extension) = os.path.splitext(basename)

        if not extension:
            extension = '.py'
        elif not extension == '.py':
            return False
        py_file = os.path.join(basepath, filename + extension)

        return os.path.isfile(py_file)

    def is_resource_file(self, file):
        return os.path.isfile(file)

    def create_instance(self, page_path):
        log.debug('Importing module path %s' % page_path)

        class_path = os.path.splitext(page_path)[0]
        class_path = class_path.replace(self.web_path, '')
        class_path = class_path.replace('/', '.')
        class_path = 'web' + class_path
        log.debug('Importing class path %s' % class_path)

        mod = None
        try:
            mod = __import__(class_path, globals(), locals(), ['Page'])
        except Exception as e:
            log.warn('Import error for file %s: %s' % (class_path, e))

        if mod is None:
            raise ServerException(501, 'Could not load module %s' % page_path)

        klass = getattr(mod, 'Page')
        if not klass:
            raise ServerException(501, 'Module %s does not contains a Page class' % page_path)

        return klass()

    def send_error(self, code, message, response):
        log.error('Returning error \'%s\' %s' % (code, message), exc_info=True)
        error_message = '%d %s' % (code, message)
        response(error_message, self.__default_headers())
        return 'ERROR: %s' % message

    def get_resource_handler(self, resource):
        return ResourceHandler(resource) # dont cache

    def __default_headers(self, headers=[]):
        if not headers:
            headers = [('Content-type', 'text/html; charset=UTF-8')]
        return headers


class ResourceHandler(object):

    def __init__(self, resource):
        log.debug('Creating ResourceHandler for resource %s' % resource)
        self.resource = resource
        self.extension = str(os.path.splitext(self.resource)[1]).lower()
        self.content_types = {
            '.css': ('text/css', 't'),
            '.htm': ('text/html', 't'),
            '.html': ('text/html', 't'),
            '.gif': ('image/gif', 'b'),
            '.png': ('image/png', 'b'),
            '.jpg': ('image/jpeg', 'b'),
            '.jpeg': ('image/jpeg', 'b'),
            '.ico': ('image/ico', 'b'),
            '.svg': ('image/svg+xml', 't'),
            '.js': ('application/x-javascript', 't'),
        }

    def handle(self, response, accept_gzip=False):
        log.debug('Handling resource %s' % self.resource)

        (content_type, open_as) = self.content_types.get(self.extension,
                ('text/plain', 't'))

        mtime = os.path.getmtime(self.resource)
        mtime = datetime.fromtimestamp(mtime)
        expiration = datetime.now() + timedelta(days=365)

        headers = [("Content-type", content_type), \
                    ('Cache-Control', 'public'), \
                    ('Last-Modified', mtime.ctime()), \
                    ('Expires', expiration.ctime())]

        open_mode = 'r%s' % open_as

        with open(self.resource, open_mode) as f:
            response('200 OK', headers)
            return f.read()


class ServerException(Exception):

    def __init__(self, code, message):
        self.code = int(code)
        self.message = message


class ClientError(ServerException):

    def __init__(self, message):
        super(ClientError, self).__init__(400, 'Bad request: {}'.format(message))
