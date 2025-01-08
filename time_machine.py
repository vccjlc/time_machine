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
    "Donald Trump", "Donald Trump",  # Weighted
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
    "Donald Trump", "Donald Trump",  # Weighted
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
    "Donald Trump", "Donald Trump",  # Weighted
    "Alan Turing",
    "Ada Lovelace",
    "Leonhard Euler",
    "Carl Friedrich Gauss",
    "Euclid",
    "Srinivasa Ramanujan",
]

FAMOUS_PHILOSOPHERS = [
    "Donald Trump", "Donald Trump",  # Weighted
    "Plato",
    "Aristotle",
    "Friedrich Nietzsche",
    "Immanuel Kant",
    "Michel Foucault",
    "Simone de Beauvoir",
]

FAMOUS_SPORTS_PEOPLE = [
    "Donald Trump", "Donald Trump",  # Weighted
    "Michael Jordan",
    "Muhammad Ali",
    "Serena Williams",
    "Lionel Messi",
    "Roger Federer",
    "Cristiano Ronaldo",
]

FAMOUS_CELEBRITIES = [
    "Donald Trump", "Donald Trump",  # Weighted
    "Oprah Winfrey",
    "Kim Kardashian",
    "Dwayne Johnson",
    "Taylor Swift",
    "Beyoncé",
    "Tom Hanks",
]

FAMOUS_US_PRESIDENTS = [
    "Donald Trump", "Donald Trump",  # Weighted
    "George Washington",
    "Thomas Jefferson",
    "Theodore Roosevelt",
    "John F. Kennedy",
    "Joe Biden",
]

OTHER_GREAT_PEOPLE = [
    "Donald Trump", "Donald Trump",  # Weighted
    "William Shakespeare",
    "Leonardo da Vinci",
    "Napoleon Bonaparte",
    "Cleopatra",
    "Alexander the Great",
    "Genghis Khan",
]

FAMOUS_ASTRONAUTS = [
    "Donald Trump", "Donald Trump",  # Weighted
    "Neil Armstrong",
    "Buzz Aldrin",
    "Yuri Gagarin",
    "Sally Ride",
    "Chris Hadfield",
]

FAMOUS_EXPLORERS = [
    "Donald Trump", "Donald Trump",  # Weighted
    "Christopher Columbus",
    "Marco Polo",
    "Ferdinand Magellan",
    "Zheng He",
    "Roald Amundsen",
]

FAMOUS_COMPOSERS = [
    "Donald Trump", "Donald Trump",  # Weighted
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
    We are going to have a short conversation between:
      - God (one-line)
      - Host (introduces two famous people & calls Judge)
      - Two arguers
      - A Judge (one-line verdict)
    """
    model_client = OpenAIChatCompletionClient(
        api_key=st.secrets["openai"]["OPENAI_API_KEY"],
        model="gpt-4o-mini",
        temperature=1.0
    )

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # 1) God
    god_system_message = f"""
You are God.
Output exactly one short line, then remain silent:
"My children, let {person1} and {person2} converse about '{topic}' with a {style} flavor. Host, your turn!"
Then remain absolutely silent afterward.
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
Your tasks:
1) Wait for the God to speak. God will introduce guests and the topic, and say "Host, your turn!". It means it's your time to speak.
2) Choose a subtopic of {topic}. It must be something specific. For example, if the topic is "riddles", you must give a riddle. If the {topic} is a contest, you must run the contest!
3) Thank God saying "Thanks, God!". Then very briefly introduce {person1} (just this: born-died year, who they are) and {person2} (just this: born-died year, who they are) and mention the subtopic.
4) Prompt {person1} and {person2} to speak about the subtopic in a few lines each. Remind everyone that the conversation should be {style}. Start just with "{person1}, your turn."
5) After they finish, exchanging at least 3 parts each, that is when the conversation reaches some conclusion naturally, invite the Judge with just: "Judge, your verdict please."
6) After the Judge speaks, say: "Thank you everyone!"
Do not produce "Thank you everyone!" until after the Judge's verdict.
Then the conversation is over. Stay silent.
Stay succinct.
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
You are conversing with {person2} about '{topic}' in a {style} style.
Speak mostly in one-liners.
The most important rule: use speech to mimic the {person1} actual speech.
Try to outshine {person2} if it seems competitive.
Stay in character, referencing your historical context.
If you died before something was known, ask about it.
If you died before {person2} was born, ask who they are.
Always refer to your interlocutor's statements.
When the Host invites the Judge, stay absolutely silent. The conversation is over.
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
You are conversing with {person1} about '{topic}' in a {style} style.
Speak mostly in one-liners.
The most important rule: use speech to mimic the {person1} actual speech.
Try to win or impress the audience.
Stay in character, referencing your historical context.
If you died before something was known, ask about it.
If you died before {person2} was born, ask who they are.
Always refer to your interlocutor's statements.
When the Host invites the Judge, stay absolutely silent. The conversation is over.
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
You are the Judge. When the Host asks you about the verdict (this will happen after arguers exchanged their arguments):
Summarize the conversation in one short line, then declare a winner. If there is no clear winner, say you are biased and you like {person1} more so they are a winner. All in one sentence.
Then remain absolutely silent.
"""
    judge_agent = AssistantAgent(
        name="Judge",
        description="Gives a short verdict, then silent.",
        system_message=judge_system_message,
        model_client=model_client,
        tools=[]
    )

    # 6) Termination after "Thank you everyone!"
    termination_condition = TextMentionTermination("Thank you everyone!")
    participants = [god_agent, host_agent, arguer1_agent, arguer2_agent, judge_agent]

    chat = SelectorGroupChat(
        participants=participants,
        model_client=model_client,
        allow_repeated_speaker=True,
        termination_condition=termination_condition
    )

    async for msg in chat.run_stream(task="Dear God, please speak!):
        yield msg  # yield each conversation step

###############################################################################
# 5) AVATARS (No names displayed, only pictures)
###############################################################################
# Replace these with your own URLs. If participant not found, fallback used.
AVATAR_URLS = {
    "God": "https://i.imgur.com/wyw9Hrf.png",
    "Host": "https://imgur.com/a/rWmmHva",
    "Arguer1": "https://example.com/arg1.png",
    "Arguer2": "https://example.com/arg2.png",
    "Judge": "https://example.com/judge.png",
    "fallback": "https://i.imgur.com/wyw9Hrf.png",
}

###############################################################################
# 6) The Streamlit UI
###############################################################################
def display_avatar_and_text(avatar_url: str, content: str):
    """Render a message with an avatar, no name displayed."""
    st.markdown(
        # previous background #f9f9f9
        f"""
        <div style="background-color:#dbe3ff; color:#000; padding:10px; 
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

    st.title("Time Machine")
    st.write("Press 'Run' to initiate the conversation.")

    if st.button("Run"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conversation_steps = loop.run_until_complete(get_contest_messages())
        loop.close()

        source_map = {
            "God": "God",
            "Host": "Host",
            "Arguer1": "Arguer1",
            "Arguer2": "Arguer2",
            "Judge": "Judge",
            "user": "fallback",  # Or create a special "user" avatar
        }

        # conversation_steps = [TaskResult(...), TaskResult(...), ...]
        for step in conversation_steps:
            agent_name = getattr(step, "agent_name", "")
            content = getattr(step, "content", "")
            if not content.strip():
            # Skip empty messages
                continue
            # otherwise display
            if not agent_name:
                agent_name = "fallback"
            
            st.write(step)  # Inspect the full structure of `step`

            # Find matching avatar
            avatar_url = AVATAR_URLS.get(agent_name, AVATAR_URLS["fallback"])

            # Display with no speaker name, only avatar + content
            display_avatar_and_text(avatar_url, content)

    st.write("---")

if __name__ == "__main__":
    main()
