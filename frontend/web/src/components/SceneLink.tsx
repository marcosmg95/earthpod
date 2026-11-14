import type { MouseEvent, ReactNode } from "react";
import { useLocation } from "wouter";
import { withTransition } from "../a11y/transition";

interface Props {
  href: string;
  className?: string;
  /** marks the link for the page you are on */
  current?: boolean;
  children: ReactNode;
}

/** A real link (open in new tab, copy link, screen-reader link lists all work) that changes page with a fade. */
export function SceneLink({ href, className, current, children }: Props) {
  const [, navigate] = useLocation();
  const go = (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
      return;
    e.preventDefault();
    withTransition(() => navigate(href));
  };
  return (
    <a
      href={`#${href}`}
      className={className}
      aria-current={current ? "page" : undefined}
      onClick={go}
    >
      {children}
    </a>
  );
}
