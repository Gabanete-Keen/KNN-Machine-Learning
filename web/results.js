// Each tip is matched to a stress level returned by the trained model.
const tipsByLevel = {
  Low: "Think about one habit that helped you this week, like taking a break between study sessions. Try keeping that habit in your routine.",
  Medium: "Choose one thing that’s on your mind today. Take one small step, such as reviewing one topic for an exam or starting the first part of an assignment.",
  High: "If things feel difficult to manage, consider checking in with someone you trust or reaching out to your school counselor for support.",
};

// Both the guest results page and the signed-in dashboard use the same tips.
function appendWellnessTip(container, level) {
  if (!Object.hasOwn(tipsByLevel, level)) return;

  const tip = document.createElement("p");
  tip.textContent = `Wellness tip: ${tipsByLevel[level]}`;
  container.append(tip);
}

async function renderResult() {
  const section = document.querySelector(".empty-state");
  if (!section) return;

  // On the dashboard, load the signed-in user's saved assessments.
  if (window.location.pathname === "/dashboard") {
    section.replaceChildren();

    try {
      const response = await fetch("/api/history", { cache: "no-store" });

      // Ask the user to sign in again if their session has expired.
      if (response.status === 401) {
        window.location.replace("/sign-in.html");
        return;
      }

      if (!response.ok) {
        throw new Error("Unable to load your results. Please refresh to try again.");
      }

      const { results } = await response.json();
      const heading = document.createElement("h2");
      heading.textContent = results.length
        ? "Your assessment history"
        : "No results yet";

      section.replaceChildren(heading);

      if (results.length > 0) {
        const list = document.createElement("ul");

        for (const result of results) {
          const item = document.createElement("li");
          item.textContent =
            `${result.created_at} UTC — Predicted stress level: ${result.stress_level}`;

          // Use this entry's level so each assessment shows its own matching tip.
          appendWellnessTip(item, result.stress_level);
          list.append(item);
        }

        section.append(list);
      }

      const link = document.createElement("a");
      link.href = "TakeTest.html";
      link.className = "button";
      link.textContent = "TakeTest";
      section.append(link);
    } catch (error) {
      section.textContent = error.message;
    }

    return;
  }

  // On the regular results page, read the latest prediction from this browser tab.
  const level = sessionStorage.getItem("pahuway-result");
  const hasResult = Object.hasOwn(tipsByLevel, level);

  const heading = document.createElement("h2");
  heading.textContent = hasResult
    ? `Predicted stress level: ${level}`
    : "No completed assessment";

  const description = document.createElement("p");
  description.textContent = hasResult
    ? "This prediction is based on your answers. It is for wellness awareness, not a medical diagnosis."
    : "Complete all five questions and submit to see a new result.";

  section.replaceChildren(heading, description);

  // Show a tip only when the tab contains a recognized prediction.
  if (hasResult) {
    appendWellnessTip(section, level);
  }

  const button = document.createElement("a");
  button.href = "TakeTest.html";
  button.className = "button";
  button.textContent = hasResult ? "Take another assessment" : "Start assessment";
  section.append(button);
}

// Render on the first visit and refresh the result when returning with Back or Forward.
window.addEventListener("pageshow", renderResult);