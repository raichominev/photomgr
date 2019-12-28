create table ss_reviewed (
ID INT UNSIGNED NOT NULL auto_increment ,
original_filename VARCHAR(300),
media_id   int,
title VARCHAR(2000),
keywords VARCHAR(2000),
data JSON
);