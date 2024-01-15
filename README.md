This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Motivation

This contains the self-hosted agents front-end that we will create for our enterprise users. It will help them:

1. Access our service from their own system
2. Let admin users add and manage general users
3. Let admin users connect to a data warehouse and add tables

## Docker

To build the docker containers, make sure you have docker running on your system.

You will need to have:

1. `.env.yaml` inside `agents-backend/agents`.
2. You will also need to pass in GOOGLE_APPLICATION_CREDENTIALS_PATH as a build arg to docker compose for the agents-backend service. Like so: ` GOOGLE_APPLICATION_CREDENTIALS_PATH="path/to/google/creds.json" docker compose up -d`
3. The db will be populated with empty meta tables for now.

Then run:
`GOOGLE_APPLICATION_CREDENTIALS_PATH="path/to/google/creds.json" docker compose up -d`

To build the images and start the containers.

Once the containers are running, you can access the front end app at `localhost:1234`

For now, can just directly go to `localhost:1234/doc` to start up a new doc. Once we have the login page, we can redirect to that page instead.

`agents-backend/docker-setup-files` contains the files for the initial setup for the backend + the db: supervisor confs, rabbitmq installation, startup bash script to start supervisor processes, and nginx config to redirect the partykit websocket requests to the right port.

A note about the partykit server: I couldn't connect to the websocket directly on port `1999`, which is where the partykit server runs.

So I had to also open port `2000`, make an nginx that redirects `http://localhost:2000` to `ws://localhost:1999`, and connect to that port on the front end instead. You can notice this in the `.env.local` file.
