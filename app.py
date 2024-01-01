from flask import Flask, request, jsonify
app = Flask(__name__)

import random, string
import pyrebase
import json

def randstr(n=10):
    randlst = [random.choice(string.ascii_letters + string.digits) for i in range(n)]
    return ''.join(randlst)

config = json.load(open(".env"))
DEFAULT_ERROR_MESSAGE = "No Room Found."
MAX_PLAYER_COUNT = 4
firebase = pyrebase.initialize_app(config)
db = firebase.database()

def _create_new_room(is_private, room_name): 
    data = {
        "is_private": is_private,
        "room_name": room_name,
        "player_count": 0,
        "guids": [], # プレイヤーを識別するためのランダムな識別子
        "names": [], # プレイヤー名(任意)
        "end_points": [""], 
        "room_seed": randstr(), 
        "status": "waiting" # waiting: 開始待ち, IPreq: 登録待ち, ingame: ゲーム開始
    }
    return data

def _join_room(room_data, name, guid):
    room_data["names"].append(name)
    room_data["guids"].append(guid)
    room_data["player_count"] = len(room_data["names"])
    player_index = room_data["names"].index(name)
    return room_data, player_index

def _leave_room(room_data, guid):
    player_index = room_data["guids"].index(guid)
    room_data["names"].pop(player_index)
    room_data["guids"].pop(player_index)
    room_data["player_count"] = len(room_data["names"])
    return room_data

def set_room_seed(room):
    rand_str = randstr(10)
    while rand_str == room["room_seed"]:
        rand_str = randstr(10)
    room["room_seed"] = rand_str
    return room

def is_arg_missing(form, keywords):
    for key in keywords:
        if key not in form: return True
    return False

# required: name, guid, game_type(private|public)
# optional: room_name
@app.route("/create_room/", methods=['POST'])
def create_room():
    if is_arg_missing(request.form, ["guid", "name", "game_type"]):
        return DEFAULT_ERROR_MESSAGE
    room_name = request.form["room_name"] if "room_name" in request.form else f"{request.form['name']}'s Room"
    data = _create_new_room(request.form["game_type"] == "private", room_name)
    data, _ = _join_room(data, request.form["name"], request.form["guid"])
    room_id = db.child("rooms").push(data)["name"]
    data["room_id"] = room_id
    data["player_index"] = 0
    return jsonify(data)

# 30件返す, ☑
@app.route("/get_all_room/", methods=["GET"])
def get_rooms():
    rooms = db.child("rooms").order_by_child("player_count").limit_to_first(30).get()
    room_info_list = []
    for room in rooms.each():
        values = room.val()
        room_info_list.append({
            "room_id": room.key(), 
            "room_name": values["room_name"],
            "player_count": values["player_count"]})
    return jsonify(room_info_list)

# プライベートで参加する
# required: room_id, guid, name
@app.route("/join_private/", methods=["POST"])
def join_private():
    if is_arg_missing(request.form, ["guid", "name", "room_id"]):
        return DEFAULT_ERROR_MESSAGE
    room = db.child("rooms").child(request.form["room_id"]).get()
    if room is None:
        return DEFAULT_ERROR_MESSAGE
    # TODO: 未実装       
    data = room.val()
    if data["player_count"] == 2: 
        return "The Room Is Full."
    if request.form["guid"] in data["guids"]: 
        return jsonify(data)
    data, player_index = _join_room(data, request.form["name"], request.form["guid"])
    db.child("rooms").child(request.form["room_id"]).update(data)
    data["player_index"] = player_index
    return jsonify(data)

# required: guid, name
@app.route("/join_public/", methods = ["POST"])
def join_random():
    if is_arg_missing(request.form, ["guid", "name"]):
        return DEFAULT_ERROR_MESSAGE
    room = db.child("rooms").order_by_child("player_count").equal_to(1).order_by_child("is_private").equal_to(False).limit_to_first(1).get()
    # room = session.query(Room).filter(Room.player_count < 8, Room.is_private==False).first()
    if room.val() is None:
        # 新しく作る
        data = _create_new_room(False)
        data, player_index = _join_room(data, request.form["name"], request.form["guid"])
        db.child("rooms").push(data)
    else: 
        # 参加する
        key = room[0].key()
        data = room[0].val()
        data, player_index = _join_room(data, request.form["name"], request.form["guid"])
        db.child("rooms").child(key).update(data)
    data["player_index"] = player_index
    return jsonify(data)

# requried: room_id, guid
@app.route("/get_room/", methods=['GET'])
def get_room_state():
    room_id = request.args.get("room_id", 0)
    guid = request.args.get("guid", " ")
    room_seed = request.args.get("room_seed", " ")
    if room_id == 0 or guid == " ": 
        return DEFAULT_ERROR_MESSAGE
    room = db.child("rooms").child(room_id).get().val()
    if room is None: 
        return DEFAULT_ERROR_MESSAGE
    if guid not in room["guids"]: 
        return DEFAULT_ERROR_MESSAGE
    if room["room_seed"] == room_seed:
        return "No Changes"
    room["player_index"] = room["guids"].index(guid)
    return jsonify(room)

# requried: room_id, guid
@app.route("/leave_room/", methods=["POST"])
def leave_room():
    if "room_id" not in request.form or "guid" not in request.form:
        return DEFAULT_ERROR_MESSAGE
    room = db.child("rooms").child(request.form["room_id"]).get()
    room_data = room.val()
    if room_data is None: 
        return DEFAULT_ERROR_MESSAGE
    if request.form["guid"] not in room_data["guids"]: 
        return DEFAULT_ERROR_MESSAGE
    if room_data["player_count"] == 1: 
        db.child("rooms").child(request.form["room_id"]).remove()
        return "Sucess"
    room_data = _leave_room(room_data, request.form["guid"])
    # 一人になったらEndpointを消す
    if room_data["player_count"] == 1 and "end_points" in room_data:
        room_data["end_points"] = []
    print(room.key())
    db.child("rooms").child(room.key()).update(room_data)
    return "Success"

# 部屋更新。スタート処理、エンドポイント設定、ポート無効報告
# required: room_id, guid
# optional: IP_endpoint(oo.oo.oo.oo:xxxx), start_game, delete_endpoint, room_name
@app.route("/update_room/", methods=['POST'])
def update_room():
    if is_arg_missing(request.form, ["room_id", "guid"]):
        return DEFAULT_ERROR_MESSAGE
    guid = request.form["guid"]
    data = db.child("rooms").child(request.form["room_id"]).get().val()
    print(data)
    if data is None or guid not in data["guids"]: 
        return DEFAULT_ERROR_MESSAGE
    player_index = data["guids"].index(guid)
    if "IP_endpoint" in request.form and data["status"] == "EPreq":
        if "end_points" not in data:
            data["end_points"] = [""] * len(data["guids"])
        data["end_points"][player_index] = request.form["IP_endpoint"]
        if len([e for e in data["end_points"] if e is not None]) == data["player_count"]:
            data["status"] = "ingame"
    if "delete_endpoint" in request.form: 
        data["end_points"][player_index] = "None"
    if "room_name" in request.form:
        data["room_name"] = request.form["room_name"]
    if "start_game" in request.form and player_index == 0:
        data["status"] = "EPreq"
        data["endpoints"] = []
    if "end_game" in request.form and player_index == 0:
        data["status"] = "waiting"
    db.child("rooms").child(request.form["room_id"]).update(data)
    data["player_index"] = player_index
    return jsonify(data)

## おまじない
if __name__ == "__main__":
    app.run(debug=True)