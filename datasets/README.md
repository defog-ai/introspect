# Adding datasets
We can convert any existing SQL db to a `.sql` file that can be easily inserted into a postgres DB on another machine

## Dumping tables from an existing database
```bash
pg_dump -h localhost -p 5432 -U postgres -d postgres -t table1 -t table2 ... > output_fname.sql
```

## Installing psql in a new VM
Before we can add a DB dump, we must install `psql`. If not already installed, we can do this with

```bash
sudo apt install postgresql-client-common
sudo apt install postgresql-client
```

## Adding data
```bash
psql -U postgres -d tickit -h localhost -1 -f fname.sql
```

If asked for a password, input `postgres`