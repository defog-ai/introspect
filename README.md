#  🔬 Defog Introspect: Deep Research for your internal data

Introspect is a service that does data-focused deep research for structured data. It understands your structured data (databases or CSV/Excel files), unstructured data (PDFs), and can query the web to get additional context.

## Demo
- [150s video](https://www.loom.com/share/ed2017d503ce4335909f47e8629a3acb)

## Quick Start

1. Set up environment variables:

```bash
# Create a .env file in your root folder
# You need all 3 - not just one
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

2. Start all services using Docker Compose:
```bash
docker compose up --build
```

3. Access the application in your browser:
   - Main application: http://localhost:80
   - Standalone Backend API: http://localhost:1235

## How it works

We use a simple AI agent with tool use. An LLM attempts to answer a user question with 3 tools – `text_to_sql`, `web_search`, and `pdf_with_citations`.

The model then recursively asks questions using one of these tools until it is satisfied that it has enough context to answer the users question. By default, we use `o3-mini` for text to SQL, `gemini-2.0-flash` for web search, and `claude-4-sonnet` for both PDF analysis and orchestration.

<img width="730" alt="image" src="https://github.com/user-attachments/assets/1b719e12-e4ea-4e85-82ee-5ac09f07f27a" />




## Development

For development workflows and more detailed instructions, see the README files in the `/backend` and `/frontend` directories.

## Supported Databases

Defog supports most database connectors including PostgreSQL, MySQL, SQLite, BigQuery, Redshift, Snowflake, and Databricks – and also includes support for CSV and Excel files.

## Build/Test/Lint Commands

### Backend (Python)
- Run all tests: `docker exec introspect-backend pytest`
- Run single test: `docker exec introspect-backend pytest tests/test_file.py::test_function -v`
- Tests use the `agents-postgres` service for database operations
- Create admin user: `docker exec introspect-backend python create_admin_user.py`

### Frontend (JavaScript/TypeScript)
- Development server: `cd frontend && npm run dev`
- Build production: `cd frontend && npm run build`
- Export static site: `cd frontend && npm run export`
- Run frontend tests: `cd frontend && npx playwright test`
- Lint (Prettier): `cd frontend && npm run lint`

## Security
- It is highly recommended to run this only as a Docker image, for security purposes
- This repo does involve code where LLM generated code (or custom human generated code) can be autonomously executed. While we have implemented some safeguards to prevent abuse, safety is not guaranteed outside a docker environment.

## Contributing and Maintainers
This repo is maintained by Defog.ai

## To do
- [ ] Create Docs
- [ ] Let users choose what model they want for which task from the `.env. file
- [ ] Docs and examples for how to add custom tools
- [ ] Docs and examples for how to integrate with unstructured data sources with search, like Google Drive and OneDrive
