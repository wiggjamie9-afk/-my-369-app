"""Every server-rendered page: the sales page, each business's lead inbox and settings, and the owner console.
Plain HTML strings; every value that came from a person goes through e() first. No inline scripts or styles."""
import html
import time

from .estimate import money, price_note
from .store import LEAD_STATES


def e(v):
    return html.escape("" if v is None else str(v), quote=True)


def when(ts):
    return time.strftime("%d %b %Y, %I:%M %p", time.localtime(ts)).lstrip("0")


LOGO = "/static/48-ai-crew-logo.png"
ICON = "/static/48-ai-crew-icon.png"


def layout(title, body, nav="", brandbar=True):
    """Every page: the crew's icon in the browser tab; a brand bar on pages with no business nav; a small
    "Powered by" line under a business's own pages."""
    top = nav or ("<header class=\"brandbar\"><img src=\"%s\" alt=\"\" width=\"40\" height=\"40\"><b>The 48 AI Crew</b></header>" % ICON
                  if brandbar else "")
    foot = ("<footer class=\"powered\"><img src=\"%s\" alt=\"\" width=\"20\" height=\"20\"> Powered by The 48 AI Crew</footer>" % ICON) if nav else ""
    return ("<!doctype html><html lang=\"en-AU\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><meta name=\"theme-color\" content=\"#1B1D21\">"
            "<link rel=\"icon\" type=\"image/png\" href=\"%s\"><link rel=\"apple-touch-icon\" href=\"%s\">"
            "<title>%s</title><link rel=\"stylesheet\" href=\"/static/site.css\"></head><body>"
            "<div class=\"stripe\" aria-hidden=\"true\"></div>%s<main class=\"wrap\">%s</main>%s</body></html>") % (ICON, LOGO, e(title), top, body, foot)


def field(label, name, value="", kind="text", hint="", extra=""):
    return ("<label class=\"f\">%s<input type=\"%s\" name=\"%s\" value=\"%s\" %s>%s</label>"
            % (e(label), kind, e(name), e(value), extra, "<small>%s</small>" % e(hint) if hint else ""))


def flash(message, bad=False):
    return "<p class=\"flash%s\" role=\"%s\">%s</p>" % (" bad" if bad else "", "alert" if bad else "status", e(message)) if message else ""


# ---------------------------------------------------------------- the sales page

def sales(site, sent=False, error="", form=None, demos=()):
    form = form or {}
    name = e(site["service_name"])
    price = lambda v: e(v) if v else "Ask for pricing"
    contact = " ".join(x for x in (
        "Call <a href=\"tel:%s\">%s</a>." % (e("".join(ch for ch in site["owner_phone"] if ch.isdigit() or ch == "+")), e(site["owner_phone"])) if site["owner_phone"] else "",
        "Email <a href=\"mailto:%s\">%s</a>." % (e(site["owner_email"]), e(site["owner_email"])) if site["owner_email"] else "") if x)
    body = """
<header class="hero">
  <img class="hero-logo" src="/static/48-ai-crew-logo.png" alt="The 48 AI Crew" width="148" height="148">
  <p class="eyebrow">%(name)s</p>
  <h1>Homeowners want a price. Give them one in 20 seconds.</h1>
  <p class="lead">%(tagline)s</p>
  <p class="row"><a class="btn" href="/q/demo/">Try the demo</a><a class="btn ghost" href="#start">Get it for my business</a></p>
  %(demos)s
</header>

<section>
  <h2>How it works</h2>
  <ol class="steps">
    <li><b>They tap four answers.</b> Job type, house height, rough size, suburb. No typing until the end.</li>
    <li><b>They see a ballpark.</b> A price range worked out from <em>your</em> rates, with GST included.</li>
    <li><b>You get the lead.</b> Name, mobile, email and what they picked, in your inbox and on your phone.</li>
  </ol>
</section>

<section>
  <h2>What you get</h2>
  <div class="plans">
    <div class="plan"><h3>Lite</h3><p class="price">%(lite)s</p>
      <ul><li>Your own quote link</li><li>Instant ballpark from your rates</li><li>Lead inbox on your phone</li><li>Leads emailed to you</li></ul></div>
    <div class="plan best"><h3>Full</h3><p class="price">%(full)s</p>
      <ul><li>Everything in Lite</li><li>Your name and logo on every screen</li><li>Customers add up to 4 photos of the job</li></ul></div>
  </div>
  <p class="small">You set your own rates and can change them any time. Ballparks are a guide for the homeowner, not a fixed quote.</p>
</section>

<section id="start">
  <h2>Get it for your business</h2>
  %(result)s
  <form method="post" action="/enquire" class="card">
    %(f_name)s%(f_business)s%(f_trade)s%(f_phone)s%(f_email)s
    <label class="f">Anything we should know? (optional)<textarea name="message" maxlength="800">%(message)s</textarea></label>
    <input class="trap" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
    <button class="btn" type="submit">Send my details</button>
    <p class="small">We'll call you to set it up. Your details are only used for that.</p>
  </form>
  <p class="small">%(contact)s</p>
</section>
""" % {
        "name": name, "tagline": e(site["tagline"]), "lite": price(site["price_lite"]), "full": price(site["price_full"]),
        "result": flash("Thanks. We've got your details and will be in touch." if sent else error, bad=bool(error)),
        "f_name": field("Your name", "name", form.get("name", ""), extra="required maxlength=\"80\" autocomplete=\"name\""),
        "f_business": field("Business name", "business", form.get("business", ""), extra="required maxlength=\"80\" autocomplete=\"organization\""),
        "f_trade": field("Trade", "trade", form.get("trade", ""), extra="required maxlength=\"60\" placeholder=\"Roofing, painting, fencing…\""),
        "f_phone": field("Mobile", "phone", form.get("phone", ""), "tel", extra="required maxlength=\"30\" autocomplete=\"tel\""),
        "f_email": field("Email", "email", form.get("email", ""), "email", extra="required maxlength=\"120\" autocomplete=\"email\""),
        "message": e(form.get("message", "")), "contact": contact,
        "demos": ("<p class=\"small\">See it for your trade: %s</p>" % " · ".join(
            "<a href=\"/q/%s/\">%s</a>" % (e(slug), e(name)) for slug, name in demos)) if len(demos) > 1 else ""}
    return layout("%s | Instant ballpark quotes for tradies" % site["service_name"], body, brandbar=False)


def paused(tenant):
    phone = tenant["phone"]
    call = "<p><a class=\"btn\" href=\"tel:%s\">Call %s</a></p>" % (e("".join(c for c in phone if c.isdigit() or c == "+")), e(phone)) if phone else ""
    return layout(tenant["name"], "<h1>%s</h1><p class=\"lead\">Online quotes are switched off right now.</p>%s" % (e(tenant["name"]), call))


def not_found():
    return layout("Not found", "<h1>Nothing here</h1><p class=\"lead\">That page doesn't exist.</p><p><a class=\"btn ghost\" href=\"/\">Home</a></p>")


# ---------------------------------------------------------------- a business's own pages

def tenant_nav(tenant, here):
    base = "/q/%s/admin" % e(tenant["slug"])
    link = lambda path, label, key: "<a href=\"%s%s\"%s>%s</a>" % (base, path, " aria-current=\"page\"" if here == key else "", label)
    return ("<nav class=\"bar\"><b>%s</b><span>%s%s<a href=\"/q/%s/\" target=\"_blank\" rel=\"noopener\">My quote page</a>"
            "<form method=\"post\" action=\"%s/logout\"><button class=\"linkish\" type=\"submit\">Sign out</button></form></span></nav>"
            % (e(tenant["name"]), link("", "Leads", "leads"), link("/settings", "Settings", "settings"), e(tenant["slug"]), base))


def login(title, action, error="", note=""):
    return layout(title, "<h1>%s</h1>%s%s<form method=\"post\" action=\"%s\" class=\"card narrow\">"
                  "<label class=\"f\">Password<input type=\"password\" name=\"password\" required autocomplete=\"current-password\" autofocus></label>"
                  "<button class=\"btn\" type=\"submit\">Sign in</button></form>"
                  % (e(title), "<p class=\"lead\">%s</p>" % e(note) if note else "", flash(error, True), e(action)))


def leads_list(tenant, leads, counts, status, link, notes):
    base = "/q/%s/admin" % e(tenant["slug"])
    total = sum(counts.values())
    chips = "".join("<a class=\"chip\" href=\"%s%s\"%s>%s <span>%d</span></a>" % (
        base, "?status=" + s if s else "", " aria-current=\"true\"" if status == s else "", label, n)
        for s, label, n in [("", "All", total)] + [(s, s.capitalize(), counts.get(s, 0)) for s in LEAD_STATES])
    if leads:
        rows = "".join(
            "<a class=\"lead-row\" href=\"%s/lead/%d\"><span class=\"who\">%s</span><span class=\"badge %s\">%s</span>"
            "<span class=\"what\">%s · %s · %s</span><span class=\"amt\">%s – %s</span><span class=\"when\">%s%s</span></a>" % (
                base, l["id"], e(l["name"]), e(l["status"]), e(l["status"]), e(l["job_type"]), e(l["size"]), e(l["suburb"]),
                money(l["low"]), money(l["high"]), when(l["created_at"]), " · %d photo%s" % (l["photos"], "" if l["photos"] == 1 else "s") if l["photos"] else "")
            for l in leads)
    else:
        rows = "<p class=\"empty\">%s</p>" % ("No %s leads." % e(status) if status else "No leads yet. Share your quote link and they'll land here.")
    share = ("<div class=\"card\"><h3>Your quote link</h3><p class=\"mono\">%s</p>"
             "<p class=\"small\">Put it on your website, your Google profile, your Facebook page and your email signature.</p></div>" % e(link))
    return layout("Leads | %s" % tenant["name"],
                  "<h1>Leads</h1>%s%s<p class=\"chips\">%s</p><div class=\"list\">%s</div>"
                  "<p><a class=\"btn ghost small-btn\" href=\"%s/leads.csv\">Download all as a spreadsheet</a></p>"
                  % ("".join(flash(n, True) for n in notes), share, chips, rows, base), tenant_nav(tenant, "leads"))


def lead_detail(tenant, lead, saved=False):
    base = "/q/%s/admin" % e(tenant["slug"])
    tel = "".join(c for c in lead["phone"] if c.isdigit() or c == "+")
    photos = "".join("<a href=\"%s/photo/%d/%d\" target=\"_blank\" rel=\"noopener\"><img src=\"%s/photo/%d/%d\" alt=\"Photo %d from the customer\" loading=\"lazy\"></a>"
                     % (base, lead["id"], n, base, lead["id"], n, n) for n in range(1, lead["photos"] + 1))
    states = "".join("<label class=\"pick\"><input type=\"radio\" name=\"status\" value=\"%s\"%s><span>%s</span></label>"
                     % (s, " checked" if lead["status"] == s else "", s.capitalize()) for s in LEAD_STATES)
    delivery = " · ".join(x for x in ("email " + e(lead["email_status"]) if lead["email_status"] else "",
                                      "webhook " + e(lead["forward_status"]) if lead["forward_status"] else "") if x)
    body = """
<p><a href="%(base)s">‹ All leads</a></p>
<h1>%(name)s</h1>
<p class="lead">%(job)s · %(diff)s · %(size)s · %(suburb)s</p>
%(saved)s
<div class="card">
  <p class="k">They were shown</p>
  <p class="big">%(low)s – %(high)s <small>%(note)s</small></p>
  <p class="row"><a class="btn" href="tel:%(tel)s">Call %(phone)s</a><a class="btn ghost" href="mailto:%(email)s">Email</a></p>
  <p class="small">%(email)s · received %(when)s%(delivery)s</p>
</div>
%(photos)s
<form method="post" action="%(base)s/lead/%(id)d" class="card">
  <h3>Where is it at?</h3>
  <div class="picks">%(states)s</div>
  <label class="f">Your notes<textarea name="notes" maxlength="2000">%(notes)s</textarea></label>
  <button class="btn" type="submit">Save</button>
</form>""" % {
        "note": e(price_note(tenant["config"])),
        "base": base, "id": lead["id"], "name": e(lead["name"]), "job": e(lead["job_type"]), "diff": e(lead["difficulty"]),
        "size": e(lead["size"]), "suburb": e(lead["suburb"]), "low": money(lead["low"]), "high": money(lead["high"]),
        "tel": e(tel), "phone": e(lead["phone"]), "email": e(lead["email"]), "when": when(lead["created_at"]),
        "delivery": " · " + delivery if delivery else "", "saved": flash("Saved." if saved else ""),
        "photos": "<div class=\"card\"><h3>Photos</h3><div class=\"photos\">%s</div></div>" % photos if photos else "",
        "states": states, "notes": e(lead["notes"])}
    return layout("%s | %s" % (lead["name"], tenant["name"]), body, tenant_nav(tenant, "leads"))


def num(v):
    return ("%g" % v) if isinstance(v, float) else str(v)


def tenant_settings(tenant, message="", error="", mail_on=False):
    c, base = tenant["config"], "/q/%s/admin" % e(tenant["slug"])
    unit = e(c["trade"]["unit"])
    cell = lambda name, value, label, step="any": ("<label class=\"cell\"><span>%s</span><input name=\"%s\" value=\"%s\" inputmode=\"decimal\" type=\"number\" min=\"0\" step=\"%s\" required></label>"
                                                   % (e(label), e(name), e(num(value)), step))
    text = lambda name, value, label: "<label class=\"cell wide\"><span>%s</span><input name=\"%s\" value=\"%s\" maxlength=\"60\" required></label>" % (e(label), e(name), e(value))
    job_types = "".join("<div class=\"grid\">%s%s%s</div>" % (
        text("jt_%s_label" % j["id"], j["label"], "Name"), cell("jt_%s_labour" % j["id"], j["labourPerUnit"], "Labour $ per " + c["trade"]["unit"]),
        cell("jt_%s_material" % j["id"], j["materialPerUnit"], "Materials $ per " + c["trade"]["unit"])) for j in c["jobTypes"])
    difficulty = "".join("<div class=\"grid\">%s%s</div>" % (
        text("df_%s_label" % d["id"], d["label"], "Name"), cell("df_%s_mult" % d["id"], d["multiplier"], "Multiplier (1 = normal, 1.25 = 25%% dearer)")) for d in c["difficulty"])
    sizes = "".join("<div class=\"grid\">%s%s%s</div>" % (
        text("sz_%s_label" % s["id"], s["label"], "Name"), cell("sz_%s_min" % s["id"], s["min"], "From (" + c["trade"]["unit"] + ")"),
        cell("sz_%s_max" % s["id"], s["max"], "To (" + c["trade"]["unit"] + ")")) for s in c["sizes"])
    p, w = c["pricing"], c["words"]
    full = tenant["tier"] == "full"
    r = p.get("rebate")
    rebate_cell = ("<div class=\"grid\">%s</div><p class=\"small\">The rebate comes off the price the customer sees. Check this figure whenever the rules or the "
                   "market price change, because every ballpark on your page uses it. It is shown to the customer as an estimate.</p>"
                   % cell("rebate_per_unit", r["perUnit"], "Rebate $ per %s (full rate)" % c["trade"]["unit"])) if r else ""
    logo = ("<h2>Your logo</h2><div class=\"card\">%s<label class=\"f\">Upload a logo (PNG or JPG, under 400 KB)<input type=\"file\" name=\"logo\" accept=\"image/png,image/jpeg,image/webp\"></label>%s</div>"
            % ("<p><img class=\"logo-now\" src=\"/q/%s/logo\" alt=\"Your current logo\"></p>" % e(tenant["slug"]) if tenant["logo"] else "<p class=\"small\">No logo yet. Your business name is shown on its own.</p>",
               "<label class=\"check\"><input type=\"checkbox\" name=\"remove_logo\" value=\"1\"> Remove my logo</label>" if tenant["logo"] else "")) if full else \
        "<h2>Your logo</h2><p class=\"small\">Your own name and logo on every screen, and customer photos, come with the Full plan.</p>"
    body = """
<h1>Settings</h1>%(message)s%(error)s
<form method="post" action="%(base)s/settings" enctype="multipart/form-data">
<h2>Your business</h2>
<div class="card">%(f_name)s%(f_phone)s%(f_licence)s</div>
%(logo)s
<h2>Your rates</h2>
<p class="small">Dollars per %(unit)s, %(gst_note)s. The homeowner sees a range, never these numbers.</p>
<div class="card">%(job_types)s</div>
<h2>Harder jobs</h2><div class="card">%(difficulty)s</div>
<h2>Job sizes</h2><div class="card">%(sizes)s</div>
<h2>How the ballpark is shown</h2>
<div class="card">
  <label class="check"><input type="checkbox" name="gst_registered" value="1"%(gst_reg)s> I'm registered for GST (the quote page will say prices include GST)</label>
  <label class="check"><input type="checkbox" name="gst_included" value="1"%(gst_checked)s> My rates above already include GST</label>
  %(rebate)s
  <div class="grid">%(spread)s%(round_to)s%(minimum)s</div>
  <label class="check strong"><input type="checkbox" name="rates_confirmed" value="1"%(confirmed)s> These are my real rates. Take the "example rates" notice off my quote page.</label>
</div>
<h2>Wording</h2>
<div class="card">%(f_headline)s%(f_subline)s%(f_note)s%(f_thanks)s</div>
<h2>Getting your leads</h2>
<div class="card">%(f_notify)s%(f_webhook)s</div>
<p><button class="btn" type="submit">Save settings</button></p>
</form>""" % {
        "base": base, "message": flash(message), "error": flash(error, True), "unit": unit,
        "gst_note": "with no GST" if p.get("gstRegistered") is False else "including GST" if p.get("ratesIncludeGst") else "before GST (the app adds it)",
        "f_name": field("Business name", "name", tenant["name"], extra="required maxlength=\"80\""),
        "f_phone": field("Phone customers can call", "phone", tenant["phone"], "tel", extra="maxlength=\"40\""),
        "f_licence": field("Licence number (optional)", "licence", tenant["licence"], extra="maxlength=\"40\""),
        "logo": logo, "job_types": job_types, "difficulty": difficulty, "sizes": sizes,
        "gst_reg": "" if p.get("gstRegistered") is False else " checked", "rebate": rebate_cell,
        "gst_checked": " checked" if p.get("ratesIncludeGst") else "", "confirmed": " checked" if tenant["rates_confirmed"] else "",
        "spread": cell("spread_pct", round(p["spread"] * 100, 4), "Widen the range by (%) each way"),
        "round_to": cell("round_to", p["roundTo"], "Round to the nearest ($)", "1"), "minimum": cell("minimum_job", p["minimumJob"], "Smallest job you'd show ($)"),
        "f_headline": field("Headline", "w_headline", w["headline"], extra="required maxlength=\"90\""),
        "f_subline": field("Line under the headline", "w_subline", w["subline"], extra="maxlength=\"140\""),
        "f_note": field("Small print under the ballpark", "w_ballparkNote", w["ballparkNote"], extra="maxlength=\"200\""),
        "f_thanks": field("Thank-you message", "w_thanksSub", w["thanksSub"], extra="maxlength=\"140\""),
        "f_notify": field("Email new leads to", "notify_email", tenant["notify_email"], "email",
                          hint="" if mail_on else "Email sending isn't switched on for this service yet. Your leads are still saved here.", extra="maxlength=\"120\""),
        "f_webhook": field("Also send each lead to this web address (optional)", "forward_webhook", tenant["forward_webhook"], "url",
                           hint="For Zapier, Make or your own system. Must start with https://", extra="maxlength=\"300\"")}
    return layout("Settings | %s" % tenant["name"], body, tenant_nav(tenant, "settings"))


# ---------------------------------------------------------------- the owner's console

def admin_home(site, tenants, enquiries, presets, message="", error="", issued=None, mail_on=False, public_url=""):
    today = time.strftime("%Y-%m-%d")
    rows = ""
    for t in tenants:
        overdue = t["paid_until"] and t["paid_until"] < today and not t["demo"]
        rows += """
<form method="post" action="/admin/business/%(id)d" class="card biz">
  <div class="row spread"><h3>%(name)s%(demo)s</h3><span class="badge %(state)s">%(state_label)s</span></div>
  <p class="small"><a href="/q/%(slug)s/" target="_blank" rel="noopener">%(url)s/q/%(slug)s/</a> · %(l30)d leads in 30 days, %(lall)d all up%(contact)s%(rates)s</p>
  <div class="grid">
    <label class="cell"><span>Plan</span><select name="tier"><option value="lite"%(lite)s>Lite</option><option value="full"%(full)s>Full</option></select></label>
    <label class="cell"><span>Paid until%(overdue)s</span><input type="date" name="paid_until" value="%(paid)s"></label>
    <label class="cell"><span>Quote page</span><select name="active"><option value="1"%(on)s>On</option><option value="0"%(off)s>Paused</option></select></label>
  </div>
  <p class="row"><button class="btn small-btn" type="submit">Save</button>
     <button class="btn ghost small-btn" type="submit" name="reset_password" value="1">Give them a new password</button></p>
</form>""" % {
            "id": t["id"], "name": e(t["name"]), "slug": e(t["slug"]), "url": e(public_url), "demo": " <span class=\"badge\">demo</span>" if t["demo"] else "",
            "state": "off" if not t["active"] else "late" if overdue else "on",
            "state_label": "paused" if not t["active"] else "payment overdue" if overdue else "live",
            "l30": t["leads_30d"], "lall": t["leads_total"],
            "contact": " · " + e(" ".join(x for x in (t["contact_email"], t["phone"]) if x)) if (t["contact_email"] or t["phone"]) else "",
            "rates": "" if t["rates_confirmed"] or t["demo"] else " · <b>still on example rates</b>",
            "lite": " selected" if t["tier"] == "lite" else "", "full": " selected" if t["tier"] == "full" else "",
            "overdue": " (overdue)" if overdue else "", "paid": e(t["paid_until"]),
            "on": " selected" if t["active"] else "", "off": "" if t["active"] else " selected"}
    enq = "".join("""
<form method="post" action="/admin/enquiry/%d" class="card%s">
  <div class="row spread"><h3>%s · %s</h3><span class="small">%s</span></div>
  <p>%s · <a href="tel:%s">%s</a> · <a href="mailto:%s">%s</a></p>%s
  <button class="btn ghost small-btn" type="submit" name="handled" value="%d">%s</button>
</form>""" % (q["id"], " done" if q["handled"] else "", e(q["business"]), e(q["trade"]), when(q["created_at"]), e(q["name"]),
              e("".join(c for c in q["phone"] if c.isdigit() or c == "+")), e(q["phone"]), e(q["email"]), e(q["email"]),
              "<p class=\"small\">%s</p>" % e(q["message"]) if q["message"] else "", 0 if q["handled"] else 1,
              "Mark as not done" if q["handled"] else "Mark as done") for q in enquiries) or "<p class=\"empty\">No enquiries yet.</p>"
    new_pw = ""
    if issued:
        new_pw = ("<div class=\"card issued\" role=\"status\"><h3>Give these to %s</h3><p>Sign-in page: <span class=\"mono\">%s/q/%s/admin</span></p>"
                  "<p>Password: <span class=\"mono\">%s</span></p><p class=\"small\">This password is shown once and is not stored in readable form. Copy it now.</p></div>"
                  % (e(issued["name"]), e(public_url), e(issued["slug"]), e(issued["password"])))
    options = "".join("<option value=\"%s\">%s</option>" % (e(p), e(p.capitalize())) for p in presets)
    body = """
<h1>Owner console</h1>%(message)s%(error)s%(new_pw)s
%(mail)s
<h2>Businesses</h2>%(rows)s
<h2>Add a business</h2>
<form method="post" action="/admin/business" class="card">
  %(f_name)s%(f_slug)s
  <div class="grid">
    <label class="cell"><span>Trade</span><select name="preset">%(options)s</select></label>
    <label class="cell"><span>Plan</span><select name="tier"><option value="lite">Lite</option><option value="full">Full</option></select></label>
  </div>
  %(f_email)s%(f_phone)s
  <button class="btn" type="submit">Create it</button>
</form>
<h2>Enquiries from the sales page</h2>%(enq)s
<h2>Sales page details</h2>
<form method="post" action="/admin/site" class="card">
  %(s_name)s%(s_tag)s%(s_lite)s%(s_full)s%(s_owner)s%(s_phone)s%(s_email)s
  <button class="btn" type="submit">Save</button>
</form>
<form method="post" action="/admin/logout"><button class="linkish" type="submit">Sign out</button></form>""" % {
        "message": flash(message), "error": flash(error, True), "new_pw": new_pw, "rows": rows or "<p class=\"empty\">No businesses yet.</p>",
        "mail": "" if mail_on else "<p class=\"flash bad\">Email sending is off (no SMTP settings), so businesses are not emailed their leads. Leads are still saved in each inbox.</p>",
        "f_name": field("Business name", "name", extra="required maxlength=\"80\""),
        "f_slug": field("Link name (optional)", "slug", hint="Their page will be /q/link-name/. Leave empty to make it from the business name.", extra="maxlength=\"40\" pattern=\"[a-z0-9-]*\""),
        "f_email": field("Their email", "contact_email", kind="email", extra="maxlength=\"120\""),
        "f_phone": field("Their phone", "phone", kind="tel", extra="maxlength=\"40\""),
        "options": options, "enq": enq,
        "s_name": field("Service name", "service_name", site["service_name"], extra="required maxlength=\"60\""),
        "s_tag": field("One-line pitch", "tagline", site["tagline"], extra="maxlength=\"200\""),
        "s_lite": field("Lite price, as you want it shown", "price_lite", site["price_lite"], hint="e.g. $49 a month. Empty shows \"Ask for pricing\".", extra="maxlength=\"60\""),
        "s_full": field("Full price, as you want it shown", "price_full", site["price_full"], extra="maxlength=\"60\""),
        "s_owner": field("Your name", "owner_name", site["owner_name"], extra="maxlength=\"80\""),
        "s_phone": field("Your phone (shown on the sales page)", "owner_phone", site["owner_phone"], "tel", extra="maxlength=\"40\""),
        "s_email": field("Your email (shown on the sales page; enquiries are sent here)", "owner_email", site["owner_email"], "email", extra="maxlength=\"120\"")}
    return layout("Owner console", body)
