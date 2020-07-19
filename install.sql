create table folder(
    id integer primary key autoincrement,
    title varchar(100) not null unique,
    expanded boolean not null default 0
);

create table channel(
    id integer primary key autoincrement,
    title varchar(100) not null,
    url varchar(512) not null,
    folder_id integer,
    channel_type integer default 0,
    foreign key (folder_id) references folder(id)
);

create table news(
    id integer primary key autoincrement,
    channel_id int not null,
    title varchar(256) not null,
    url varchar(512) not null unique,
    summary text not null,
    is_read boolean default 0,
    foreign key (channel_id) references channel(id)
);

-- test data
insert into channel(title, url) values
    ('Ścigani.pl', 'http://www.scigani.pl/rss/programista/'),
    ('wykop.pl', 'https://www.wykop.pl/rss/');


-- migracja 1 - dodawanie folderów na kanały
-- ekstport danych do plików
-- usuwanie starych tabel
-- tworzenie nowych tabel
-- import danych z plików
