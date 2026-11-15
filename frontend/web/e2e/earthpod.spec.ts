import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/** axe finds nothing at WCAG 2.2 A/AA on the page as it is now. */
async function expectNoAxeViolations(page: Page) {
  const { violations } = await new AxeBuilder({ page })
    .withTags(WCAG)
    .analyze();
  const found = violations.map(
    (v) =>
      `${v.id} (${v.impact}): ${v.help} → ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`,
  );
  expect(found).toEqual([]);
}

/** WCAG 1.4.10: nothing needs sideways scrolling. */
async function expectNoSidewaysScroll(page: Page) {
  const { scroll, width } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    width: document.documentElement.clientWidth,
  }));
  expect(scroll).toBeLessThanOrEqual(width);
}

const h1 = (page: Page) => page.getByRole("heading", { level: 1 });

test.describe("intro", () => {
  test("nothing plays on its own; the heading has focus; Begin is there", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(h1(page)).toHaveText("Listen to the Earth");
    await expect(h1(page)).toBeFocused();
    await expect(page.getByRole("button", { name: /Begin/ })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Skip intro" }),
    ).toBeVisible();
    await expectNoAxeViolations(page);
  });

  test("the film announces itself and Escape skips it", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Begin/ }).click();
    await expect(
      page.getByRole("heading", { name: /the Earth tells its story/ }),
    ).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page).toHaveURL(/#\/listen$/);
    await expect(h1(page)).toContainText("How to listen");
  });

  test("Skip intro goes straight to 00", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Skip intro" }).click();
    await expect(page).toHaveURL(/#\/listen$/);
  });
});

test("00 How to listen: the instruments are toggle buttons", async ({
  page,
}) => {
  await page.goto("/#/listen");
  await expect(h1(page)).toBeFocused();
  await expectNoAxeViolations(page);

  await page.getByRole("button", { name: /Meet the instruments/ }).click();
  await expect(h1(page)).toHaveText("Meet the instruments");
  await expect(h1(page)).toBeFocused();

  const europe = page.getByRole("button", {
    name: "Europe Flute",
    exact: true,
  });
  await expect(europe).toHaveAttribute("aria-pressed", "false");
  await europe.click();
  await expect(europe).toHaveAttribute("aria-pressed", "true");
  await expectNoAxeViolations(page);
  await europe.click();
  await expect(europe).toHaveAttribute("aria-pressed", "false");
});

for (const id of ["co2", "nightlights", "aerosols"]) {
  test(`chapter ${id}: title card, scene, keyboard and options`, async ({
    page,
  }) => {
    await page.goto(`/#/${id}`);
    await expect(h1(page)).toBeFocused();
    const start = page.getByRole("button", { name: /Start/ });
    await expect(start).toHaveAttribute("aria-disabled", "false");
    await expectNoAxeViolations(page);

    await start.click();
    await expect(
      page.getByRole("heading", { level: 1, name: /Scene 1 of/ }),
    ).toBeFocused();
    await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();

    // the sound chart is a real slider that speaks its position
    const slider = page.getByRole("slider", { name: "Position" });
    await expect(slider).toHaveAttribute("aria-valuetext", /\S/);

    // Space inside the player pauses
    await slider.focus();
    await page.keyboard.press("Space");
    await expect(page.getByRole("button", { name: "Play" })).toBeVisible();

    const options = page.getByRole("button", { name: "Options" });
    await expect(options).toHaveAttribute("aria-expanded", "false");
    await options.click();
    await expect(options).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByRole("group", { name: "Speed" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Describe this moment/ }),
    ).toBeVisible();
    await page.locator("summary", { hasText: "Read about this scene" }).click();
    await expect(
      page.getByRole("heading", { name: "What happens" }),
    ).toBeVisible();
    const cc = page.getByRole("button", { name: "Descriptions on the video" });
    await expect(cc).toHaveAttribute("aria-pressed", "false");
    await cc.click();
    await expect(cc).toHaveAttribute("aria-pressed", "true");
    await expectNoAxeViolations(page);
  });
}

test("skip link and menu work from the keyboard", async ({ page }) => {
  await page.goto("/#/record");
  await expect(h1(page)).toBeFocused();

  await page.getByRole("link", { name: "Skip to content" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();

  const menu = page.locator("summary", { hasText: "Menu" });
  await menu.click();
  await expect(
    page.getByRole("navigation", { name: "Chapters" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("navigation", { name: "Chapters" })).toBeHidden();
  await expect(menu).toBeFocused();
});

for (const [path, heading, title] of [
  ["/#/record", "Record", "Record · EarthPod"],
  ["/#/accessibility", "Accessibility", "Accessibility · EarthPod"],
  ["/#/nowhere", "Chapter not found", "Chapter not found · EarthPod"],
]) {
  test(`${path}: focused h1, title, no axe violations`, async ({ page }) => {
    await page.goto(path);
    await expect(h1(page)).toHaveText(heading);
    await expect(h1(page)).toBeFocused();
    await expect(page).toHaveTitle(title);
    await expectNoAxeViolations(page);
  });
}

test("follows the system reduced-motion setting", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduce");
});

test.describe("400% zoom (320 px wide)", () => {
  test.use({ viewport: { width: 320, height: 720 } });

  for (const path of ["/", "/#/listen", "/#/record", "/#/accessibility"]) {
    test(`${path} fits without sideways scrolling`, async ({ page }) => {
      await page.goto(path);
      await expect(h1(page)).toBeFocused();
      await expectNoSidewaysScroll(page);
    });
  }

  test("a scene with Options open fits", async ({ page }) => {
    await page.goto("/#/co2");
    await page.getByRole("button", { name: /Start/ }).click();
    await page.getByRole("button", { name: "Options" }).click();
    await expect(page.getByRole("group", { name: "Speed" })).toBeVisible();
    await expectNoSidewaysScroll(page);
  });
});
