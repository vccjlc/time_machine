##########################################################
# time_machine.py
##########################################################
import os
import random
import asyncio
import re

import streamlit as st

# This is the official client from autogen_ext, which references azure.*
# so we need azure-core installed to avoid "No module named 'azure'"
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_agentchat.messages import (
    # If these aren’t actually present in your version, remove or adapt:
    SystemMessage,
    UserMessage,
    AssistantMessage
)
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination

##############################################################################
# Convert autogen_agentchat messages to valid OpenAI roles
##############################################################################
def transform_autogen_messages(autogen_messages):
    """
    Convert autogen_agentchat's message objects (SystemMessage, UserMessage, etc.)
    into valid OpenAI chat messages:  [{role: ..., content: ...}, ...].
    """
    openai_messages = []
    for m in autogen_messages:
        # Just in case your version doesn't have these classes, remove or tweak:
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
            # Default to assistant if it's some other custom class
            role = "assistant"
            content = getattr(m, "content", "")
        openai_messages.append({"role": role, "content": content})
    return openai_messages

##############################################################################
# Patching the `create` method to do the transformation automatically
##############################################################################
async def patched_create(self, messages=None, model=None, temperature=None, **kwargs):
    """
    We monkey-patch `OpenAIChatCompletionClient.create` so that any incoming
    autogen_agentchat messages are first converted to valid OpenAI messages.
    """
    used_model = model or self.model
    used_temp = temperature if (temperature is not None) else self.temperature
    openai_messages = transform_autogen_messages(messages or [])
    response = await self._original_create(
        messages=openai_messages,
        model=used_model,
        temperature=used_temp,
        **kwargs
    )
    return response

##############################################################################
# The main run_famous_people_contest function
##############################################################################
async def run_famous_people_contest():
    # 1) Create the official model client
    model_client = OpenAIChatCompletionClient(
        openai_api_key=st.secrets["openai"]["api_key"],
        model="gpt-4",   # or your chosen model
        temperature=1.0
    )

    # 2) Monkey-patch its create method to inject the transformation
    #    We'll store the original method, then override it
    model_client._original_create = model_client.create
    model_client.create = lambda **kwargs: patched_create(model_client, **kwargs)

    # 3) Random picks
    def pick_two_people():
        all_famous = [["Albert Einstein", "Richard Feynman"]]
        random.shuffle(all_famous)
        return all_famous[0][0], all_famous[0][1]

    def pick_random_topic():
        topics = ["conspiracy theories", "Jeopardy-like trivia game"]
        return random.choice(topics)

    def decide_style():
        val = random.random()
        if val < 0.5:
            return "witty"
        elif val < 0.75:
            return "serious"
        else:
            return "moderate"

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # 4) God agent
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

    # 5) Decorator agent
    decorator_system_message = """
You are the Decorator.
Pick 'light theme' or 'dark theme' plus an icon. Then say: "Host, here is the theme and icon. Thank you."
Afterwards, remain silent.
"""
    decorator_agent = AssistantAgent(
        name="Decorator",
        description="Chooses environment theme and icon.",
        system_message=decorator_system_message,
        model_client=model_client,
        tools=[]
    )
    decorator_agent.display_name = "Decorator"

    # 6) Host, Arguer1, Arguer2, Judge (for brevity, we’ll just do the Host)
    host_system_message = f"""
You are the Host.
Acknowledge Decorator, introduce {person1} and {person2}, mention {topic}.
Prompt them for 3 lines each. Then call the Judge. Then end with THE_END after verdict.
"""
    host_agent = AssistantAgent(
        name="Host",
        description="Introduces the conversation, calls the Judge, ends the show.",
        system_message=host_system_message,
        model_client=model_client,
        tools=[]
    )
    host_agent.display_name = "Host"

    # 7) Arguer1 & Arguer2
    arguer1_system_message = f"You are {person1}. Keep lines short. Remain witty."
    arguer1_agent = AssistantAgent(
        name="Arguer1",
        description=f"Represents {person1}.",
        system_message=arguer1_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer1_agent.display_name = person1

    arguer2_system_message = f"You are {person2}. Keep lines short. Try to outshine {person1}."
    arguer2_agent = AssistantAgent(
        name="Arguer2",
        description=f"Represents {person2}.",
        system_message=arguer2_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer2_agent.display_name = person2

    # 8) Judge
    judge_system_message = """
You are the Judge.
Summarize in one short line and declare a winner or draw in one sentence.
Then remain silent.
"""
    judge_agent = AssistantAgent(
        name="Judge",
        description="Gives short verdict, picks winner or draw, then silent.",
        system_message=judge_system_message,
        model_client=model_client,
        tools=[]
    )
    judge_agent.display_name = "Judge"

    # 9) Termination
    termination_condition = TextMentionTermination("THE_END")
    participants = [
        god_agent,
        decorator_agent,
        host_agent,
        arguer1_agent,
        arguer2_agent,
        judge_agent
    ]

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

##############################################################################
# STREAMLIT UI
##############################################################################
def display_message(speaker_name: str, content: str, theme: str, icon: str):
    if theme == "dark theme":
        box_style = "background-color: #333; color: #fff; padding:10px; border-radius:5px; margin-bottom:10px;"
    else:
        box_style = "background-color: #f9f9f9; color: #000; padding:10px; border-radius:5px; margin-bottom:10px;"

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
    st.write("Press the button below to see a short comedic or dramatic interplay among God, a Decorator, two historical figures, a Host, and a Judge!")

    if st.button("Start the Contest"):
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(get_contest_messages())
        loop.close()

        # Check for Decorator's theme & icon
        for msg in messages:
            if msg.source == "Decorator":
                if "dark theme" in msg.content.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in msg.content.lower():
                    st.session_state.theme = "light theme"

                icon_match = re.search(r"icon\s*'([^']+)'", msg.content)
                if icon_match:
                    st.session_state.icon = icon_match.group(1)

        # Display messages
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
