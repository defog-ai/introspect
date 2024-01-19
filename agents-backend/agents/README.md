# Agents GCP

This directory contains the source code for the agents deployment on GCP.

## Local testing

First install the requirements:
`pip install requirements.txt`

Then, run the app with hypercorn
`python3 -m hypercorn main:app --reload`

This will start a live reloading function on http://localhost:8080.

Check with `curl http://localhost:8000`

You should get the following json back:

`{"message":"Hello World"}`

## Environment variables and RabbitMQ
Additionally, make sure that you have RabbitMQ installed with `brew install rabbitmq`, followed by `brew services start rabbitmq`