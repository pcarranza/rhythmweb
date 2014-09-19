import random
import logging
log = logging.getLogger(__name__)

from gi.repository import RB, GLib
from rhythmweb.utils import to_list, to_int

ORDER_LINEAR = 'linear'
ORDER_SHUFFLE = 'shuffle'
ORDER_SHUFFLE_BY_AGE_AND_RATING = 'random-by-age-and-rating'
ORDER_SHUFFLE_BY_AGE = 'random-by-age'
ORDER_SHUFFLE_BY_RATING = 'random-by-rating'
ORDER_SHUFFLE_EQUALS = 'random-equal-weights'

PLAY_ORDER_KEY = '/apps/rhythmbox/state/play_order'
PLAY_LOOP = '-loop'

TYPE_SONG = 'song'
TYPE_RADIO = 'iradio'
TYPE_PODCAST = 'podcast-post'

RB_SOURCELIST_MODEL_COLUMN_PLAYING = 0
RB_SOURCELIST_MODEL_COLUMN_PIXBUF = 1
RB_SOURCELIST_MODEL_COLUMN_NAME = 2
RB_SOURCELIST_MODEL_COLUMN_SOURCE = 3
RB_SOURCELIST_MODEL_COLUMN_ATTRIBUTES = 4
RB_SOURCELIST_MODEL_COLUMN_VISIBILITY = 5
RB_SOURCELIST_MODEL_COLUMN_IS_GROUP = 6
RB_SOURCELIST_MODEL_COLUMN_GROUP_CATEGORY = 7

SOURCETYPE_PLAYLIST = 'playlist'
SOURCETYPE_SOURCE = 'source'


class RBHandler(object):
    """
    Rhythmbox shell wrapper, provides player, queue, playlist,
    artist/album/genre count cache and max instances
    and some other functionallities
    """

    def __init__(self, shell):
        """
        Creates a new rhythmbox handler, wrapping the RBShell object that gets
        by parameter
        """
        if not shell:
            raise ValueError('Shell object cannot be null')

        log.debug('Loading rb handler')

        self.shell = shell
        self.player = shell.props.shell_player
        self.db = shell.props.db
        self.queue_source = self.shell.props.queue_source

        LINEAR_LOOP = "%s%s" % (ORDER_LINEAR, PLAY_LOOP)
        SHUFFLE_LOOP = "%s%s" % (ORDER_SHUFFLE, PLAY_LOOP)

        self._play_toggle_loop = {
            ORDER_LINEAR : LINEAR_LOOP,
            LINEAR_LOOP : ORDER_LINEAR,
            ORDER_SHUFFLE : SHUFFLE_LOOP,
            SHUFFLE_LOOP : ORDER_SHUFFLE}

        self._play_toggle_shuffle = {
            ORDER_LINEAR : ORDER_SHUFFLE,
            ORDER_SHUFFLE : ORDER_LINEAR,
            LINEAR_LOOP : SHUFFLE_LOOP,
            SHUFFLE_LOOP : LINEAR_LOOP,
            ORDER_SHUFFLE_EQUALS : ORDER_LINEAR,
            ORDER_SHUFFLE_BY_AGE : ORDER_LINEAR,
            ORDER_SHUFFLE_BY_RATING : ORDER_LINEAR,
            ORDER_SHUFFLE_BY_AGE_AND_RATING : ORDER_LINEAR}

        self.entry_types = {}
        for entry_type in [TYPE_SONG, TYPE_RADIO, TYPE_PODCAST]:
            rb_type = self.db.entry_type_get_by_name(entry_type)
            self.entry_types[entry_type] = rb_type
        self.entry_types['radio'] = self.entry_types[TYPE_RADIO]

        log.debug('rb handler loaded')

    def get_playing_status(self):
        log.debug('get playing status')
        return self.player.get_playing()[1]

    def get_mute(self):
        log.debug('get mute')
        return self.player.get_mute()[1]

    def toggle_mute(self):
        log.debug('toggle mute')
        self.player.toggle_mute()

    def get_volume(self):
        log.debug('get volume')
        return self.player.get_volume()[1]

    def set_volume(self, volume):
        volume = float(volume)
        log.debug('set volume %d' % volume)
        if volume > 1: log.warning('Volume cannot be set over 1')
        self.player.set_volume(volume)

    def get_playing_entry(self):
        log.debug('get playing entry')
        entry = self.player.get_playing_entry()
        return RBEntry(entry) if entry else None

    def get_playing_time(self):
        log.debug('get playing time')
        return self.player.get_playing_time()[1]

    def get_playing_time_string(self):
        log.debug('get playing time string')
        return self.player.get_playing_time_string()

    def play_next(self):
        log.debug('skip to next')
        if self.get_playing_status():
            self.player.do_next()

    def seek(self, seconds):
        seconds = int(seconds)
        log.debug('seek %d seconds' % seconds)
        self.player.seek(seconds)

    def previous(self):
        log.debug('skip to previous')
        if self.get_playing_status():
            self.player.do_previous()

    def play_pause(self):
        log.debug('play/pause')
        status = self.get_playing_status()
        return self.player.playpause(not status)

    def pause(self):
        log.debug('pause')
        if self.get_playing_status():
            self.play_pause()

    def play_entry(self, entry_id):
        log.debug('play entry {}'.format(entry_id))
        entry = self.get_entry(entry_id)
        if not entry:
            log.debug('no entry found')
            return
        self.pause()
        playing_source = self.player.props.queue_source
        if entry.get_entry_type() == self.entry_types['radio']:
            playing_source = self.shell.get_source_by_entry_type(self.entry_types['radio'])
        self.player.play_entry(entry, playing_source)

    def toggle_shuffle(self):
        log.debug('toggle shuffle')
        play_order = self.get_play_order()
        new_status = self._play_toggle_shuffle[play_order]
        self.set_play_order(new_status)

    def toggle_loop(self):
        log.debug('toggle loop')
        old_order = self.get_play_order()
        new_order = ORDER_LINEAR
        if old_order in self._play_toggle_loop:
            new_order = self._play_toggle_loop[old_order]
        self.set_play_order(new_order)

    def get_play_order(self):
        log.debug('get play order')
        return self.player.props.play_order

    def set_play_order(self, play_order):
        log.debug('set play order: {}'.format(play_order))
        self.player.props.play_order = play_order

#    def playing_song_changed(self, player, entry):
#        log.debug('Playing song changed....')
#        if not self.__playing_song is None:
#            old_playcount = self.__playing_song.play_count
#            old_entry = self.get_entry(self.__playing_song.id)
#            new_play_count = self.get_value(old_entry, RB.RhythmDBPropType.PLAY_COUNT)
#            if old_playcount < new_play_count:
#                diff = new_play_count - old_playcount
#                self.__append_artist(self.__playing_song.artist, diff)
#                self.__append_album(self.__playing_song.album, diff)
#                self.__append_genre(self.__playing_song.genre, diff)
#
#        if entry is None:
#            self.__playing_song = None
#        else:
#            self.__playing_song = self.load_rb_entry(entry)

    # QUEUE
    def get_play_queue(self, queue_limit=100):
        log.debug('get play queue, limit: {}'.format(queue_limit))
        return [entry for entry in Reader(self.get_play_queue_model(), limit=queue_limit)]

    def get_play_queue_model(self):
        log.debug('get play queue model')
        return self.queue_source.props.query_model

    def clear_play_queue(self):
        log.debug("Cleaning playing queue")
        for entry in Reader(self.get_play_queue_model()):
            self.dequeue(entry)
        log.debug("Playing queue cleared")

    def shuffle_queue(self):
        entries = self.get_play_queue()
        if entries:
            random.shuffle(entries)
            queue = self.queue_source
            for i in range(0, len(entries)):
                entry = self.db.entry_lookup_by_id(entries[i].id)
                queue.move_entry(entry, i)

    def enqueue(self, entry_ids):
        log.debug("Enqueuing {}".format(entry_ids))
        for entry_id in to_list(entry_ids):
            entry = self.db.entry_lookup_by_id(int(entry_id))
            if entry is None:
                continue
            self.queue_source.add_entry(entry, -1)
        self.queue_source.queue_draw()

    def dequeue(self, entry_ids):
        log.debug("Dequeuing {}".format(entry_ids))
        for entry_id in to_list(entry_ids):
            entry = self.db.entry_lookup_by_id(int(entry_id))
            if entry is None:
                continue
            self.queue_source.remove_entry(entry)
        self.queue_source.queue_draw()

    # ENTRY
    def get_entry(self, entry_id):
        log.debug('get entry {}'.format(entry_id))
        entry_id = int(entry_id)
        return self.db.entry_lookup_by_id(entry_id)

    def set_rating(self, entry_id, rating):
        """Sets the provided rating to the given entry id, int 0 to 5"""
        rating = to_int(rating, 'Rating parameter must be an int')
        entry = self.get_entry(entry_id)
        if not entry is None:
            self.db.entry_set(entry, RB.RhythmDBPropType.RATING, rating)

    # Query
    def search_song(self, query):
        """Performs a query for entry type "song" with the provided query"""
        log.info('Searching for a song with query %s' % query)
        return self.search(query, TYPE_SONG)

    def search_radio(self, query):
        """Performs a query for entry type "radio" with the provided query"""
        log.info('Searching for a radio with filter %s' % query)
        return self.search(query, TYPE_RADIO)

    def search_podcast(self, query):
        """Performs a query for entry type "podcast" with the provided filters"""
        log.info('Searching for a podcast with filter %s' % query)
        return self.search(query, TYPE_PODCAST)

    def search(self, query, media_type):
        """Performs a query for provided entry type with the provided query and media type"""
        filters = {}
        filters['type'] = media_type
        filters['all'] = query
        return self.query(filters)

    def query(self, filters):
        """Performs a query with the provided filters"""
        log.debug('RBHandler.query...')
        if not filters:
            log.info('No filters, returning empty result')
            return []

        media_type = self.entry_types[TYPE_SONG]
        rating, play_count, first, limit = 0, 0, 0, 0
        query = Query()

        if filters:
            for key in filters:
                value = filters[key]
                if type(value) is str:
                    log.debug('Searching for %s: "%s"' % (key, value))
                else:
                    log.warning('Searching for %s but type is "%s"' % (key, type(value)))

            if 'exact-match' in filters:
                query.matcher = RB.RhythmDBQueryType.EQUALS

            if 'first' in filters:
                try:
                    first = int(filters['first'])
                except:
                    raise InvalidQueryException('Parameter first must be a number, it actually is \"%s\"' % first)

            if 'limit' in filters:
                try:
                    limit = int(filters['limit'])
                except:
                    raise InvalidQueryException('Parameter limit must be a number, it actually is \"%s\"' % limit)

            if 'type' in filters:
                media_type = self.entry_types.get(filters['type'], None)
                if not media_type:
                    raise InvalidQueryException('Unknown type {}'.format(filters['type']))

            if 'rating' in filters:
                try:
                    rating = float(filters['rating'])
                except:
                    raise InvalidQueryException('Parameter rating must be a float, it actually is \"%s\"' % rating)

            if 'play_count' in filters:
                try:
                    play_count = int(filters['play_count'])
                except:
                    raise InvalidQueryException('Parameter play_count must be an int, it actually is \"%s\"' % play_count)

            if 'all' in filters:
                query.add_all(filters['all'])
            else:
                query.add_artist(filters.get('artist', None))
                query.add_title(filters.get('title', None))
                query.add_album(filters.get('album', None))
                query.add_genre(filters.get('genre', None))
            query.add_type(media_type)
            query.add_rating(rating)
            query.add_play_count(play_count)

        query_model = query.execute(self.db)
        log.debug('RBHandler.query executed, loading results...')
        entries = [entry for entry in Reader(query_model, first, limit)]
        log.debug('RBHandler.query executed, returning results...')
        return entries

    # SOURCE
    def play_source(self, source):
        log.info('Set source playing')
        if self.get_playing_status():
            self.play_pause()
        self.player.set_playing_source(source.source)
        return self.play_pause()

    def get_source(self, source_index):
        source_index = to_int(source_index, 'source_index parameter must be an int')
        sources = self.get_sources()
        for source in enumerate(sources):
            if source.index == source_index:
                log.debug('Returning source %s' % source)
                return source
        return None

    def load_source_entries(self, source, limit=100):
        if source is None:
            return
        source.entries = [entry for entry in Reader(source.query_model, limit=limit)]

    def get_playlists(self):
        """Returns all registered playlists"""
        sourcelist = self.shell.props.playlist_manager.get_playlists()
        sources = []
        for index, source in enumerate(sourcelist):
            sources.append(RBSource(index, source))
        return sources

    def get_sources(self):
        """Returns all fixed sources, disabled by now"""
        return []

    def enqueue_source(self, source):
        """Enqueues in the play queue the given playlist"""
        if not source:
            return 0
        # playlist.add_to_queue(self.queue_source)
        # This way we will know how many songs are added
        for entry in Reader(source.query_model):
            self.enqueue(entry)

class Reader(object):

    def __init__(self, model, first=0, limit=0):
        if model is None:
            raise ValueError('Model is required')
        self.model = model
        self.first = first
        self.limit = limit
        self.total = 0

    def __iter__(self):
        for (index, row) in enumerate(self.model):
            if index < self.first:
                continue
            yield RBEntry(row[0])
            self.total += 1
            if self.limit and self.total >= self.limit:
                break


class Query(object):

    def __init__(self):
        self.filters = []
        self.static_filters = []
        self.query_for_all = False
        self.matcher = RB.RhythmDBQueryType.FUZZY_MATCH
        self.sort_func = RB.RhythmDBQueryModel.album_sort_func

    def add_artist(self, artist):
        if not artist:
            return
        self.filters.append((self.matcher,
            RB.RhythmDBPropType.ARTIST_FOLDED,
            artist.lower()))

    def add_title(self, title):
        if not title:
            return
        self.filters.append((self.matcher,
            RB.RhythmDBPropType.TITLE_FOLDED,
            title.lower()))

    def add_album(self, album):
        if not album:
            return
        self.filters.append((self.matcher,
            RB.RhythmDBPropType.ALBUM_FOLDED,
            album.lower()))

    def add_genre(self, genre):
        if not genre:
            return
        self.filters.append((self.matcher,
            RB.RhythmDBPropType.GENRE_FOLDED,
            genre.lower()))

    def add_all(self, value):
        if not value:
            return
        self.add_artist(value)
        self.add_title(value)
        self.add_album(value)
        self.add_genre(value)
        self.query_for_all = True

    def add_type(self, media_type):
        self.static_filters.append((RB.RhythmDBQueryType.EQUALS,
            RB.RhythmDBPropType.TYPE,
            media_type))

    def add_play_count(self, play_count):
        if not play_count:
            return
        self.static_filters.append((RB.RhythmDBQueryType.GREATER_THAN,
            RB.RhythmDBPropType.PLAY_COUNT,
            play_count))

    def add_rating(self, rating):
        if not rating:
            return
        self.static_filters.append((RB.RhythmDBQueryType.GREATER_THAN,
            RB.RhythmDBPropType.RATING,
            rating))

    def execute(self, db):
        """Runs the query on the database"""
        query_model = RB.RhythmDBQueryModel.new_empty(db)
        query_model.set_sort_order(self.sort_func, None, False)

        if self.query_for_all: # equivalent to use an OR (one query for each parameter)
            log.info('Query for all parameters separatedly')
            for parameter in self.filters:
                query = GLib.PtrArray()
                for static_filter in self.static_filters:
                    db.query_append_params(query, static_filter[0], static_filter[1], static_filter[2])
                db.query_append_params(query, parameter[0], parameter[1], parameter[2])
                db.do_full_query_parsed(query_model, query)
        else:
            log.info('Query for all parameters in one only full search')
            query = GLib.PtrArray()
            for static_filter in self.static_filters:
                db.query_append_params(query, static_filter[0], static_filter[1], static_filter[2]) # Append parameter
            for parameter in self.filters:
                db.query_append_params(query, parameter[0], parameter[1], parameter[2])
            db.do_full_query_parsed(query_model, query)
        return query_model



class InvalidQueryException(Exception):

    def __init__(self, message):
        Exception.__init__(self)
        self.message = message


class RBEntry(object):

    def __init__(self, entry):
        self.id = entry.get_ulong(RB.RhythmDBPropType.ENTRY_ID)
        self.title = entry.get_string(RB.RhythmDBPropType.TITLE) # self.get_value(entry, RB.RhythmDBPropType.TITLE)
        self.artist = entry.get_string(RB.RhythmDBPropType.ARTIST) # self.get_value(entry, RB.RhythmDBPropType.ARTIST)
        self.album = entry.get_string(RB.RhythmDBPropType.ALBUM)
        self.track_number = entry.get_ulong(RB.RhythmDBPropType.TRACK_NUMBER)
        self.duration = entry.get_ulong(RB.RhythmDBPropType.DURATION)
        self.rating = entry.get_double(RB.RhythmDBPropType.RATING)
        self.genre = entry.get_string(RB.RhythmDBPropType.GENRE)
        self.play_count = entry.get_ulong(RB.RhythmDBPropType.PLAY_COUNT)
        self.location = entry.get_string(RB.RhythmDBPropType.LOCATION)
        self.year = entry.get_ulong(RB.RhythmDBPropType.YEAR)
        self.bitrate = entry.get_ulong(RB.RhythmDBPropType.BITRATE)
        self.last_played = entry.get_ulong(RB.RhythmDBPropType.LAST_PLAYED)

    def __int__(self):
        return self.id


class RBSource(object):

    def __init__(self, index, entry, source_type='playlist'):
        self.id = index
        self.index = index
        self.source_type = source_type
        self.is_playing = False # entry[RB_SOURCELIST_MODEL_COLUMN_PLAYING] (Check agains shell.get_playing_source)
        self.name = entry.props.name # entry[RB_SOURCELIST_MODEL_COLUMN_NAME]
        self.source = entry
        self.query_model = entry.props.query_model
        self.entries = None
        self.attributes = None # entry[RB_SOURCELIST_MODEL_COLUMN_ATTRIBUTES]
        self.visibility = None # entry[RB_SOURCELIST_MODEL_COLUMN_VISIBILITY]
        self.is_group = False # entry[RB_SOURCELIST_MODEL_COLUMN_IS_GROUP]
        self.group_category = None #entry[RB_SOURCELIST_MODEL_COLUMN_GROUP_CATEGORY]

    def __int__(self):
        return self.id
