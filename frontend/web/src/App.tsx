import { Route, Router, Switch, useLocation } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { Header } from "./components/Header";
import { ChapterPage } from "./routes/ChapterPage";
import { HowToListen } from "./routes/HowToListen";
import { Intro } from "./routes/Intro";
import { RecordPage } from "./routes/Record";
import { SettingsProvider } from "./settings/SettingsProvider";
import { Accessibility } from "./routes/Accessibility";

function Shell() {
  const [location] = useLocation();
  const intro = location === "/";
  return (
    <>
      {!intro && <Header />}
      <main id="main" tabIndex={-1}>
        <Switch>
          <Route path="/">
            <Intro />
          </Route>
          <Route path="/record">
            <RecordPage />
          </Route>
          <Route path="/listen" component={HowToListen} />
          <Route path="/accessibility" component={Accessibility} />
          <Route path="/:chapter/:track?">
            {(p) => (
              <ChapterPage
                key={`${p.chapter}/${p.track ?? ""}`}
                chapterId={p.chapter}
                trackId={p.track}
              />
            )}
          </Route>
        </Switch>
      </main>
      {!intro && (
        <footer className="site-footer">
          <p>
            Images: NASA Scientific Visualization Studio (SVS 5196, SVS 5313,
            SVS 5669); aerosol images created by NASA's Global Modeling and
            Assimilation Office (GMAO). Not endorsed by NASA.
          </p>
          <p>
            <a
              href="https://github.com/marcosmg95/earthpod"
              target="_blank"
              rel="noopener"
            >
              Source code on GitHub
            </a>{" "}
            · NASA Space Apps 2026 · Barcelona
          </p>
        </footer>
      )}
    </>
  );
}

export default function App() {
  return (
    <SettingsProvider>
      <Router hook={useHashLocation}>
        <Shell />
      </Router>
    </SettingsProvider>
  );
}
