# Using AI agents with Clip Studio

Clip Studio ships an **MCP server** (`mcp_server.py`). Any MCP-capable agent (Claude Desktop, Claude Code, or another agent framework) can use it to make clips, carousels and content calendars for you.

**The rule: agents propose, you approve.** An agent can create clips, carousels and calendars, and put clips in the queue as *private drafts*. It **cannot** add or change rights entries, approve, upload or delete. Those stay in the Clipping page, under your control, so an agent can never invent a permission or publish something.

## Setup (5 minutes)
1. Start Clip Studio and leave it running: `python3 server.py` (or `./run.sh`).
2. Connect your agent to the MCP server. Check your client's current docs for the exact steps; the config looks like:
   ```json
   {"mcpServers": {"clip-studio": {"command": "python3", "args": ["/full/path/to/clip-studio/mcp_server.py"]}}}
   ```
   - **Claude Desktop:** add that to its MCP config file (Settings → Developer → Edit Config), then restart it.
   - **Claude Code:** `claude mcp add clip-studio -- python3 /full/path/to/clip-studio/mcp_server.py`
3. Ask the agent: "Use clip-studio to check status." It should report your encoder, transcription and queue counts.

If the agent says Clip Studio isn't running, start `server.py`.

## What the agent can do
| Tool | Use |
|---|---|
| `cs_status`, `cs_list_media`, `cs_list_exports`, `cs_queue_list`, `cs_list_rights` | Look around (read-only) |
| `cs_find_highlights` | Rank the best moments in a source video |
| `cs_make_clips` | Find, reframe, caption and export finished clips |
| `cs_build_carousel` | Render a numbered image carousel |
| `cs_plan_calendar` | Build a content calendar from a business's real facts |
| `cs_queue_draft` | Queue an exported clip as a **private draft** linked to an existing rights entry |
| `cs_job_status` | Check a long job (clips can take minutes on a laptop) |

## Prompts that work
**Weekly clips from footage you have permission to use**
> Use clip-studio. List the media. For `my_stream_12nov.mp4` (I have a rights entry for it), make 5 clips of about 30 seconds in 9:16 with captions. Then for each clip, write a title (under 100 characters) and a 2-sentence description in my voice, and queue each as a draft linked to my rights entry. Do not invent anything about the people or events in the clips. Tell me which drafts need my approval.

**Client content calendar**
> Use clip-studio to plan 4 weeks for [business]. Use only these facts: [paste the owner's real facts]. Then list every post that needs more input from the owner and write me the questions to ask them. Do not fill in missing facts yourself.

**Carousel**
> Use clip-studio to build a 7-slide 1:1 carousel from these notes: [your notes]. Keep my wording.

## Your 10-minute daily routine
1. The agent works (clips, carousels, drafts).
2. You open **/clipping**, read each draft, fix titles, and **approve** the ones you're happy with.
3. Press **Upload** (private) and publish in YouTube Studio, or post to TikTok/Instagram by hand.

## Limits and cautions
- **Agents make mistakes.** Read everything before approving. Never let an agent post unattended.
- **Permissions are yours to provide.** If the agent says no rights entry covers a clip, add one yourself (with real proof) or skip that clip.
- **Originality:** Meta and YouTube penalise repetitive, unoriginal content. Use your own footage or permitted material, and add real commentary.
- **Speed:** on an 8 GB Mac, long jobs can take minutes. The tools return a `job_id` after ~50 s; the agent checks with `cs_job_status`. Close heavy apps while it runs.
- **Local AI vs Claude:** Clip Studio's own AI features use a local model (Ollama/Jan). Your agent (e.g. Claude) writes titles and descriptions itself; Clip Studio only does the video and file work.
- **Not tested with a real MCP client.** The protocol is tested against my own harness. If your agent can't see the tools, send me its error message.
