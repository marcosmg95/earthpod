import { useEffect, useRef } from "react";
import { SceneLink } from "../components/SceneLink";

const contactEmail = "marcosmunozgonzalez95@gmail.com";

export function Accessibility() {
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    document.title = "Accessibility · EarthPod";
    heading.current?.focus();
  }, []);

  return (
    <article className="page statement" aria-labelledby="a11y-title">
      <h1 id="a11y-title" ref={heading} tabIndex={-1}>
        Accessibility
      </h1>
      <p className="lede">
        EarthPod is made so that you can explore NASA Earth data by listening,
        with or without seeing the screen. Accessibility was part of the design
        from the first day, not added at the end.
      </p>

      <h2>What we aim for</h2>
      <p>
        We follow the Web Content Accessibility Guidelines (WCAG) 2.2 at level
        AA. EarthPod was built in 48 hours at NASA Space Apps Challenge 2026 and
        has not had an independent audit, so we describe below what works and
        what does not yet.
      </p>

      <h2>What you can expect</h2>
      <ul>
        <li>
          Nothing plays until you press a button, and every sound can be paused.
        </li>
        <li>
          Everything works with a keyboard. Each new screen moves focus to its
          heading.
        </li>
        <li>
          The intro narration has captions, and its full text is available to
          screen readers.
        </li>
        <li>
          In the chapters, the sound chart is also the position slider. It says
          the date and time as you move it, and a short summary describes the
          shape of the sound.
        </li>
        <li>
          Key moments are announced while a scene plays and listed in a
          transcript you can read at your own pace.
        </li>
        <li>
          Keyboard shortcuts work only inside the player (Space, arrow keys, D)
          and can be turned off in the settings.
        </li>
        <li>
          Motion stops when your device asks for reduced motion, or when you
          turn motion off in the settings. Nothing moves for more than five
          seconds without a way to pause it.
        </li>
        <li>
          Text meets WCAG contrast ratios, and the app works in high-contrast
          mode.
        </li>
        <li>You can zoom to 400% and change the text size in your browser.</li>
      </ul>

      <h2>Known limits</h2>
      <ul>
        <li>
          Some scenes do not have spoken descriptions yet, so their transcript
          is empty.
        </li>
        <li>EarthPod needs JavaScript to play sound and video.</li>
        <li>
          The sound is made from model and satellite data. It shows patterns,
          not exact measurements.
        </li>
      </ul>

      <h2>How we checked</h2>
      <p>
        We used automated checkers and tested by hand with a keyboard, VoiceOver
        on macOS, browser zoom, increased text spacing, reduced motion and
        high-contrast mode.
      </p>

      <h2>Tell us about a problem</h2>
      <p>
        If something does not work for you, please tell us what you were trying
        to do and which device, browser and assistive technology you use. Write
        to <a href={`mailto:${contactEmail}`}>{contactEmail}</a>.
      </p>

      <p className="statement-date">Last updated: 15 November 2026</p>
      <p>
        <SceneLink href="/">Back to the start</SceneLink>
      </p>
    </article>
  );
}
