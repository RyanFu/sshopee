drop table if exists items;
create table items (
    item_id real,
    parent_sku text,
    pre_order real,
    status real,
    name real,
    original_price real,
    current_price real,
    stock real,
    view real,
    sold real,
    like real,
    rating_star real,
    rating_count real,
    category_id text,
    create_time text,
    images_count real,
    model_id real,
    model_sku text,
    model_name text,
    model_original_price real,
    model_current_price real,
    model_sold real,
    model_stock real,
    account text,
    update_time text
);

drop table if exists password;
    create table password (
    account text,
    password text
);

drop table if exists cookies;
create table cookies (
    account text,
    cookies text,
    update_time text
);

drop table if exists zong;
create table zong (
    sku text,
    cname text,
    special text,
    status text,
    cost real,
    weight real
);

drop table if exists stock;
create table stock (
    sku text,
    ado real,
    available real
);
