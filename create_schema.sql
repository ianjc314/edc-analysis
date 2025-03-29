CREATE TABLE posts (
    post_id TEXT PRIMARY KEY,
    img_url TEXT,
    upvotes INT,
    created_utc TIMESTAMP
);

CREATE TABLE edc_items (
    item_id SERIAL PRIMARY KEY,
    item_name TEXT UNIQUE
);

CREATE TABLE posts_edc_items (
    post_id TEXT REFERENCES posts (post_id) ON DELETE CASCADE,
    item_id INT REFERENCES edc_items (item_id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, item_id)
);