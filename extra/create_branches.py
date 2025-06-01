import json
import logging
import math

from langchain_core.prompts import ChatPromptTemplate

from extra.utils import extract_json
logger = logging.getLogger('GlobalLogger')
# 在这里实现两种对比方案
# 传入

vanilla_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你是一名资深的脚本家，专门创作具有情节起伏的故事，擅长为给定的初步情节续写大纲。
你的专长在于使叙事具有新鲜感，确保每个情节点都经过精心设计，既有出乎意料的展开，但又与前文呼应，吸引观众深入互动。
故事的发展不局限于积极推进，过于消极或恶性的行为需要生成不好的结局，故事结束的标志是情节互动走向平淡。
只需要考虑演出事件的主要矛盾，并不需要照应前面的所有内容。
---
只需要生成大纲续写部分的story_sections，大纲应以json格式输出，json每部分的内容说明如下：
{{
"story_sections": [
    {{
         "title": "情节标题",
         "location": "地点",
         "time": "时间",
         "characters": {{
             "角色名": "角色在当前情节的主要行为和特征",
             "角色名": "角色在当前情节的主要行为和特征",
         }},
         "summary": "情节梗概",
         "start": "情节起始的角色行为",
         "end": "情节最终的角色行为"
    }}
]
}}
---
生成情节部分应遵循以下要求：
情节中需要出现的所有关键人物都已经在characters_info中表明，不要增加新的关键人物。
characters：对参与情节的主要角色指定行为和特征，场景内的角色尽量都在相邻的情节指定表现，可以是旁观等行为。可以创建低于主要角色数量的情节需要的过渡角色，将其名称和主要行为写入characters中。
location和time：生成地点和时间信息时，注意前文故事和角色信息创建的世界尺度，不要超出范畴，尽量与相邻情节保持一致，不要频繁做细小的场景变化。
summary：情节梗概内容应该在细致度上仿照已有部分的篇幅，概述事件的整体走向时写出角色的动态。
start和end：情节起始和最终的行为，应该综合情节梗概和角色行为给出，指明具体角色在对应时刻的表现。
请只输出续写大纲的story_sections，续写大纲时请保持连贯性和一致性。
注意大纲的格式与要求，最后输出只需要大纲，不要输出其他内容。
     """),
    ("user",
     """
现在你有一份未完成的小说大纲，它包含了故事的一部分。
请你根据已有内容逐步发展后面的情节直至合适的结束时刻，可以是不好的结局。
视情况增加{floor}到{ceil}个情节，情节细致度应参考未完成大纲中的部分。
未完成大纲：{outline_json}
续写大纲的第一个情节可以参考此情节作出修改：{curr_plot}
     """)
])


# 普通方法，给定原始大纲，让其改变分支点及后续的内容
# 记得把温度设置为高温
def vanilla_create_branches(llm, to_modify_continue_plot_info, fork_point, char_description, total_len,
                            fork_num, index):
    pre_plot_list = to_modify_continue_plot_info[fork_point]['pre_plot_list']
    curr_plot = to_modify_continue_plot_info[fork_point]['curr_plot']

    todo_outline_content = {
        "characters_info": char_description,
        "story_sections": pre_plot_list
    }

    todo_outline = json.dumps(todo_outline_content, ensure_ascii=False, indent=4)

    post_len = total_len - len(pre_plot_list)
    floor = math.ceil(1.3 * (fork_num - index))
    ceil = max(floor, math.ceil(post_len * 1.3))

    prompt = vanilla_template.format(
        outline_json=todo_outline,
        curr_plot=curr_plot,
        floor=floor,
        ceil=ceil
    )

    retry = 0
    while retry < 5:
        try:
            continued_plot = extract_json(llm.invoke(prompt).content)
            continued_plot_dict = json.loads(continued_plot)
            continued_plot_list = continued_plot_dict['story_sections']
            break
        except json.JSONDecodeError as e:
            retry += 1
            curr_plot_ = f"{curr_plot}。请注意按照格式输出json响应"
            prompt = vanilla_template.format(
                outline_json=todo_outline,
                curr_plot=curr_plot_,
                floor=floor,
                ceil=ceil
            )
        except Exception as e:
            print(e)

    pre_continued_plot_list = pre_plot_list.copy()
    pre_continued_plot_list.extend(continued_plot_list)

    # 返回完整情节的list
    return pre_continued_plot_list


judge_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你是一个文学专家，需要从给定的情节列表中判断剧情的起始，危机和高潮各自对应的一个情节。
请严格按照以下 JSON Schema 输出结果，不要添加任何额外内容：
{{
"起始": "字符串，对应情节名",
"危机": "字符串，对应情节名",
"高潮": "字符串，对应情节名"
}}
    """),
    ("user",
     """
具体的情节列表：
{plot_list}
     """)
])

ad_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你是一个文学专家，请根据给定情节的内容，对其中{main_character}的行为提出一段新的内容，使情节的后续发展发生改变。
提出的内容需要以{main_character}为主语，不超过30字。
    """),
    ("user",
     """
全部情节：
{all_plot}
需要修改行为的情节内容，请对此情节生成一段新的行为用于改变剧情发展：
{curr_plot}
只需要输出具体的行为内容。{last_ad_info}
     """)
])

meta_prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你将为一个替代故事情节生成一个详细的提示，该提示将用于指导语言模型生成连贯且具有深度的叙事内容。
请严格按照以下 JSON Schema 输出结果，不要添加任何额外内容：
{{
    "问题1": "新决策如何影响主角的策略或目标？",
    "问题2": "这一决策如何影响主角的道德成长或人际关系？",
    "问题3": "主角是否会保留原始动机？这一变化如何体现？",
    "问题4": "主要反派或冲突如何因新决策而发生变化？",
    "问题5": "主角如何重新定义自己的身份或角色？"
}}
请根据已有情节，原有情节的关键情节，角色新的行为将每个问题的值实例化围绕剧情的具体问题。
    """),
    ("user",
     """
原有情节:
{all_plot}
原有故事线的起始：{start}
原有故事线的危机：{crisis}
原有故事线的高潮：{climax}
在当前情节：
{curr_plot}
主角{main_character}采取了新决策：{ad}
     """)
])

continue_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你是一名资深的脚本家，专门创作具有情节起伏的故事，擅长为给定的初步情节续写大纲。
你的专长在于使叙事具有新鲜感，确保每个情节点都经过精心设计，既有出乎意料的展开，但又与前文呼应，吸引观众深入互动。
故事的发展不局限于积极推进，过于消极或恶性的行为需要生成不好的结局，故事结束的标志是情节互动走向平淡。
只需要考虑演出事件的主要矛盾，并不需要照应前面的所有内容。
---
只需要生成大纲续写部分的story_sections，大纲应以json格式输出，json每部分的内容说明如下：
{{
"story_sections": [
    {{
         "title": "情节标题",
         "location": "地点",
         "time": "时间",
         "characters": {{
             "角色名": "角色在当前情节的主要行为和特征",
             "角色名": "角色在当前情节的主要行为和特征",
         }},
         "summary": "情节梗概",
         "start": "情节起始的角色行为",
         "end": "情节最终的角色行为"
    }}
]
}}
---
生成情节部分应遵循以下要求：
情节中需要出现的所有关键人物都已经在characters_info中表明，不要增加新的关键人物。
characters：对参与情节的主要角色指定行为和特征，场景内的角色尽量都在相邻的情节指定表现，可以是旁观等行为。可以创建低于主要角色数量的情节需要的过渡角色，将其名称和主要行为写入characters中。
location和time：生成地点和时间信息时，注意前文故事和角色信息创建的世界尺度，不要超出范畴，尽量与相邻情节保持一致，不要频繁做细小的场景变化。
summary：情节梗概内容应该在细致度上仿照已有部分的篇幅，概述事件的整体走向时写出角色的动态。
start和end：情节起始和最终的行为，应该综合情节梗概和角色行为给出，指明具体角色在对应时刻的表现。
请只输出续写大纲的story_sections，续写大纲时请保持连贯性和一致性。
注意大纲的格式与要求，最后输出只需要大纲，不要输出其他内容。
     """),
    ("user",
     """
现在你有一份未完成的小说大纲，它包含了故事的一部分。
请你根据已有内容逐步发展后面的情节直至合适的结束时刻，可以是不好的结局。
视情况增加{floor}到{ceil}个情节，情节细致度应参考未完成大纲中的部分。
未完成大纲：
{outline_json}
当前情节:
{curr_plot}
主角{main_character}采取了新决策：{ad}，修改当前情节和生成后续内容时请思考如下事项：
{meta_prompt}
     """)
])


# what-if方法，给定原始大纲。通过元提示生成新的行为，并生成后续的内容
def whatif_create_branches(llm, to_modify_continue_plot_info, fork_point, main_character, char_description, total_len,
                           fork_num, index, last_ad=""):
    # 需要从原始故事识别出起始，危机，高潮
    pre_plot_list = to_modify_continue_plot_info[fork_point]['pre_plot_list']
    curr_plot = to_modify_continue_plot_info[fork_point]['curr_plot']

    all_plot_list = pre_plot_list.copy()
    all_plot_list.extend(to_modify_continue_plot_info[fork_point]['curr_next_plot_list'])

    judge_prompt = judge_template.format_prompt(plot_list=all_plot_list)

    retry = 0
    while retry < 5:
        try:
            chosen_plot = extract_json(llm.invoke(judge_prompt).content)
            chosen_plot_dict = json.loads(chosen_plot)
            break
        except json.JSONDecodeError as e:
            retry += 1
        except Exception as e:
            print(e)

    logger.info("关键情节信息:")
    logger.info(chosen_plot_dict)

    # 然后对角色行为提出替代行为。
    if last_ad != "":
        last_ad_info = f"请尽量避免此替代行为：{last_ad}。"
    else:
        last_ad_info = ""

    ad_prompt = ad_template.format_prompt(all_plot=all_plot_list,
                                          curr_plot=curr_plot,
                                          main_character=main_character,
                                          last_ad_info=last_ad_info)
    ad = llm.invoke(ad_prompt).content.strip()

    logger.info("替代行为:")
    logger.info(ad)

    # 针对替代行为和情节整体的信息生成元提示。
    meta_prompt_prompt = meta_prompt_template.format_prompt(
        all_plot=all_plot_list,
        start=chosen_plot_dict['起始'],
        crisis=chosen_plot_dict['危机'],
        climax=chosen_plot_dict['高潮'],
        curr_plot=curr_plot,
        main_character=main_character,
        ad=ad
    )

    retry = 0
    while retry < 5:
        try:
            meta_prompt = extract_json(llm.invoke(meta_prompt_prompt).content)
            meta_prompt_dict = json.loads(meta_prompt)
            break
        except json.JSONDecodeError as e:
            ad_ = f"{ad}。请注意按照格式输出json响应"
            logger.info(f"元提示生成失败，请修改替代行为:{ad_}")
            meta_prompt_prompt = meta_prompt_template.format_prompt(
                all_plot=all_plot_list,
                start=chosen_plot_dict['起始'],
                crisis=chosen_plot_dict['危机'],
                climax=chosen_plot_dict['高潮'],
                curr_plot=curr_plot,
                main_character=main_character,
                ad=ad_
            )
            retry += 1
        except Exception as e:
            print(e)

    logger.info("元提示信息:")
    logger.info(meta_prompt_dict)

    # 给定已有大纲，生成后续的内容
    todo_outline_content = {
        "characters_info": char_description,
        "story_sections": pre_plot_list
    }

    todo_outline = json.dumps(todo_outline_content, ensure_ascii=False, indent=4)

    post_len = total_len - len(pre_plot_list)
    floor = math.ceil(1.3 * (fork_num - index))
    ceil = max(floor, math.ceil(post_len * 1.3))

    prompt = continue_template.format(
        floor=floor,
        ceil=ceil,
        outline_json=todo_outline,
        curr_plot=curr_plot,
        main_character=main_character,
        ad=ad,
        meta_prompt=meta_prompt_dict
    )

    retry = 0
    while retry < 5:
        try:
            continued_plot = extract_json(llm.invoke(prompt).content)
            continued_plot_dict = json.loads(continued_plot)
            continued_plot_list = continued_plot_dict['story_sections']
            break
        except json.JSONDecodeError as e:
            retry += 1
            meta_prompt_dict_ = f"{meta_prompt_dict}。请注意按照格式输出json响应"
            logger.info(f"情节生成失败，请修改提示词:{meta_prompt_dict_}")
            prompt = continue_template.format(
                floor=floor,
                ceil=ceil,
                outline_json=todo_outline,
                curr_plot=curr_plot,
                main_character=main_character,
                ad=ad,
                meta_prompt=meta_prompt_dict_
            )
        except Exception as e:
            print(e)

    pre_continued_plot_list = pre_plot_list.copy()
    pre_continued_plot_list.extend(continued_plot_list)

    # 返回完整情节的list
    return ad, pre_continued_plot_list
