// Starting an assessment clears the previous result.
sessionStorage.removeItem("pahuway-result");

window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    sessionStorage.removeItem("pahuway-result");
  }
});

const questions = [
  {
    key: "Sleep_Hours",
    text: "How many hours do you sleep per day?",
    min: 4, max: 9, step: 0.1,
    hint: "Enter hours, such as 6.5 for 6 hours and 30 minutes.",
  },
  {
    key: "Screen_Time",
    text: "How many hours of screen time do you have per day?",
    min: 2, max: 10, step: 0.1,
    hint: "Enter your daily screen time in hours.",
  },
  {
    key: "Assignment_Load",
    text: "How would you rate your assignment load?",
    min: 1, max: 9, step: 1,
    hint: "1 = lowest load; 9 = highest load.",
  },
  {
    key: "Exam_Pressure",
    text: "How would you rate your exam pressure?",
    min: 1, max: 10, step: 1,
    hint: "1 = lowest pressure; 10 = highest pressure.",
  },
  {
    key: "Social_Support",
    text: "How would you rate your social support?",
    min: 1, max: 10, step: 1,
    hint: "1 = weakest support; 10 = strongest support.",
  },
];

const form = document.querySelector("#TakeTest-form");
const question = form.querySelector(".question");
const nextButton = document.querySelector("#next-question");
const counter = document.querySelector(".question-number");
const progress = document.querySelector(".progress");
const progressFill = document.querySelector(".progress-fill");
const help = document.querySelector("#question-help");

const answers = {};
let currentQuestion = 0;
let submitting = false;

const error = document.createElement("p");
error.setAttribute("role", "alert");
form.after(error);

function renderQuestion() {
  const item = questions[currentQuestion];
  question.replaceChildren();

  const legend = document.createElement("legend");
  legend.textContent = item.text;

  const input = document.createElement("input");
  input.id = "current-answer";
  input.type = "number";
  input.min = item.min;
  input.max = item.max;
  input.step = item.step;
  input.required = true;
  input.setAttribute("aria-label", item.text);
  input.setAttribute("aria-describedby", "question-help");
  input.placeholder = `${item.min}–${item.max}`;

  question.append(legend, input);

  help.textContent =
    `${item.hint} Dataset range: ${item.min}–${item.max}. ` +
    "If your answer falls outside this range, do not change it to fit.";

  counter.textContent =
    `Question ${currentQuestion + 1} of ${questions.length}`;

  progress.setAttribute("aria-valuemax", questions.length);
  progress.setAttribute("aria-valuenow", currentQuestion + 1);
  progressFill.style.width =
    `${((currentQuestion + 1) / questions.length) * 100}%`;

  nextButton.textContent =
    currentQuestion === questions.length - 1 ? "Get result" : "Next";

  nextButton.disabled = true;

  input.addEventListener("input", () => {
  const invalid = input.value === "" || !input.validity.valid;
  nextButton.disabled = submitting || invalid;

  if (input.validity.rangeUnderflow || input.validity.rangeOverflow) {
    error.textContent =
      `This prototype supports values from ${item.min} to ${item.max}. ` +
      "We cannot provide a prediction for your answer. " +
      "Please do not change your actual answer to continue.";
  } else if (input.validity.stepMismatch) {
    error.textContent = item.step === 1
      ? "Please enter a whole-number rating."
      : "Please enter hours using at most one decimal place.";
  } else {
    error.textContent = "";
  }
});

  input.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (submitting || !form.reportValidity()) return;

  const input = document.querySelector("#current-answer");
  answers[questions[currentQuestion].key] = input.valueAsNumber;

  if (currentQuestion < questions.length - 1) {
    currentQuestion++;
    renderQuestion();
    return;
  }

  submitting = true;
  nextButton.disabled = true;
  nextButton.textContent = "Calculating...";
  error.textContent = "";

  try {
    sessionStorage.removeItem("pahuway-result");

    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(answers),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Prediction failed.");
    }

    if (!["Low", "Medium", "High"].includes(result.stress_level)) {
      throw new Error("The server returned an unexpected result.");
    }

    sessionStorage.setItem("pahuway-result", result.stress_level);
    window.location.href = "results.html";
  } catch (err) {
    error.textContent = `${err.message} Please try again.`;
  } finally {
    submitting = false;
    nextButton.disabled = false;
    nextButton.textContent = "Get result";
  }
});

renderQuestion();