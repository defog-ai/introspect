# create an extensionless copy of all html files in the out/ directory
for file in out/*.html; do
  cp "$file" "${file%.*}"
done