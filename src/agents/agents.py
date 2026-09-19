import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.tools.tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model Initialization
llm = ChatOpenAI(
    model="openrouter/free",
    temperature=0,
    max_tokens=1024,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# 1st Agent : Search Agent
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
    )

# 2nd Agent : Reader Agent
def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url],
    )

# 3rd Chain : Writer Chain
writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()

# 4th Chain : Critic Chain
critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""),
])

critic_chain = critic_prompt | llm | StrOutputParser()
