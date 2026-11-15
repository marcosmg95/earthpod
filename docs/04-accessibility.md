# 04 — Accessibility

Accessibility is a core design goal of EarthPod. The app's [accessibility statement](https://earthpod.earth/#/accessibility) is the user-facing source for current behavior and limitations.

## Implemented behavior

- Audio does not start until the user presses a control; playback can be paused.
- Pages and player controls support keyboard use. Player shortcuts include Space, arrow keys, and D, and can be disabled in settings.
- The introduction has captions and text available to screen readers.
- The sound chart acts as a position control and announces its date/time; key scene descriptions are announced and can be read in a transcript.
- Reduced-motion preferences and an in-app motion setting are supported.
- The app supports browser zoom, text resizing, and high-contrast mode.

## Known limitations

- The app has not had an independent accessibility audit. Its design target is WCAG 2.2 AA; this is not a claim of conformance.
- Some scenes do not yet have spoken descriptions, so the corresponding transcript may be empty.
- JavaScript is required for playback.
- The sonifications represent visual patterns and not exact scientific measurements.

## Checks reported by the project

The app's accessibility statement reports automated checks and manual checks with a keyboard, VoiceOver on macOS, browser zoom, increased text spacing, reduced motion, and high-contrast mode. The production end-to-end suite uses Playwright and axe. These checks do not replace testing with a broad range of users and assistive technologies.

To report an accessibility issue, use the contact information in the app's accessibility statement.
