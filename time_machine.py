##########################################################
# time_machine.py
##########################################################
import os
import random
import asyncio
import re

import streamlit as st

# 1) We import the official model client from autogen_ext (no custom wrapper)
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 2) We import message types from autogen_agentchat
#    (If they're not actually present, skip them or see below)
from autogen_agentchat.messages import (
    SystemMessage,
    UserMessage,
    AssistantMessage
)

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

    Why needed? Because the ChatCompletion API requires "role" in {"system","user","assistant"},
    but autogen_agentchat might produce SystemMessage, UserMessage, etc.
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
            # If there's a custom message type (like tool messages),
            # default to assistant or handle differently
            role = "assistant"
            content = getattr(m, "content", "")

        openai_messages.append({"role": role, "content": content})
    return openai_messages

##############################################################################
# 1) Helper function: "model_client_create" that calls OpenAIChatCompletionClient
##############################################################################
async def model_client_create(
    model_client,
    messages=None,
    model=None,
    temperature=None,
    **kwargs
):
    """
    We do the transformation (SystemMessage->role=system, etc.)
    then call model_client.create(...) with the final dict format.

    This is effectively an inline approach—no separate "wrapper" class needed.
    """
    used_model = model or model_client.model
    used_temp = temperature if (temperature is not None) else model_client.temperature

    # Convert autogen_agentchat messages to OpenAI chat format
    openai_messages = transform_autogen_messages(messages or [])

    # Now we call the official `model_client.create(...)` method
    # which expects messages in the correct OpenAI format
    response = await model_client.create(
        messages=openai_messages,
        model=used_model,
        temperature=used_temp,
        **kwargs
    )
    return response

##############################################################################
# 2) Lists of famous individuals by category
##############################################################################
FAMOUS_PHYSICISTS = [
    "Albert Einstein",
    "Richard Feynman",
    "Marie Curie",
    "Stephen Hawking",
    "Isaac Newton",
    "Niels Bohr",
    "Erwin Schrödinger",
    "Oppenheimer",
]
# (Rest of your lists) ...
ALL_CATEGORIES = [ FAMOUS_PHYSICISTS, ]  # plus the others

##############################################################################
# 3) Topics
##############################################################################
UNEXPECTED_TOPICS = [
    "conspiracy theories",
    # ...
]
FAMOUS_CONTESTS = [
    "Jeopardy-like trivia game",
    # ...
]
UNEXPECTED_TOPICS.extend(FAMOUS_CONTESTS)

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

##############################################################################
# 4) The main function
##############################################################################
async def run_famous_people_contest():
    # 1) Create the official model client (no custom wrapper),
    #    from autogen_ext.models.openai
    model_client = OpenAIChatCompletionClient(
        openai_api_key=st.secrets["openai"]["api_key"],  # or your env var
        model="gpt-4",
        temperature=1.0
    )

    # 2) We'll build the conversation participants
    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # 3) God
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
        # We'll override how "create" is called by hooking into the partial
        # or by hooking into `on_message_impl`. Another approach is to monkey-patch.
        tools=[]
    )
    god_agent.display_name = "God"

    # 4) Decorator, Host, Arguer1, Arguer2, Judge
    #    (Same as your code—just ensure they have system messages, model_client, etc.)
    # Example for Decorator:
    decorator_system_message = """
You are the Decorator.
Pick light or dark theme plus an icon.
Then pass to the Host.
"""
    decorator_agent = AssistantAgent(
        name="Decorator",
        description="Chooses environment theme (light/dark) and icon.",
        system_message=decorator_system_message,
        model_client=model_client,
        tools=[]
    )
    decorator_agent.display_name = "Decorator"

    # ... same for Host, Arguer1, Arguer2, Judge ...
    # (omitted for brevity)

    # 5) Termination and participants
    termination_condition = TextMentionTermination("THE_END")
    participants = [
        god_agent,
        decorator_agent,
        # host_agent,
        # arguer1_agent,
        # arguer2_agent,
        # judge_agent
    ]

    # 6) The group chat
    chat = SelectorGroupChat(
        participants=participants,
        model_client=model_client,
        allow_repeated_speaker=True,
        termination_condition=termination_condition
    )

    print("\n========== Starting the Chat ==========\n")

    # 7) The main loop
    async for msg in chat.run_stream(task="Dear GOD, please speak."):
        # If the "speaker" is user, skip
        if msg.source == "user":
            continue
        yield msg

    print("\n========== End of Chat ==========\n")

##############################################################################
# STREAMLIT
##############################################################################
import asyncio

def display_message(speaker_name: str, content: str, theme: str, icon: str):
    if theme == "dark theme":
        box_style = (
            "background-color: #333; color: #fff; padding:10px;"
            "border-radius:5px; margin-bottom:10px;"
        )
    else:
        box_style = (
            "background-color: #f9f9f9; color: #000; padding:10px;"
            "border-radius:5px; margin-bottom:10px;"
        )

    display_name = speaker_name
    if speaker_name == "Decorator":
        display_name += f" {icon}"

    st.markdown(
        f"""
        <div style="{box_style}">
            <strong>{display_name}:</strong> {content}
        </div>
        """,
        unsafe_allow_html=True
    )

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
    st.write("Press the button below to begin the short multi-agent conversation.")

    if st.button("Start the Contest"):
        # Reset theme/icon
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(get_contest_messages())
        loop.close()

        # Check if Decorator changes theme
        for msg in messages:
            if msg.source == "Decorator":
                if "dark theme" in msg.content.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in msg.content.lower():
                    st.session_state.theme = "light theme"

                icon_match = re.search(r"icon\s*'([^']+)'", msg.content)
                if icon_match:
                    st.session_state.icon = icon_match.group(1)

        # Display all messages
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
