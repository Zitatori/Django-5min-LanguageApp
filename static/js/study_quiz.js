document.querySelectorAll('.study-quiz').forEach(function (quiz) {
  quiz.addEventListener('change', function (event) {
    if (!event.target.matches('input[type="radio"]')) return;
    quiz.querySelector('.quiz-result').textContent = event.target.value === quiz.dataset.correct ? quiz.dataset.right : quiz.dataset.wrong;
    quiz.querySelector('.quiz-feedback').hidden = false;
  });
});
