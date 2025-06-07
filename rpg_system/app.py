from flask import Flask, jsonify, request
from flask_cors import CORS
from agent import GM, Character
import json
import time
from logger_config import setup_logger
from extra.config import *

# 获取当前本地时间
current_time = time.localtime()
# 格式化为指定格式的字符串
formatted_time = time.strftime("%m%d%H%M", current_time)
logger = setup_logger(formatted_time)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# 初始化一个game_manager(mode设为guide触发GM_guide)
with open("./assets/plot_0524.json", 'r', encoding='utf-8') as f:
    outline = json.load(f)
characters = {}
for name, description in outline['characters'].items():
    characters[name] = Character(name, description)

GAME = GM(characters, mode="goal")
GAME.load_outline(outline)
GAME.init_game()


@app.route("/", methods=["GET"])
def t():
    return "hello"


@app.route("/next_plot", methods=["POST"])
def next_plot():
    data = request.get_json()
    node_index = data.get('next_index')
    node_index, char_resp = GAME.next_plot(node_index)
    return jsonify({
        "node_index": node_index,
        "char_resp": char_resp
    })


# 加入start_chat
@app.route("/go_plot", methods=["POST"])
def go_plot():
    data = request.get_json()
    player_input = data.get("content")
    go_index = player_input.strip()
    go_title = outline[go_index]['node_info'].split("：")[0]
    GAME.dialogue_history = []

    node_index = {go_title: [go_index]}
    post_plot_list = []

    children_index = go_index
    while children_index != "0":
        for key, value in outline.items():
            if "children_index" in value.keys():
                if int(children_index) in value["children_index"]:
                    post_plot_list.append(value)
                    children_index = key

    post_plot_list.reverse()
    for character_name, character in GAME.characters.items():
        character.experience = outline["characters"][character_name]["经历"]
        character.set_llm(model_pools[0])
        character.update_experience(post_plot_list)

    return jsonify({
        "node_index": node_index,
    })


# 当后端返回给前端的index是大于1的list的时候，前端选择大于1的list传给后端调用的是此方法
@app.route("/next_mixed_plot", methods=["POST"])
def next_fixed_plot():
    data = request.get_json()
    node_index_list = data.get("node_index_list")
    return jsonify(GAME.next_mixed_plot(node_index_list))


# 返回数据：场景编号，响应角色内容
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    player_input = data.get("content")
    node_index, char_resp = GAME.interact_chat(player_input, mixed=False)

    return jsonify({
        "node_index": node_index,
        "char_resp": char_resp
    })


@app.route("/mixed_chat", methods=["POST"])
def mixed_chat():
    data = request.get_json()
    player_input = data.get("content")
    node_index, char_resp = GAME.interact_chat(player_input, mixed=True)

    return jsonify({
        "node_index": node_index,
        "char_resp": char_resp
    })


@app.route("/char_info", methods=["POST"])
def char_info():
    data = request.get_json()
    character_name = data.get("character")
    if character_name in GAME.characters.keys():
        info = {
            "外观": GAME.characters[character_name].appearance,
            "简历": GAME.characters[character_name].profile,
            "性格": GAME.characters[character_name].personality,
            "经历": GAME.characters[character_name].experience,
        }
    else:
        info = {
            "简历": "不是重要角色"
        }
    return jsonify(info)


@app.after_request
def print_routes(response):
    if request.path == "/routes":
        for rule in app.url_map.iter_rules():
            print(rule)
    return response


if __name__ == "__main__":
    app.run(port=5001, debug=True)
