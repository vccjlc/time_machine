##########################################################
# time_machine.py
##########################################################
import os
import random
import asyncio
import re
import streamlit as st

# If your code complains about missing azure, add azure-core + azure-identity to requirements
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination

###############################################################################
# 1) Lists of famous individuals by category
###############################################################################
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
FAMOUS_POLITICIANS = [
    "Donald Trump", "Donald Trump",  # Weighted for comedic effect
    "Barack Obama",
    "Winston Churchill",
    "Abraham Lincoln",
    "Margaret Thatcher",
    "Angela Merkel",
    "Mahatma Gandhi",
    "Franklin D. Roosevelt",
    "Julius Caesar",
]
ALL_CATEGORIES = [
    FAMOUS_PHYSICISTS,
    FAMOUS_POLITICIANS,
    # Add the rest if you’d like
]

###############################################################################
# 2) Topics
###############################################################################
UNEXPECTED_TOPICS = [
    "conspiracy theories",
    "riddles",
    "Jeopardy-like trivia game",
    "Rap battle",
]

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
    val = random.random()
    if val < 0.5:
        return "witty"
    elif val < 0.75:
        return "serious"
    else:
        return "moderate"

###############################################################################
# 4) The main multi-agent function
###############################################################################
async def run_famous_people_contest():
    """
    Runs a short conversation among:
      - God (one-line)
      - Decorator (sets theme/icon)
      - Host (introduces two famous people & calls Judge)
      - Two arguers
      - A Judge (one-line verdict)
    """
    # Create the official model client
    model_client = OpenAIChatCompletionClient(
        openai_api_key=st.secrets['openai']["OPENAI_API_KEY"],
        model="gpt-4o-mini",
        temperature=1.0
    )

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # A) God
    god_system_message = f"""
You are GOD.
Output exactly one short line, then remain silent:
"My children, let {person1} and {person2} converse about '{topic}' with a {style} flavor. 
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

    # B) Decorator
    decorator_system_message = f"""
You are the Decorator.
Pick 'light theme' or 'dark theme' plus a cool icon.
Then say: "Host, here is the theme and icon. Thank you."
Remain silent afterward.
"""
    decorator_agent = AssistantAgent(
        name="Decorator",
        description="Chooses environment theme/icon, then silent.",
        system_message=decorator_system_message,
        model_client=model_client,
        tools=[]
    )
    decorator_agent.display_name = "Decorator"

    # C) Host
    host_system_message = f"""
You are the Host.
1) Acknowledge the Decorator's theme/icon.
2) Introduce {person1} and {person2}, mention the subtopic of {topic}.
3) Prompt them to each speak ~3 short lines.
4) Then invite the Judge: "Judge, your verdict please."
5) After the Judge speaks, say: "Thank you everyone! THE_END."
Don't produce THE_END until after the Judge's verdict.
"""
    host_agent = AssistantAgent(
        name="Host",
        description="Introduces conversation, calls Judge, ends show.",
        system_message=host_system_message,
        model_client=model_client,
        tools=[]
    )
    host_agent.display_name = "Host"

    # D) Arguer1
    arguer1_system_message = f"""
You are {person1}.
Converse with {person2} about '{topic}' in {style} style.
Try to outshine them. 1-2 sentence lines. Stay in character.
"""
    arguer1_agent = AssistantAgent(
        name="Arguer1",
        description=f"Represents {person1}.",
        system_message=arguer1_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer1_agent.display_name = person1

    # E) Arguer2
    arguer2_system_message = f"""
You are {person2}.
Converse with {person1} about '{topic}' in {style} style.
Try to win or impress. 1-2 sentence lines.
Stay in character.
"""
    arguer2_agent = AssistantAgent(
        name="Arguer2",
        description=f"Represents {person2}.",
        system_message=arguer2_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer2_agent.display_name = person2

    # F) Judge
    judge_system_message = f"""
You are the Judge.
Summarize the conversation in one short line,
then declare a winner or draw in one sentence.
Remain silent afterward.
"""
    judge_agent = AssistantAgent(
        name="Judge",
        description="Issues a short verdict, picks a winner or draws, then silent.",
        system_message=judge_system_message,
        model_client=model_client,
        tools=[]
    )
    judge_agent.display_name = "Judge"

    # G) Termination condition
    termination_condition = TextMentionTermination("THE_END")
    participants = [
        god_agent,
        decorator_agent,
        host_agent,
        arguer1_agent,
        arguer2_agent,
        judge_agent
    ]

    # Build the group chat
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
# STREAMLIT UI
###############################################################################
def display_message(speaker_name: str, content: str, theme: str, icon: str):
    """
    Display each message with a minimal box style.
    If speaker is Decorator, append the icon.
    """
    if theme == "dark theme":
        box_style = (
            "background-color: #333; color: #fff; "
            "padding: 10px; border-radius: 5px; margin-bottom: 10px;"
        )
    else:
        box_style = (
            "background-color: #f9f9f9; color: #000; "
            "padding: 10px; border-radius: 5px; margin-bottom: 10px;"
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

    st.title("Famous People Contest — Streamlit")
    st.write(
        "Press the button below to see a short comedic or dramatic interplay "
        "among God, a Decorator, two historical figures, a Host, and a Judge."
    )

    if st.button("Start the Contest"):
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(get_contest_messages())
        loop.close()

        # Look for Decorator's theme/icon references
        for msg in messages:
            if msg.source == "Decorator":
                if "dark theme" in msg.content.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in msg.content.lower():
                    st.session_state.theme = "light theme"

                match = re.search(r"icon\s*'([^']+)'", msg.content)
                if match:
                    st.session_state.icon = match.group(1)

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
