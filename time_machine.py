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
# 2) Topics
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
    # 1) Create the official model client
    model_client = OpenAIChatCompletionClient(
        api_key=st.secrets["openai"]["OPENAI_API_KEY"],
        model="gpt-4",  # or "gpt-3.5-turbo", etc.
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
    decorator_system_message = """
You are the Decorator.
1) Greet God briefly, confirm you will use '{chosen_theme}' and icon '{chosen_icon}'.
2) Then say: "Host, here is the theme and icon. Thank you."
After that, remain silent.
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
Your tasks:
1) Acknowledge the Decorator's theme and icon. Then quickly introduce {person1} and {person2} and mention the subtopic of {topic}.
2) Prompt them to speak about 3 short lines each. Start with "{person1}, your turn."
3) After they finish, invite the Judge with: "Judge, your verdict please."
4) After the Judge speaks, say: "Thank you everyone! THE_END."
Do not produce "THE_END" until after the Judge's verdict.
Stay succinct.
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
You are conversing with {person2} about '{topic}' in a {style} style.
Keep lines short (1-2 sentences).
Try to outshine {person2} if it seems competitive.
Stay in character, referencing your historical context.
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
You are conversing with {person1} about '{topic}' in a {style} style.
Keep lines short (1-2 sentences).
Try to win or impress the audience.
Stay in character, referencing your historical context.
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
    judge_system_message = """
You are the Judge.
Summarize in one short line, then declare a winner or a draw in exactly one sentence.
Then remain silent.
"""
    judge_agent = AssistantAgent(
        name="Judge",
        description="Short verdict, picks a winner or draw, then silent.",
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

    chat = SelectorGroupChat(
        participants=participants,
        model_client=model_client,
        allow_repeated_speaker=True,
        termination_condition=termination_condition
    )

    print("\n========== Starting the Chat ==========\n")

    # 2) We'll remove the "if msg.source == 'user': continue" line,
    #    because the returned object is now "TaskResult" (no 'source' attribute).
    async for msg in chat.run_stream(task="Dear GOD, please speak."):
        yield msg  # yield the entire TaskResult

    print("\n========== End of Chat ==========\n")

###############################################################################
# STREAMLIT UI
###############################################################################
def display_message(speaker_name: str, content: str, theme: str, icon: str):
    """Display each message with minimal styling."""
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

    st.title("Time Machine")
    st.write("Click below to see a short multi-agent interplay.")

    if st.button("Start the Contest"):
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = loop.run_until_complete(get_contest_messages())
        loop.close()

        # Each returned item is likely a TaskResult. Let's see what's inside:
        # We can check, for example, .agent_name, .content, etc.
        # We'll do something like:
        for task_result in tasks:
            # Try to figure out agent name & text from the TaskResult
            agent_name = getattr(task_result, "agent_name", "UnknownAgent")
            text_output = getattr(task_result, "content", "")
            # Or if there's .message or something else:
            # text_output = getattr(task_result, "message", "")

            # If the Decorator changed theme/icon:
            if agent_name == "Decorator":
                # Check if they said "dark theme" or "light theme"
                if "dark theme" in text_output.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in text_output.lower():
                    st.session_state.theme = "light theme"

                match = re.search(r"icon\s*'([^']+)'", text_output)
                if match:
                    st.session_state.icon = match.group(1)

            # Now show it
            display_message(
                speaker_name=agent_name,
                content=text_output,
                theme=st.session_state.theme,
                icon=st.session_state.icon
            )

    st.write("---")
    st.write("End of the Streamlit demo.")


if __name__ == "__main__":
    main()
