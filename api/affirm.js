// Writes a personal affirmation for one goal with Claude Haiku 5.5.
// Deploy on Vercel (this folder becomes /api/affirm) and set ANTHROPIC_API_KEY
// in the project's environment variables. The key never reaches the browser.
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const SYSTEM = `You write affirmations for a 3-6-9 manifestation app.
Given one goal, write a single affirmation of 1 or 2 short sentences (under 35 words).
Write in the first person, present tense, as if the goal has already happened, with warmth and gratitude.
Start with "I am so happy and grateful now that" unless another opening reads much better.
Use British spelling. No hashtags, emojis, quotation marks or preamble: reply with the affirmation only.
If the goal would harm the user or someone else, reply with a gentle general affirmation about peace and wellbeing instead.`;

// Only these sites may call the endpoint. Add your real domain when you have one.
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || "").split(",").map(s => s.trim()).filter(Boolean);

export default async function handler(req, res) {
  const origin = req.headers.origin || "";
  if (ALLOWED_ORIGINS.length === 0 || ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin || "*");
  }
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Use POST" });
  if (ALLOWED_ORIGINS.length && !ALLOWED_ORIGINS.includes(origin)) return res.status(403).json({ error: "Not allowed" });

  const goal = typeof req.body?.goal === "string" ? req.body.goal.trim().slice(0, 80) : "";
  if (!goal) return res.status(400).json({ error: "Missing goal" });

  try {
    const response = await client.messages.create({
      model: "claude-haiku-5-5",
      max_tokens: 1024,
      output_config: { effort: "low" },
      system: SYSTEM,
      messages: [{ role: "user", content: `Goal: ${goal}` }],
    });

    if (response.stop_reason === "refusal") {
      return res.status(422).json({ error: "Could not write an affirmation for that goal" });
    }
    const text = response.content
      .filter(block => block.type === "text")
      .map(block => block.text)
      .join(" ")
      .replace(/\s+/g, " ")
      .replace(/^["“]|["”]$/g, "")
      .trim();
    if (!text) return res.status(502).json({ error: "Empty reply" });
    return res.status(200).json({ affirmation: text });
  } catch (err) {
    if (err instanceof Anthropic.RateLimitError) return res.status(429).json({ error: "Busy, try again shortly" });
    if (err instanceof Anthropic.APIError) return res.status(502).json({ error: "AI service error" });
    return res.status(500).json({ error: "Server error" });
  }
}
