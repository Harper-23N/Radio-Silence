import asyncio, os, sys
from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter
B = os.path.dirname(os.path.abspath(__file__))
FOOT = '<div style="width:100%;font-family:Inter,sans-serif;font-size:7.5pt;color:#8a8984;padding:0 0.8in;display:flex;justify-content:space-between"><span>GaugeDark · hour-by-hour research guide</span><span><span class="pageNumber"></span></span></div>'
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await br.new_page()
        await pg.goto("file://" + os.path.join(B, "cover.html")); await pg.wait_for_timeout(300)
        await pg.pdf(path=os.path.join(B, "cover.pdf"), format="Letter", print_background=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
        await pg.goto("file://" + os.path.join(B, "body.html")); await pg.wait_for_timeout(800)
        await pg.pdf(path=os.path.join(B, "body.pdf"), format="Letter", print_background=True, prefer_css_page_size=True,
                     display_header_footer=True, header_template="<div></div>", footer_template=FOOT,
                     margin={"top":"0.75in","bottom":"0.8in","left":"0.8in","right":"0.8in"})
        await br.close()
asyncio.run(main())
w = PdfWriter()
for f in ["cover.pdf", "body.pdf"]:
    for pg in PdfReader(os.path.join(B, f)).pages: w.add_page(pg)
out = os.path.join(os.path.dirname(B), "out", "GaugeDark_Research_Guide.pdf")
w.add_metadata({"/Title": "Research: GaugeDark hour-by-hour guide", "/Author": "Prepared with Claude (AI) for the student"})
w.write(out); print(out, len(PdfReader(out).pages), "pages")
