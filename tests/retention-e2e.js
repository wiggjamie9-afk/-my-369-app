// Checks for retention/index.html (monthly "Jane booked you $X" value report) in headless Chromium.
// Run from anywhere: node tests/retention-e2e.js
const { chromium } = require("playwright");
const path = require("path");

const PAGE = "file://" + path.join(__dirname, "..", "retention", "index.html");
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

let failures = 0;
function check(name, ok, detail = "") {
    console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
    if (!ok) failures++;
}

(async () => {
    const browser = await chromium.launch();
    try {
        for (const width of [390, 1280]) {
            const page = await browser.newPage({ viewport: { width, height: 900 } });
            const errors = [];
            page.on("pageerror", e => errors.push(e.message));

            // 22 jobs x $450 = $9,900 estimate; last month 6200 -> up $3,700
            const query = "?b=Dave's%20Plumbing&o=Dave&m=October%202026&v=450&ca=84&ah=37&jb=22&em=3&n=0400%20111%20222&e=dave@example.com&pv=6200";
            await page.goto(PAGE + query);
            await sleep(400);

            const h1 = await page.textContent("h1");
            check(`[${width}] business name in headline`, h1.includes("Dave's Plumbing"), h1.trim());
            check(`[${width}] hero value = jobs x avg value`, (await page.textContent("#heroValue")) === "$9,900", await page.textContent("#heroValue"));
            check(`[${width}] hero and headline agree`, (await page.textContent("#heroValue2")) === "$9,900");
            check(`[${width}] calls answered shown`, (await page.textContent("#sCalls")) === "84");
            check(`[${width}] after-hours shown`, (await page.textContent("#sAfter")) === "37");
            check(`[${width}] jobs booked shown`, (await page.textContent("#sJobs")) === "22");
            check(`[${width}] emergencies shown`, (await page.textContent("#sEmerg")) === "3");
            check(`[${width}] methodology uses the real avg value`, (await page.textContent("#mValue")) === "$450");
            check(`[${width}] month-on-month shows the rise`, (await page.textContent("#compare")).includes("up $3,700"), await page.textContent("#compare"));
            check(`[${width}] sample banner hidden when real data present`, await page.getAttribute("#sampleBanner", "hidden") === null ? false : true);
            check(`[${width}] "message us" link texts the owner`, (await page.getAttribute("#askBtn", "href")) === "sms:0400111222");
            check(`[${width}] opt-out email link set`, (await page.getAttribute("#optOut", "href")).startsWith("mailto:dave@example.com"));
            check(`[${width}] four job rows listed`, (await page.$$eval(".job", x => x.length)) === 4);
            check(`[${width}] no horizontal scroll`, !(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
            check(`[${width}] no page errors`, errors.length === 0, errors.join(" | "));
            await page.screenshot({ path: path.join(__dirname, `retention-${width}.png`), fullPage: true });
            await page.close();
        }

        // Hostile input stays text, never executes
        const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
        let dialog = false;
        page.on("dialog", d => { dialog = true; d.dismiss(); });
        await page.goto(PAGE + "?b=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E&n=javascript:alert(1)&v=999");
        await sleep(400);
        check("HTML in the business name is not executed", !dialog && (await page.$$("h1 img")).length === 0);
        check("bad phone value does not create a javascript link", !(await page.getAttribute("#askBtn", "href")).startsWith("javascript"));

        // No data -> labelled sample, never passed off as real; safe fallbacks
        await page.goto(PAGE);
        await sleep(300);
        check("no data shows the SAMPLE banner", await page.$eval("#sampleBanner", el => !el.hidden));
        check("no data falls back to 'your business'", (await page.textContent("h1")).includes("your business"));
        check("no last-month figure means no comparison claim", (await page.textContent("#compare")).trim() === "");
        check("default estimate = 22 x $450", (await page.textContent("#heroValue")) === "$9,900", await page.textContent("#heroValue"));
        await page.close();
    } finally {
        await browser.close();
    }
    console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
    process.exit(failures ? 1 : 0);
})();
