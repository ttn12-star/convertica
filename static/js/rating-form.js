/**
 * Tool rating form. Rendered under the download button after a successful
 * operation. Unobtrusive: never blocks downloading. 1-3 stars require a comment.
 */
(function () {
    'use strict';

    function alreadyRated(token) {
        try { return sessionStorage.getItem('rated:' + token) === '1'; }
        catch (e) { return false; }
    }
    function markRated(token) {
        try { sessionStorage.setItem('rated:' + token, '1'); } catch (e) {}
    }

    window.renderRatingForm = function (container, token, toolSlug) {
        if (!container || !token || alreadyRated(token)) return;
        if (container.querySelector('#ratingForm')) return;

        const wrap = document.createElement('div');
        wrap.id = 'ratingForm';
        wrap.className = 'mt-5 pt-5 border-t border-gray-200 dark:border-gray-700 text-center';
        wrap.innerHTML =
            '<p class="text-sm font-semibold text-gray-800 dark:text-gray-100">'
                + (window.RATING_PROMPT || 'How was the result?') + '</p>'
            + '<p class="text-xs text-gray-500 dark:text-gray-400 mb-3">'
                + (window.RATING_SUBPROMPT || '') + '</p>'
            + '<div id="ratingStars" class="flex justify-center gap-1 mb-3" role="radiogroup" aria-label="'
                + (window.RATING_PROMPT || 'Rate') + '">'
            + [1, 2, 3, 4, 5].map(function (n) {
                return '<button type="button" data-star="' + n + '" role="radio" aria-checked="false" '
                    + 'class="rating-star text-3xl leading-none text-gray-300 dark:text-gray-600 '
                    + 'hover:text-yellow-400 transition-colors" aria-label="' + n + '">★</button>';
            }).join('')
            + '</div>'
            + '<div id="ratingCommentWrap" class="hidden">'
                + '<textarea id="ratingComment" rows="3" maxlength="1000" '
                + 'class="w-full rounded-lg border border-gray-300 dark:border-gray-600 '
                + 'dark:bg-gray-800 dark:text-gray-100 p-2 text-sm" placeholder=""></textarea>'
            + '</div>'
            + '<div id="ratingActions" class="hidden mt-3">'
                + '<button type="button" id="ratingSubmit" '
                + 'class="px-6 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold '
                + 'hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">'
                + (window.RATING_SUBMIT || 'Submit feedback') + '</button>'
            + '</div>'
            + '<p id="ratingThanks" class="hidden text-sm font-semibold text-green-600 dark:text-green-400"></p>';
        container.appendChild(wrap);

        let selected = 0;
        const stars = wrap.querySelectorAll('.rating-star');
        const commentWrap = wrap.querySelector('#ratingCommentWrap');
        const comment = wrap.querySelector('#ratingComment');
        const actions = wrap.querySelector('#ratingActions');
        const submit = wrap.querySelector('#ratingSubmit');

        function paint() {
            stars.forEach(function (s) {
                const n = parseInt(s.getAttribute('data-star'), 10);
                s.classList.toggle('text-yellow-400', n <= selected);
                s.classList.toggle('text-gray-300', n > selected);
                s.classList.toggle('dark:text-gray-600', n > selected);
                s.setAttribute('aria-checked', n === selected ? 'true' : 'false');
            });
        }
        function refreshSubmitState() {
            const needComment = selected > 0 && selected <= 3;
            const ok = selected > 0 && (!needComment || comment.value.trim().length > 0);
            submit.disabled = !ok;
        }
        stars.forEach(function (s) {
            s.addEventListener('click', function () {
                selected = parseInt(s.getAttribute('data-star'), 10);
                paint();
                const low = selected <= 3;
                commentWrap.classList.remove('hidden');
                comment.placeholder = low
                    ? (window.RATING_COMMENT_BAD || 'What went wrong?')
                    : (window.RATING_COMMENT_GOOD || 'What did you like? (optional)');
                actions.classList.remove('hidden');
                refreshSubmitState();
            });
        });
        comment.addEventListener('input', refreshSubmitState);

        submit.addEventListener('click', function () {
            submit.disabled = true;
            fetch(window.RATING_API_URL || '/api/v1/feedback/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN || '' },
                body: JSON.stringify({ feedback_token: token, rating: selected, comment: comment.value.trim() }),
            }).then(function () {
                markRated(token);
                wrap.querySelector('#ratingStars').classList.add('hidden');
                commentWrap.classList.add('hidden');
                actions.classList.add('hidden');
                const thanks = wrap.querySelector('#ratingThanks');
                thanks.textContent = window.RATING_THANKS || 'Thank you for your feedback!';
                thanks.classList.remove('hidden');
            }).catch(function () {
                submit.disabled = false;
            });
        });
    };
})();
