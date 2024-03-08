#!/bin/bash

# Define the expected number of containers. Update this if you add more containers to the docker-compose file.
expected_count=5

# Get the count of containers with names starting with 'defog-self-hosted-agents-'
container_count=$(docker container ls -a | grep 'defog-self-hosted-agents-' | wc -l)

# Check if the count is equal to the expected count
if [ "$container_count" -eq "$expected_count" ]; then
  # print out a list of the container names
  echo "There are $container_count containers with names starting with 'defog-self-hosted-agents-'."
else
  echo "There are $container_count containers with names starting with 'defog-self-hosted-agents-'. Starting docker-compose..."
  # Run docker-compose up -d
  docker-compose up -d
fi

# print out a list of the container names
echo "The containers are:"
docker container ls -a | grep 'defog-self-hosted-agents-' | awk '{print $NF}'