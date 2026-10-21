// The remaining questions are sample content for this front-end preview.
const questions = [
  {
    text: "How well have you been sleeping lately?",
    options: ["Very well", "Fairly well", "Not great", "Poorly"],
  },
  {
    text: "How has your energy been lately?",
    options: ["Full of energy", "Mostly steady", "A little low", "Very low"],
  },
  {
    text: "How often have you felt overwhelmed lately?",
    options: ["Rarely", "Sometimes", "Often", "Very often"],
  },
  {
    text: "How easy has it been to focus lately?",
    options: [
      "Very easy",
      "Fairly easy",
      "A little difficult",
      "Very difficult",
    ],
  },
  {
    text: "How much tension have you noticed in your body?",
    options: ["Very little", "A little", "Quite a bit", "A lot"],
  },
  {
    text: "How connected have you felt to others lately?",
    options: [
      "Very connected",
      "Fairly connected",
      "A little disconnected",
      "Very disconnected",
    ],
  },
  {
    text: "How easy has it been to make time to rest?",
    options: [
      "Very easy",
      "Fairly easy",
      "A little difficult",
      "Very difficult",
    ],
  },
  {
    text: "How manageable does today feel?",
    options: [
      "Very manageable",
      "Mostly manageable",
      "A little difficult",
      "Very difficult",
    ],
  },
];

const form = document.querySelector("#TakeTest-form");
const question = form.querySelector(".question");
const nextButton = document.querySelector("#next-question");
const counter = document.querySelector(".question-number");
const progress = document.querySelector(".progress");
const progressFill = document.querySelector(".progress-fill");
let currentQuestion = 0;

function renderQuestion() {
  const item = questions[currentQuestion];
  const legend = document.createElement("legend");
  legend.textContent = item.text;
  legend.tabIndex = -1;
  question.replaceChildren(legend);

  item.options.forEach((option, index) => {
    const label = document.createElement("label");
    label.className = "answer";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "answer";
    input.value = String(index);
    const text = document.createElement("span");
    text.textContent = option;
    label.append(input, text);
    question.append(label);
  });

  counter.textContent = `Question ${currentQuestion + 1} of ${questions.length}`;
  progress.setAttribute("aria-valuenow", String(currentQuestion + 1));
  progressFill.style.width = `${((currentQuestion + 1) / questions.length) * 100}%`;
  nextButton.textContent =
    currentQuestion === questions.length - 1 ? "Finish" : "Next";
  nextButton.disabled = true;
  legend.focus();
}

form.addEventListener("change", () => {
  nextButton.disabled = !question.querySelector("input:checked");
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!question.querySelector("input:checked")) return;

  if (currentQuestion < questions.length - 1) {
    currentQuestion += 1;
    renderQuestion();
    return;
  }

  form.hidden = true;
  counter.hidden = true;
  document.querySelector("#question-help").hidden = true;
  document.querySelector("#TakeTest-complete").hidden = false;
  document.querySelector("#complete-title").focus();
});
