import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.sw_prompt import *
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
import json

from extra.utils import extract_json, dtw_distance
import math
from sklearn.metrics.pairwise import cosine_distances
import numpy as np
from agent import VirtualPlayer, Character
from tqdm import tqdm
import copy
from collections import deque
from datetime import datetime
from agent import GM
from extra.config import *

logger = logging.getLogger('GlobalLogger')


class PlotChain:
    def __init__(self, plot_chain, generated_index, todo_fork_num, info):
        self.all_plot = plot_chain
        self.info = info

        self.generated_index = generated_index
        self.generated_plot = plot_chain[generated_index:]
        self.todo_fork_num = todo_fork_num
        self.todo_fork_point = []

        self.fork_stream_cache = {}
        self.children = []
        self.parent = None

    def check_fork_point(self):
        if len(self.todo_fork_point) < self.todo_fork_num:
            self.todo_fork_num = len(self.todo_fork_point)
        else:
            self.todo_fork_point = self.todo_fork_point[:self.todo_fork_num]

    def load_stream_cache(self, fork_point, stream_cache):
        self.fork_stream_cache[fork_point] = stream_cache


def get_llm(model):
    return ChatOpenAI(
        model=model,
        temperature=0.7,
        top_p=0.8,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=api_key,
        base_url=base_url,
    )


# 直接输出分支状的大纲
class ScriptWriter:
    def __init__(self, original_outline, fork_index, todo_fork_num):
        self.main_character = list(original_outline['characters'].keys())[0]

        self.original_plot_chain = original_outline['plot_chain']
        self.original_char_info = original_outline['characters']

        self.personality_api_pools = {
            "开拓": model_pools[0],
            "同谐": model_pools[1],
            "毁灭": model_pools[2],
            "虚无": model_pools[3],
            "欢愉": model_pools[4],
        }

        self.vp = VirtualPlayer(self.main_character, get_llm(self.personality_api_pools['开拓']))

        self.character_dict = {}

        self.personality_choice = {
            "欢愉": "玩世不恭，希望事态变得严重",
            "同谐": "处事圆滑，希望问题能够平歇",
            "虚无": "摆烂摸鱼，消极应对事件推进",
            "毁灭": "言行好斗，主动破坏场景平衡",
        }

        self.outline = {
            "characters": original_outline['characters'],
            "initial_relationship": original_outline['initial_relationship'],
            "plot_chains": [
                PlotChain(self.original_plot_chain, fork_index, todo_fork_num, "开拓"),
            ]
        }

        self.embedding_model = HuggingFaceEmbeddings(model_name='BAAI/bge-large-zh-v1.5')
        self.queue = deque()

        self.llm = get_llm(r1)

        self.gm = None
        self.current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

    def make_stream(self, curr_plot_chain):
        character_dict = {}
        for character, description in self.original_char_info.items():
            character_dict[character] = Character(character, description)

        self.gm = GM(character_dict)

        save_dir = f"./{self.current_time}/{curr_plot_chain.info}"

        to_modify_continue_plot_info = {}
        num = curr_plot_chain.todo_fork_num
        last_j = 0
        for i in tqdm(range(num), total=num):
            fork_point = curr_plot_chain.todo_fork_point[i]
            for j, plot in enumerate(curr_plot_chain.all_plot):
                if fork_point == plot['title']:
                    # post是刚过去的上个分支点到当前分支点之间的内容，pre是当前分支点之前的所有
                    post_plot_list = curr_plot_chain.all_plot[last_j:j]
                    curr_plot = copy.deepcopy(plot)

                    to_modify_continue_plot_info[fork_point] = {
                        "pre_plot_list": curr_plot_chain.all_plot[:j],
                        "curr_plot": curr_plot,
                        "curr_next_plot_list": curr_plot_chain.all_plot[j:],
                    }

                    self.gm.single_plot_complete(save_dir, post_plot_list, curr_plot)
                    last_j = j
        logger.info(to_modify_continue_plot_info)
        return to_modify_continue_plot_info

    def make_behavior(self, curr_plot_chain, to_modify_continue_plot_info):
        result = copy.deepcopy(to_modify_continue_plot_info)
        num = curr_plot_chain.todo_fork_num

        save_dir = f"./{self.current_time}/{curr_plot_chain.info}"
        for i in tqdm(range(num), total=num):
            fork_point = curr_plot_chain.todo_fork_point[i]
            with open(f"{save_dir}/{fork_point}.json", 'r', encoding='utf-8') as f:
                result[fork_point]['stream_cache'] = json.load(f)

            behavior_dict = copy.deepcopy(self.vp.make_change(result[fork_point]))
            for key, value in behavior_dict.items():
                if key in list(self.personality_choice.keys()):
                    result[fork_point][key] = {
                        "behavior": value,
                    }

        logger.info(result)
        return result

    def complete_outline(self, curr_plot_chain, to_modify_continue_plot_info):
        num = curr_plot_chain.todo_fork_num
        save_dir = f"./{self.current_time}/{curr_plot_chain.info}"
        # 在各分支点的信息上，让sw开始改写并续写分支，最后筛选

        for i in tqdm(range(num), total=num):
            fork_point = curr_plot_chain.todo_fork_point[i]

            new_plot_chain_dict = self.continue_plot(to_modify_continue_plot_info[fork_point], i, num,
                                                     f"{save_dir}/{fork_point}")

            for personality, new_plot_chain_content in new_plot_chain_dict.items():
                new_fork_num = num - i - 1
                all_plot = new_plot_chain_content['all']

                generated_index = len(to_modify_continue_plot_info[fork_point]['pre_plot_list'])
                info = curr_plot_chain.info + f"_{fork_point}_{personality}"

                new_plot_chain = PlotChain(all_plot, generated_index + 1, new_fork_num, info)

                self.outline['plot_chains'].append(new_plot_chain)
                curr_plot_chain.children.append(new_plot_chain)

                if new_fork_num > 0:
                    self.queue.append(new_plot_chain)

    def create_branches(self):
        self.queue.append(self.outline['plot_chains'][0])

        while len(self.queue) > 0:
            curr_plot_chain = self.queue.popleft()

            if len(curr_plot_chain.todo_fork_point) == 0:
                curr_plot_chain.todo_fork_point = self.find_fork_point(curr_plot_chain)

            curr_plot_chain.check_fork_point()

            to_modify_continue_plot_info = self.make_stream(curr_plot_chain)
            # 按fork_point使用json读取本地的流，让VP对每个分支点提出四种性格偏置的行为
            to_modify_continue_plot_info = self.make_behavior(curr_plot_chain, to_modify_continue_plot_info)

            self.complete_outline(curr_plot_chain, to_modify_continue_plot_info)

        return self.outline

    # 使用r1做分支点的判别
    def find_fork_point(self, plot_chain):
        generated_plot = plot_chain.generated_plot
        title_list = [plot['title'] for plot in generated_plot]
        todo_fork_num = plot_chain.todo_fork_num
        find_prompt = find_template.format(num=todo_fork_num, character=self.main_character,
                                           plot_chain=json.dumps(generated_plot, ensure_ascii=False, indent=2))
        chosen_plot = self.llm.invoke(find_prompt).content.strip()
        result_list = []
        for s in chosen_plot.split(';'):
            # s两侧可能有引号，去掉
            if s.strip() in title_list:
                result_list.append(s.strip())
        return [s.strip() for s in chosen_plot.split(';')]

    # 这种偏离方式，只考虑了现在生成的相较于父节点的偏离
    # 没有考虑整个已有大纲空间的偏离情况
    def select_outline(self, curr_next_plot_chain, generated_outlines, save_dir, start_index):
        logger.info("偏离度筛选情节")
        original_outline_summary_list = [plot['summary'] for plot in curr_next_plot_chain]
        original_outline_summary_embeddings = [self.embedding_model.embed_query(summary) for summary in
                                               original_outline_summary_list]
        original_outline_summary_matrix = np.array(original_outline_summary_embeddings)

        generated_outlines_eval = {}
        for personality, outline in generated_outlines.items():
            outline_summary_list = [plot['summary'] for plot in outline[start_index:]]
            outline_summary_embeddings = [self.embedding_model.embed_query(summary) for summary in outline_summary_list]
            outline_summary_matrix = np.array(outline_summary_embeddings)

            distance_matrix = cosine_distances(original_outline_summary_matrix, outline_summary_matrix)
            distance = dtw_distance(distance_matrix, visualize=True, save_dir=save_dir, personality=personality)

            generated_outlines_eval[personality] = {
                "outline": outline,
                "embeddings_matrix": outline_summary_matrix,
                "distance_to_original": distance,
                "personality_match": None
            }

        # 两两一组计算大纲之间的距离
        score_list = []
        for i in range(len(generated_outlines_eval)):
            for j in range(i + 1, len(generated_outlines_eval)):
                personality_i = list(generated_outlines_eval.keys())[i]
                personality_j = list(generated_outlines_eval.keys())[j]
                outline_i_summary_matrix = generated_outlines_eval[personality_i]['embeddings_matrix']
                outline_j_summary_matrix = generated_outlines_eval[personality_j]['embeddings_matrix']
                outline_i_distance_to_original = generated_outlines_eval[personality_i]['distance_to_original']
                outline_j_distance_to_original = generated_outlines_eval[personality_j]['distance_to_original']

                distance_matrix = cosine_distances(outline_i_summary_matrix, outline_j_summary_matrix)
                distance = dtw_distance(distance_matrix, visualize=False)

                score_prod = min(outline_i_distance_to_original, outline_j_distance_to_original) * distance

                score = {
                    "i": personality_i,
                    "j": personality_j,
                    "prod": score_prod
                }

                score_list.append(score)

        score_list.sort(key=lambda x: x['prod'], reverse=True)
        logger.info(score_list)
        # 四个偏置中选择了2个偏置，只返回personality
        return score_list[0]['i'], score_list[0]['j']

    # 根据vp基于4种不同的偏置生成的行动，先改写当前分支点的情节
    # 然后续写4种不同的大纲，综合偏离度进行4选2
    def process_personality(self, personality, fork_point_to_modify_continue_plot_info, other_char_info,
                            fork_num, index):
        pre_plot_list = fork_point_to_modify_continue_plot_info['pre_plot_list']
        curr_plot = fork_point_to_modify_continue_plot_info['curr_plot']
        all_plot_list = pre_plot_list.copy()
        all_plot_list.extend(fork_point_to_modify_continue_plot_info['curr_next_plot_list'])

        llm = get_llm(self.personality_api_pools[personality])
        special_behavior = fork_point_to_modify_continue_plot_info[personality]['behavior']

        # 增加提示词内容
        prompt = modify_prompt.format(virtual_player=self.main_character, behavior=special_behavior,
                                      pre_outline=pre_plot_list, outline_json=curr_plot,
                                      other_char_info=json.dumps(other_char_info, ensure_ascii=False, indent=4))

        modified_plot = extract_json(llm.invoke(prompt).content)
        modified_plot_dict = json.loads(modified_plot)

        # 添加修改后的plot作为已有大纲
        curr_plot_list = pre_plot_list.copy()  # 创建 pre_plot_list 的副本
        curr_plot_list.append(modified_plot_dict)  # 在副本上添加新元素

        char_description = {}
        for name, value in self.original_char_info.items():
            if name == self.main_character:
                char_description[name] = {
                    "简介": self.personality_choice[personality],
                    "经历": []
                }
            else:
                char_description[name] = {
                    "简介": value["简介"],
                    "经历": value["经历"]
                }

        todo_outline_content = {
            "characters_info": char_description,
            "story_sections": curr_plot_list
        }
        todo_outline = json.dumps(todo_outline_content, ensure_ascii=False, indent=4)

        post_len = len(self.original_plot_chain) - len(curr_plot_list)
        floor = math.ceil(1.3 * (fork_num - index))
        ceil = max(floor, math.ceil(post_len * 1.3))

        # 编写剧情的梗概和关键点，可以不用大纲的所有内容
        all_plot_content_list = []
        for plot in all_plot_list:
            all_plot_content_list.append({
                "title": plot["title"],
                "location": plot["location"],
                "time": plot['time'],
                "summary": plot["summary"]
            })

        prompt = skeleton_prompt.format(virtual_player=self.main_character, floor=floor, ceil=ceil,
                                        all_plot=all_plot_content_list,
                                        outline_json=todo_outline, behavior=special_behavior)

        skeleton = extract_json(llm.invoke(prompt).content)

        prompt = convert_prompt.format(virtual_player=self.main_character, floor=floor, ceil=ceil,
                                       outline_json=todo_outline, skeleton=skeleton, behavior=special_behavior)

        continued_plot = extract_json(llm.invoke(prompt).content)
        continued_plot_dict = json.loads(continued_plot)
        continued_plot_list = continued_plot_dict['story_sections']

        pre_modified_continued_plot_list = curr_plot_list.copy()
        pre_modified_continued_plot_list.extend(continued_plot_list)

        return {
            personality: {
                "all": pre_modified_continued_plot_list,
                "modified": modified_plot_dict,
                "continued": continued_plot_list
            }
        }

    def continue_plot(self, fork_plot_to_modify_continue_plot_info, index, fork_num, save_dir):
        pre_plot_list = fork_plot_to_modify_continue_plot_info['pre_plot_list']
        start_index = len(pre_plot_list)
        curr_plot = fork_plot_to_modify_continue_plot_info['curr_plot']
        experience = fork_plot_to_modify_continue_plot_info['stream_cache']['character_experience']

        # 改写当前情节时读所有的角色信息
        curr_char_info = copy.deepcopy(self.original_char_info)
        for key, value in self.original_char_info.items():
            curr_char_info[key]['经历'] = experience[key]

        char_list = list(curr_plot['characters'].keys())
        other_char_list = [c for c in char_list if c != self.main_character]
        other_char_info = {}
        for char in other_char_list:
            other_char_info[char] = copy.deepcopy(curr_char_info[char])

        all_outlines = {}
        modified_plots = {}
        continued_outlines = {}

        # 在此考虑并行
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.process_personality, personality, fork_plot_to_modify_continue_plot_info,
                                other_char_info, fork_num, index): personality
                for personality in self.personality_choice.keys()
            }

            for future in as_completed(futures):
                personality = futures[future]
                try:
                    result = future.result()
                    all_outlines[personality] = result[personality]['all']
                    modified_plots[personality] = result[personality]['modified']
                    continued_outlines[personality] = result[personality]['continued']
                except Exception as e:
                    logger.error(f"Error processing {personality}: {e}")

        # 考虑改成只判断后面的部分
        chosen_personality = self.select_outline(fork_plot_to_modify_continue_plot_info['curr_next_plot_list'],
                                                 all_outlines, save_dir, start_index)

        # 根据personality读取改写的plot和续写的plot
        return {
            chosen_personality[0]: {
                "all": all_outlines[chosen_personality[0]],
                "modified": modified_plots[chosen_personality[0]],
                "continued": continued_outlines[chosen_personality[0]]
            },
            chosen_personality[1]: {
                "all": all_outlines[chosen_personality[1]],
                "modified": modified_plots[chosen_personality[1]],
                "continued": continued_outlines[chosen_personality[1]]
            }
        }
