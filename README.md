This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Motivation

This contains the self-hosted agents front-end and back-end that we have created for our enterprise users. It will help them:

1. Access our service from their own system
2. Let admin users add and manage general users
3. Let admin users connect to a data warehouse and add tables

## Docker

To build the docker containers, make sure you have docker running on your system.

(only needed if you have to export the frontend to static files)

```bash
cd frontend && npm run export
```

On Linux/Mac

```bash
ENDPOINT="localhost:80 OR your IP" docker compose up --no-attach agents-nginx
```

On Windows

```bash
$env.ENDPOINT = "localhost:80 OR your IP"
docker compose up -d
```

Once the containers are running, you can access the front end app at `localhost:1234`

## Username and password

The default username is `admin` and the default password is `admin`.

## Internals

`backend/docker-setup-files` contains the files for the initial setup for the backend + the db: supervisor confs, rabbitmq installation, startup bash script to start supervisor processes, and nginx config to redirect the partykit websocket requests to the right port.

A note about the partykit server: I couldn't connect to the websocket directly on port `1999`, which is where the partykit server runs.

So I had to also open port `2000`, make an nginx that redirects `http://localhost:2000` to `ws://localhost:1999`, and connect to that port on the front end instead. You can notice this in the `.env.local` file.

## Testing Locally

The following sections explain how to test portions of the different containers locally. This could be helpful when debugging.

### Running Agents App Locally

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

Open [http://localhost:1234](http://localhost:1234) with your browser to see the result. Note that full functionality will not be available unless the backend is also running.

### Testing the UI

We use [playwright](https://playwright.dev/) to test the UI. The tests are located in `test-ui/`. To run the tests you can directly run the following command:

```bash
# run this from the root folder, not from the test-ui folder
# if first time running, install playwright:
npx playwright install
# then run the tests:
npx playwright test
# or in UI mode (useful for debugging)
npx playwright test --ui
```

This command will start all of the docker containers (if not already running) via [start-containers.sh](test-ui/start-containers.sh) and then run the tests. This is to spin up the full app and enable our tests to verify the end-to-end behavior (including the backend). If you're adding new containers to or removing any containers from our [docker-compose.yaml](docker-compose.yaml), please update the expected container count in [start-containers.sh](test-ui/start-containers.sh) to ensure that our container script expects the right number of containers.

After you are done testing, you can run the following command to stop all of the containers:

```bash
docker compose down
```

#### Test Structure

Each test file `*.spec.js` should correspond with a route or some component of the UI. Once the test is done, it will output the results in the `test-results` folder, with a highly readable HTML output served at a custom port. You can view the results by opening the HTML file in your browser.

#### VSCode Debugging

You can also install the playwright extension for VSCode and debug the tests from there.

#### Codegen for Tests

You can use the following command to generate the playwright code from a set of recorded actions on the actual UI:

```sh
npx playwright codegen http://localhost:1234
```
