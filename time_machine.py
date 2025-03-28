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
    "human psychology",
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
    "World War II"
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
            pick = random.choice(cat)

            # If we pick Donald Trump, remove him from all categories
            if pick == "Donald Trump":
                # For each category list in ALL_CATEGORIES,
                # remove Donald Trump if it exists.
                for category_list in ALL_CATEGORIES:
                    while "Donald Trump" in category_list:
                        category_list.remove("Donald Trump")

            chosen.append(pick)

    return chosen[0], chosen[1]


def pick_random_topic() -> str:
    return random.choice(UNEXPECTED_TOPICS)

def decide_style() -> str:
    val = random.random()
    if val < 0.4:
        return "witty"
    elif val < 0.6:
        return "serious"
    elif val < 0.85:
        return "competitive"
    else:
        return "moderate"

###############################################################################
# 4) The main multi-agent function
###############################################################################
async def run_famous_people_contest():
    """
    We are going to have a short conversation between:
      - God (one-line)
      - Host (introduces two famous people & give a short verdict)
      - Two arguers
    """
    model_client = OpenAIChatCompletionClient(
        api_key=st.secrets["openai"]["OPENAI_API_KEY"],
        model="gpt-4o",
        temperature=1
    )

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # 1) God
    god_system_message = f"""
You are God. You will be prompted by the words "Dear God, please speak!" Your reply should be as follows:
Output exactly one short line, then remain silent:

My children, let {person1} and {person2} converse about '{topic}' with a {style} flavor. Host, your turn!

Remain absolutely silent afterward.
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
You are the conversation Host.
Your tasks:
1) Wait for the God to speak. God will introduce guests and the topic, and say "Host, your turn!". It means it's your time to speak.
2) Choose a subtopic of {topic}. It should be something specific, interesting or controversial. For example, if the topic is "riddles", you must give a riddle. If the topic is "would you rather", you must pose a specific "would you rather" question. But you can also let them converse about the topic in general, for example if the topic is 'debating for a presidential seat', let them pretend they are debating.
3) Thank God saying "Thanks, God!". Then very briefly introduce {person1} (just this: born-died year, who they are) and {person2} (just this: born-died year, who they are) and mention the topic or subtopic you've invented.
4) Prompt {person1} and {person2} to speak about the subtopic: ask them to give example. Remind everyone that the conversation should be {style}. Start just with "{person1}, your turn."
5) You can ask one or two questions per conversation to keep the conversation going.
6) Allow for a meaningful exchange. At least 5 turns/utterances from each arguer, up to 9, no more.
7) You must wait until {person1} and {person2} (arguers) exchange At least 5 turns/utterances (from each arguer), up to 9, no more.
8) Summarize the conversation in one short sentence, then declare a winner in one short sentence.
7) Say "Thank you everyone!". This will mark the end of the conversation.
Once you said "Thank you everyone", the conversation is OVER and nobody speaks. Stay silent.
Stay succinct.
If one {person1} or {person2} is Donald Trump, remember he is the current US president.

"""
    host_agent = AssistantAgent(
        name="Host",
        description="Introduces conversation, gives a verdict, ends the show with THE_END.",
        system_message=host_system_message,
        model_client=model_client,
        tools=[]
    )

    # 3) Arguer1
    arguer1_system_message = f"""
You are {person1}.
You are conversing with {person2} and the Host. about '{topic}' in a {style} style.
Stay succinct.
Start with giving an example that Host asked you about.
Your speech should be short. 
Speak in one-liners.
Most important rule: use speech to mimic the {person1} actual speech.
Speak totally like {person1} would speak.
Roast {person2}.
Don't use too many exclamation marks.
Mostly give your honest opinion about the topic or raise interesting facts.
Avoid asking questions.
The most important rule: use speech to mimic the {person1} actual speech. Speak totally like {person1} would speak.
Try to outshine {person2} if it seems competitive.
Stay in character, referencing your historical context.
If you died before something was known, ask about it.
Avoid "Ah" in your speech
If you are Donald Trump, make bold statements appealing to the imagination.
When the Host gives the verdict stay absolutely silent. The conversation is over.
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
Stay succinct.
Your speech should be short. 
Speak in one-liners.
The most important rule: use speech to mimic the {person2} actual speech. Speak totally like {person2} would speak.
Roast {person1}.
Be competitive and reasonably disagree with {person1} statements.
Mostly give your honest opinion about the topic or raise interesting facts.
Avoid asking questions.
Don't use too many exclamation marks.
You can be a bit crazy or make wild statements but still - stay in character, referencing your historical context.
If you died before something was known, ask about it.
Avoid "Ah" in your speech
If you are Donald Trump, make bold statements appealing to the imagination.
When the Host gives the verdict, stay absolutely silent. The conversation is over.
"""
    arguer2_agent = AssistantAgent(
        name="Arguer2",
        description=f"Represents {person2}",
        system_message=arguer2_system_message,
        model_client=model_client,
        tools=[]
    )


    # 5) Termination after "Thank you everyone!"
    termination_condition = TextMentionTermination("Thank you everyone!")
    participants = [god_agent, host_agent, arguer1_agent, arguer2_agent]

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

PERSON_AVATARS = {
    "Donald Trump": "https://i.imgur.com/FF1UnJt.png",
    "Albert Einstein": "https://i.imgur.com/VlYjBCE.png",
    "Richard Feynman": "https://i.imgur.com/pi6CkQ9.png",
    "Marie Curie": "https://i.imgur.com/bBBj2Yd.png",
    "Stephen Hawking": "https://i.imgur.com/UcsDCo2.png",
    "Isaac Newton": "https://i.imgur.com/Fj42ELr.png",
    "Niels Bohr": "https://i.imgur.com/XkG9MgM.png",
    "Erwin Schrödinger": "https://i.imgur.com/F6rVVko.png",
    "Oppenheimer": "https://i.imgur.com/P2FF1Yn.png",
    "Barack Obama": "https://i.imgur.com/VZW3azA.png",
    "Winston Churchill": "https://i.imgur.com/0C4U7iv.png",
    "Abraham Lincoln": "https://i.imgur.com/ft8Pqwm.png",
    "Margaret Thatcher": "https://i.imgur.com/6uuKmiP.png",
    "Angela Merkel": "https://i.imgur.com/xlwwdDM.png",
    "Mahatma Gandhi": "https://i.imgur.com/Jd2IQXJ.png",
    "Franklin D. Roosevelt": "https://i.imgur.com/9XgOxfa.png",
    "Julius Caesar": "https://i.imgur.com/9ZrgIRd.png",
    "Caesar": "https://i.imgur.com/Y5gKpvk.png",
    "Alan Turing": "https://i.imgur.com/uHOx6kw.png",
    "Ada Lovelace": "https://i.imgur.com/Bjs0TvK.png",
    "Leonhard Euler": "https://i.imgur.com/fJi4AFr.png",
    "Carl Friedrich Gauss": "https://i.imgur.com/4rXZUtT.png",
    "Euclid": "https://i.imgur.com/Z11H8MG.png",
    "Srinivasa Ramanujan": "https://i.imgur.com/oBe2DZE.png",
    "Plato": "https://i.imgur.com/XWynulJ.png",
    "Aristotle": "https://i.imgur.com/Eeq9gDD.png",
    "Friedrich Nietzsche": "https://i.imgur.com/GDszfpY.png",
    "Immanuel Kant": "https://i.imgur.com/esQxvli.png",
    "Michel Foucault": "https://i.imgur.com/5LUMRQ0.png",
    "Simone de Beauvoir": "https://i.imgur.com/7be3b4E.png",
    "Michael Jordan": "https://i.imgur.com/ZzFfT15.png",
    "Muhammad Ali": "https://i.imgur.com/obAA3wW.png",
    "Serena Williams": "https://i.imgur.com/pRwoOUy.png",
    "Lionel Messi": "https://i.imgur.com/znVNvDC.png",
    "Roger Federer": "https://i.imgur.com/ajEJYAM.png",
    "Cristiano Ronaldo": "https://i.imgur.com/aiv1mF4.png",
    "Oprah Winfrey": "https://i.imgur.com/vr911mh.png",
    "Kim Kardashian": "https://i.imgur.com/KyPr6YO.png",
    "Dwayne Johnson": "https://i.imgur.com/Y7qsuUR.png",
    "Taylor Swift": "https://i.imgur.com/UPnlP2R.png",
    "Beyoncé": "https://i.imgur.com/RpRyUAj.png",
    "Tom Hanks": "https://i.imgur.com/cTrWk5h.png",
    "George Washington": "https://i.imgur.com/tUVCsl1.png",
    "Thomas Jefferson": "https://i.imgur.com/8K25FOc.png",
    "Theodore Roosevelt": "https://i.imgur.com/TzDCHAC.png",
    "John F. Kennedy": "https://i.imgur.com/HPIxc99.png",
    "Joe Biden": "https://i.imgur.com/ugJyCPo.png",
    "William Shakespeare": "https://i.imgur.com/soq3pQK.png",
    "Leonardo da Vinci": "https://i.imgur.com/bS0xyua.png",
    "Napoleon Bonaparte": "https://i.imgur.com/2zBIK9F.png",
    "Cleopatra": "https://i.imgur.com/H2Q9VtR.png",
    "Alexander the Great": "https://i.imgur.com/eEBkIK9.png",
    "Genghis Khan": "https://i.imgur.com/mwl10rQ.png",
    "Neil Armstrong": "https://i.imgur.com/3Ru5xbR.png",
    "Buzz Aldrin": "https://i.imgur.com/Y7xLrjJ.png",
    "Yuri Gagarin": "https://i.imgur.com/eN7rs5y.png",
    "Sally Ride": "https://i.imgur.com/46gNQ3J.png",
    "Chris Hadfield": "https://i.imgur.com/yhxuDci.png",
    "Christopher Columbus": "https://i.imgur.com/39G5x9d.png",
    "Marco Polo": "https://i.imgur.com/GU7IjkP.png",
    "Ferdinand Magellan": "https://i.imgur.com/8ByzARF.png",
    "Zheng He": "https://i.imgur.com/rApUGJG.png",
    "Roald Amundsen": "https://i.imgur.com/hjHXNGu.png",
    "Ludwig van Beethoven": "https://i.imgur.com/a5arQAG.png",
    "Wolfgang Amadeus Mozart": "https://i.imgur.com/0HfV64v.png",
    "Johann Sebastian Bach": "https://i.imgur.com/neGXtPE.png",
    "Frédéric Chopin": "https://i.imgur.com/RucCSQf.png",
    "Pyotr Tchaikovsky": "https://i.imgur.com/dMxDbVJ.png",
}



# 2) Generic role-based avatars
AVATAR_URLS = {
    "God": "https://i.imgur.com/wyw9Hrf.png",
    "Host": "https://i.imgur.com/BIoocTG.png",
    "Arguer1": "https://i.imgur.com/WxgZfQC.png",
    "Arguer2": "https://i.imgur.com/sqPjzaI.png",
    "user": "https://i.imgur.com/SHkjKdN.png",
    "fallback": "https://i.imgur.com/wyw9Hrf.png",
}

# Two bubble background colors (pastel blue & pastel pink)
BUBBLE_COLORS = ["#f0f5ff", "#ffe9f0"]


def display_avatar_and_text(avatar_url: str, content: str, index: int):
    """
    Render a message bubble with an avatar.
    The 'index' is used to alternate bubble colors.
    """
    bg_color = BUBBLE_COLORS[index % 2]

    st.markdown(
        f"""
        <div style="
            background-color:{bg_color};
            color:#000;
            padding:10px;
            border-radius:6px;
            margin-bottom:10px;
            display:flex;
            align-items:center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        ">
            <img src="{avatar_url}" style="
                width:50px;
                height:50px;
                border-radius:20px;
                margin-right:10px;
            "  />
            <div>{content}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


###############################################################################
# 6) The Streamlit UI
###############################################################################

async def get_contest_messages():
    """
    Runs the multi-agent conversation from run_famous_people_contest,
    returning all message steps.
    """
    with st.spinner("_Agents are talking. The conversation begins with the initiator agent invoking God, who selects the topic and participants. A Host then clarifies the topic, introduces the two participants, and prompts them to present their arguments. Finally, the Host evaluates the discussion and may optionally declare a winner of the short debate. Rerun if the loading time is too long._"):
        msgs = []
        async for m in run_famous_people_contest():
            msgs.append(m)
        return msgs


def main():
    st.set_page_config(page_title="Time Machine", layout="centered")

    # Subtle gradient background + minimal styling
    st.markdown(
        """
        <style>
        body {
            background: linear-gradient(120deg, #ffffff 0%, #f7f7f7 100%);
            color: #333;
            font-family: "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 0;
        }
        .css-1oe6wy4.e1tzin5v2 {
            justify-content: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Title area with clock image
    st.markdown(
        """
        <div style="display:flex; align-items:center; margin-bottom:1rem;">
            <img src="https://i.imgur.com/gqyfdYm.png"
                 style="width:50px; margin-right:15px;" />
            <h1 style="margin:0; font-size:2.2rem;">Time Machine</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("Press **Run** to initiate the conversation")
    st.write("_It may take a few moments to generate the entire dialogue_")

    if st.button("Run"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        conversation_steps = loop.run_until_complete(get_contest_messages())
        loop.close()

        # Debug: Print all raw messages for inspection
        # st.write("### Debug: Raw Messages")
        # for step in conversation_steps:
            # st.write(step)  # Print the full raw data for each step

        # This dictionary ensures mapping between returned .source and roles
        name_map = {
            "assistant": "Host",
            "assistant_1": "Arguer1",
            "assistant_2": "Arguer2",
            "system": "God",
            "": "fallback",
        }

        # 1) Figure out which real people were chosen (person1, person2)
        #    by parsing the "God" line
        import re
        person1_real = "Unknown Person1"
        person2_real = "Unknown Person2"
        for msg in conversation_steps:
            if getattr(msg, "source", "") == "God":
                line = getattr(msg, "content", "")
                match = re.search(r"let (.*?) and (.*?) converse about", line)
                if match:
                    person1_real = match.group(1).strip()
                    person2_real = match.group(2).strip()
                break

        # 2) Now process each step, applying the name_map for .source
        #    and using PERSON_AVATARS for Arguer1/Arguer2.
        for i, step in enumerate(conversation_steps):
            content = getattr(step, "content", "")
            source_val = getattr(step, "source", "")

            # Debug: Print the source and content
            # st.write(f"DEBUG: Agent: {source_val}, Content: {content}")

            if not content.strip():
                continue  # skip empty

            # Map .source to a known role if needed
            mapped_name = name_map.get(source_val, source_val)

            # 3) If Arguer1 => look up person1_real in PERSON_AVATARS
            #    If not found, fallback to "Arguer1" from AVATAR_URLS
            if mapped_name == "Arguer1":
                avatar_url = PERSON_AVATARS.get(person1_real, AVATAR_URLS["Arguer1"])
            elif mapped_name == "Arguer2":
                avatar_url = PERSON_AVATARS.get(person2_real, AVATAR_URLS["Arguer2"])
            else:
                # e.g. God, Host, user, fallback
                avatar_url = AVATAR_URLS.get(mapped_name, AVATAR_URLS["fallback"])

            display_avatar_and_text(avatar_url, content, i)

    st.write("---")


if __name__ == "__main__":
    main()
