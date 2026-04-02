# DevMax

DevMax is a coding forum platform built with Django and Tailwind CSS. It is designed around discussion-first workflows for developers: creating subthreads, posting questions or updates, commenting, and voting inside a community-style feed.

## Features

- Community-style feed for developer discussions
- Subthreads for topic-specific spaces such as `d/python` or `d/django`
- User authentication with signup, login, logout, and profile views
- Post creation, threaded comments, and voting
- Light and dark display modes
- Supabase-backed PostgreSQL support for hosted persistence

## Tech Stack

- Django
- Django templates
- Tailwind CSS
- PostgreSQL
- Supabase

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/luxhishi/devmax.git
cd devmax
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install django psycopg[binary]
```

If you are using the Tailwind workflow in this repo, also install frontend dependencies in the Tailwind source folder used by the project.

### 4. Configure environment variables

Create a `.env` file in the project root and add your Supabase database values:

```env
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.YOUR_PROJECT_REF
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_HOST=YOUR_POOLER_HOST
SUPABASE_DB_PORT=5432
SUPABASE_DB_SSLMODE=require
```

## Running the Project

Apply migrations:

```bash
python manage.py migrate
```

Start the Django development server:

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Project Structure

```text
devmax/
├── DevMax/              # Django project settings and configuration
├── main/                # Core forum app
├── landing/             # Landing-related app/views
├── theme/               # Tailwind/theme assets
├── manage.py
└── README.md
```

## Current Notes

- The project uses Django templates rather than a separate SPA frontend.
- Supabase is used as the hosted PostgreSQL backend for this app.
- The UI is currently styled to feel forum-like, with sticky rails, modal flows, and a Reddit-inspired feed layout.

## Contributing

1. Create a branch
2. Make your changes
3. Run the app locally and test the affected flows
4. Open a pull request

## License

This project is currently unlicensed unless a license file is added to the repository.
