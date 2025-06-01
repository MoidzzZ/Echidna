import copy

from agent import PlotChain
from graphviz import Digraph


def plot_chains_to_nodes_tree(plot_chains, root_info):
    plot_chain_dict = {}
    for key, value in plot_chains.items():
        new_plot_chain = PlotChain(plot_chain=value['all_plot'],
                                   generated_index=value['generated_index'],
                                   todo_fork_num=len(value['todo_fork_point']),
                                   info=key)
        new_plot_chain.fork_stream_cache = value['fork_stream_cache']
        plot_chain_dict[key] = new_plot_chain

    for key, value in plot_chains.items():
        curr_plot_chain = plot_chain_dict[key]
        children_list = value['children']
        for children_name in children_list:
            plot_chain_dict[children_name].parent = curr_plot_chain
            curr_plot_chain.children.append(plot_chain_dict[children_name])

    plot_nodes = []

    def dfs_load_plot(plot_chain, parent_start_index=None, parent_end_index=None):
        start_index = len(plot_nodes)

        if plot_chain.parent is None:
            for i, plot in enumerate(plot_chain.all_plot):
                plot_nodes.append(PlotTreeNode(plot, plot_chain.info))

        else:
            # 对于生成的分支的点如何加入树
            # 找到父分支中的分支节点处（这里直接忽视第一个plot分支的可能性，也不考虑只有一个plot的情况）
            parent_modified_node_title = plot_chain.info.split('_')[-2]
            parent_modified_node_parent_index = parent_end_index

            for i in range(parent_start_index, parent_end_index):
                if plot_nodes[i].title == parent_modified_node_title:
                    # 分叉点的前一位就是当前分支的父节点（不考虑某个分支第一个节点就再做分支）
                    parent_modified_node_parent_index = i - 1

            # 遍历直到分支的父节点，将后面的节点加入树
            for i, plot in enumerate(plot_chain.all_plot):
                if plot['title'] == plot_nodes[parent_modified_node_parent_index].title:
                    for j in range(i + 1, len(plot_chain.all_plot)):
                        plot_nodes.append(PlotTreeNode(plot_chain.all_plot[j], plot_chain.info))

            plot_nodes[parent_modified_node_parent_index].children.append(plot_nodes[start_index])
            # 对父分支中的分叉节点增加流
            plot_nodes[parent_modified_node_parent_index + 1].stream = plot_chain.parent.fork_stream_cache[
                plot_nodes[parent_modified_node_parent_index + 1].title]

        end_index = len(plot_nodes)
        for i in range(start_index, end_index - 1):
            plot_nodes[i].children.append(plot_nodes[i + 1])

        for child in plot_chain.children:
            dfs_load_plot(child, start_index, end_index)

    dfs_load_plot(plot_chain_dict[root_info])
    return plot_nodes


def draw_node_tree(root, save_name):
    # 使用 Graphviz 构建图

    def build_graph(node, dot=None):
        if dot is None:
            dot = Digraph()  # 创建一个有向图
        dot.node(node.node_info)  # 添加当前节点
        for child in node.children:
            dot.edge(node.node_info, child.node_info)  # 添加边
            build_graph(child, dot)  # 递归处理子节点
        return dot

    # 绘制树形图
    dot = build_graph(root)
    dot.graph_attr["fontname"] = "SimHei"  # 全局字体
    dot.node_attr["fontname"] = "SimHei"  # 节点字体
    dot.edge_attr["fontname"] = "SimHei"  # 边字体
    dot.render(save_name, format="png", cleanup=True)  # 保存为 PNG 文件
    dot.view()  # 打开图形


class PlotTreeNode:
    def __init__(self, plot_info, chain_info, stream_cache=None):
        # 预定义的信息
        if stream_cache is None:
            stream_cache = {}
        self.title = plot_info["title"]
        self.summary = plot_info["summary"]
        self.start = plot_info["start"]
        self.end = plot_info["end"]

        self.location = plot_info["location"]
        self.time = plot_info["time"]

        self.characters_behavior = plot_info["characters"]
        # 实际模拟的信息
        self.stream = stream_cache
        self.chain_info = chain_info
        self.node_info = self.chain_info + '：' + self.title

        self.children = []  # 子节点列表

    # 打印树结构（递归）
    def print_tree(self, level=0):
        print("  " * level + str(self.title))  # 缩进显示层级
        for child in self.children:
            child.print_tree(level + 1)

    def print_value(self):
        print("title:", self.title)
        print("summary:", self.summary)


