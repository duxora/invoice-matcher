"""Predefined conversation scenarios for English practice."""

SCENARIOS = {
    "standup": {
        "name": "Daily Standup",
        "description": "Practice giving status updates in a team standup meeting",
        "opening": "Good morning! Let's do our daily standup. What did you work on yesterday, what are you planning today, and do you have any blockers?",
    },
    "code_review": {
        "name": "Code Review Discussion",
        "description": "Practice explaining and defending your code changes",
        "opening": "I've been looking at your pull request. Can you walk me through the main changes and explain your design decisions?",
    },
    "presentation": {
        "name": "Technical Presentation",
        "description": "Practice presenting a technical topic to your team",
        "opening": "Thanks for preparing this presentation. Please go ahead and present your topic. I'll ask questions afterward.",
    },
    "interview": {
        "name": "Job Interview",
        "description": "Practice answering technical interview questions",
        "opening": "Welcome to the interview. Let's start with a warm-up: tell me about yourself and your experience as a developer.",
    },
    "free": {
        "name": "Free Conversation",
        "description": "Open conversation on any topic",
        "opening": "Hi! What would you like to talk about today? Feel free to pick any topic.",
    },
}


def get_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}. Available: {', '.join(SCENARIOS)}")
    return SCENARIOS[name]


def list_scenarios() -> list[dict]:
    return [{"key": k, **v} for k, v in SCENARIOS.items()]
