create table if not exists transactions (
    id text primary key,
    job_id text,
    sender text not null,
    receiver text not null,
    amount bigint not null,
    status text not null,
    confidence double precision,
    expected_value double precision,
    timestamp double precision not null,
    inserted_at timestamptz not null default timezone('utc'::text, now())
);

create index if not exists transactions_job_id_idx on transactions (job_id);
create index if not exists transactions_timestamp_idx on transactions (timestamp);
create index if not exists transactions_job_timestamp_idx on transactions (job_id, timestamp, id);

-- Optional future tables:
-- create table if not exists agents (...);
-- create table if not exists jobs (...);
