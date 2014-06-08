
import unittest

from mock import Mock
from io import StringIO
from rhythmweb.server import Server
from rhythmweb.view import app, route

class TestNewServer(unittest.TestCase):

    def test_create_server(self):
        server = Server(Mock())
        self.assertIsNotNone(server)

    def test_get_index_file(self):
        server = Server(Mock())
        response = Mock()
        server.handle_request({}, response)
        content = app.get_file('/index.html', 'default')
        self.assertIsNotNone(content)
        response.reply_with_file.assert_called_with(content)

    def test_file_not_found(self):
        server = Server(Mock())
        response = Mock()
        server.handle_request({}, response)
        app.get_file('/index.py', 'default')
        response.reply_with_not_found.assert_called_with()

    def test_return_dict_with_path_argument(self):
        server = Server(Mock())
        response = Mock()
        server.handle_request({'PATH_INFO': '/something/myarg'}, response)
        response.reply_with_json.assert_called_with({'the_argument', 'myarg'})

    def test_post_parameters(self):
        server = Server(Mock())
        response = Mock()
        server.handle_request(
            {
                'PATH_INFO': '/path/with/kwargs',
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': 'application/x-www-form-urlencoded',
                'wsgi.input': StringIO('key1=value1&key2=value2')
            }, response)
        response.reply_with_json.assert_called_with({
            'key1': ['value1'],
            'key2': ['value2']})



@route('/something/<argument>')
def try_one_path_argument(argument):
    return {'the_argument', argument}

@route('/path/with/kwargs')
def path_with_kwargs(**kwargs):
    return kwargs
