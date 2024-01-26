# load environment variables
source .env.local

# create an extensionless copy of all html files in the out/ directory
for file in out/*.html; do
  cp "$file" "${file%.*}"
done

# replace all instances of NEXT_PUBLIC_AGENTS_ENDPOINT with DEFOGHOSTNAME
find out -type f | while read file; do
  LC_ALL=C sed -i '' "s/$NEXT_PUBLIC_AGENTS_ENDPOINT/DEFOGHOSTNAME/g" "$file"
done