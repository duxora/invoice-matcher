"""Daily prompt generator."""
import random
from datetime import date

PROMPT_BANK = [
    "Should AI development be regulated by governments? Argue your position.",
    "Is remote work better than office work for software teams? Defend your view.",
    "Describe a technical decision you made recently. What were the trade-offs?",
    "Should developers be responsible for the ethical implications of their code?",
    "Is test-driven development always worth the extra effort? Why or why not?",
    "Compare microservices vs monolith architecture. When would you choose each?",
    "Should programming languages enforce strict typing? Argue your position.",
    "Is open source software sustainable as a business model?",
    "Describe a time you were wrong about a technical assumption. What did you learn?",
    "Should AI be used in hiring decisions? What safeguards are needed?",
    "Is perfectionism helpful or harmful in software engineering?",
    "Should companies require return-to-office? What does the evidence show?",
    "Describe your ideal development workflow. Why does each part matter?",
    "Is the current pace of AI advancement sustainable and safe?",
    "Should junior developers use AI coding assistants? What are the risks?",
]


def get_daily_prompt(specific_date: date | None = None) -> str:
    """Return a deterministic daily prompt based on the date."""
    d = specific_date or date.today()
    random.seed(d.toordinal())
    return random.choice(PROMPT_BANK)
