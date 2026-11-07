async function renderResult() {
  const section = document.querySelector(".empty-state");
  if (!section) return;

  if (window.location.pathname === '/dashboard') {
    section.replaceChildren();
    try {
      const response = await fetch('/api/history', { cache: 'no-store' });
      if (response.status === 401) {
        window.location.replace('/sign-in.html');
        return;
      }
      if (!response.ok) throw new Error('Unable to load your results. Please refresh to try again.');
      const { results } = await response.json();
      const heading = document.createElement('h2');
      heading.textContent = results.length ? 'Your assessment history' : 'No results yet';
      const list = document.createElement('ul');
      results.forEach((result) => {
        const item = document.createElement('li');
        item.textContent = `${result.created_at} UTC — Predicted stress level: ${result.stress_level}`;
        list.append(item);
      });
      const link = document.createElement('a');
      link.href = 'TakeTest.html';
      link.className = 'button';
      link.textContent = 'TakeTest';
      section.replaceChildren(heading, ...(results.length ? [list] : []), link);
    } catch (error) {
      section.textContent = error.message;
    }
    return;
  }

  const level = sessionStorage.getItem("pahuway-result");
  const hasResult = ["Low", "Medium", "High"].includes(level);

  const heading = document.createElement("h2");
  heading.textContent = hasResult
    ? `Predicted stress level: ${level}`
    : "No completed assessment";

  const description = document.createElement("p");
  description.textContent = hasResult
    ? "This prediction is based on your answers. " +
      "It is for wellness awareness, not a medical diagnosis."
    : "Complete all five questions and submit to see a new result.";

  const button = document.createElement("a");
  button.href = "TakeTest.html";
  button.className = "button";
  button.textContent = hasResult
    ? "Take another assessment"
    : "Start assessment";

  section.replaceChildren(heading, description, button);
}

renderResult();
window.addEventListener("pageshow", renderResult);
