import json
import concurrent.futures
from langchain_openai import ChatOpenAI
from tqdm import tqdm
from agent.gm_prompt import *
import logging
from datetime import datetime
import random
from extra.utils import *

logger = logging.getLogger('GlobalLogger')
api_key = ""
base_url = ""


def set_llm(model, temperature=0.7):
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        top_p=0.9,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=api_key,
        base_url=base_url,
    )


class GM:
    def __init__(self, gm_llm, npc_api_pools, characters, mode="goal"):
        self.gm_llm = gm_llm

        self.npc_api_pools = npc_api_pools
        # 对于每一个性格也指定一个npc_api
        self.personality_api_pools = {
            "开拓": self.npc_api_pools[0],
            "同谐": self.npc_api_pools[1],
            "毁灭": self.npc_api_pools[2],
            "虚无": self.npc_api_pools[3],
            "欢愉": self.npc_api_pools[4],
        }

        self.characters = characters
        self.other_characters = {}
        self.player = list(characters.keys())[0]
        self.involved_characters = []
        self.character_list = []

        self.plot_nodes = {}
        self.node_index = 0
        self.step = 0
        self.dialogue_history = []
        self.plot_history = []
        self.guide = True if mode == 'guide' else False
        self.title = ""
        self.goal = ""
        self.start = ""
        self.end = ""
        self.mixed_plot_dict = {}

        # 维护一张角色关系表
        self.relationship = {}

        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_dir = f"./{current_time}"

    def load_outline(self, outline):
        self.plot_nodes = outline
        self.relationship = outline['initial_relationship']

    def load_plot(self, characters_behavior):
        self.involved_characters = []
        self.character_list = []

        for name, behavior in characters_behavior.items():
            if name not in list(self.characters.keys()):
                self.other_characters[name] = behavior
            else:
                self.involved_characters.append(self.characters[name])

        for c in self.involved_characters:
            self.character_list.append(c.name)

        for c in list(self.other_characters.keys()):
            self.character_list.append(c)

        for i, c in enumerate(self.involved_characters):
            c.set_llm(self.npc_api_pools[i])
            c.set_behavior(characters_behavior[c.name])
            c.set_goal(self.goal)
            c.set_guidance("")

    def get_env_info(self, character):
        env_info = {}

        relationship_sheet = self.relationship[character.name]
        other_char_info = '\n'
        involved_characters = [c.name for c in self.involved_characters]

        for name, relationship in relationship_sheet.items():
            if name not in involved_characters:
                continue

            # 熟悉的人不仅知道性格，同样也要知道外观和简介，对下面代码做修改
            if relationship == "陌生":
                other_char_info += f"有一位{self.characters[name].appearance}\n"
            elif relationship == "认识":
                other_char_info += (f"{name}: \n外观上，{self.characters[name].appearance}。\n"
                                    f"{self.characters[name].profile}\n")
            elif relationship == "熟悉":
                other_char_info += (f"{name}: \n外观上，{self.characters[name].appearance}。\n"
                                    f"{self.characters[name].profile}"
                                    f"\n 性格上，{self.characters[name].personality}\n")
            else:
                other_char_info += f'{name}\n'

        # 未来可以考虑加入互动信息，比如背景角色
        env_info['other_char_info'] = other_char_info
        return env_info

    # 对于一些生成的过渡角色，让GM进行简化地扮演，只作为背景信息
    def other_character_talk(self, character_name):
        history = format_history(self.dialogue_history)

        # 同样只考虑主要角色
        other_char_info = '\n'
        for character in self.involved_characters:
            other_char_info += (f"{character.name}: \n外观上，{character.appearance}。\n"
                                f"{character.profile}")

        prompt = other_talk_template.format(name=character_name, goal=self.goal,
                                            behavior=self.other_characters[character_name],
                                            other_char_info=other_char_info, history=history)
        response = self.gm_llm.invoke(prompt).content.strip()
        return postprocess(response, character_name)

    # 根据当前情节的起因指定第一句话的角色
    def start_chat(self):
        if self.guide:
            self.llm_guide()

        prompt = start_template.format(summary=self.goal, start=self.start, characters=self.character_list)
        chosen_character_name = self.gm_llm.invoke(prompt).content.strip()

        if chosen_character_name not in self.character_list:
            chosen_character_name = random.choice(list(self.characters.keys()))
        if chosen_character_name in list(self.other_characters.keys()):
            result = self.other_character_talk(chosen_character_name)
        else:
            chosen_character = self.characters[chosen_character_name]
            env_info = self.get_env_info(chosen_character)
            result = chosen_character.start_talk(env_info, self.start)

        self.dialogue_history.append((chosen_character_name, result))

    def get_respond(self, character_name):
        if character_name in list(self.other_characters.keys()):
            return self.other_character_talk(character_name)
        elif self.characters[character_name] in self.involved_characters:
            # 对每个角色的对话历史进行修正
            history = []
            relationship_sheet = self.relationship[character_name]

            character = self.characters[character_name]
            env_info = self.get_env_info(character)
            for chat in self.dialogue_history:
                name = chat[0]
                content = chat[1]
                if name in relationship_sheet:
                    if relationship_sheet[name] == "陌生":
                        history.append(f"{self.characters[name].appearance}: {content}")
                    else:
                        history.append(f"{name}: {content}")
                elif name == character_name:
                    history.append(f"{name}(自己): {content}")
            # guide_talk是behavior+guidance，talk是goal+behavior（消融实验）
            if self.guide:
                return character.guide_talk(env_info, history)
            else:
                return character.talk(env_info, history)
        else:
            return "Error: Character not found."

    def make_thoughts(self, style="auto"):
        thoughts = {}
        # 不能使用全部的other_characters，GM只有一个可以调用的机会（暂时使用随机调用）
        if style == "interact":
            curr_character_list = [involved_character.name for involved_character in self.involved_characters
                                   if involved_character.name != self.player]
        else:
            curr_character_list = [involved_character.name for involved_character in self.involved_characters]

        if len(list(self.other_characters.keys())) != 0:
            other_character = random.choice(list(self.other_characters.keys()))
            curr_character_list.append(other_character)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_npc = {executor.submit(self.get_respond, character): character
                             for character in curr_character_list}
            for future in concurrent.futures.as_completed(future_to_npc):
                try:
                    thought = future.result()
                    # 将结果合成字典，key为角色名
                    npc = future_to_npc[future]
                    thoughts[npc] = thought
                except Exception as exc:
                    npc = future_to_npc[future]
                    thoughts[npc] = f"Error generating thought: {exc}"

        return thoughts

    def order_output(self, thoughts, style="auto", mode="multi_step"):
        char_info = []
        for character in self.involved_characters:
            if style == "interact":
                if character.name == self.player:
                    continue
            char_info.append(f"{character.name}: {character.profile}")
        for character, behavior in self.other_characters.items():
            char_info.append(f"{character}")

        history = format_history(self.plot_history)

        thoughts_list = []
        for name, thought in thoughts.items():
            thoughts_list.append(f"{name}: {thought}")

        chosen_characters = []

        if mode == "multi_step":
            prompt = multi_step_order_template.format(goal=self.goal, char_info=char_info,
                                                      thoughts=thoughts_list, history=history)
        else:
            prompt = order_template.format(goal=self.goal, char_info=char_info, thoughts=thoughts_list, history=history)

        chosen_character_str = self.gm_llm.invoke(prompt).content.strip()
        for s in chosen_character_str.split(';'):
            if s.strip() in list(thoughts.keys()):
                chosen_characters.append(s.strip())

        if len(chosen_characters) == 0:
            chosen_character = random.choice(list(thoughts.keys()))
            chosen_characters.append(chosen_character)

        return chosen_characters

    def update_plot(self, new_node_index):
        new_node_index = str(new_node_index)
        # relationship更新
        name_list = []
        for chat in self.plot_history:
            name = chat[0]
            if name in list(self.characters.keys()):
                if name not in name_list:
                    name_list.append(name)
        for i, name in enumerate(name_list):
            for other_name in name_list[i+1:]:
                if self.relationship[name][other_name] == "陌生":
                    self.relationship[name][other_name] = "认识"
                    self.relationship[other_name][name] = "认识"

        # 判断场景是否发生改变，从地点时间角色的角度，如果改变，清空对话历史，更新角色记忆
        new_location = self.plot_nodes[new_node_index]['location']
        new_time = self.plot_nodes[new_node_index]['time']
        new_character_list = self.plot_nodes[new_node_index]['characters'].keys()

        old_location = self.plot_nodes[self.node_index]['location']
        old_time = self.plot_nodes[self.node_index]['time']
        old_character_list = self.plot_nodes[self.node_index]['characters'].keys()

        # 变换场景时更新记忆
        if old_location != new_location or old_time != new_time or set(old_character_list) != set(new_character_list):
            for c in self.involved_characters:
                c.update_memory(self.dialogue_history)
            self.dialogue_history = []

    def init_game(self):
        self.node_index = str(self.node_index)
        self.goal = self.plot_nodes[self.node_index]['summary']

        self.end = self.plot_nodes[self.node_index]['end']
        self.load_plot(self.plot_nodes[self.node_index]['characters'])
        if self.guide:
            self.llm_guide()

    def next_plot(self, node_index):
        self.update_plot(node_index)
        self.node_index = node_index
        self.node_index = str(self.node_index)
        self.plot_history = []
        self.step = 0

        self.goal = self.plot_nodes[self.node_index]['summary']
        self.start = self.plot_nodes[self.node_index]['start']
        self.end = self.plot_nodes[self.node_index]['end']

        characters_behavior = self.plot_nodes[self.node_index]['characters']
        self.load_plot(characters_behavior)

        # 在这个地方使用start_chat
        self.start_chat()
        chosen_character, resp = self.dialogue_history[-1]
        self.step += 1
        self.plot_history.append(self.dialogue_history[-1])
        return {}, [[chosen_character, resp]]

    def next_mixed_plot(self, node_index_list):
        self.update_plot(node_index_list[0])
        self.plot_history = []
        self.step = 0

        # 用第一个节点做一下初始化，goal在实际交互中初始化
        first_node_index = str(node_index_list[0])
        self.load_plot(self.plot_nodes[first_node_index]['characters'])

        for node_index in node_index_list:
            plot_node_info = self.plot_nodes[str(node_index)]['node_info']
            plot_node_chain = plot_node_info.split('：')[0]
            personality = plot_node_chain.split('_')[-1]
            self.mixed_plot_dict[personality] = {
                "index": str(node_index),
                "summary": self.plot_nodes[str(node_index)]['summary'],
                "characters": self.plot_nodes[str(node_index)]['characters'],
                "end": self.plot_nodes[str(node_index)]['end'],
            }
        return {
            "location": self.plot_nodes[first_node_index]['location'],
            "time": self.plot_nodes[first_node_index]['time']
        }

    def interact_chat(self, player_input, mixed=False):
        if player_input == "":
            style = "auto"
        else:
            style = "interact"
            self.dialogue_history.append((self.player, player_input))
            self.plot_history.append(self.dialogue_history[-1])
            self.step += 1
            new_index, char, resp = self.step_check()
            if char == "system":
                return new_index, [[char, resp]]

        if mixed:
            results = {}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {executor.submit(self.mixed_plot_score, personality): personality
                           for personality in self.mixed_plot_dict.keys()}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        score = future.result()
                        personality = futures[future]
                        results[personality] = score
                    except Exception as exc:
                        personality = futures[future]
                        results[personality] = 0

            personalities = list(results.keys())
            scores = [results[personality] for personality in personalities]
            max_score = max(scores)
            chosen_personality = personalities[scores.index(max_score)]

            self.node_index = str(self.mixed_plot_dict[chosen_personality]["index"])
            self.goal = self.mixed_plot_dict[chosen_personality]["summary"]
            self.end = self.mixed_plot_dict[chosen_personality]["end"]

            characters_behavior = self.mixed_plot_dict[chosen_personality]["characters"]
            self.load_plot(characters_behavior)

            if self.guide:
                self.llm_guide()

        thoughts = self.make_thoughts(style=style)
        chosen_characters = self.order_output(thoughts, style=style)
        char_resp = []
        for chosen_character in chosen_characters:
            self.step += 1
            response = thoughts[chosen_character]
            self.dialogue_history.append((chosen_character, response))
            self.plot_history.append(self.dialogue_history[-1])

            char_resp.append([chosen_character, response])

            new_index, char, resp = self.step_check()
            if char == "GM":
                char_resp.append([char, resp])
                return new_index, char_resp
        return {}, char_resp

    def step_check(self, period=3, max_step=12):
        if self.step % period == 0:
            if self.llm_plot_complete_check_and_guide():
                new_index = self.get_next_index()
                return new_index, "GM", "goal satisfied, plot complete"
        if self.step >= max_step:
            new_index = self.get_next_index()
            return new_index, "GM", "too many turns, plot complete"
        return {}, "", ""

    def get_next_index(self):
        next_plot_index = self.plot_nodes[self.node_index]['children_index']
        curr_chain = self.plot_nodes[self.node_index]['node_info'].split('：')[0]
        curr_personality = curr_chain.split('_')[-1]

        if len(next_plot_index) == 0:
            return {
                curr_personality: [999]
            }
        elif len(next_plot_index) == 1:
            return {
                curr_personality: next_plot_index
            }
        # 按照涉及到的人物进行划分，可能删减了部分线路
        else:
            plot_characters = {}
            for i in range(len(next_plot_index)):
                next_index = next_plot_index[i]
                next_plot_node_info = self.plot_nodes[str(next_index)]['node_info']
                next_plot_node_chain = next_plot_node_info.split('：')[0]
                next_personality = next_plot_node_chain.split('_')[-1]
                characters = list(self.plot_nodes[str(next_index)]['characters'].keys())
                plot_characters[next_personality] = {
                    'characters': characters,
                    'next_index': next_index
                }
            # 组合characters相同的next_index
            grouped_characters = {}
            # 遍历 plot_characters，按 characters 分组
            for personality, info in plot_characters.items():
                # 考虑生成的角色名顺序可能不同，使用frozenset
                characters = frozenset(info['characters'])  # 将 characters 转为元组以便用作字典键
                next_index = info['next_index']

                if characters not in grouped_characters:
                    grouped_characters[characters] = {
                        'personalities': [],
                        'indices': []
                    }

                # 添加当前 personality 和对应的 index
                grouped_characters[characters]['personalities'].append(personality)
                grouped_characters[characters]['indices'].append(next_index)

            # 转换为最终结果格式
            result = {}
            for characters, group_info in grouped_characters.items():
                merged_personalities = ''.join(sorted(group_info['personalities']))  # 合并 personalities 为字符串
                result[merged_personalities] = group_info['indices']
            return result

    def llm_plot_complete_check_and_guide(self):
        history = format_history(self.plot_history)
        prompt = end_check_template.format(goal=self.goal, end=self.end, history=history)
        value = float(self.gm_llm.invoke(prompt).content.strip())

        try:
            if value > 0.8:
                return True
            else:
                if self.guide:
                    self.llm_guide()
                return False
        except ValueError:
            return False

    def llm_guide(self):
        # 让GM给参与角色指导
        char_info = []
        for character in self.involved_characters:
            char_info.append(f"{character.name}: {character.profile}")

        history = format_history(self.plot_history)

        prompt = guide_template.format(goal=self.goal, char_info=char_info, history=history)

        character_guidance = extract_json(self.gm_llm.invoke(prompt).content)
        guidance_dict = json.loads(character_guidance)

        for character in self.involved_characters:
            if character.name in list(guidance_dict.keys()):
                character.set_guidance(guidance_dict[character.name])

    def mixed_plot_score(self, personality):
        api = self.personality_api_pools[personality]
        score_llm = set_llm(api, temperature=0)

        history = format_history(self.plot_history)
        plot_info = self.mixed_plot_dict[personality]
        plot_summary = plot_info['summary']

        prompt = mixed_score_template.format(goal=plot_summary, history=history)
        result = score_llm.invoke(prompt).content
        score = int(result)

        return score

    # 用于branching_system
    def single_plot_complete(self, save_dir, post_plot_list, curr_plot):
        os.makedirs(save_dir, exist_ok=True)
        self.save_dir = save_dir

        self.title = curr_plot['title']
        self.load_plot(curr_plot["characters"])

        # 更新当前场景角色的记忆，不是很多就用串行了，实际调用每个角色的llm并行更好
        for character in tqdm(self.involved_characters):
            character.update_experience(post_plot_list)

        character_experience = {}
        for name in self.characters:
            character_experience[name] = self.characters[name].experience
        plot_info = {
            "title": self.title,
            "character_experience": character_experience,
        }

        with open(f'{self.save_dir}/{self.title}.json', 'w', encoding='utf-8') as f:
            json.dump(plot_info, f, ensure_ascii=False, indent=4)
