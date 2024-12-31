##########################################################
# time_machine.py
##########################################################
import os
import random
import asyncio
import re
import streamlit as st

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination

###############################################################################
# 1) Lists of famous individuals by category (UNCHANGED)
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

FAMOUS_MATHEMATICIANS = [
    "Alan Turing",
    "Ada Lovelace",
    "Leonhard Euler",
    "Carl Friedrich Gauss",
    "Euclid",
    "Srinivasa Ramanujan",
]

FAMOUS_PHILOSOPHERS = [
    "Plato",
    "Aristotle",
    "Friedrich Nietzsche",
    "Immanuel Kant",
    "Michel Foucault",
    "Simone de Beauvoir",
]

FAMOUS_SPORTS_PEOPLE = [
    "Michael Jordan",
    "Muhammad Ali",
    "Serena Williams",
    "Lionel Messi",
    "Roger Federer",
    "Cristiano Ronaldo",
]

FAMOUS_CELEBRITIES = [
    "Oprah Winfrey",
    "Kim Kardashian",
    "Dwayne Johnson",
    "Taylor Swift",
    "Beyoncé",
    "Tom Hanks",
]

FAMOUS_US_PRESIDENTS = [
    "George Washington",
    "Thomas Jefferson",
    "Theodore Roosevelt",
    "John F. Kennedy",
    "Joe Biden",
]

OTHER_GREAT_PEOPLE = [
    "William Shakespeare",
    "Leonardo da Vinci",
    "Napoleon Bonaparte",
    "Cleopatra",
    "Alexander the Great",
    "Genghis Khan",
]

FAMOUS_ASTRONAUTS = [
    "Neil Armstrong",
    "Buzz Aldrin",
    "Yuri Gagarin",
    "Sally Ride",
    "Chris Hadfield",
]

FAMOUS_EXPLORERS = [
    "Christopher Columbus",
    "Marco Polo",
    "Ferdinand Magellan",
    "Zheng He",
    "Roald Amundsen",
]

FAMOUS_COMPOSERS = [
    "Ludwig van Beethoven",
    "Wolfgang Amadeus Mozart",
    "Johann Sebastian Bach",
    "Frédéric Chopin",
    "Pyotr Tchaikovsky",
]

ALL_CATEGORIES = [
    FAMOUS_PHYSICISTS,
    FAMOUS_POLITICIANS,
    FAMOUS_MATHEMATICIANS,
    FAMOUS_PHILOSOPHERS,
    FAMOUS_SPORTS_PEOPLE,
    FAMOUS_CELEBRITIES,
    FAMOUS_US_PRESIDENTS,
    OTHER_GREAT_PEOPLE,
    FAMOUS_ASTRONAUTS,
    FAMOUS_EXPLORERS,
    FAMOUS_COMPOSERS,
]

###############################################################################
# 2) Topics (UNCHANGED)
###############################################################################
UNEXPECTED_TOPICS = [
    "conspiracy theories",
    "paradoxes",
    "riddles",
    "unbelievable facts",
    "challenges and experiments",
    "controversial topics",
    "how-to guides",
    "content creators",
    "social media platforms",
    "history with irony",
    "fun facts that sound unbelievable",
    "statistical facts",
    "polarizing topics",
    "escape room strategies",
    "war strategies",
    "the meaning or plot of a book",
    "escape prison scenarios",
    "hypothetical situations",
    "quirks in legal systems",
    "food and unusual dishes",
    "would you rather scenarios",
    "simple probability theory",
    "simple riddles",
    "math puzzles",
    "historical facts",
    "trivia questions",
    "corporate dynamics",
    "startup strategies",
    "negotiating a big contract",
    "diplomatic negotiations",
    "debating for a presidential seat",
    "religious doctrines",
    "family vacation plans",
    "doctor-patient disagreements",
    "sci-fi concepts",
    "the best movies or TV shows",
    "sports strategies",
    "video games",
    "art styles",
    "music genres",
    "technology trends",
    "famous quotes",
]

FAMOUS_CONTESTS = [
    "Jeopardy-like trivia game",
    "Duel of wits",
    "Rap battle",
    "Chess match",
    "Cooking showdown",
    "Rock-paper-scissors",
    "Talent show competition",
    "Arm-wrestling match",
    "Baking contest",
]

# Extend
UNEXPECTED_TOPICS.extend(FAMOUS_CONTESTS)

###############################################################################
# 3) Helper functions (UNCHANGED)
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
# 4) The main multi-agent function (UPDATED for new library)
###############################################################################
async def run_famous_people_contest():
    """
    Runs a short conversation among:
      - God (one-line)
      - Decorator (theme/icon)
      - Host (introduces two historical figures & calls Judge)
      - Two arguers
      - A Judge (one-line verdict)
    """
    # Create the model client
    model_client = OpenAIChatCompletionClient(
        api_key=st.secrets["openai"]["OPENAI_API_KEY"],
        model="gpt-4",   # or "gpt-3.5-turbo"
        temperature=1.0
    )

    # Pick random participants
    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # 1) God
    god_system_message = f"""
You are GOD.
Output exactly one short line, then remain silent:
"My children, let {person1} and {person2} converse about '{topic}' with a {style} flavor.
Decorator, do your job: pick a theme, choose an icon, pass it to the Host. Thank you."
Then remain silent afterward.
"""
    god_agent = AssistantAgent(
        name="God",
        description="A deity that calls on Decorator, then is silent.",
        system_message=god_system_message,
        model_client=model_client,
        tools=[]
    )
    god_agent.display_name = "God"

    # 2) Decorator
    decorator_system_message = """
You are the Decorator.
Pick either 'light theme' or 'dark theme' plus an icon.
Then say: "Host, here is the theme and icon. Thank you."
Then remain silent.
"""
    decorator_agent = AssistantAgent(
        name="Decorator",
        description="Chooses environment theme/icon, then silent.",
        system_message=decorator_system_message,
        model_client=model_client,
        tools=[]
    )
    decorator_agent.display_name = "Decorator"

    # 3) Host
    host_system_message = f"""
You are the Host.
1) Acknowledge Decorator's theme/icon.
2) Introduce {person1} and {person2} about {topic}.
3) Let them each speak ~3 short lines.
4) Then call the Judge: "Judge, your verdict please."
5) After the Judge, say: "Thank you everyone! THE_END."
Don't produce THE_END until after the Judge's verdict.
"""
    host_agent = AssistantAgent(
        name="Host",
        description="Introduces conversation, calls Judge, ends the show.",
        system_message=host_system_message,
        model_client=model_client,
        tools=[]
    )
    host_agent.display_name = "Host"

    # 4) Arguer1
    arguer1_system_message = f"""
You are {person1}.
Speak with {style} style.
Try to outshine {person2}. Keep lines short (1-2 sentences).
Stay in character.
"""
    arguer1_agent = AssistantAgent(
        name="Arguer1",
        description=f"Represents {person1}.",
        system_message=arguer1_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer1_agent.display_name = person1

    # 5) Arguer2
    arguer2_system_message = f"""
You are {person2}.
Speak with {style} style.
Try to win or impress {person1}. Keep lines short (1-2 sentences).
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

    # 6) Judge
    judge_system_message = """
You are the Judge.
Summarize the conversation in one short line,
then declare a winner or draw in exactly one sentence.
Remain silent afterward.
"""
    judge_agent = AssistantAgent(
        name="Judge",
        description="Issues a short verdict, picks a winner or draw, then silent.",
        system_message=judge_system_message,
        model_client=model_client,
        tools=[]
    )
    judge_agent.display_name = "Judge"

    # Termination
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

    async for msg in chat.run_stream(task="Dear GOD, please speak."):
        # Return each TaskResult as we get it
        yield msg

###############################################################################
# 5) AVATAR DICTIONARY (for icons/pictures)
###############################################################################
# You can replace these URLs with real images, or remove if you don't want avatars.
AVATAR_URLS = {
    "God": "https://raw.githubusercontent.com/misc-1/gpt-avatars/main/god.png",
    "Decorator": "https://raw.githubusercontent.com/misc-1/gpt-avatars/main/decorator.png",
    "Host": "https://raw.githubusercontent.com/misc-1/gpt-avatars/main/host.png",
    "Judge": "https://raw.githubusercontent.com/misc-1/gpt-avatars/main/judge.png",
    # If you want specific images for individuals:
    "Albert Einstein": "https://raw.githubusercontent.com/misc-1/gpt-avatars/main/einstein.png",
    # fallback for unknown
    "fallback": "https://raw.githubusercontent.com/misc-1/gpt-avatars/main/generic.png",
}

###############################################################################
# 6) The Streamlit UI
###############################################################################
def display_message(speaker_name: str, content: str, theme: str, icon: str):
    """Render each message with minimal styling + optional avatar image."""
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

    # Grab a matching avatar if we have it, else fallback
    avatar_url = AVATAR_URLS.get(speaker_name, AVATAR_URLS["fallback"])

    # We'll embed the avatar next to the text
    st.markdown(
        f"""
        <div style="{box_style} display:flex; align-items:flex-start;">
            <img src="{avatar_url}" style="width:40px; height:40px; border-radius:20px; margin-right:10px;" />
            <div>
                <strong>{speaker_name} {icon if speaker_name=='Decorator' else ''}:</strong>
                <p style="margin:0;">{content}</p>
            </div>
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
    st.set_page_config(page_title="Time Machine", layout="centered")

    # Initialize theme/icon if not set
    if "theme" not in st.session_state:
        st.session_state.theme = "light theme"
    if "icon" not in st.session_state:
        st.session_state.icon = "☀️"

    st.title("Time Machine — Multi-Agent Demo")
    st.write("Press the button below to see a short comedic or dramatic interplay among God, a Decorator, two famous figures, a Host, and a Judge.")

    if st.button("Start the Contest"):
        # Re-initialize theme/icon each run
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        # 1) Run the conversation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = loop.run_until_complete(get_contest_messages())
        loop.close()

        # 2) Each returned item is likely a TaskResult with e.g. .agent_name, .content
        #    We'll parse the agent name, text
        for task_result in tasks:
            agent_name = getattr(task_result, "agent_name", "") or getattr(task_result, "participant_name", "")
            if not agent_name:
                agent_name = "UnknownAgent"

            text_output = getattr(task_result, "content", "") or ""

            # If Decorator picks theme/icon
            if agent_name == "Decorator":
                # Check if they said "dark theme" or "light theme"
                if "dark theme" in text_output.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in text_output.lower():
                    st.session_state.theme = "light theme"

                # Check if an icon is specified
                match = re.search(r"icon\s*'([^']+)'", text_output)
                if match:
                    st.session_state.icon = match.group(1)

            # 3) Display
            display_message(
                speaker_name=agent_name,
                content=text_output,
                theme=st.session_state.theme,
                icon=st.session_state.icon
            )

    st.write("---")
    st.write("End of Streamlit demo.")


if __name__ == "__main__":
    main()
