// Checks for demo/index.html (personalised prospect demo) in headless Chromium.
// Run from anywhere: node tests/demo-e2e.js
const { chromium } = require("playwright");
const path = require("path");

const PAGE = "file://" + path.join(__dirname, "..", "demo", "index.html");
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

            const query = "?b=Dave's%20Plumbing&t=Plumber&s=Joondalup&n=0400%20111%20222&o=Dave&e=hello@example.com";
            await page.goto(PAGE + query);
            await sleep(9000);

            const h1 = await page.textContent("h1");
            check(`[${width}] business name in headline`, h1.includes("Dave's Plumbing"), h1.trim());
            check(`[${width}] call button dials the demo line`, (await page.getAttribute("#callBtn", "href")) === "tel:0400111222");
            const chat = await page.textContent("#chat");
            check(`[${width}] Jane discloses she is an AI`, /I'm Jane, the AI assistant/.test(chat));
            check(`[${width}] conversation uses trade and suburb`, chat.includes("plumber in Joondalup") && chat.includes("Dave"));
            check(`[${width}] all chat messages visible`, (await page.$$eval(".msg.show", x => x.length)) === 7);

            await page.fill("#jobValue", "500");
            await page.$eval("#missed", el => { el.value = 10; el.dispatchEvent(new Event("input")); });
            await page.$eval("#rate", el => { el.value = 30; el.dispatchEvent(new Event("input")); });
            // 10 calls x 30% x $500 = $1,500 a week -> x52/12 = $6,500 a month
            check(`[${width}] calculator gives the right monthly loss`, (await page.textContent("#loss")) === "$6,500", await page.textContent("#loss"));

            check(`[${width}] opt-out email link set`, (await page.getAttribute("#optOut", "href")).startsWith("mailto:hello@example.com"));
            check(`[${width}] no horizontal scroll`, !(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)));

            const callBox = await page.$eval("#callBtn", el => el.getBoundingClientRect().toJSON());
            const stickyTop = await page.$eval(".sticky", el => el.getBoundingClientRect().top);
            check(`[${width}] main call button not covered by the sticky bar`, callBox.bottom <= stickyTop);
            check(`[${width}] no page errors`, errors.length === 0, errors.join(" | "));
            await page.screenshot({ path: path.join(__dirname, `demo-${width}.png`), fullPage: true });
            await page.close();
        }

        // Hostile input stays text, and missing values fall back safely
        const page = await browser.newPage({ viewport: { width: 390, height: 900 } });
        let dialog = false;
        page.on("dialog", d => { dialog = true; d.dismiss(); });
        await page.goto(PAGE + "?b=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E&n=javascript:alert(1)");
        await sleep(500);
        check("HTML in the business name is not executed", !dialog && (await page.$$("h1 img")).length === 0);
        check("bad phone value does not create a javascript link", !(await page.getAttribute("#callBtn", "href")).startsWith("javascript"));

        await page.goto(PAGE);
        await sleep(300);
        check("no parameters falls back to 'your business'", (await page.textContent("h1")).includes("your business"));
        check("no demo line points the call button at the example", (await page.getAttribute("#callBtn", "href")) === "#chat");
        await page.close();
    } finally {
        await browser.close();
    }
    console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
    process.exit(failures ? 1 : 0);
})();
