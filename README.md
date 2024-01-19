This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Motivation

This contains the self-hosted agents front-end that we will create for our enterprise users. It will help them:

1. Access our service from their own system
2. Let admin users add and manage general users
3. Let admin users connect to a data warehouse and add tables

## Docker

To build the docker containers, make sure you have docker running on your system.

Before building, you will need to:

1. Create a file `.env.yaml` inside `agents-backend/agents`, using `.env.yaml.template` as an example. This file will contain all of the environment variables that the backend needs.
2. The db will be populated with empty meta tables for now.

Altogether, the steps are:
```bash
docker compose up -d
```

To build the images and start the containers.

Once the containers are running, you can access the front end app at `localhost:1234`

For now, can just directly go to `localhost:1234/doc` to start up a new doc. Once we have the login page, we can redirect to that page instead.

`agents-backend/docker-setup-files` contains the files for the initial setup for the backend + the db: supervisor confs, rabbitmq installation, startup bash script to start supervisor processes, and nginx config to redirect the partykit websocket requests to the right port.

A note about the partykit server: I couldn't connect to the websocket directly on port `1999`, which is where the partykit server runs.

So I had to also open port `2000`, make an nginx that redirects `http://localhost:2000` to `ws://localhost:1999`, and connect to that port on the front end instead. You can notice this in the `.env.local` file.

## Testing Locally

The following sections explain how to test portions of the different containers locally. This could be helpful when debugging.

### Agents App

This project requires Node.js. If you don't have it, you can follow the instructions [here](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm#using-a-node-installer-to-install-nodejs-and-npm).

First, install the npm dependencies.
```bash
npm install
```

Next, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:1234](http://localhost:1234) with your browser to see the result.
