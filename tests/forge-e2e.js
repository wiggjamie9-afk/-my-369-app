// End-to-end checks for generator.html (369 Forge) in headless Chromium.
// The Hugging Face library is replaced by tests/stub-hf.js, so no tokens or credits are used.
// Run from anywhere: node tests/forge-e2e.js
const { chromium } = require("playwright");
const http = require("http");
const fs = require("fs");
const path = require("path");

const PAGE = path.join(__dirname, "..", "generator.html");
const STUB = fs.readFileSync(path.join(__dirname, "stub-hf.js"), "utf8");
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

let failures = 0;
function check(name, ok, detail = "") {
    console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
    if (!ok) failures++;
}

async function freshPage(browser, port, routeStub = true) {
    const context = await browser.newContext({ viewport: { width: 390, height: 900 } });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    if (routeStub) {
        await page.route("**/cdn.jsdelivr.net/**", route => route.fulfill({
            contentType: "application/javascript",
            headers: { "access-control-allow-origin": "*" },
            body: STUB,
        }));
    }
    await page.goto(`http://localhost:${port}/`);
    await sleep(400);
    return { page, errors };
}

const idle = (page, id = "forgeBtn", timeout = 60000) =>
    page.waitForFunction(i => !document.getElementById(i).disabled, id, { timeout });

(async () => {
    const server = http.createServer((req, res) => {
        res.setHeader("content-type", "text/html");
        res.end(fs.readFileSync(PAGE));
    }).listen(0);
    const port = server.address().port;
    const browser = await chromium.launch();

    try {
        // 1. Core clover flow
        {
            const { page, errors } = await freshPage(browser, port);
            const status = () => page.textContent("#statusLine");

            await page.fill("#promptInput", "a golden spiral");
            await page.click("#forgeBtn");
            await sleep(300);
            check("asks for a token when none is set", /token/i.test(await status()));

            await page.fill("#tokenInput", "hf_test");
            await page.dispatchEvent("#tokenInput", "change");
            await page.click(".tab[data-view=create]");
            check("cost hint shows the generation cap", /at most 12 image generations/.test(await page.textContent("#costHint")));

            await page.click("#forgeBtn");
            await idle(page);
            const calls = await page.evaluate(() => window.__calls.map(c => c[0]));
            check("image run finds a winner", /Winner: .*9\/10/.test(await status()), await status());
            check("retries a second round when round 1 misses the target", (await page.$$(".round")).length === 2);
            check("director rewrite runs first", calls[0] === "director");
            check("judge output is escaped", (await page.innerHTML(".issues")).includes("&lt;b&gt;"));

            await page.evaluate(() => window.__calls = []);
            await page.click("[data-act=animate]");
            await sleep(300);
            check("Animate switches to video with a start image", await page.isVisible("#refPreview"));
            await page.click("#forgeBtn");
            await idle(page);
            const videoCalls = await page.evaluate(() => window.__calls.filter(c => c[0] === "i2v").map(c => c[1]));
            check("video run uses image-to-video models", videoCalls.includes("Wan-AI/Wan2.2-I2V-A14B"), videoCalls.join(", "));

            const before = await page.$$eval("#libraryGrid .lib-card", x => x.length);
            await page.evaluate(() => {
                const card = [...document.querySelectorAll(".cand")].find(c => !c.classList.contains("winner") && c.querySelector(".has-media"));
                card.querySelector("[data-act=pick]").click();
            });
            await sleep(400);
            check("thumbs-up after a run saves to the library", (await page.$$eval("#libraryGrid .lib-card", x => x.length)) === before + 1);

            await page.evaluate(() => window.__judgeDown = true);
            await page.click("#mode-image");
            await page.click("#refClear");
            await page.click("#forgeBtn");
            await idle(page);
            check("judge outage stops after one round and asks the user to pick", /could not score/.test(await status()) && (await page.$$(".round")).length === 1);
            await page.evaluate(() => window.__judgeDown = false);

            await page.click(".tab[data-view=storyboard]");
            await page.selectOption("#sceneLength", "15");
            await page.selectOption("#clipSeconds", "5");
            await page.click("#planShots");
            const prompts = await page.$$(".shot textarea");
            check("15 s scene at 5 s per clip plans 3 shots", prompts.length === 3);
            for (let i = 0; i < prompts.length; i++) await prompts[i].fill(`shot ${i + 1}`);
            await page.evaluate(() => window.__calls = []);
            await page.click("#runAllShots");
            await idle(page, "runAllShots", 180000);
            const kinds = await page.evaluate(() => window.__calls.filter(c => c[0] === "t2v" || c[0] === "i2v").map(c => c[0]));
            check("all shots get clips", (await page.$$(".shot video")).length === 3);
            check("shots 2 and 3 continue from the previous last frame", kinds.slice(4).every(k => k === "i2v") && kinds.length === 12, kinds.join(","));

            await page.reload();
            await sleep(800);
            check("library and storyboard survive a reload", (await page.$$("#libraryGrid .lib-card")).length >= 5 && (await page.$$(".shot video")).length === 3);

            for (const view of ["create", "storyboard", "library", "stats", "settings"]) {
                await page.click(`.tab[data-view=${view}]`);
                await sleep(100);
                check(`no horizontal scroll at 390px: ${view}`, !(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
            }
            check("no page errors in the core flow", errors.length === 0, errors.join(" | "));
            await page.context().close();
        }

        // 2. Standing rules and failure ledger
        {
            const { page, errors } = await freshPage(browser, port);
            await page.evaluate(() => localStorage.setItem("forge_settings", JSON.stringify({ token: "hf_test", rounds: "1" })));
            await page.reload();
            await sleep(400);

            await page.fill("#notesInput", "never use neon colours");
            await page.click("#saveRule");
            check("note is saved as a standing rule", (await page.textContent("#rulesList")).includes("never use neon colours"));

            await page.evaluate(() => { window.__failModel = "black-forest-labs/FLUX.1-dev"; globalThis.__scores = [3, 4, 3, 4, 3, 4, 3, 4]; });
            await page.fill("#promptInput", "a cat");
            for (let i = 0; i < 2; i++) { await page.click("#forgeBtn"); await idle(page); }
            check("judge receives the standing rule", (await page.evaluate(() => window.__lastJudge)).includes("never use neon colours"));
            check("a model unserved twice is benched", /1 benched/.test(await page.textContent("#costHint")));

            await page.evaluate(() => window.__calls = []);
            await page.click("#forgeBtn");
            await idle(page);
            const used = await page.evaluate(() => window.__calls.filter(c => c[0] === "t2i").map(c => c[1]));
            check("benched model is skipped", used.length === 3 && !used.includes("black-forest-labs/FLUX.1-dev"), used.join(", "));
            const director = await page.evaluate(() => window.__lastDirector);
            check("director receives rules and recent problems", director.includes("never use neon") && /word the prompt to avoid them/.test(director));

            await page.click(".tab[data-view=stats]");
            check("ledger shows the benched model", /benched/.test(await page.textContent("#ledgerTable")));
            await page.click("#resetLedger");
            await page.click(".tab[data-view=create]");
            check("clearing the ledger restores all leaves", /4 leaves/.test(await page.textContent("#costHint")));
            check("no page errors in rules and ledger", errors.length === 0, errors.join(" | "));
            await page.context().close();
        }

        // 3. Library unavailable: the page still works and explains the problem
        {
            const context = await browser.newContext();
            const page = await context.newPage();
            await page.route("**/cdn.jsdelivr.net/**", route => route.abort());
            await page.goto(`http://localhost:${port}/`);
            await sleep(400);
            await page.evaluate(() => localStorage.setItem("forge_settings", JSON.stringify({ token: "hf_test" })));
            await page.reload();
            await sleep(400);
            await page.fill("#promptInput", "x");
            await page.click("#forgeBtn");
            await idle(page);
            check("CDN failure gives a clear message", /Could not load the Hugging Face library/.test(await page.textContent("#statusLine")));
            await context.close();
        }
    } finally {
        await browser.close();
        server.close();
    }

    console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
    process.exit(failures ? 1 : 0);
})();
