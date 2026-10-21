# PAHUWAY

Open `index.html` in a browser. No installation or server is needed.

All pages load shared styles from `styling/common.css` and their own page stylesheet in `styling/`. Navigation filenames follow the home page navigation:

- `index.html`: home
- `TakeTest.html`: eight-question TakeTest with a green Next button; question one follows the screenshot and the remaining questions are sample content
- `results.html`: empty results page (no reference screenshot was supplied)
- `tips.html`: wellness tips
- `sign-in.html`: sign-in screen
- `sign-up.html`: create-account screen
- `forgot-password.html`: password reset preview

This is a responsive HTML/CSS recreation with no external fonts or dependencies. The separate `TakeTest.js` file handles question progression, requires an answer before enabling Next, updates the progress bar, and shows a completion message after Finish. Answers are not saved or scored. Navigation and radio selection work. Account buttons are visual previews; authentication, email, result calculation, and storage are not implemented. Text describing those services is reproduced from the reference design and does not represent connected functionality. The Lovable editor overlay is omitted.
