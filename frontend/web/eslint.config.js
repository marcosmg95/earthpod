import js from "@eslint/js"
import prettier from "eslint-config-prettier/flat"
import jsxA11y from "eslint-plugin-jsx-a11y"
import reactHooks from "eslint-plugin-react-hooks"
import reactRefresh from "eslint-plugin-react-refresh"
import { defineConfig, globalIgnores } from "eslint/config"
import globals from "globals"
import tseslint from "typescript-eslint"

const AUDIO_MSG = "Audio lives in src/engine. Use the engine store instead."

export default defineConfig([
  globalIgnores(["dist", ".venv-tts", "originals", "node_modules"]),

  // every file: base rules (formatting is Prettier's job)
  {
    extends: [js.configs.recommended],
    rules: {
      eqeqeq: ["error", "smart"],
      "prefer-const": "error",
      "no-alert": "error",
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },

  // the app: type-aware TS, React, strict accessibility
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [
      tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended, // if this line errors, keep the react-hooks line the Vite template generated
      reactRefresh.configs.vite,
      jsxA11y.flatConfigs.strict,
    ],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    settings: { "jsx-a11y": { components: { Link: "a" } } }, // wouter <Link> renders an <a>
    rules: {
      "@typescript-eslint/consistent-type-imports": ["error", { fixStyle: "inline-type-imports" }],
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "@typescript-eslint/no-misused-promises": ["error", { checksVoidReturn: { attributes: false } }],
      "jsx-a11y/control-has-associated-label": "error",
      "jsx-a11y/no-autofocus": ["error", { ignoreNonDOM: true }],
    },
  },

  // UI code (everything except the engine): keep audio, announcements and haptics in one place each
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/engine/**"],
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "AudioContext", message: AUDIO_MSG },
        { name: "webkitAudioContext", message: AUDIO_MSG },
        { name: "speechSynthesis", message: "Use say() from src/a11y/announce, so screen-reader users are not talked over." },
      ],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "AudioContext", message: AUDIO_MSG },
        { object: "navigator", property: "vibrate", message: "Use the feature-detected haptics helper in src/a11y." },
      ],
      "no-restricted-syntax": [
        "error",
        { selector: "JSXAttribute[name.name='autoPlay']", message: "No autoplay (WCAG 1.4.2): sound starts only on a user action." },
        { selector: "JSXAttribute[name.name='aria-live']", message: "Announce through say() from src/a11y/announce, which is throttled." },
      ],
    },
  },

  // Playwright tests and tool configs run in Node, without type-aware rules
  {
    files: ["e2e/**/*.ts", "*.config.{ts,js}"],
    extends: [tseslint.configs.recommended],
    languageOptions: { globals: globals.node },
  },

  // last: turns off every rule that would fight Prettier
  prettier,
])
