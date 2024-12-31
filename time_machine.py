##########################################################
# time_machine.py
##########################################################
import os
import random
import asyncio
import re

import streamlit as st

# For openai>=1.0.0, we use AsyncOpenAI
from openai import AsyncOpenAI

# Import these so we can do isinstance checks
from autogen_agentchat.messages import SystemMessage, UserMessage, AssistantMessage

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination

##############################################################################
# 0) transform_autogen_messages using type checks
##############################################################################
def transform_autogen_messages(autogen_messages):
    """
    Convert autogen_agentchat's message objects (SystemMessage, UserMessage, etc.)
    into valid OpenAI chat messages with 'role' and 'content'.
    """
    openai_messages = []
    for m in autogen_messages:
        if isinstance(m, SystemMessage):
            role = "system"
            content = m.content
        elif isinstance(m, UserMessage):
            role = "user"
            content = m.content
        elif isinstance(m, AssistantMessage):
            role = "assistant"
            content = m.content
        else:
            # If there's a custom message type (like custom tool messages),
            # default to assistant or handle differently as needed.
            role = "assistant"
            # sometimes m might have .content; if not, fallback to empty
            content = getattr(m, "content", "")

        openai_messages.append({"role": role, "content": content})
    return openai_messages

##############################################################################
# LOCAL WRAPPER for openai => "OpenAIChatCompletionClient"
##############################################################################
class OpenAIChatCompletionClient:
    def __init__(self, openai_api_key, model="gpt-4", temperature=1.0):
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.temperature = temperature

    @property
    def model_info(self):
        """
        Mark function_calling=True so autogen_agentchat won't raise ValueError.
        """
        return {
            "function_calling": True
        }

    async def run_chat(self, messages):
        openai_messages = transform_autogen_messages(messages)
        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=openai_messages
        )
        return response.choices[0].message.content

    async def create(self, messages=None, model=None, temperature=None, **kwargs):
        used_model = model or self.model
        used_temp = temperature if (temperature is not None) else self.temperature

        openai_messages = transform_autogen_messages(messages or [])

        response = await self.client.chat.completions.create(
            model=used_model,
            temperature=used_temp,
            messages=openai_messages,
            **kwargs
        )

        return {
            "choices": [
                {
                    "message": response.choices[0].message
                }
            ]
        }

###############################################################################
# 1) Lists of famous individuals by category
###############################################################################
FAMOUS_PHYSICISTS = [
    "Albert Einstein",
    "Richard Feynman",
    # ...
]
# ... rest of your lists ...
ALL_CATEGORIES = [
    FAMOUS_PHYSICISTS,
    # ...
]

###############################################################################
# 2) List of general topics
###############################################################################
UNEXPECTED_TOPICS = [
    "conspiracy theories",
    # ...
]
FAMOUS_CONTESTS = [
    "Jeopardy-like trivia game",
    # ...
]
UNEXPECTED_TOPICS.extend(FAMOUS_CONTESTS)

###############################################################################
# 3) Helper functions
###############################################################################
def pick_two_people() -> tuple[str, str]:
    random.shuffle(ALL_CATEGORIES)
    chosen = []
    used_categories = set()
    while len(chosen) < 2:
        cat = random.choice(ALL_CATEGORIES)
        if tuple(cat) not in used_categories:
            used_categories.add(tuple(cat))
            chosen.append(random.choice(cat))
    return chosen[0], chosen[1]

def pick_random_topic() -> str:
    return random.choice(UNEXPECTED_TOPICS)

def decide_style() -> str:
    rnd = random.random()
    if rnd < 0.50:
        return "witty"
    elif rnd < 0.75:
        return "serious"
    else:
        return "moderate"

###############################################################################
# 4) run_famous_people_contest
###############################################################################
async def run_famous_people_contest():
    model_client = OpenAIChatCompletionClient(
        openai_api_key=st.secrets["openai"]["api_key"],
        model="gpt-4",
        temperature=1.0
    )

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # God
    god_system_message = f"""
You are GOD.
Output exactly one short line, then remain silent:
"My children, let {person1} and {person2} converse about '{topic}' in {style} style.
Decorator, do your job: pick a theme, choose an icon, pass it to the Host. Thank you."
Then remain absolutely silent afterward.
"""
    god_agent = AssistantAgent(
        name="God",
        description="A deity that calls on Decorator, then is silent.",
        system_message=god_system_message,
        model_client=model_client,
        tools=[]
    )
    god_agent.display_name = "God"

    # Decorator, Host, Arguer1, Arguer2, Judge, etc. same as before
    # ...
    # (just as in your code, referencing model_client, building them all)

    # Example end:
    termination_condition = TextMentionTermination("THE_END")
    participants = [god_agent, Decorator, Host, Arguer1, Arguer2, Judge]

    chat = SelectorGroupChat(
        participants=participants,
        model_client=model_client,
        allow_repeated_speaker=True,
        termination_condition=termination_condition
    )

    print("\n========== Starting the Chat ==========\n")
    async for msg in chat.run_stream(task="Dear GOD, please speak."):
        if msg.source == "user":
            continue
        yield msg
    print("\n========== End of Chat ==========\n")

###############################################################################
# STREAMLIT
###############################################################################
import asyncio

def display_message(speaker_name: str, content: str, theme: str, icon: str):
    if theme == "dark theme":
        box_style = ("background-color: #333; color: #fff; padding:10px;"
                     "border-radius:5px; margin-bottom:10px;")
    else:
        box_style = ("background-color: #f9f9f9; color: #000; padding:10px;"
                     "border-radius:5px; margin-bottom:10px;")

    display_name = speaker_name
    if speaker_name == "Decorator":
        display_name += f" {icon}"

    st.markdown(f"""
    <div style="{box_style}">
        <strong>{display_name}:</strong> {content}
    </div>
    """, unsafe_allow_html=True)

async def get_contest_messages():
    msgs = []
    async for m in run_famous_people_contest():
        msgs.append(m)
    return msgs

def main():
    st.set_page_config(page_title="Famous People Contest", layout="centered")

    if "theme" not in st.session_state:
        st.session_state.theme = "light theme"
    if "icon" not in st.session_state:
        st.session_state.icon = "☀️"

    st.title("Famous People Contest")
    st.write("Press the button below to begin.")

    if st.button("Start the Contest"):
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(get_contest_messages())
        loop.close()

        for msg in messages:
            if msg.source == "Decorator":
                if "dark theme" in msg.content.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in msg.content.lower():
                    st.session_state.theme = "light theme"

                icon_match = re.search(r"icon\s*'([^']+)'", msg.content)
                if icon_match:
                    st.session_state.icon = icon_match.group(1)

        for msg in messages:
            display_message(
                speaker_name=msg.source,
                content=msg.content,
                theme=st.session_state.theme,
                icon=st.session_state.icon
            )

    st.write("---")
    st.write("End of Streamlit demo.")

if __name__ == "__main__":
    main()
