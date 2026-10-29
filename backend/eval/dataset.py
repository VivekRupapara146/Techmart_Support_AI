"""
Labeled evaluation dataset for router comparison (Milestone 10).

Ground truth `expected_agents` reflects genuine intent, including
deliberately multi-label cases (mirroring the M0 example: "paid yesterday
but Premium still locked" spans billing + technical) and a batch of
harder, more ambiguous/messily-phrased queries to stress-test beyond
clean textbook phrasing — a stand-in for the CFPB stress-testing
originally planned in M0, since this sandbox's network blocks
consumerfinance.gov and the real dataset couldn't be fetched here.
That substitution is a real methodological limitation, disclosed, not
hidden — a capstone report should note real CFPB validation was
planned but not executed for this reason.
"""
from dataclasses import dataclass


@dataclass
class EvalCase:
    query: str
    expected_agents: list[str]
    category: str  # "clean_single" | "clean_multi" | "hard_paraphrase" | "ambiguous"


EVAL_DATASET: list[EvalCase] = [
    # --- Clean, single-domain queries (the "easy" baseline) ---
    EvalCase("I was charged twice for the same order", ["billing"], "clean_single"),
    EvalCase("How do I get a refund for a defective item", ["billing"], "clean_single"),
    EvalCase("My subscription payment failed", ["billing"], "clean_single"),
    EvalCase("My device won't connect to Wi-Fi", ["technical"], "clean_single"),
    EvalCase("The app keeps showing a login error", ["technical"], "clean_single"),
    EvalCase("Firmware update is stuck", ["technical"], "clean_single"),
    EvalCase("What is the warranty period on this product", ["product"], "clean_single"),
    EvalCase("Is this charger compatible with the older model", ["product"], "clean_single"),
    EvalCase("How do I file a warranty claim", ["product"], "clean_single"),
    EvalCase("I want to file a complaint about my experience", ["complaint"], "clean_single"),
    EvalCase("This is the third time I've had this issue, I'm furious", ["complaint"], "clean_single"),
    EvalCase("I'd like to escalate my case to a manager", ["complaint"], "clean_single"),
    EvalCase("What are your store hours", ["faq"], "clean_single"),
    EvalCase("How long does shipping take", ["faq"], "clean_single"),
    EvalCase("How do I reset my password", ["faq"], "clean_single"),

    # --- Genuinely multi-domain queries (the hard, interesting case) ---
    EvalCase("I paid yesterday but Premium is still locked with a login error", ["billing", "technical"], "clean_multi"),
    EvalCase("I was charged for a product that arrived defective and I want to complain", ["billing", "product", "complaint"], "clean_multi"),
    EvalCase("My refund never came through and now I can't log into my account either", ["billing", "technical"], "clean_multi"),
    EvalCase("The warranty claim was denied and I'm extremely unhappy about it", ["product", "complaint"], "clean_multi"),
    EvalCase("I got double-charged and this is the second time, I want to escalate this", ["billing", "complaint"], "clean_multi"),

    # --- Harder / messier real-world-style phrasing (stand-in for CFPB stress test) ---
    EvalCase("yeah so i ordered this thing like 2 weeks ago and money left my account twice not sure why", ["billing"], "hard_paraphrase"),
    EvalCase("cant get the thing to talk to my phone anymore worked fine last week", ["technical"], "hard_paraphrase"),
    EvalCase("does the 2 year thing cover it if i drop it in water", ["product"], "hard_paraphrase"),
    EvalCase("been on hold forever and nobody is helping me this is ridiculous", ["complaint"], "hard_paraphrase"),
    EvalCase("when are yall open on sunday", ["faq"], "hard_paraphrase"),
    EvalCase("so i paid for the premium thing but its still not working and idk why", ["billing", "technical"], "hard_paraphrase"),

    # --- Ambiguous / genuinely hard to classify (sanity check, not a fail if routers disagree) ---
    EvalCase("can I speak to a human", ["complaint", "faq"], "ambiguous"),
    EvalCase("is there a mobile app for this", ["technical", "faq"], "ambiguous"),
    EvalCase("do you sell smartphones", ["product", "faq"], "ambiguous"),
    EvalCase("my order is late and I'm not happy about it", ["faq", "complaint"], "ambiguous"),
]
