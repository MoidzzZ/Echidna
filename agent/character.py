import copy

from langchain_openai import ChatOpenAI
from agent.char_prompt import *
from extra.utils import *
import logging

logger = logging.getLogger('GlobalLogger')


class Character:
    def __init__(self, name, description):
        self.name = name
        self.description = copy.deepcopy(description)
        self.appearance = self.description["外观"]
        self.profile = self.description["简介"]
        self.personality = self.description["性格"]
        self.experience = self.description["经历"]

        self.llm = None
        self.goal = None
        self.behavior = None

        self.guidance = ""

    def set_llm(self, model):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.5,
            top_p=0.5,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key="ab33d003-082d-419f-b750-48c436280595",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )

    def set_goal(self, goal):
        self.goal = goal

    def set_behavior(self, behavior):
        self.behavior = behavior

    def set_guidance(self, guidance):
        self.guidance = guidance

    def start_talk(self, env_info, cause):
        other_char_info = env_info['other_char_info']

        prompt = start_talk_template.format(name=self.name, appearance=self.appearance, profile=self.profile,
                                            personality=self.personality, other_char_info=other_char_info,
                                            memory=self.experience, goal=self.goal, cause=cause, behavior=self.behavior)

        response = self.llm.invoke(prompt).content
        result = postprocess(response, self.name)
        return result

    def talk(self, env_info, history):
        other_char_info = env_info['other_char_info']

        prompt = talk_template.format(name=self.name, appearance=self.appearance, profile=self.profile,
                                      personality=self.personality, other_char_info=other_char_info, goal=self.goal,
                                      memory=self.experience, history=history, behavior=self.behavior)

        response = self.llm.invoke(prompt).content
        result = postprocess(response, self.name)
        return result

    # 用于auto_chat
    def guide_talk(self, env_info, history):
        other_char_info = env_info['other_char_info']

        prompt = guide_talk_template.format(name=self.name, appearance=self.appearance, profile=self.profile,
                                            personality=self.personality, other_char_info=other_char_info,
                                            memory=self.experience, history=history,
                                            behavior=self.behavior, guidance=self.guidance)

        response = self.llm.invoke(prompt).content
        result = postprocess(response, self.name)
        return result

    # 用于guide_chat
    def act(self, env_info, history, guidance):
        other_char_info = env_info['other_char_info']
        prompt = act_template.format(name=self.name, appearance=self.appearance, profile=self.profile,
                                     personality=self.personality, other_char_info=other_char_info,
                                     behavior=self.behavior, memory=self.experience, history=history, guidance=guidance)

        response = self.llm.invoke(prompt).content
        result = postprocess(response, self.name)
        return result

    def update_memory(self, dialogue_history):
        history = []
        for chat in dialogue_history:
            name = chat[0]
            content = chat[1]
            if name == self.name:
                history.append(f"{name}(自己): {content}")
            else:
                history.append(f"{name}: {content}")

        prompt = memorize_template.format(name=self.name, appearance=self.appearance, history=history)
        self.experience.append(self.llm.invoke(prompt).content)

    def update_experience(self, post_plot_list):
        experienced = []
        # 先提取pre_plot_list中有当前角色参与的情节
        for plot in post_plot_list:
            if self.name in list(plot['characters'].keys()):
                experienced.append(plot)

        # 将时间地点相同的情节合并
        curr_scene = {}
        # 默认至少两个情节
        for i, plot in enumerate(experienced):
            if i == 0:
                curr_scene = {
                    '地点': plot['location'],
                    '时间': plot['time'],
                    '情节链': [
                        {"情节内容": plot['summary'],
                         "角色表现": plot['characters'][self.name]}
                    ]
                }
                continue
            else:
                if plot['location'] == curr_scene['地点'] and plot['time'] == curr_scene['时间']:
                    curr_scene['情节链'].append(
                        {"情节内容": plot['summary'],
                         "角色表现": plot['characters'][self.name]}
                    )
                else:
                    # 将此前的内容更新到记忆里
                    prompt = summarize_template.format(name=self.name, profile=self.profile, experience=self.experience,
                                                       curr_scene=curr_scene)

                    self.experience.append(self.llm.invoke(prompt).content)
                    curr_scene = {
                        '地点': plot['location'],
                        '时间': plot['time'],
                        '情节链': [
                            {"情节内容": plot['summary'],
                             "角色表现": plot['characters'][self.name]}
                        ]
                    }

        if curr_scene:
            prompt = summarize_template.format(name=self.name, profile=self.profile, experience=self.experience,
                                               curr_scene=curr_scene)
            experience_updated = self.llm.invoke(prompt).content
            self.experience.append(experience_updated)


class VirtualPlayer:
    def __init__(self, name, llm):
        self.name = name
        self.llm = llm

    def make_change(self, to_modify_continue_plot_info):
        # 提取plot_title前的plot
        pre_plot_list = to_modify_continue_plot_info['pre_plot_list']
        stream_cache = to_modify_continue_plot_info['stream_cache']
        experience = stream_cache['character_experience']
        fork_plot = to_modify_continue_plot_info['curr_plot']

        prompt = change_prompt.format(
            name=self.name,
            plot_list=pre_plot_list,
            experience=experience[self.name],
            curr_plot=fork_plot,
        )

        response = self.llm.invoke(prompt).content
        behavior_list = response.split('；')
        behavior_dict = {}
        for behavior in behavior_list:
            behavior_dict[behavior.split('：')[0].strip()] = behavior.split('：')[1].strip()

        return behavior_dict
