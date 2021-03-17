CREATE TABLE items (
    item_id              INTEGER,
    parent_sku           TEXT,
    pre_order            INTEGER,
    status               INTEGER,
    name                 TEXT,
    original_price       REAL,
    current_price        REAL,
    stock                INTEGER,
    [view]               INTEGER,
    sold                 INTEGER,
    [like]               INTEGER,
    rating_star          REAL,
    rating_count         INTEGER,
    category_id          TEXT,
    create_time          TEXT,
    images_count         INTEGER,
    model_id             INTEGER,
    model_sku            TEXT,
    model_name           TEXT,
    model_original_price REAL,
    model_current_price  REAL,
    model_sold           INTEGER,
    model_stock          INTEGER,
    account              TEXT,
    update_time          TEXT
);

CREATE TABLE zong (
    sku     TEXT,
    cname   TEXT,
    special TEXT,
    status  TEXT,
    cost    REAL,
    weight  REAL
);

CREATE TABLE stock (
    sku       TEXT,
    available INTEGER,
    total     INTEGER,
    ado       INTEGER
);

CREATE TABLE cookies (
    account     TEXT UNIQUE,
    cookies     TEXT,
    update_time TEXT
);

CREATE TABLE password (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    account  TEXT    UNIQUE,
    password TEXT    NOT NULL
);

CREATE TABLE sufix (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account     TEXT    UNIQUE,
    name        TEXT,
    description TEXT,
    image       TEXT
);

CREATE TABLE log (
    name        TEXT,
    update_time TEXT
);


CREATE TABLE performance (
    account            TEXT    UNIQUE,
    follower_count     INTEGER,
    item_count         INTEGER,
    rating_star        REAL,
    rating_count       INTEGER,
    pre_sale_rate      REAL,
    points             INTEGER,
    response_rate      REAL,
    non_fulfill_rate   REAL,
    cancel_rate        REAL,
    refund_rate        REAL,
    apt                REAL,
    late_shipping_rate REAL
);

CREATE TABLE listings_count (
    account            TEXT    UNIQUE,
    d7     INTEGER,
    d30         INTEGER,
    d3060         INTEGER,
    ds3060         INTEGER,
    total         INTEGER
);

CREATE TABLE catname (
    cat1  CHAR (200),
    cat2  CHAR (200),
    cat3  CHAR (200),
    cat4  CHAR (200),
    cat5  CHAR (200),
    catid INTEGER,
    site  CHAR (100) 
);