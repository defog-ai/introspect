
# check if jq exists
if ! [ -x "$(command -v jq)" ]; then
  echo 'Error: jq is not installed. Please install it from here (https://stedolan.github.io/jq/download/)' >&2
  exit 1
fi

# take the argument --stage passed
stage=$1
# if nothing, then use "optimize"
if [ -z "$stage" ]; then
  stage="optimize"
fi

echo "Running stage $stage with task type optimization"

# use jq to merge the json file with the json file containing the data
jq ".stage = \"$stage\"" ./test_optimize_dsh.json > ./temp.json

curl 'http://0.0.0.0:1235/oracle/test_stage' --header 'Content-Type: application/json' -d @./temp.json | jq --indent 2

# remove the temporary json file
rm ./temp.json

