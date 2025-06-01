from flask import Flask, render_template, request, redirect, url_for,jsonify
from init import init,get_graph_html,get_content,delete_node,save_file
import json,re


app = Flask(__name__)
@app.route('/', methods=['GET', 'POST'])
def home():
    graph_html=get_graph_html()
    if request.method == 'POST':
         save_file()
    return render_template('home.html', graph_html=graph_html)


@app.route('/<int:node_id>',methods=['GET', 'POST'])
def node(node_id):
    node_content,edge=get_content(node_id)
    if request.method == 'POST':
         delete_node(node_id)
    return render_template('node.html',node_content=node_content,edge=edge)

if __name__ == '__main__':
    init()
    app.run(debug=True)
