from graphviz import Digraph
import re
import os
import json


graph_html = ""
data={}

def init():
    global graph_html,data  # 声明 graph_html 为全局变量
    # 指定要遍历的文件夹路径
    path = "../assets/plot_0524.json"
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    dot = Digraph()
    dot.graph_attr["fontname"] = "SimHei"  # 全局字体
    dot.node_attr["fontname"] = "SimHei"  # 节点字体
    dot.edge_attr["fontname"] = "SimHei"  # 边字体
    for key,value in data.items():
        if key!="characters" and key!="initial_relationship":
            dot.node(key,value["node_info"])
            if value["children_index"]:
                for i in value["children_index"]:
                    dot.edge(key,str(i))
    graph_html = dot.pipe(format='svg')
    # 清理SVG代码，去除不必要的空白字符
    graph_html = re.sub(r'\s+', ' ', graph_html.decode('utf-8'))


def get_graph_html():
    return graph_html

def get_content(node_id):
    path = "/new_game_plot_nodes.json"
    edge={}
    content=""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for key,value in data.items():
        if key==str(node_id):
            content=json.dumps(value, indent=4,ensure_ascii=False)
            if value["children_index"]:
                for i in value["children_index"]:
                    edge[str(i)]=data[str(i)]["summary"]
    return content,edge


def delete_node(node_id):
    global graph_html,data  # 声明 graph_html 为全局变量
    path = "/new_game_plot_nodes.json"
    with open(path, 'r', encoding='utf-8') as f:
        first_data = json.load(f)
    #删除自己
    del data[str(node_id)]
    target_node = node_id
    flag = 0
    #删除前面的点
    while flag==0:
        for key,value in first_data.items():
            if key!="characters" and key!="initial_relationship":
                if value["children_index"]:
                    for i in value["children_index"]:
                        if i==target_node:
                            if len(value["children_index"])>1:
                                flag=1
                                data[key]["children_index"].remove(target_node)
                            else:
                                target_node=int(key)
                                del data[key]
    #递归删除子节点
    def remove_children(node_key):
        if node_key not in data:
            return
        # 获取当前节点的子节点索引
        children = first_data[node_key].get("children_index", [])
        # 删除当前节点
        del data[node_key]
        # 递归删除所有子节点
        for child in children:
            remove_children(str(child))  # 确保子节点键是字符串类型
    childrens = first_data[str(node_id)].get("children_index", [])
    for i in childrens:
        remove_children(str(i))
    dot = Digraph()
    dot.graph_attr["fontname"] = "SimHei"  # 全局字体
    dot.node_attr["fontname"] = "SimHei"  # 节点字体
    dot.edge_attr["fontname"] = "SimHei"  # 边字体
    for key,value in data.items():
        if key!="characters" and key!="initial_relationship":
            dot.node(key,value["node_info"])
            if value["children_index"]:
                for i in value["children_index"]:
                    dot.edge(key,str(i))
    print(1)
    graph_html = dot.pipe(format='svg')
    # 清理SVG代码，去除不必要的空白字符
    graph_html = re.sub(r'\s+', ' ', graph_html.decode('utf-8'))

def save_file():
    global graph_html,data
    path = "/deleted_new_game_plot_nodes.json"
    # 将字典存储为 JSON 文件
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
