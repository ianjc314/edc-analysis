import psycopg
import time
import json
from dotenv import dotenv_values

config = dotenv_values(".env")

conn = psycopg.connect(
    host=config['DB_HOST'],
    dbname=config['DB_NAME'],
    user=config['DB_USER'],
    password=config['DB_PASSWORD']
)

cur = conn.cursor()
insert_post_query = '''
INSERT INTO posts (post_id, img_url, upvotes, created_utc)
VALUES (%s, %s, %s, %s)
ON CONFLICT DO NOTHING;
'''

with open('EDC_submissions', 'r') as file:
    data = [json.loads(line) for line in file]

for i in range(len(data)):
    img_url = data[i]['url']
    if img_url == None:
        continue

    if img_url.endswith(('jpg', 'png', 'gif', 'jpeg')):
        post_data = (
            data[i]['id'],
            img_url,
            data[i]['score'],
            time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(data[i]['created_utc']))))

        cur.execute(insert_post_query, post_data)

conn.commit()
cur.close()
conn.close()