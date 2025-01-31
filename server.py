# This is a flask server to play the game.
# It serves the static files for the Svelte frontend and the API for the game.
from typing import Dict
from flask import Flask, send_from_directory, request # type: ignore
from waitress import serve # type: ignore
from uuid import uuid4
from npc.game import Game
from npc.apps import Summarizer, generate_image
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources=r'/*')
summarizer = Summarizer()

# Utilities for operating the game
def get_game():
    game = Game(game_file='./zork1.z5', max_steps=1)#, agent_turns=3)
    game.world.reset()
    return game
def get_prompt(game_state):
    # if game_state['feedback'] != '' and game_state['description'] not in game_state['feedback']:
    #     prompt = game_state['description'] + game_state['feedback']
    # else:
    prompt = game_state['description']
    if len(prompt) > 800:
        prompt = summarizer.run(prompt)
    return prompt

games: Dict[str, Game] = {}

# API paths for the game
@app.route("/api/start")
def start():
    print("/api/start")
    session_id = str(uuid4())
    games[session_id] = get_game()
    shem = games[session_id].agent.shem
    resp = {"sessionId": session_id, "shem": shem}
    print(resp)
    return resp

@app.route("/api/stop/<session_id>")
def stop(session_id):
    del games[session_id]
    resp = {"sessionId": session_id}
    # print(resp)
    return resp

@app.route("/api/step_world/<session_id>/<command>")
async def step_world(session_id, command):
    print("/api/step_world/")
    game = games[session_id]
    game.step_world(command)
    game_state = game.get_state()
    return game_state

# API paths for the bot
@app.route("/api/step_agent/<session_id>")
async def step_agent(session_id):
    game = games[session_id]
    resp = game.step_agent()
    return resp

@app.route("/api/get_image/<session_id>")
async def get_image(session_id):
    game = games[session_id]
    game_state = game.get_state()
    prompt = get_prompt(game_state)
    # print(prompt)
    # output = await diffusion.get_image(prompt)
    output = await generate_image(prompt)
    resp = {'image_url': output}
    # print(resp)
    return resp
    
# API route for making a new NPC with a different shem
# Need to use JSON here rather than string parameters
@app.route("/api/set_shem/", methods=['POST'])
async def set_shem():
    data = request.get_json()
    session_id = data['sessionId']     
    shem = data['shem']
    mem_length = data['memLength']
    stuck_length = data['stuckLength']
    temp = data['llmTemp']
    toks = data['llmTokens']
    game = games[session_id]
    game.new_npc(shem, mem_length, stuck_length, temp, toks)
    resp = {"sessionId": session_id, "shem": shem, "memLength": mem_length, "stuckLength": stuck_length, "llmTemp": temp, "llmTokens": toks}
    # print(resp)
    return resp


# Path for our main Svelte page
@app.route("/")
def base():
    return send_from_directory('client/public', 'index.html')

# Path for all the static files (compiled JS/CSS, etc.)
@app.route("/<path:path>")
def home(path):
    return send_from_directory('client/public', path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    debug = args.debug
    
    if debug:
        app.run(debug=True,
                host="0.0.0.0",
                port=8081)  

    else:
        print("server start....")
        serve(app, host="0.0.0.0", port=8081)
