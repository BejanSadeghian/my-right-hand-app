CREATE SCHEMA IF NOT EXISTS v0;

SET search_path TO v0;

CREATE TABLE assessments (
	id TEXT NOT NULL, 
	time_sensitive BOOLEAN, 
	requires_response BOOLEAN, 
	payment_required BOOLEAN, 
	payment_received BOOLEAN, 
	attention_req BOOLEAN, 
	created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	edited_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);


CREATE TABLE acknowledge (
	id TEXT NOT NULL, 
	acknowledge BOOLEAN, 
	created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	edited_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);


CREATE TABLE emails (
	id TEXT NOT NULL, 
	sender TEXT, 
	recipient TEXT, 
	subject TEXT, 
	body TEXT, 
	date TEXT, 
	snippet TEXT, 
	link TEXT, 
	created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	edited_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE TABLE email_errors (
	id TEXT NOT NULL, 
	description TEXT, 
	created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	edited_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);


CREATE TABLE logs (
	id TEXT NOT NULL, 
	description TEXT, 
	created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	edited_date TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

