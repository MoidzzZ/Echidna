import math
import os

import numpy as np
import re
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


# 定义余弦相似度函数
def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0
    return dot_product / (norm_vec1 * norm_vec2)


def format_history(plot_history):
    history = []
    for chat in plot_history:
        name = chat[0]
        content = chat[1]
        history.append(f"{name}: {content}")
    return history


def postprocess(response, name):
    # 去掉回复里的引号
    response = response.replace("\"", "")
    response = response.replace("”", "")
    response = response.replace("“", "")

    # 模型回复时可能带角色名
    # 这里处理的还是糙了，比如：
    # 我是青雀，常言道：xxxx
    # 这种情况就会只返回xxxx，应该把青雀：作为匹配
    pattern = r'^(.*?)[：:]\s*(.*)$'

    # 使用正则表达式匹配
    match = re.search(pattern, response)

    if match:
        # 如果匹配成功，提取冒号后的内容并去掉首尾空白
        if name in match.group(1) or "我" in match.group(1) or "自己" in match.group(1):
            return match.group(2).strip()
        else:
            return response
    else:
        # 如果没有匹配到，直接返回原句
        return response


def extract_json(text):
    # 使用正则表达式匹配任意首尾标记
    match = re.search(r'^[\s`]*json\s*(.*?)\s*`+$', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# 边界初始化方法有问题
def dtw_distance(matrix, visualize=False, save_dir=None, personality=None):
    m, n = matrix.shape

    # 初始化累积成本矩阵（边缘设为无穷大）
    dtw = np.full((m + 1, n + 1), np.inf)
    dtw[0, 0] = 0  # 起点成本为0

    # 初始化路径矩阵（0:对角线, 1:垂直, 2:水平）
    path = np.zeros((m + 1, n + 1), dtype=int)

    # 填充DTW矩阵（注意索引偏移）
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = matrix[i - 1, j - 1]  # 原始矩阵是0-based

            # 获取三个可能方向的最小成本
            min_val = min(dtw[i - 1, j],  # 垂直
                          dtw[i, j - 1],  # 水平
                          dtw[i - 1, j - 1])  # 对角线

            # 记录最小成本的方向（优先选择对角线）
            if min_val == dtw[i - 1, j - 1]:
                direction = 0
            elif min_val == dtw[i - 1, j]:
                direction = 1
            else:
                direction = 2

            dtw[i, j] = cost + min_val
            path[i, j] = direction

    # 可视化部分
    if visualize:
        plt.figure(figsize=(12, 6))

        # 原始成本矩阵
        plt.subplot(1, 2, 1)
        plt.imshow(matrix, cmap='viridis', origin='lower')
        plt.colorbar(label='Local Cost')
        plt.title("Cost Matrix")
        plt.xlabel("Sequence 2")
        plt.ylabel("Sequence 1")

        # DTW矩阵和路径
        plt.subplot(1, 2, 2)
        plt.imshow(dtw[1:, 1:], cmap='viridis', origin='lower')  # 去掉边界
        plt.colorbar(label='Accumulated Cost')
        plt.title("DTW Matrix with Optimal Path")

        # 回溯路径（强制从终点到起点）
        i, j = m, n
        path_points = [(i - 1, j - 1)]  # 转换为0-based坐标
        while i > 1 or j > 1:
            if path[i, j] == 0:  # 对角线
                i -= 1
                j -= 1
            elif path[i, j] == 1:  # 垂直
                i -= 1
            else:  # 水平
                j -= 1
            path_points.append((i - 1, j - 1))

        # 绘制路径（确保顺序正确）
        path_x = [p[1] for p in reversed(path_points)]
        path_y = [p[0] for p in reversed(path_points)]
        plt.plot(path_x, path_y, 'r-', linewidth=2)

        plt.tight_layout()
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            plt.savefig(f"{save_dir}/{personality}_dtw.png", dpi=300, bbox_inches='tight')
        else:
            plt.show()
        plt.close()

    # 返回归一化距离（可根据需要调整分母）
    return dtw[m, n] / (m + n)  # 或 max(m, n) 或 (m^2 + n^2)^0.5


def softmax(scores):
    """计算 softmax 概率分布"""
    exp_scores = [math.exp(score) for score in scores]  # 计算指数值
    total = sum(exp_scores)  # 归一化分母
    return [exp_score / total for exp_score in exp_scores]  # 归一化概率


if __name__ == "__main__":
    test_matrix = np.array([
        [0.12, 0.85, 0.72, 0.91, 0.63, 0.77, 0.54, 0.68],
        [0.83, 0.15, 0.78, 0.62, 0.44, 0.39, 0.91, 0.27],
        [0.71, 0.69, 0.23, 0.55, 0.81, 0.12, 0.67, 0.48],
        [0.92, 0.54, 0.61, 0.08, 0.76, 0.33, 0.45, 0.59],
        [0.63, 0.47, 0.79, 0.71, 0.19, 0.88, 0.52, 0.36],
        [0.75, 0.32, 0.14, 0.29, 0.93, 0.05, 0.61, 0.72],
        [0.58, 0.91, 0.67, 0.43, 0.56, 0.64, 0.21, 0.83],
        [0.69, 0.28, 0.49, 0.57, 0.34, 0.77, 0.82, 0.11]
    ])

    distance = dtw_distance(test_matrix, visualize=True)
    print(f"Normalized DTW distance: {distance:.4f}")
