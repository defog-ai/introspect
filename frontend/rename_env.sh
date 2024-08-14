# if .env.local exists, rename it to .env.local.backup
if [ -f .env.local ]; then
  mv .env.local .env.local.backup
else
  # if .env.local does not exist, rename .env.local.backup to .env.local
  mv .env.local.backup .env.local
fi