# campus-management

## Deploy on Render

Create a Render Blueprint from this repository using `render.yaml`. Set
`SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` when prompted. Render uses
`requirements.txt` to install dependencies and starts the service with Gunicorn.

For local development, set those variables in `.env` and run:

```sh
python app.py
```

This API currently has no authentication. User IDs are supplied by callers,
and event registrations are publicly readable. Configure Supabase policies
accordingly before deploying.