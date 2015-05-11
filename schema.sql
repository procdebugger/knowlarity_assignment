drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  username text not null,
  email text not null,
  pw_hash text not null
);

drop table if exists contact;
create table contact (
	contact_id integer primary key autoincrement,
	contact_name text not null,
	email text,
	address text not null,
	phone_no integer,
	user_id integer
);

drop table if exists usercontact;
create table usercontact (
	usercontact_id integer primary key autoincrement,
	contact_id integer,
	user_id integer
);