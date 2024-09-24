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

### Postgres

Assuming you have Postgres installed and running, with `defog_db_creds` updated,

```bash
psql -U postgres -d tickit -h localhost -1 -f fname.sql
```

If asked for a password, input `postgres`

### MySQL

You can launch a mysql container for easy testing and copy over the dataset like below:

```shell
# pull and launch mysql container
docker run --name mysql -e MYSQL_ROOT_PASSWORD=password -v ~/appdata/mysql:/app/mysql -p 3306:3306 -d mysql:9.0.1

# copy over mysql dataset (from defog-self-hosted into mysql docker image)
docker cp datasets/housing_mysql.sql mysql:/housing_mysql.sql

# launch mysql cli (enter password when prompted):
docker exec -it mysql mysql -u root -p

# add housing dataset into the database for querying
mysql> CREATE DATABASE housing;
mysql> USE housing;
Database changed
mysql> SOURCE /housing_mysql.sql;
```

If you would like to build a smaller docker image for mysql (290MB vs 609MB), you can do the following:

```shell
docker build --load -t defog/alpine-mysql:latest -f datasets/mysql/mysql.dockerfile datasets/mysql

# launch mysql container with the smaller image
docker run -it --name mysql -p 3306:3306 -v ~/appdata/mysql:/app/mysql -e MYSQL_DATABASE=housing  -e MYSQL_USER=root -e MYSQL_ROOT_PASSWORD=password -d defog/alpine-mysql:latest

# copy over mysql dataset (from defog-self-hosted into mysql docker image)
docker cp datasets/housing_mysql.sql mysql:/housing_mysql.sql

# launch mysql cli (just hit enter when prompted, no password needed):
docker exec -it mysql mysql -u root -p

# the rest of the mysql cli commands are the same as above
```
