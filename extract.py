import psycopg
import openai
from openai import OpenAI
import ast
import time
from dotenv import dotenv_values

config = dotenv_values(".env")

conn = psycopg.connect(
    host=config['DB_HOST'],
    dbname=config['DB_NAME'],
    user=config['DB_USER'],
    password=config['DB_PASSWORD']
)

client = OpenAI(
    api_key=config['OPENAI_API_KEY']
)

item_names = ['Pocket knife', 'Multi-tool', 'Fixed-blade knife', 'Flashlight', 'Headlamp', 'Keychain', 'Bottle opener',
'Screwdriver', 'Writing pen', 'Stylus pen', 'Notebook', 'Analog/Digital watch', 'Smartwatch', 'Power bank',
'Earphone/Headphone', 'USB flash drive', 'Charging cable', 'Backpack', 'Wallet', 'First-aid kit',
'Face mask', 'Lighter', 'Tissue/Wet wipe', 'Other']

ai_prompt = '''
You are an advanced image recognition model trained for object identification.
Given an image from a post on r/EDC (Everyday Carry), identify and list all recognizable
items in the image into one of the following categories:
['Pocket knife', 'Multi-tool', 'Fixed-blade knife', 'Flashlight', 'Headlamp', 'Keychain', 'Bottle opener',
'Screwdriver', 'Writing pen', 'Stylus pen', 'Notebook', 'Analog/Digital watch', 'Smartwatch', 'Power bank',
'Earphone/Headphone', 'USB flash drive', 'Charging cable', 'Backpack', 'Wallet', 'First-aid kit',
'Face mask', 'Lighter', 'Tissue/Wet wipe'].
If an item does not belong to one of those categories, classify it as 'Other'.
Ensure the output follows a valid Python string list format, without any Markdown formatting or code block
syntax, where each item is a properly formatted string enclosed in double quotes and separated by
commas. If no items can be identified, output an empty list, [].
'''

def get_items(img_url):
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': ai_prompt},
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': img_url
                    },
                },
            ],
        }],
    )

    return ast.literal_eval(response.choices[0].message.content)

cur = conn.cursor()

top_n = 200
for year in range(2012, 2023):
    cur.execute(f'SELECT post_id, img_url FROM posts WHERE EXTRACT(YEAR FROM created_utc) = {year} ORDER BY upvotes DESC LIMIT {top_n*10};')
    rows = cur.fetchall()

    insert_item_query = '''
    INSERT INTO edc_items (item_name)
    VALUES (%s)
    ON CONFLICT DO NOTHING;
    '''

    insert_post_item_query = '''
    INSERT INTO posts_edc_items (post_id, item_id)
    VALUES (%s, %s)
    ON CONFLICT DO NOTHING;
    '''

    cur.execute(f'SELECT COUNT(DISTINCT posts_edc_items.post_id) FROM posts_edc_items INNER JOIN posts ON posts_edc_items.post_id = posts.post_id WHERE EXTRACT(YEAR FROM created_utc) = {year};')
    count = cur.fetchone()[0]
    for row in rows:
        cur.execute('SELECT post_id FROM posts_edc_items WHERE post_id = %s;', (row[0],))
        result = cur.fetchone()
        if result:
            continue

        while True:
            try:
                items = get_items(row[1])
                break
            except openai.RateLimitError:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                print(f'[{timestamp}] Rate limit exceeded. Waiting 10s to retry...')
                time.sleep(10)
            except Exception as e:
                items = []
                break

        if items == []:
            continue

        count += 1

        for item in items:
            cur.execute(insert_item_query, (item,))

            cur.execute('SELECT item_id FROM edc_items WHERE item_name = %s;', (item,))
            cur.execute(insert_post_item_query, (row[0], str(cur.fetchone()[0])))
        
        if count % 10 == 0:
            conn.commit()

            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            print(f'[{timestamp}] Completed extracting {count}/{top_n} posts in {year}')

        if count == top_n:
            break

conn.commit()
cur.close()
conn.close()
