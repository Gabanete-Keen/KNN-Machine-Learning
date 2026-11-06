function renderResult() {
  const section = document.querySelector(".empty-state");
  if (!section) return;

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