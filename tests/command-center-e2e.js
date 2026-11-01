// Checks for command-center/index.html in headless Chromium.
// Run: node tests/command-center-e2e.js
const { chromium } = require("playwright");
const path = require("path");
const PAGE = "file://" + path.join(__dirname, "..", "command-center", "index.html");
const sleep = ms => new Promise(r => setTimeout(r, ms));

let failures = 0;
const check = (name, ok, detail = "") => { console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`); if (!ok) failures++; };

(async () => {
    const browser = await chromium.launch();
    try {
        for (const width of [390, 1280]) {
            const page = await browser.newPage({ viewport: { width, height: 900 } });
            const errors = [];
            page.on("pageerror", e => errors.push(e.message));
            await page.goto(PAGE);
            await sleep(600);

            check(`[${width}] preview banner shown`, /nothing posts on its own/i.test(await page.textContent("#banner")));
            check(`[${width}] 4 stat tiles`, (await page.$$("#stats .stat")).length === 4);
            check(`[${width}] 8 departments`, (await page.$$("#depts .dept")).length === 8);
            check(`[${width}] 6 orchestrator steps`, (await page.$$("#orchSteps .ostep")).length === 6);
            check(`[${width}] 3 approvals waiting`, /3 waiting/.test(await page.textContent("#apprCount")));
            check(`[${width}] activity feed has rows`, (await page.$$("#feed div")).length >= 3);
            check(`[${width}] no horizontal scroll`, !(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
            check(`[${width}] no page errors`, errors.length === 0, errors.join(" | "));
            await page.screenshot({ path: path.join(__dirname, `command-center-${width}.png`), fullPage: true });
            await page.close();
        }

        // Approve / reject behaviour, and that nothing is sent on its own
        const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
        let requests = 0;
        page.on("request", r => { if (!r.url().startsWith("file:")) requests++; });
        await page.goto(PAGE);
        await sleep(400);
        await page.click('#appr-0 [data-act="ok"]');
        check("approve marks the card done", /Approved/.test(await page.textContent("#appr-0")));
        await page.click('#appr-1 [data-act="no"]');
        check("reject marks the card rejected and sends nothing", /Rejected — nothing sent/.test(await page.textContent("#appr-1")));
        check("count drops after decisions", /1 waiting/.test(await page.textContent("#apprCount")));
        check("page makes no network calls of its own", requests === 0, requests + " requests");
        await page.close();
    } finally {
        await browser.close();
    }
    console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
    process.exit(failures ? 1 : 0);
})();
