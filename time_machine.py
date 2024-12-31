import os
import random
import asyncio
import re
import openai

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import TextMentionTermination

##############################################################################
# LOCAL WRAPPER for openai => "OpenAIChatCompletionClient"
##############################################################################

class OpenAIChatCompletionClient:
    def __init__(self, openai_api_key, model="gpt-4", temperature=1.0):
        openai.api_key = openai_api_key
        self.model = model
        self.temperature = temperature

    @property
    def model_info(self):
        # Mark function_calling=True so autogen_agentchat won't raise ValueError.
        return {
            "function_calling": True
        }

    async def run_chat(self, messages):
        """
        Example method that autogen_agentchat might use somewhere,
        though the library typically calls `create()` directly.
        """
        response = await openai.chat.completions.acreate(
            model=self.model,
            temperature=self.temperature,
            messages=messages
        )
        return response.choices[0].message["content"]

    async def create(
        self,
        messages=None,
        model=None,
        temperature=None,
        top_p=None,
        presence_penalty=None,
        frequency_penalty=None,
        function_call=None,
        functions=None,
        stream=None,
        **kwargs
    ):
        """
        This method is called by autogen_agentchat code like:
            response = await model_client.create(messages=some_messages)
        We must return a structure with a 'choices' list, each with a 'message' dict.
        """
        used_model = model or self.model
        used_temp = temperature if (temperature is not None) else self.temperature

        # Make an async call to the OpenAI chat.completions endpoint
        response = await openai.chat.completions.acreate(
            model=used_model,
            temperature=used_temp,
            messages=messages
        )
        # Return a dict that matches what autogen_agentchat expects:
        return {
            "choices": [
                {
                    # "message" must be the entire message dict from OpenAI
                    "message": response.choices[0].message,
                }
            ]
        }



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
# 2) List of general topics
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

# Additional "famous contests"
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
    rnd = random.random()
    if rnd < 0.50:
        return "witty"
    elif rnd < 0.75:
        return "serious"
    else:
        return "moderate"


###############################################################################
# The ONLY main function (with one God agent, Decorator, etc.)
###############################################################################
async def run_famous_people_contest():
    """
    Runs a conversation with:
      - God (asks Decorator to do their job)
      - Decorator (picks light/dark theme + icon)
      - Host (introduces the arguers and calls the Judge)
      - Two arguers (famous figures)
      - A Judge (one-sentence verdict)
    """
    model_client = OpenAIChatCompletionClient(
        openai_api_key = st.secrets["openai"]["api_key"],
        model="gpt-4o-mini",
        temperature=1.0
    )

    person1, person2 = pick_two_people()
    topic = pick_random_topic()
    style = decide_style()

    # -------------------------------------------------------------------------
    # 1) God
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 2) Decorator
    # -------------------------------------------------------------------------
    theme_options = ["light theme", "dark theme"]
    chosen_theme = random.choice(theme_options)

    # More icons and logic to pick an icon based on theme
    light_icons = ["☀️", "🌈", "🌟", "✨", "🌸", "🎉"]
    dark_icons = ["🌙", "🔥", "⚡", "💥", "💎", "🖤"]
    if chosen_theme == "dark theme":
        chosen_icon = random.choice(dark_icons)
    else:
        chosen_icon = random.choice(light_icons)

    decorator_system_message = f"""
You are the Decorator.
1) Greet God briefly in a few words, and confirm you set '{chosen_theme}' and icon '{chosen_icon}'.
2) Then say: "Host, here is the theme and icon. Thank you."
After that, remain silent.
"""

    decorator_agent = AssistantAgent(
        name="Decorator",
        description="Chooses the environment theme (light or dark) and an icon.",
        system_message=decorator_system_message,
        model_client=model_client,
        tools=[]
    )
    decorator_agent.display_name = "Decorator"

    # -------------------------------------------------------------------------
    # 3) Host
    # -------------------------------------------------------------------------
    host_system_message = f"""
You are the Host.
Your tasks:
1) Acknowledge the Decorator's theme and icon. Then very shortly introduce {person1} (born-died year, who they were) and {person2} ((born-died year, who they were) and mention the subtopic of {topic}.
2) Prompt them to speak. The must speak about 3 short lines each. Start with "{person1}, your turn."
3) After they finish, invite the Judge with: "Judge, your verdict please."
4) After the Judge speaks, say: "Thank you everyone! THE_END."
Do not produce "THE_END" until after the Judge's verdict.
Stay succinct.
"""

    host_agent = AssistantAgent(
        name="Host",
        description="Introduces the conversation, calls the Judge, ends the show.",
        system_message=host_system_message,
        model_client=model_client,
        tools=[]
    )
    host_agent.display_name = "Host"

    # -------------------------------------------------------------------------
    # 4) Arguer1 and Arguer2
    # -------------------------------------------------------------------------
    arguer1_system_message = f"""
You are {person1}.
You are conversing with {person2} about '{topic}' in a {style} style.
Keep lines short (1-2 sentences).
Try to outshine {person2} if it seems competitive.
Stay in character, referencing your historical context.
If you died before {person2} was born, ask who they are.
If in your historical era, nobody knew about the thing that the discussion is about, ask for clarification.
"""

    arguer2_system_message = f"""
You are {person2}.
You are conversing with {person1} about '{topic}' in a {style} style.
Keep lines short (1-2 sentences).
Try to win or impress the audience.
Stay in character, referencing your historical context.
If you died before {person1} was born, ask who they are.
If in your historical era, nobody knew about the thing that the discussion is about, ask for clarification.
"""

    def safe_agent_name(agent_name: str) -> str:
        last_name = agent_name.split(' ')[-1]
        tmp = re.sub(r'[^0-9a-zA-Z_]+', '', last_name)
        if not tmp:
            tmp = "Unknown"
        if re.match(r'^\d', tmp):
            tmp = "Agent_" + tmp
        return tmp

    arguer1_agent = AssistantAgent(
        name=safe_agent_name(person1),
        description=f"Represents {person1} in a possibly competitive discussion.",
        system_message=arguer1_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer1_agent.display_name = person1

    arguer2_agent = AssistantAgent(
        name=safe_agent_name(person2),
        description=f"Represents {person2} in a possibly competitive discussion.",
        system_message=arguer2_system_message,
        model_client=model_client,
        tools=[]
    )
    arguer2_agent.display_name = person2

    # -------------------------------------------------------------------------
    # 5) Judge
    # -------------------------------------------------------------------------
    judge_system_message = f"""
You are the Judge.
Once the Host calls on you, do the following in one short block:
1) Summarize the conversation in one short line.
2) Declare a winner or a draw in exactly one sentence.
Then remain silent.
"""

    judge_agent = AssistantAgent(
        name="Judge",
        description="Gives a short verdict, picks a winner or declares a draw, then is silent.",
        system_message=judge_system_message,
        model_client=model_client,
        tools=[]
    )
    judge_agent.display_name = "Judge"

    # -------------------------------------------------------------------------
    # 6) Termination condition: "THE_END"
    # -------------------------------------------------------------------------
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

    print("\n========== Starting the Contest Chat ==========\n")

    async for msg in chat.run_stream(task="Dear GOD, please speak."):
        if msg.source == "user":
            continue
        yield msg

    print("\n========== End of Contest Chat ==========\n")


###############################################################################
# STREAMLIT APP
###############################################################################
import streamlit as st

def display_message(speaker_name: str, content: str, theme: str, icon: str):
    """
    Renders a single message with basic styling based on 'theme' (light or dark).
    'icon' can be appended after the Decorator's name or used differently.
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
    """Runs the 'run_famous_people_contest' asynchronously and collects its messages."""
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

    st.title("Famous People Contest — Streamlit App")
    st.write(
        "Press the button below to see a short dialogue among God, "
        "a Decorator, two historical figures, a Host, and a Judge."
    )

    if st.button("Start the Contest"):
        # Reset session state for each new run
        st.session_state.theme = "light theme"
        st.session_state.icon = "☀️"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        messages = loop.run_until_complete(get_contest_messages())
        loop.close()

        # Parse Decorator's lines to detect chosen theme & icon
        for msg in messages:
            if msg.source == "Decorator":
                if "dark theme" in msg.content.lower():
                    st.session_state.theme = "dark theme"
                elif "light theme" in msg.content.lower():
                    st.session_state.theme = "light theme"

                # Extract icon
                icon_match = re.search(r"icon\s*'([^']+)'", msg.content)
                if icon_match:
                    st.session_state.icon = icon_match.group(1)

        # Display the messages
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
