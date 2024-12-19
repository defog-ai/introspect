# get the argument passed to the script
arg=$1

# if arg is 1, means we are doing the first rename
# in this case, env.local should exist, and env.local.backup should not
# error if above is not true
if [ $arg -eq 1 ]; then
  if [ ! -f .env.local ]; then
    echo "env.local does not exist"
    exit 1
  fi
  if [ -f .env.local.backup ]; then
    echo "env.local.backup already exists"
    exit 1
  fi
fi

# if arg is 2, means we are doing the second rename
# in this case, env.local.backup should exist, and env.local should not
# error if above is not true
if [ $arg -eq 2 ]; then
  if [ ! -f .env.local.backup ]; then
    echo "env.local.backup does not exist"
    exit 1
  fi
  if [ -f .env.local ]; then
    echo "env.local already exists"
    exit 1
  fi
fi

# if .env.local exists, rename it to .env.local.backup
if [ -f .env.local ]; then
  echo "renaming .env.local to .env.local.backup"
  mv .env.local .env.local.backup
else
  # if .env.local does not exist, rename .env.local.backup to .env.local
  echo "renaming .env.local.backup to .env.local"
  mv .env.local.backup .env.local
fi