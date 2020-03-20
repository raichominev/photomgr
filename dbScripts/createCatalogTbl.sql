CREATE TABLE public.ss_reviewed (
	id serial NOT NULL,
	original_filename varchar(500) NULL,
	title varchar(2000) NULL,
	kw_mykeyworder varchar(2000) NULL,
	kw_keywordsready varchar(2000) NULL,
	ss_media_id int4 NULL,
	ss_filename varchar(300) NULL,
	ss_title varchar(2000) NULL,
	ss_keywords varchar(2000) NULL,
	ss_cat1 int4 NULL,
	ss_cat2 int4 NULL,
	ss_data json NULL,
	CONSTRAINT ss_reviewed_pkey PRIMARY KEY (id),
	status int4 default 0,
	date_loaded timestamp default 'now',
	date_submitted timestamp
);



CREATE UNIQUE INDEX ss_reviewed_ss_filename_idx ON public.ss_reviewed (ss_filename);
