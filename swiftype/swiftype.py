import anyjson
import httplib
import urllib
import urlparse
import base64
import datetime

from version import VERSION

USER_AGENT = 'Swiftype-Python/' + VERSION
DEFAULT_API_HOST = 'api.swiftype.com'
DEFAULT_API_BASE_PATH = '/api/v1/'

class Client(object):

  def __init__(self, username=None, password=None, api_key=None, host=DEFAULT_API_HOST):
      self.conn = Connection(username=username, password=password, api_key=api_key, host=host, base_path=DEFAULT_API_BASE_PATH)

  def engines(self):
    return self.conn._get(self.__engines_path())

  def create_engine(self, engine_id):
    engine = {'engine': {'name': engine_id }}
    return self.conn._post(self.__engines_path(), data=engine)

  def destroy_engine(self, engine_id):
    return self.conn._delete(self.__engine_path(engine_id))

  def document_types(self, engine_id):
    return self.conn._get(self.__document_types_path(engine_id))

  def create_document_type(self, engine_id, document_type_id):
    document_type = {'document_type': {'name': document_type_id }}
    return self.conn._post(self.__document_types_path(engine_id), data=document_type)

  def destroy_document_type(self, engine_id, document_type_id):
    return self.conn._delete(self.__document_type_path(engine_id, document_type_id))

  def documents(self, engine_id, document_type_id):
    return self.conn._get(self.__documents_path(engine_id, document_type_id))

  def create_document(self, engine_id, document_type_id, document={}):
    return self.conn._post(self.__documents_path(engine_id, document_type_id), data={'document':document})

  def create_or_update_document(self, engine_id, document_type_id, document={}):
    return self.conn._post(self.__documents_path(engine_id, document_type_id) + '/create_or_update', data={'document':document})

  def create_documents(self, engine_id, document_type_id, documents=[]):
    return self.conn._post(self.__documents_path(engine_id, document_type_id) + '/bulk_create', data={'documents':documents})

  def create_or_update_documents(self, engine_id, document_type_id, documents=[]):
    return self.conn._post(self.__documents_path(engine_id, document_type_id) + '/bulk_create_or_update', data={'documents':documents})

  def update_document(self, engine_id, document_type_id, document_id, fields={}):
    return self.conn._put(self.__document_path(engine_id, document_type_id, document_id) + '/update_fields', data={'fields':fields})

  def update_documents(self, engine_id, document_type_id, documents=[]):
    return self.conn._put(self.__documents_path(engine_id, document_type_id) + '/bulk_update', data={'documents':documents})

  def destroy_document(self, engine_id, document_type_id, document_id):
    return self.conn._delete(self.__document_path(engine_id, document_type_id, document_id))

  def destroy_documents(self, engine_id, document_type_id, document_ids=[]):
    return self.conn._post(self.__documents_path(engine_id, document_type_id) + '/bulk_destroy', data={'documents':document_ids})

  def search(self, engine_id, query, options={}):
    query_string = {'q': query}
    full_query = dict(query_string.items() + options.items())
    return self.conn._get(self.__search_path(engine_id), data=full_query)

  def search_document_type(self, engine_id, document_type_id, query, options={}):
    query_string = {'q': query}
    full_query = dict(query_string.items() + options.items())
    return self.conn._get(self.__document_type_search_path(engine_id, document_type_id), data=full_query)

  def suggest(self, engine_id, query, options={}):
    query_string = {'q': query}
    full_query = dict(query_string.items() + options.items())
    return self.conn._get(self.__suggest_path(engine_id), data=full_query)

  def analytics_searches(self, engine_id, start_date=None, end_date=None):
    params = dict((k,v) for k,v in {'start_date': start_date, 'end_date': end_date}.iteritems() if v is not None)
    return self.conn._get(self.__analytics_path(engine_id) + '/searches', params)

  def analytics_autoselects(self, engine_id, start_date=None, end_date=None):
    params = dict((k,v) for k,v in {'start_date': start_date, 'end_date': end_date}.iteritems() if v is not None)
    return self.conn._get(self.__analytics_path(engine_id) + '/autoselects', params)

  def analytics_top_queries(self, engine_id, page=None, per_page=None):
    params = dict((k,v) for k,v in {'page': page, 'per_page': per_page}.iteritems() if v is not None)
    return self.conn._get(self.__analytics_path(engine_id) + '/top_queries', params)

  def __search_path(self, engine_id): return 'engines/%s/search' % (engine_id)
  def __suggest_path(self, engine_id): return 'engines/%s/suggest' % (engine_id)
  def __engines_path(self): return 'engines'
  def __engine_path(self,engine_id): return 'engines/%s' % (engine_id)
  def __document_type_path(self, engine_id, document_type_id): return '%s/document_types/%s' % (self.__engine_path(engine_id), document_type_id)
  def __document_types_path(self, engine_id): return '%s/document_types' % (self.__engine_path(engine_id))
  def __document_type_search_path(self, engine_id, document_type_id): return '%s/search' % (self.__document_type_path(engine_id, document_type_id))
  def __document_path(self, engine_id, document_type_id, document_id): return '%s/documents/%s' % (self.__document_type_path(engine_id, document_type_id), document_id)
  def __documents_path(self, engine_id, document_type_id): return '%s/documents' % (self.__document_type_path(engine_id, document_type_id))
  def __analytics_path(self, engine_id): return '%s/analytics' % (self.__engine_path(engine_id))

class HttpException(Exception):
    def __init__(self, status, msg):
        self.status = status
        self.msg = msg
        super(HttpException, self).__init__('HTTP %d: %s' % (status, msg))

class Connection(object):

  def __init__(self, username=None, password=None, api_key=None, host=None, base_path=None):
    self.__username = username
    self.__password = password
    self.__api_key = api_key
    self.__host = host
    self.__base_path = base_path

  def _get(self, path, params={}, data={}):
    return self._request('GET', path, params=params, data=data)

  def _delete(self, path, params={}, data={}):
    return self._request('DELETE', path, params=params, data=data)

  def _post(self, path, params={}, data={}):
    return self._request('POST', path, params=params, data=data)

  def _put(self, path, params={}, data={}):
    return self._request('PUT', path, params=params, data=data)

  def _request(self, method, path, params={}, data={}):

    headers = {}
    headers['User-Agent'] = USER_AGENT
    headers['Content-Type'] = 'application/json'

    if self.__username is not None and self.__password is not None:
      credentials = "%s:%s" % (self.__username, self.__password)
      base64_credentials = base64.encodestring(credentials)
      authorization = "Basic %s" % base64_credentials[:-1]
      headers['Authorization'] = authorization
    elif self.__api_key is not None:
      params['auth_token'] = self.__api_key
    else:
      raise Unauthorized('Authorization required.')

    full_path = self.__base_path + path + '.json'
    query = urllib.urlencode(params, True)
    if query:
      full_path += '?' + query

    body = anyjson.serialize(data) if data else ''

    connection = httplib.HTTPConnection(self.__host)
    connection.request(method, full_path, body, headers)

    response = connection.getresponse()
    response.body = response.read()
    if (response.status / 100 == 2):
        if response.body:
            try:
                response.body = anyjson.deserialize(response.body)
            except ValueError, e:
                raise InvalidResponseFromServer('The JSON response could not be parsed: %s.\n%s' % (e, response.body))
            ret = {'status': response.status, 'body':response.body }
        else:
            ret = {'status': response.status }
    elif response.status == 401:
        raise Unauthorized('Authorization required.')
    else:
        raise HttpException(response.status, response.body)
    connection.close()
    return ret
