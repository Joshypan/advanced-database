-- A stored procedure, for PostgreSQL. SQLite has no CREATE PROCEDURE.
-- Run with:  psql -d yourdatabase -f stored_procedure.sql

drop table if exists adoption_log;
drop table if exists pets;

create table pets (
    id serial primary key,
    name text not null,
    owner text not null
);

create table adoption_log (
    id serial primary key,
    pet_id integer not null references pets(id),
    old_owner text not null,
    new_owner text not null,
    changed_at timestamptz not null default now()
);

insert into pets (name, owner) values ('Buddy', 'Kim'), ('Whiskers', 'Lee');

-- One call from the application replaces a read, an update, and an insert.
create or replace procedure change_owner(pet integer, new_owner text)
language plpgsql
as $$
declare
    previous text;
begin
    select owner into previous from pets where id = pet for update;
    if not found then
        raise exception 'No pet with id %', pet;
    end if;
    update pets set owner = new_owner where id = pet;
    insert into adoption_log (pet_id, old_owner, new_owner)
    values (pet, previous, new_owner);
end;
$$;

call change_owner(1, 'Sam');

select p.name, p.owner, l.old_owner, l.new_owner
from pets p join adoption_log l on l.pet_id = p.id;
