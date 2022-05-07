import os

settings = {
    'host': os.environ.get('ACCOUNT_HOST', 'https://twitty.documents.azure.com:443/'),
    'master_key': os.environ.get('ACCOUNT_KEY', 'OiuUSlng1GmnmdnZZZn5g7wF2hX93MxLoaKq5lfVBMrOOU1fx4dq2RhDxn6n3ny7MrEH6LebN9ypCHpTxG1dog=='),
    'imdb_database_id': os.environ.get('COSMOS_IMDB_DATABASE', 'IMDB'),
    'imdb_container_id': os.environ.get('COSMOS_IMDB_CONTAINER', 'Items'),
    'twitter_database_id': os.environ.get('COSMOS_TWITTER_DATABASE', 'ToDoList'),
    'twitter_container_id': os.environ.get('COSMOS_TWITTER_CONTAINER', 'Items'),
    'top_movie_database_id': os.environ.get('COSMOS_TOP_MOVIE_DATABASE', 'TOP_MOVIES'),
    'top_movie_container_id': os.environ.get('COSMOS_TOP_MOVIE_CONTAINER', 'TOP_MOVIES')
}