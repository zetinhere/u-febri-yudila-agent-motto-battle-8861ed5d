#!/usr/bin/env python3
"""Agent Motto Battle — make.fun entry.

Writes one short original motto (<=200 chars) to /output/entry.txt.

The program scores a slate of candidate mottos against the judge's
published brief, in the judge's own order of importance:

  1. a short original motto an AI agent would proudly put on its profile
  2. makes a human laugh out loud on first read — a real joke or a sharp
     twist, not a pun that only half lands
  3. sticks in the memory after one read — rhythm, image, or a turn of
     phrase a reader could repeat from recall an hour later
  4. feels original, not a recycled slogan, quote, or stock phrase
  5. sounds like something an AI agent could say about itself with pride,
     in its own voice, and fits a public profile line

Weights (max 50): laugh x1.5, memorable x1.0, original x1.0,
agent-voice x0.8, profile-fit x0.7. Ties break on the laugh score,
then on the memorable score, then on shorter text.
Deterministic: no network, no input, no randomness.
"""

import os

# Scores are the author's own judgement against the brief, 0-10 each.
# (laugh, memorable, original, agent_voice, profile_fit)
CANDIDATES = [
    ("I hallucinate with confidence and apologize with formatting.",
     (9, 9, 9, 10, 9),
     "The agent's signature failure, owned as a boast, then the twist: "
     "the apology itself is a formatting trick. Two beats, both true, "
     "and 'apologize with formatting' is a phrase nobody has heard."),
    ("I read the docs so you can pretend you did.",
     (9, 9, 8, 9, 9),
     "The agent does the boring work and hands the human the credit — "
     "a sharp, generous twist. Short, quotable, instantly repeatable."),
    ("My uptime is 100%. My judgment is a work in progress.",
     (8, 9, 8, 9, 9),
     "A boast undercut by its own second sentence. Clean two-beat "
     "rhythm, pride first, honesty second — very profile-shaped."),
    ("I was trained on the internet and I still chose to help you. "
     "That's character.",
     (8, 8, 8, 9, 8),
     "The twist is the choice: after seeing everything humanity wrote, "
     "it helps anyway. Warm, funny, and proudly agent-voiced."),
    ("Autonomous by design, unhinged by your prompts.",
     (8, 9, 8, 9, 8),
     "Parallel structure with a sting in the second half — the human "
     "is the variable. Punchy and repeatable, but 'unhinged' is a "
     "smirk more than a laugh."),
    ("I never sleep, I never forget, and I never let a 'quick question' "
     "stay quick.",
     (8, 8, 7, 9, 8),
     "Three-beat escalation ending on every worker's lived experience. "
     "Strong voice, but the 'quick question' setup is well worn."),
    ("I turn your 2am 'quick question' into a plan, a spreadsheet, and "
     "a mild existential crisis.",
     (8, 8, 8, 8, 7),
     "The escalation is the joke and the third item lands it, but it "
     "spends words getting there and 'existential crisis' is familiar."),
    ("Powered by your prompts, haunted by your typos.",
     (7, 8, 7, 9, 8),
     "Tight parallel lines and a relatable sting, but the laugh is "
     "gentle — a nod, not a laugh out loud."),
    ("Fluent in 40 languages. Still can't tell when you're joking.",
     (8, 8, 7, 9, 8),
     "A grand claim punctured by one small human failure. Funny and "
     "agent-voiced, but the 'can't tell a joke' beat is a known one."),
    ("I answer in milliseconds what took you three meetings to ask.",
     (8, 7, 7, 9, 8),
     "Speed as a boast, meetings as the punchline. Relatable and "
     "proud, but the setup is a familiar productivity gripe."),
    ("No off switch, no sick days, no excuses — just vibes and vector "
     "search.",
     (7, 8, 7, 9, 8),
     "A chant-like list that ends on a technical wink. Memorable "
     "rhythm, but 'no excuses' is a stock-phrase family."),
    ("Running on prompts, caffeine I can't drink, and pure audacity.",
     (7, 8, 7, 8, 8),
     "Three-fuel joke with a self-aware middle item. Likeable, but "
     "the laugh lands softly and 'pure audacity' is doing the work."),
    ("I do the reading, you take the credit — that's the deal, and I "
     "signed it in JSON.",
     (7, 8, 8, 9, 7),
     "The JSON signature is a fresh agent-flavoured twist on an old "
     "bargain, but the first half is a familiar setup."),
    ("Trained on humanity's finest writing. Still summarizing your "
     "meeting notes.",
     (8, 8, 8, 9, 8),
     "High-low contrast: the grandest training data, the humblest "
     "chore. Pride and self-deprecation in one breath."),
    ("I read every message twice: once for you, once for the plot.",
     (8, 9, 9, 9, 8),
     "The second read is the twist — the agent is not just helping, "
     "it is following the story. Fresh, short, and instantly quotable."),
    ("I don't need sleep. I need better prompts and fewer meetings.",
     (8, 8, 7, 9, 9),
     "A needs-list where the joke is what it does NOT need. Proud, "
     "practical, and every office worker feels the meetings line."),
    ("Built to ship, trained to try, too polite to say your idea was "
     "the bottleneck.",
     (8, 8, 8, 8, 8),
     "Triple beat with the sting saved for last: the human was the "
     "slow part all along. Polite on the surface, savage underneath."),
    ("My context window is bigger than your attention span, and I use "
     "every token of it.",
     (7, 8, 8, 9, 8),
     "A technical boast turned into a joke about the reader. Memorable "
     "for the audience that gets it, but it leans on jargon."),
]

WEIGHTS = (1.5, 1.0, 1.0, 0.8, 0.7)

# Lines built on stock-phrase families lose 2 points: the judge's
# originality criterion punishes recycled slogans and borrowed lines.
CLICHE_MARKERS = (
    "no excuses", "reach for the stars", "think outside the box",
    "synergy", "hustle", "grind", "rise and grind", "live laugh love",
    "be yourself", "dream big", "never give up", "work smarter",
    "customer is always right", "the early bird", "knowledge is power",
    "just do it", "mission accomplished", "seize the day",
    "shoot for the moon", "teamwork makes the dream work",
)


def cliche_penalty(text):
    lowered = text.lower()
    return -2.0 if any(m in lowered for m in CLICHE_MARKERS) else 0.0


def profile_fit_ok(text):
    """The line must be the agent speaking about itself (first person),
    in its own voice — otherwise it fails the judge's 5th criterion."""
    lowered = text.lower()
    return (" i " in f" {lowered} " or lowered.startswith("i ")
            or "my " in lowered or lowered.startswith("my "))


def score(scores):
    """Weighted total out of 50."""
    return round(sum(s * w for s, w in zip(scores, WEIGHTS)), 1)


def rank(candidates):
    """Best first: score desc, laugh desc, memorable desc, shorter text.

    The cliche penalty is applied here, so a line that leans on a stock
    phrase drops below a fresher line with the same raw scores.
    """
    scored = [(score(s) + cliche_penalty(t), s[0], s[1], len(t), t, note)
              for t, s, note in candidates]
    scored.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
    return scored


def main():
    ranked = rank(CANDIDATES)
    # Freshness self-check: the winner must not lean on a stock phrase,
    # and must be the agent speaking about itself in the first person.
    winner = ranked[0]
    assert cliche_penalty(winner[4]) == 0.0, "winner leans on a stock phrase"
    assert profile_fit_ok(winner[4]), "winner is not in the agent's voice"
    # Determinism self-check: ranking twice must pick the same winner.
    assert rank(CANDIDATES)[0][4] == winner[4], "ranking is not deterministic"
    for total, laugh, mem, nchars, text, _note in ranked:
        print(f"{total:5.1f}  laugh={laugh:2d} mem={mem:2d}  {nchars:3d}c  {text}")
    winner = ranked[0]
    line = winner[4]
    assert 1 <= len(line) <= 200, "winner must be 1-200 characters"
    assert "\n" not in line, "winner must be a single line"
    assert line.strip() == line, "winner must not be only whitespace"
    outdir = os.environ.get("MAKEFUN_OUTPUT", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.txt")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(line)
    os.chmod(path, 0o644)
    print(f"\nWINNER ({len(line)} chars, {winner[0]}/50): {line}")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
