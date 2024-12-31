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
# 4) The main multi-agent function (NO DECORATOR, NO THEME)
###############################################################################
async def run_famous_people_contest():
    """
    We do a short conversation among:
      - God (one-line)
      - Host (introduces two famous people & calls Judge)
      - Two arguers
      - A Judge (one-line verdict)

    The 'Decorator' is removed, so no theme picking.
    """
    model_client = OpenAIChatCompletionClient(
        api_key=st.secrets["openai"]["OPENAI_API_KEY"],
        model="gpt-4o-mini",  # You said this model is valid in your environment
        temperature=1.0
    )

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # 1) God
    god_system_message = f"""
You are GOD.
Output exactly one short line, then remain silent:
"My children, let {person1} and {person2} speak about '{topic}' in a {style} manner.
Host, please guide them. Thank you."
Then remain silent afterward.
"""
    god_agent = AssistantAgent(
        name="God",
        description="A deity that briefly introduces the conversation, then is silent.",
        system_message=god_system_message,
        model_client=model_client,
        tools=[]
    )

    # 2) Host
    host_system_message = f"""
You are the Host.
1) Introduce {person1} and {person2} (who they were, briefly).
2) Mention the subtopic of {topic}.
3) Prompt them to speak ~3 lines each.
4) Then call the Judge: "Judge, your verdict please."
5) After the Judge, say: "THE_END."
Stop only after THE_END.
"""
    host_agent = AssistantAgent(
        name="Host",
        description="Introduces conversation, calls Judge, ends show with THE_END.",
        system_message=host_system_message,
        model_client=model_client,
        tools=[]
    )

    # 3) Arguer1
    arguer1_system_message = f"""
You are {person1}.
Engage with {person2} about '{topic}' using a {style} style.
Keep lines short. Remain in character.
"""
    arguer1_agent = AssistantAgent(
        name="Arguer1",
        description=f"Represents {person1}",
        system_message=arguer1_system_message,
        model_client=model_client,
        tools=[]
    )

    # 4) Arguer2
    arguer2_system_message = f"""
You are {person2}.
Engage with {person1} about '{topic}' using a {style} style.
Try to impress or outshine them. Short lines.
"""
    arguer2_agent = AssistantAgent(
        name="Arguer2",
        description=f"Represents {person2}",
        system_message=arguer2_system_message,
        model_client=model_client,
        tools=[]
    )

    # 5) Judge
    judge_system_message = """
You are the Judge.
Summarize in one short line, then declare a winner or a draw in one sentence.
Then remain absolutely silent.
"""
    judge_agent = AssistantAgent(
        name="Judge",
        description="Gives a short verdict, then silent.",
        system_message=judge_system_message,
        model_client=model_client,
        tools=[]
    )

    # 6) Termination after "THE_END"
    termination_condition = TextMentionTermination("THE_END")
    participants = [god_agent, host_agent, arguer1_agent, arguer2_agent, judge_agent]

    chat = SelectorGroupChat(
        participants=participants,
        model_client=model_client,
        allow_repeated_speaker=True,
        termination_condition=termination_condition
    )

    async for msg in chat.run_stream(task="Dear GOD, please speak."):
        yield msg  # yield each conversation step

###############################################################################
# 5) AVATARS (No names displayed, only pictures)
###############################################################################
# Replace these with your own URLs. If participant not found, fallback used.
AVATAR_URLS = {
    "God": "data:image/jpeg;base64,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",
    "Host": "https://example.com/host.png",
    "Arguer1": "https://example.com/arg1.png",
    "Arguer2": "https://example.com/arg2.png",
    "Judge": "https://example.com/judge.png",
    "fallback": "https://example.com/fallback.png",
}

###############################################################################
# 6) The Streamlit UI
###############################################################################
def display_avatar_and_text(avatar_url: str, content: str):
    """Render a message with avatar, no name displayed."""
    st.markdown(
        f"""
        <div style="background-color:#f9f9f9; color:#000; padding:10px; 
                    border-radius:5px; margin-bottom:10px; display:flex;">
            <img src="{avatar_url}" style="width:40px; height:40px; 
                     border-radius:20px; margin-right:10px;" />
            <div>{content}</div>
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

    st.title("Time Machine — Simplified")
    st.write("A short conversation between God, a Host, two arguers, and a Judge. Decorator is removed.")

    if st.button("Run the Contest"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conversation_steps = loop.run_until_complete(get_contest_messages())
        loop.close()

        # conversation_steps = [TaskResult(...), TaskResult(...), ...]
        for step in conversation_steps:
            agent_name = getattr(step, "agent_name", "")
            content = getattr(step, "content", "")
            if not agent_name:
                agent_name = "fallback"

            # Find matching avatar
            avatar_url = AVATAR_URLS.get(agent_name, AVATAR_URLS["fallback"])

            # Display with no speaker name, only avatar + content
            display_avatar_and_text(avatar_url, content)

    st.write("---")
    st.write("End of the demo.")

if __name__ == "__main__":
    main()
