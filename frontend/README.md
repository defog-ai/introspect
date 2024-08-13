# The Defog Frontend

## Installing Dependencies

Run `npm i` to install all dependencies

## Exporting to static website

Run `npm run export` to export this to a static website. When doing this, make sure that `.env.local` does not exist (or is temporarily renamed if it does exist)

## Developing locally

Run `npm run dev` to develop the app locally. When this happens, make sure that the API Key names in `.env.local` match those in your docker's `.env` file.

## How It Works
The frontend contains Javascript, CSS, and HTML files that provide a browser interface to interact with our backend. It is built with React, NextJS, and Tailwind.

There are two ways we use the frontend:

**1. In Production**
When we ship Defog to a customer, they access both the frontend and the backend from the same http server and port, via Nginx. For this to happen, we need to export the entire frontend as a static HTML, Javascript, and CSS resources that can be served directly via Nginx.

**2. In Development**
When developing locally, we want to iteratively make changes while having the frontend app respond in close to real time to those changes. To this end, we do not want to export every single time.

Instead, we can just use `npm run dev` to develop the app iteratively.