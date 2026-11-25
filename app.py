import os
from uuid import UUID

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from postgrest import APIError
from supabase import Client, create_client

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
if not supabase_url or not supabase_key:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be configured."
    )

app = Flask(__name__)
supabase: Client = create_client(supabase_url, supabase_key)


def parse_uuid(value, field_name):
    if not isinstance(value, str):
        return None, (jsonify(error=f"{field_name} must be a UUID."), 400)
    try:
        return str(UUID(value)), None
    except ValueError:
        return None, (jsonify(error=f"{field_name} must be a UUID."), 400)


def get_one(table_name, row_id):
    response = (
        supabase.table(table_name)
        .select("*")
        .eq("id", row_id)
        .execute()
    )
    return response.data[0] if response.data else None


@app.errorhandler(APIError)
def handle_database_error(error):
    if getattr(error, "code", None) == "23505":
        return jsonify(error="This registration already exists."), 409
    app.logger.exception("Supabase request failed")
    return jsonify(error="The database request failed."), 500


@app.get("/")
def index():
    return jsonify(message="Event API is running.")


@app.get("/api/events")
def list_events():
    response = supabase.table("events").select("*").execute()
    return jsonify(response.data)


@app.get("/api/events/<event_id>")
def event_details(event_id):
    event_id, error_response = parse_uuid(event_id, "event_id")
    if error_response:
        return error_response

    event = get_one("events", event_id)
    if event is None:
        return jsonify(error="Event not found."), 404
    return jsonify(event)


@app.post("/api/registrations")
def create_registration():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="A JSON object is required."), 400

    user_id, error_response = parse_uuid(payload.get("user_id"), "user_id")
    if error_response:
        return error_response
    event_id, error_response = parse_uuid(payload.get("event_id"), "event_id")
    if error_response:
        return error_response

    if get_one("users", user_id) is None:
        return jsonify(error="User not found."), 404

    event = get_one("events", event_id)
    if event is None:
        return jsonify(error="Event not found."), 404

    existing = (
        supabase.table("registrations")
        .select("id")
        .eq("user_id", user_id)
        .eq("event_id", event_id)
        .execute()
    )
    if existing.data:
        return jsonify(error="User is already registered for this event."), 409

    registrations = (
        supabase.table("registrations")
        .select("id")
        .eq("event_id", event_id)
        .execute()
    )
    capacity = event.get("capacity")
    if capacity is not None and len(registrations.data) >= capacity:
        return jsonify(error="Event is at capacity."), 409

    created = (
        supabase.table("registrations")
        .insert({"user_id": user_id, "event_id": event_id})
        .execute()
    )
    registration = created.data[0] if created.data else {
        "user_id": user_id,
        "event_id": event_id,
    }
    return jsonify(registration), 201


@app.get("/api/me/registrations")
def my_registrations():
    user_id, error_response = parse_uuid(
        request.args.get("user_id"), "user_id"
    )
    if error_response:
        return error_response

    response = (
        supabase.table("registrations")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return jsonify(response.data)


@app.get("/api/events/<event_id>/registrations")
def event_registrations(event_id):
    event_id, error_response = parse_uuid(event_id, "event_id")
    if error_response:
        return error_response

    if get_one("events", event_id) is None:
        return jsonify(error="Event not found."), 404

    response = (
        supabase.table("registrations")
        .select("*")
        .eq("event_id", event_id)
        .execute()
    )
    return jsonify(response.data)


if __name__ == "__main__":
    app.run()
