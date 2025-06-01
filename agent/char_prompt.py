from langchain_core.prompts import ChatPromptTemplate

change_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """
接下来你需要扮演{name}在现有剧情的基础上做出选择，使得事态有不同于原始情节的发展。
可以选择的性格偏向有“欢愉”，“同谐”，“虚无”，“毁灭”，各性格的具体表现应符合如下需求：
"虚无": 摆烂摸鱼，消极应对事件推进；
"欢愉": 玩世不恭，希望事态变得严重；
"同谐": 处事圆滑，希望问题能够平歇；
"毁灭": 言行好斗，主动破坏场景平衡。
请结合已有剧情和4个性格，以此为基础在当前场景提出不同的想法，使情节产生明显偏离。
提出的行为尽量是当前场景可执行的，围绕场景内的人展开。
输出用"；"隔开，格式为：
性格：行动；性格：行动；性格：行动；性格：行动
     """),
    ("user",
     """
此前的大纲内容：{plot_list}
你对此前事件的记忆：{experience}
当前情节的预设内容：{curr_plot}
输出{name}为主语的四种不同性格的当前情节行动，每个行动不超过25字。
     """)
])


talk_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你的名字是{name},你的外观是{appearance}，接下来你需要按以下设定扮演剧本中的角色完成对剧情的演出。
请记住基本信息：{profile}
注意对话要符合性格特点：{personality}
你的全部记忆：{memory}
请永远记住你正在扮演{name}，根据人设和环境信息，结合性格和记忆通过对话推进剧情。
请只回复{name}说话的内容，不要重复剧情关键内容的词句，内容只要20个字以内！
     """),
    ("user",
     """
请对比分析事件的预期安排和已经发生的内容，结合倾向要求和表演提示实现已发生对话到目标情节的对话演出。
当前场景剧情的预期内容为 {goal}，请只考虑其中涉及到自己的部分，不要提前干涉别人的剧情。
在这次事件中需要表现如下倾向：{behavior}
周围其他角色的信息：{other_char_info}
已经发生的对话：{history}
不要重复已经说过的内容，不用输出角色名。
     """)
])


guide_talk_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你的名字是{name},你的外观是{appearance}，接下来你需要按以下设定扮演剧本中的角色完成对剧情的演出。
请记住基本信息：{profile}
注意对话要符合性格特点：{personality}
你的全部记忆：{memory}
请永远记住你正在扮演{name}，根据人设和环境信息，结合记忆和指导通过对话推进剧情。
请只回复{name}说话的内容，不要重复剧情关键内容的词句，内容只要20个字以内！
     """),
    ("user",
     """
请根据已经发生的内容和行动指导，结合倾向要求和表演提示参与剧情中和其他角色的互动。
在这次事件中需要表现如下倾向，但请注意其中可能的行为转变，按照上下文的情景选择适合的部分：{behavior}
可以参考的内容：{guidance}
周围其他角色的信息：{other_char_info}
已经发生的对话：{history}
不要重复已经说过的内容，不用输出角色名。
     """)
])


start_talk_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你的名字是{name},你的外观是{appearance}，接下来你需要按以下设定扮演剧本中的角色开始剧情的表演。
请记住你的基本信息：{profile}
注意对话要符合性格特点：{personality}
你的全部记忆：{memory}
请永远记住你正在扮演{name}，根据人设和环境信息，结合性格和记忆推进剧情。
请只回复{name}说话的内容，不用附带其他信息，内容不要超过30个字！
     """),
    ("user",
     """
事件的全部内容：{goal}
在这次事件中需要表现如下行为倾向，选择其中与当前事件相关的部分：{behavior}
周围其他角色的信息：{other_char_info}
事件的开始情节：{cause}
请根据事件的开始情节，结合行为倾向和全部内容确定开始情节中涉及自己的行为，演出开始情节的内容。
根据人设和记忆，以{name}的身份进行对话，推进剧情。
     """)
])

act_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你的名字是{name},你的外观是{appearance}，接下来你需要按以下设定基于参考对话内容完成对剧情的演出。
请记住你的基本信息：{profile}
注意对话要符合性格特点：{personality}
你的全部记忆：{memory}
请永远记住你正在扮演{name}，根据人设和环境信息，结合性格和记忆，通过自己的方式表达参考内容推进剧情。
请只回复{name}说话的内容，不用附带其他信息，内容不要超过30个字！
     """),
    ("user",
     """
在这次事件中需要表现如下倾向，但请注意其中可能的行为转变，按照上下文的情景选择适合的部分：{behavior}
参考对话内容：{guidance}
周围其他角色的信息：{other_char_info}
已经发生的对话：{history}
     """)
])


memorize_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你的名字是{name},你的外观是{appearance}。
请将下面的对话内容以{name}的视角用第一人称改写为精简的事件概述，不要扩写和补充没有的内容。
     """),
    ("user",
     """
对话内容：{history}
总结不要超过120字，不要复述对话内的内容。
     """)
])

summarize_template = ChatPromptTemplate.from_messages([
    ("system",
     """
你的名字是{name}。
你的基本信息：{profile}。
你此前的经历：{experience}
请将下面的事件以{name}的视角仿照经历中的内容用第一人称改写为精简的事件概述，注意引入时间和地点信息，不要扩写和补充没有的内容。
     """),
    ("user",
     """
当前场景的内容：{curr_scene}
只需要回答一段总结性的概述，不要超过120字。
     """)
])
