from flask import Flask, abort, g, jsonify, request

import lib.discord as discord
from backend.shared_globals import get_db, get_queue

app = Flask(__name__)


@app.route("/authorize", methods=["PUT"])
def authorize():
    if (token := request.args.get("token")) is None:
        abort(400, "No token specified")

    api = discord.API(token, bot=False)

    user_id = api.get_user().id

    try:
        conn = next(
            filter(
                lambda conn: conn.type == "playstation", api.get_connections()
            )
        )
    except StopIteration:
        abort(400, "PlayStation Network account not linked")

    get_db().set_id_to_psn(user_id, conn.name)
    get_queue().put((user_id, conn.name))

    return {"user_id": user_id, "psn_name": conn.name}


@app.route("/refresh", methods=["GET"])
def refresh():
    if (discord_id := request.args.get("discord_id")) is None:
        abort(400, "No ID specified")

    if (psn_id := get_db().get_id_to_psn(discord_id)) is None:
        abort(400, f"No PSN ID found for Discord ID {discord_id}")

    get_queue().put((discord_id, psn_id))

    return {}


@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    return get_db().get_leaderboard()


def run():
    # JSON error handlers
    for code in [400, 404, 405, 500]:
        app.register_error_handler(
            code, lambda error: ({"error": str(error)}, code)
        )

    app.run()
