# CLAUDE.md - Defog Self-Hosted Helper Guide

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
- Lint: `cd frontend && npm run lint`

### Docker
- Build and run: `docker-compose up --build`

## Code Style Guidelines

### Python (Backend)
- Use type hints consistently
- Snake_case for variables/functions, PascalCase for classes
- Docstrings for functions and classes
- Organize imports: stdlib → third-party → local
- Use Pydantic for request/response models
- Proper exception handling with try/except

### JavaScript/TypeScript (Frontend)
- Use TypeScript interfaces/types for props and state
- Functional components with React hooks
- camelCase for variables/functions, PascalCase for components
- JSX/TSX for component templates
- Tailwind CSS for styling
- Async/await for API calls