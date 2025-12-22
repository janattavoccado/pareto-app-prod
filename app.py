import os
import asyncio
from flask import Flask, render_template, request
from dotenv import load_dotenv

# -------------------------------------------------
# Load environment variables (.env)
# -------------------------------------------------
load_dotenv()  # loads OPENAI_API_KEY from .env

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not found. "
        "Make sure you have a .env file with OPENAI_API_KEY=sk-..."
    )

# -------------------------------------------------
# OpenAI Agents SDK imports
# -------------------------------------------------
from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner
from agents.exceptions import InputGuardrailTripwireTriggered
from pydantic import BaseModel

# -------------------------------------------------
# Flask setup
# -------------------------------------------------
app = Flask(__name__)

# -------------------------------------------------
# Agent definitions
# -------------------------------------------------

class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="Check if the user is asking about homework.",
    output_type=HomeworkOutput,
)

math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="Specialist agent for math questions",
    instructions=(
        "You provide help with math problems. "
        "Explain your reasoning step by step and include examples."
    ),
)

history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="Specialist agent for historical questions",
    instructions=(
        "You provide assistance with historical queries. "
        "Explain important events and context clearly."
    ),
)


async def homework_guardrail(ctx, agent, input_data):
    """
    Guardrail that blocks non-homework questions.
    """
    result = await Runner.run(
        guardrail_agent,
        input_data,
        context=ctx.context,
    )

    final_output = result.final_output_as(HomeworkOutput)

    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.is_homework,
    )


triage_agent = Agent(
    name="Triage Agent",
    instructions="Determine which specialist agent should handle the user's homework question.",
    handoffs=[
        history_tutor_agent,
        math_tutor_agent,
    ],
    input_guardrails=[
        InputGuardrail(guardrail_function=homework_guardrail),
    ],
)

# -------------------------------------------------
# Async → Sync bridge
# -------------------------------------------------

async def run_agent_async(question: str) -> str:
    try:
        result = await Runner.run(triage_agent, question)
        return result.final_output
    except InputGuardrailTripwireTriggered:
        return "❌ This question was blocked by the homework guardrail."


def run_agent(question: str) -> str:
    """
    Flask runs synchronously; this safely executes async agent code.
    """
    return asyncio.run(run_agent_async(question))

# -------------------------------------------------
# Flask routes
# -------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    answer = None
    question = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            answer = run_agent(question)

    return render_template(
        "index.html",
        question=question,
        answer=answer,
    )

# -------------------------------------------------
# Main entry point
# -------------------------------------------------

if __name__ == "__main__":
    print("✅ OPENAI_API_KEY loaded successfully")
    app.run(debug=True)
