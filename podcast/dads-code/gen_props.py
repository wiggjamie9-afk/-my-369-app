#!/usr/bin/env python3
"""Generate 18 Dad's Code promo-clip props (5 scenes, ~24s each), on-brand."""
import json, pathlib

BG = "#14121A"; AMBER = "#DFB76C"; CREAM = "#F4F1EA"; MUTED = "#B4AEC0"
OUT = pathlib.Path(__file__).parent / "public" / "demo-props"

# slug, title, hook(sub), line1, line2, stat, statLabel, cmpTitle, leftV, rightV, closeSub
P = [
 ("01-5-minute-present-dad","The 5-Minute Present Dad","Show up when you're running on empty","You feel like you're never doing enough.","Five minutes a day changes that.","5 min","a day to a closer, calmer bond — starting tonight","Most nights","Half-there, phone in hand","Five real minutes, phone down","Free guide — start tonight."),
 ("02-present-not-perfect","Present, Not Perfect","A rebuilt dad's field guide to showing up","You don't need to be the perfect dad.","You need to be the one who shows up.","6","short, blunt chapters — a story, an idea, one thing to try","What kids remember","The perfect, tidy dad","The dad who showed up","The book — out now."),
 ("03-30-day-present-dad-journal","The 30-Day Present Dad Journal","Two minutes a day, thirty days","One tiny action. One line to write.","No guilt if you miss a day.","30","daily pages built for real, busy dads","Your day","Blurs past, forgotten","Two minutes, remembered","Printable journal — $14."),
 ("04-dads-code-kitchen","Dad's Code Kitchen","Fast, fun meals dads can make","Even when Mum's working,","dinner can be quick, tasty and kid-approved.","40","quick meals — all under 30 minutes, all with a protein hit","Weeknight dinner","Cereal again, guilt after","30 min, kids grinning","Cookbook — intro $9."),
 ("05-dad-fuel","Dad Fuel","High-protein meals for the tired dad","You can't pour from an empty cup.","Fuel yourself like you matter.","40","high-protein meals + a 1-hour Sunday prep system","Your energy","Empty by 3pm","Fuelled, showing up","Fuel up — $14."),
 ("06-adhd-dads-playbook","The ADHD Dad's Playbook","Diagnosed at 47 — it finally made sense","Your brain works differently.","Here are systems that survive it.","7","practical plays — systems over willpower","The ADHD trap","White-knuckle willpower","Systems that hold","The playbook — $14."),
 ("07-steady","Steady","A dad's mental health workbook","If you're running on empty,","this is for you.","6","gentle sections — name it, ask, build your anchors","Carrying it","Alone and silent","Named, steadier","Steady — $14."),
 ("08-still-choosing-you","Still Choosing You","Choosing each other on ordinary days","Kids, stress, hard seasons —","keep choosing each other.","20","honest prompts + a weekly 'us' check-in","Your relationship","Ships passing at night","Chosen, on purpose","Couples journal — $12."),
 ("09-dad-and-me-cards","Dad & Me: 100 Conversation Cards","The best talks happen sideways","In the car. At bedtime.","One question opens everything.","100","warm questions in six categories, print or on your phone","Car-ride silence","'How was school?' 'Fine.'","Real talks, sideways","Conversation cards — $9."),
 ("10-dads-bedtime-stories","Dad's Bedtime Stories","For the dad who reads it anyway","Six cosy, read-aloud stories,","each with a gentle code to share.","6","original stories, written to be read slow and soft","Bedtime","Rushed, screen glow","Cosy, a soft lesson","Bedtime stories — $12."),
 ("11-90-day-rebuilt-dad","The 90-Day Rebuilt Dad","I rebuilt myself at 48","Movement. Sleep. Mindset. Momentum.","Three simple 30-day phases.","90","days to your energy, body and momentum back","At 48","Run-down, stuck","Rebuilt, moving","Start today — $15."),
 ("12-days-left","Days Left","See how much time you have left","Enter one birthday.","See the bedtimes you have left.","936","weeks of childhood — mapped, so you spend today well","Today","One of endless days","One of the ones left","Free tool — try it."),
 ("13-the-play-machine","The Play Machine","Never say 'I dunno' again","Age, energy, time you've got —","one tap, a science-backed play idea.","1 tap","to a play idea — deal another, never run out","'What do you want to do?'","Shrug, screens win","Dealt a game, playing","The Play Machine — $9."),
 ("14-letters-to-you","Letters to You","Write letters they'll treasure forever","Their 18th. Their wedding.","The day you're gone.","∞","the most meaningful thing you'll make all year","Your words","Lost, unsaid","Kept, forever","Letters to You — $19."),
 ("15-the-dad-deck","The Dad Deck","For the talks you're dreading","Vaping. Bullying. Consent. Death.","Get a calm, age-tuned script.","1","calm script for every hard talk — how to open, what to avoid","The hard talk","Avoided, fumbled","Opened, steady","The Dad Deck — $12."),
 ("16-dad-battery","Dad Battery","Check your levels before you burn out","A private 60-second weekly check-in.","You can't show up on empty.","60 sec","a week — your energy, mood and connection, tracked","Burnout","Runs you into empty","Caught early, topped up","Dad Battery — $12."),
 ("17-the-bedtime-engine","The Bedtime Engine","A new bedtime story every night","Type their name. Pick a hero.","A unique story, starring your kid.","∞","combinations — never the same story twice","Story time","'Read it again…' the same one","A new world nightly","The Bedtime Engine — $12."),
 ("18-time-capsule","Time Capsule","Capture the little stuff before it's gone","The funny things they said.","The new words. The moments.","1","keepsake yearbook of your kid's whole year","A year","Blurs, forgotten","Printed, kept forever","Time Capsule — $14."),
]

def scenes(title, sub, l1, l2, stat, statLabel, cmpT, leftV, rightV, closeSub):
    return {
      "theme":"flat-motion-graphics",
      "cuts":[
        {"id":"c1","source":"","type":"hero_title","in_seconds":0,"out_seconds":4.5,
         "text":title,"subtitle":sub,"backgroundColor":BG},
        {"id":"c2","source":"","type":"text_card","in_seconds":4.5,"out_seconds":9,
         "text":l1,"subtitle":l2,"color":CREAM,"backgroundColor":BG},
        {"id":"c3","source":"","type":"stat_card","in_seconds":9,"out_seconds":13.5,
         "stat":stat,"subtitle":statLabel,"accentColor":AMBER,"backgroundColor":BG},
        {"id":"c4","source":"","type":"comparison","in_seconds":13.5,"out_seconds":19,
         "title":cmpT,"leftLabel":"Without","leftValue":leftV,"rightLabel":"With Dad's Code",
         "rightValue":rightV,"backgroundColor":BG},
        {"id":"c5","source":"","type":"text_card","in_seconds":19,"out_seconds":24,
         "text":"Present, not perfect.","subtitle":closeSub,"color":AMBER,"backgroundColor":BG},
      ],
      "overlays":[
        {"type":"section_title","in_seconds":9.2,"out_seconds":12.2,
         "text":"Dad's Code","subtitle":"by Jamie Wigg","accentColor":AMBER},
      ],
      "captions":[],"audio":{},
    }

for row in P:
    slug=row[0]; data=scenes(*row[1:])
    fp=OUT/f"dc-{slug}.json"
    fp.write_text(json.dumps(data,indent=2))
    print(fp.name)
print(f"\n{len(P)} props written to {OUT}")
