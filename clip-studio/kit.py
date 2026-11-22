"""48 AI Crew marketing kit: one planner client + one carousel per niche, built from true statements only.

Rules baked in:
  * Only facts about Jane that match the build brief (AI disclosure, inbox, bookings, on/after-hours, minute caps, beta languages).
  * No income, ROI or "while you sleep" promises. No statistics.
  * Anything not confirmed (launch status, price) stays an [ADD: ...] placeholder, which blocks approval in the planner.
  * Every caption ends with an AI-assistance line.
"""
import planner as PL

DISCLOSURE = "Made with AI assistance."

# Statements that are true of the design in 48-AI-finish-today-brief.md. Edit if the product changes.
JANE_FACTS = [
    "Jane is an AI receptionist. She says so at the start of every call and mentions the call may be recorded.",
    "Missed callers get a callback request in your Inbox, and urgent ones are flagged.",
    "When a caller wants a job booked, Jane can offer a free slot and add it to your Bookings.",
    "You choose when Jane answers: always, after hours only, or off.",
    "Plans include a set number of call minutes, and you can see how many you've used.",
    "[ADD: launch status, e.g. 'early access' or 'live in Perth']",
    "[ADD: price you want to show publicly]",
]

# id: (label, business type, audience, service, pain line, extra hashtags)
NICHES = {
    "trades": ("Trades (plumbing, electrical, HVAC)", "tradie", "tradies and small crews", "call-outs and quotes", "Missed a call while you were under a sink?", ["tradie", "plumber", "electrician"]),
    "cleaning": ("Cleaning", "cleaner", "cleaning business owners", "home and commercial cleans", "Can't answer the phone mid-clean?", ["cleaning", "cleaningbusiness"]),
    "landscaping": ("Landscaping and pool care", "landscaper", "landscaping and pool crews", "garden and pool jobs", "Calls come in while you're running a mower.", ["landscaping", "poolcare"]),
    "pest": ("Pest control", "pest controller", "pest control operators", "treatments and inspections", "Customers ring when they see the problem, not when you're free.", ["pestcontrol"]),
    "property": ("Property management", "property manager", "property managers", "maintenance requests", "Tenant maintenance calls pile up fast.", ["propertymanagement"]),
    "auto": ("Auto repair and mobile mechanics", "mechanic", "workshops and mobile mechanics", "servicing and repairs", "Hands covered in grease, phone ringing.", ["mechanic", "autorepair"]),
    "salon": ("Salons, barbers and beauty", "salon owner", "salons, barbers and beauty businesses", "appointments", "Booking calls arrive mid-appointment.", ["salon", "barber", "beauty"]),
    "health": ("Dental, medical and allied health", "clinic", "clinics and practices", "patient appointments", "Front desks miss calls at lunch and after hours. Jane must never give medical advice.", ["dentist", "physio", "clinic"]),
    "legal": ("Law and immigration", "law practice", "small law practices", "client intake", "New enquiries come in after hours. Jane must never give legal advice.", ["lawyer", "legal"]),
    "movers": ("Removalists and movers", "removalist", "removalists", "move quotes and bookings", "Quote calls come in mid-lift.", ["removalist", "movers"]),
}


def niche_ids():
    return list(NICHES)


def brief_for(niche, handle="", cta="Message us to find out more.", extra_facts=None):
    label, biz, audience, service, pain, tags = NICHES[niche]
    return {"business": f"48 AI Crew for {label}", "niche": biz, "service": service, "city": "Perth", "audience": audience,
            "tone": "plain, friendly, honest. No hype, no income claims", "cta": cta, "handle": handle,
            "platforms": ["instagram", "facebook"], "posts_per_week": 3,
            "facts": [pain] + list(JANE_FACTS) + list(extra_facts or []), "hashtags": ["48aicrew", "aireceptionist"] + tags}


def slides_for(niche, cta="Message us to find out more."):
    label, biz, audience, service, pain, tags = NICHES[niche]
    return [
        {"kind": "cover", "title": pain.rstrip(".?") + "?", "body": "Meet Jane, an AI receptionist"},
        {"kind": "text", "title": "What Jane does", "body": f"Answers calls for {audience} and takes the details."},
        {"kind": "text", "title": "Callbacks", "body": "Missed callers land in your Inbox. Urgent ones are flagged."},
        {"kind": "text", "title": "Bookings", "body": "Jane can offer a free slot and add the job to your calendar."},
        {"kind": "text", "title": "Always honest", "body": "Jane tells every caller she's an AI and that the call may be recorded."},
        {"kind": "text", "title": "You're in control", "body": "Always on, after hours only, or off."},
        {"kind": "cta", "title": "Want to try it?", "body": cta},
    ]


def add_disclosure(posts):
    for p in posts:
        if DISCLOSURE not in p["caption"]:
            p["caption"] = p["caption"].rstrip() + "\n\n" + DISCLOSURE
    return posts


def make_client(clients_dir, niche, handle, cta, weeks, start, model, extra_facts=None):
    """Create + save one planner client for a niche. Returns (client, engine)."""
    brief = brief_for(niche, handle, cta, extra_facts)
    client = PL.new_client(brief)
    posts, engine = PL.generate(brief, weeks, start, model)
    client["posts"] = add_disclosure(posts)
    client["brief"]["kit_niche"] = niche
    PL.save_client(clients_dir, client)
    return client, engine
