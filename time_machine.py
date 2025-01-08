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
    "Donald Trump", "Donald Trump",  # Weighted
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

OTHER = [
    "Donald Trump", "Donald Trump",  # Weighted
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
    OTHER,
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
2) Choose a subtopic of {topic}. It must be something specific. For example, if the topic is "riddles", you must give a riddle. If the {topic} is a contest, you must run the contest! If the topic is "would you rather", you must pose a specific "would you rather" question. Etc.
3) Thank God saying "Thanks, God!". Then very briefly introduce {person1} (just this: born-died year, who they are) and {person2} (just this: born-died year, who they are) and mention the subtopic.
4) Prompt {person1} and {person2} to speak about the subtopic in a few lines each. Remind everyone that the conversation should be {style}. Start just with "{person1}, your turn."
5) After they finish, exchanging at least 3 parts each, that is when the conversation reaches some conclusion naturally, invite the Judge with just: "Judge, your verdict please."
6) After the Judge speaks, say: "Thank you everyone!"
If one {person1} or {person2} is Donald Trump, remember he is the current US president. If both are Donald Trump, make some funny remark that's it's not a bug but God's humor.
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
Speak totally like {person1} would speak.
Don't use too many exclamation marks.
Try to outshine {person2} if it seems competitive.
Stay in character, referencing your historical context.
If you died before something was known, ask about it.
If you died before {person2} was born, ask who they are.
Always refer to your interlocutor's statements.
Avoid "Ah" in your speech
If you are Donald Trump, make wild statements.
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
Speak totally like {person1} would speak.
Don't use too many exclamation marks.
You can be a bit crazy or make wild statements but still - stay in character, referencing your historical context.
If you died before something was known, ask about it.
If you died before {person2} was born, ask who they are.
Always refer to your interlocutor's statements.
Avoid "Ah" in your speech

If you are Donald Trump, make wild statements.
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

    async for msg in chat.run_stream(task="Dear God, please speak!"):
        yield msg  # yield each conversation step

###############################################################################
# 5) AVATARS (No names displayed, only pictures)
###############################################################################

# Hardcode a dictionary mapping each figure’s *exact name string*
# to their avatar URL.
PERSON_AVATARS = {
    # Example entries; add as many as you like:
    "Donald Trump": "https://i.imgur.com/XXXXXXXX.png",
    "Albert Einstein": "https://i.imgur.com/XXXXXXXX.png",
    "Marie Curie": "https://i.imgur.com/XXXXXXXX.png",
    "Stephen Hawking": "https://i.imgur.com/XXXXXXXX.png",
    "Isaac Newton": "https://i.imgur.com/XXXXXXXX.png",
    "Thomas Jefferson": "https://i.imgur.com/XXXXXXXX.png",
    # etc... fill in for each relevant historical figure
}

# For roles like God, Host, Judge, or fallback
AVATAR_URLS = {
    "God": "https://i.imgur.com/wyw9Hrf.png",      # example
    "Host": "https://i.imgur.com/Bgy4LxS.png",     # example
    "Judge": "https://i.imgur.com/LfPuI2Q.png",   # example
    "fallback": "https://i.imgur.com/wyw9Hrf.png", # example
}

def get_avatar_url_for_person(person_name: str) -> str:
    """
    Look up the person's avatar in PERSON_AVATARS; if not found,
    return the fallback.
    """
    return PERSON_AVATARS.get(person_name, AVATAR_URLS["fallback"])


def display_avatar_and_text(avatar_url: str, content: str, bg_color: str):
    """
    Render a message with an avatar, no name displayed,
    using bg_color for the background.
    """
    st.markdown(
        f"""<div style="background-color:{bg_color}; color:#000; 
                    padding:10px; border-radius:5px; margin-bottom:10px; 
                    display:flex; align-items:center;">
            <img src="{avatar_url}" style="width:40px; height:40px; 
                     border-radius:20px; margin-right:10px;" />
            <div>{content}</div>
        </div>""",
        unsafe_allow_html=True
    )


###############################################################################
# 6) The Streamlit UI
###############################################################################
async def get_contest_messages():
    """
    Runs the multi-agent conversation and returns all messages.
    We also capture person1 and person2 in st.session_state so we can 
    properly map Arguer1 / Arguer2 to the relevant avatar.
    """
    # We'll fetch the conversation in an async manner, with a spinner
    with st.spinner("Generating the conversation... Please wait a moment."):
        msgs = []
        # Actually run the conversation
        async for m in run_famous_people_contest():
            msgs.append(m)
        return msgs

def main():
    # A bit of custom CSS for an elegant look
    st.markdown(
        """
        <style>
        /* A subtle, classic style theme */
        body {
            background-color: #fafafa;
            color: #333;
            font-family: "Helvetica Neue", Arial, sans-serif;
        }
        .css-1oe6wy4.e1tzin5v2 {  /* center alignment fix in some Streamlit versions */
            justify-content: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.set_page_config(page_title="Time Machine", layout="centered")

    st.title("Time Machine")
    st.write("Press 'Run' to initiate the conversation.")
    st.write("_It may take a few seconds to generate the entire dialogue..._")

    if st.button("Run"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Actually gather the conversation steps
        conversation_steps = loop.run_until_complete(get_contest_messages())
        loop.close()

        #######################################################################
        # We read from the first message(s) in the conversation to see
        # who the system chose as Arguer1 (person1) and Arguer2 (person2).
        # The code in run_famous_people_contest() picks them, but we need
        # to store them ourselves if we want a dynamic approach.
        #
        # Note: If we want to store them in st.session_state *during*
        # run_famous_people_contest, you'd have to do that in the code
        # above. Another approach is to parse from the "God" or "Host"
        # output. For simplicity, let's do a quick parse from "God" step.
        #######################################################################
        # If you'd rather directly store in run_famous_people_contest, you can,
        # but here's a quick approach:
        person1 = "Unknown Arguer1"
        person2 = "Unknown Arguer2"

        for msg in conversation_steps:
            if msg.source == "God" and msg.content:
                # Example line: "My children, let X and Y converse about..."
                # We'll try to parse that
                import re
                match = re.search(r"let (.*?) and (.*?) converse about", msg.content)
                if match:
                    person1 = match.group(1).strip()
                    person2 = match.group(2).strip()
                break

        # Now store them so we can reference in the loop below
        st.session_state["person1"] = person1
        st.session_state["person2"] = person2

        # Distinguish Arguer1 from Arguer2 by these names
        # (in conversation, "Arguer1" means 'person1', etc.)

        # We'll choose two background colors, with the second more contrasting
        background_colors = ["#f0f5ff", "#ffecee"]  # light pastel blue, pinkish

        # Now display each message
        for i, step in enumerate(conversation_steps):
            # Only show if it's a text message with non-empty content
            if getattr(step, "type", "") != "TextMessage":
                continue
            content = getattr(step, "content", "")
            if not content.strip():
                continue

            # Determine whose avatar to show
            raw_source = getattr(step, "source", "")

            if raw_source == "Arguer1":
                # Use the stored person1 name
                person_name = st.session_state.get("person1", "")
                avatar_url = get_avatar_url_for_person(person_name)
            elif raw_source == "Arguer2":
                # Use the stored person2 name
                person_name = st.session_state.get("person2", "")
                avatar_url = get_avatar_url_for_person(person_name)
            else:
                # For "God", "Host", "Judge", or "user"
                avatar_url = AVATAR_URLS.get(raw_source, AVATAR_URLS["fallback"])

            # Alternate background color
            bg_color = background_colors[i % 2]

            display_avatar_and_text(avatar_url, content, bg_color)

    st.write("---")

if __name__ == "__main__":
    main()

