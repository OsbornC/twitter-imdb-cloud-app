from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import requests
import os 
import azure.cosmos.documents as documents
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
from azure.cosmos.partition_key import PartitionKey
import redis
import json
import config
# from flask_cors import CORS, cross_origin

HOST = config.settings['host']
MASTER_KEY = config.settings['master_key']
IMDB_DATABASE_ID = config.settings['imdb_database_id']
IMDB_CONTAINER_ID = config.settings['imdb_container_id']
TWITTER_DATABASE_ID = config.settings['twitter_database_id']
TWITTER_CONTAINER_ID = config.settings['twitter_container_id']
TOP_MOVIE_DATABASE_ID = config.settings['top_movie_database_id']
TOP_MOVIE_CONTAINER_ID = config.settings['top_movie_container_id']

app = Flask(__name__)

# Redis Cache Layer
hostName = 'twitterwebcache.redis.cache.windows.net'
accessKey = '43L8ufTJY8VCrOKtrXm5lS0znLvpUFjcIAzCaOrtjPk='

redis_client = redis.StrictRedis(host=hostName, port=6380,
                      password=accessKey, ssl=True)

# CORS(app)

client = cosmos_client.CosmosClient(HOST, {'masterKey': MASTER_KEY}, user_agent="CosmosDBPythonQuickstart", user_agent_overwrite=True)
try:
    imdb_db = client.create_database(id=IMDB_DATABASE_ID)
    print('Database with id \'{0}\' created'.format(IMDB_DATABASE_ID))

    twitter_db = client.create_database(id=TWITTER_DATABASE_ID)
    print('Database with id \'{0}\' created'.format(TWITTER_DATABASE_ID))

    top_movie_db = client.create_database(id=TOP_MOVIE_DATABASE_ID)
    print('Database with id \'{0}\' created'.format(TOP_MOVIE_DATABASE_ID))

except exceptions.CosmosResourceExistsError:
    imdb_db = client.get_database_client(IMDB_DATABASE_ID)
    print('Database with id \'{0}\' was found'.format(IMDB_DATABASE_ID))

    twitter_db = client.get_database_client(TWITTER_DATABASE_ID)
    print('Database with id \'{0}\' was found'.format(TWITTER_DATABASE_ID))

    top_movie_db = client.get_database_client(TOP_MOVIE_DATABASE_ID)
    print('Database with id \'{0}\' was found'.format(TOP_MOVIE_DATABASE_ID))

# setup container for this sample
try:
    imdb_container = imdb_db.create_container(id=IMDB_CONTAINER_ID, partition_key=PartitionKey(path='/partitionKey'))
    print('Container with id \'{0}\' created'.format(IMDB_CONTAINER_ID))
    
    twitter_container = twitter_db.create_container(id=TWITTER_CONTAINER_ID, partition_key=PartitionKey(path='/partitionKey'))
    print('Container with id \'{0}\' created'.format(TWITTER_CONTAINER_ID))

    top_movie_container = top_movie_db.create_container(id=TOP_MOVIE_CONTAINER_ID, partition_key=PartitionKey(path='/partitionKey'))
    print('Container with id \'{0}\' created'.format(TOP_MOVIE_CONTAINER_ID))

except exceptions.CosmosResourceExistsError:
    imdb_container = imdb_db.get_container_client(IMDB_CONTAINER_ID)
    print('Container with id \'{0}\' was found'.format(IMDB_CONTAINER_ID))

    twitter_container = twitter_db.get_container_client(TWITTER_CONTAINER_ID)
    print('Container with id \'{0}\' was found'.format(TWITTER_CONTAINER_ID))

    top_movie_container = top_movie_db.get_container_client(TOP_MOVIE_CONTAINER_ID)
    print('Container with id \'{0}\' was found'.format(TOP_MOVIE_CONTAINER_ID))


@app.route('/')
def index():
   print('Request for index page received')
   return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')
   response = requests.get('https://cloud-computing-twitter-function-app.azurewebsites.net//api/HttpExample?name=%s' % name)
   greeting = response.text
   
   if name:
       print('Request for hello page received with greeting=%s' % greeting)
       return render_template('hello.html', greeting = greeting)
   else:
       print('Request for hello page received with no name or blank name -- redirecting')
       return redirect(url_for('index'))

@app.route('/read', methods=['GET'])
def read_item():
    doc_id = request.args.get('doc_id')
    account_number = request.args.get('account_number')
    key = doc_id + '_' + account_number
    r = {}

    # Caching Layer
    if redis_client.get(key) is None:
        r = imdb_container.read_item(item=doc_id, partition_key=account_number)
        redis_client.set(key, json.dumps(r))
    else:
        r = json.loads(redis_client.get(key))
    print('Item read by Id {0}'.format(doc_id))
    print('Partition Key: {0}'.format(r.get('partitionKey')))
    print('Subtotal: {0}'.format(r.get('subtotal')))
    response = jsonify({'Subtotal': r.get('subtotal')})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/box_office_top_movies', methods=['GET'])
def fetch_box_office_top_movies():
    key = 'BOX_OFFICE_TOP_MOVIES'
    today = date.today()
    start = today - timedelta(days=today.weekday())
    start = str(start)
    redis_key = key + '/' + start
    movie_list = []
    if redis_client.get(redis_key) is None:
        r = imdb_container.read_item(item=key, partition_key=key)
        redis_client.set(redis_key, json.dumps(r.get('movie_list')))
        movie_list = r.get('movie_list')
    else:
        movie_list = json.loads(redis_client.get(redis_key))
    title = []
    for movie in movie_list:
        movie_response = imdb_container.read_item(item=movie, partition_key=movie)
        title.append(movie_response)
    response = jsonify({'movie_list': title})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/movie_related_tweets', methods=['GET'])
def fetch_movie_related_tweets():
    movie_id = request.args.get('movie_id')
    # tweet_data = twitter_container.read_item(item=movie_id, partition_key=movie_id)
    items = list(twitter_container.query_items(
        query="Select top 10 * from c where c.partitionKey=@movie_id order by c._ts DESC",
        parameters=[
            { "name":"@movie_id", "value": movie_id }
        ]
    ))
    tweet_ids = [(item.get('conversation_id')) for item in items]
    etags = [item.get('_etag') for item in items]
    response = jsonify({'movie_list': tweet_ids, 'etags': etags})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/top_rated_movies', methods=['GET'])
def fetch_top_rated_movies():
    key = 'TOP_RATED_ID'
    today = date.today()
    start = today - timedelta(days=today.weekday())
    start = str(start)
    redis_key = key + '-' + start
    movie_list = []
    if redis_client.get(redis_key) is None:
        r = imdb_container.read_item(item=key, partition_key=key)
        redis_client.set(redis_key, json.dumps(r.get('movie_list')[0:10]))
        movie_list = r.get('movie_list')[0:10]
    else:
        movie_list = json.loads(redis_client.get(redis_key))
    title = []
    for movie in movie_list:
        movie_response = imdb_container.read_item(item=movie, partition_key=movie)
        title.append(movie_response)
    response = jsonify({'movie_list': title})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/top_movie_related_tweets', methods=['GET'])
def fetch_top_movie_related_tweets():
    movie_id = request.args.get('movie_id')
    # tweet_data = top_movie_container.read_item(item=movie_id, partition_key=movie_id)
    items = list(top_movie_container.query_items(
        query="Select top 10 * from c where c.partitionKey=@movie_id order by c.favorite_count DESC",
        parameters=[
            { "name":"@movie_id", "value": movie_id }
        ]
    ))
    tweet_ids = [item.get('id') for item in items]
    etags = [item.get('_etag') for item in items]
    response = jsonify({'movie_list': tweet_ids, 'etags': etags})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == '__main__':
   app.run()