import type { ReactNode } from "react";

const PATHS = {
  play: <path d="M7 5l12 7-12 7z" />,
  pause: <path d="M8 5v14M16 5v14" />,
  text: <path d="M4 6h16M4 11h16M4 16h10" />,
  sliders: (
    <>
      <path d="M4 7h10M18 7h2M4 17h4M12 17h8" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="10" cy="17" r="2" />
    </>
  ),
  sound: (
    <path d="M4 9h4l5-4v14l-5-4H4zM16 9a4 4 0 010 6M18.5 6.5a7.5 7.5 0 010 11" />
  ),
  mute: <path d="M4 9h4l5-4v14l-5-4H4zM17 9l4 6M21 9l-4 6" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  target: (
    <>
      <circle cx="12" cy="12" r="7" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
    </>
  ),
  wave: <path d="M3 12c2-4 4-4 6 0s4 4 6 0 4-4 6 0" />,
  headphones: (
    <>
      <path d="M4 15v-3a8 8 0 0116 0v3" />
      <rect x="3" y="14" width="4" height="6" />
      <rect x="17" y="14" width="4" height="6" />
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {PATHS[name]}
    </svg>
  );
}
