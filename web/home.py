
from serve.page.base import BasePage
from player import PlayerPanel
from status import StatusPanel
from queue import QueuePanel
from search import SearchPanel

import socket


class Page(BasePage):
    
    _search_results = None
    _queue = None
    _components = None
    
    def __init__(self, components):
        super(BasePage, self).__init__(__file__)
        self._components = components
        self._handler = components['RB']
        self._queue = self._handler.get_play_queue()
    
    
    def name(self):
        return 'HomePage'

    
    def render_template(self, node):
        self.debug('Rendering template %s' % self.name())
        path = self._environ['PATH_INFO']
        host = socket.gethostname()
        node.title.content = 'Rhythmbox Server - %s - %s' % (host, path)
        node.status.raw = StatusPanel(self._components).render()
        node.player.raw = PlayerPanel(self._components).render()
        node.queue.raw = QueuePanel(self._queue, self._components).render()
        node.search.raw = SearchPanel(self._components).render()
        
        # Render search results
        if not self._search_results is None:
            node.search_results.raw = QueuePanel(self._search_results, self._components).render()
        else:
            node.search_results.raw = ''
            
        
    def post(self):
        params = self._parameters
        if 'action' in params:
            action = params['action']
            
            self.debug('Action - %s' % action)
            handler = self._handler
            
            if action == ['play_pause']:
                handler.play_pause()
                
            elif action == ['next']:
                handler.next()
                
            elif action == ['prev']:
                handler.previous()
                
            elif action == ['seek_back']:
                handler.seek(-10)
                
            elif action == ['seek_forward']:
                handler.seek(10)
                
            elif action == ['search']:
                if 'search' in params:
                    filter = params['search'][0]
                    self._search_results = handler.search_song(filter)
                    
            elif action == ['enqueue']:
                if 'song' in params:
                    songs = params['song']
                    self.debug('Enqueuing songs: %s' % songs)
                    handler.enqueue(songs)








