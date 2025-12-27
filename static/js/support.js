(function () {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }

    const oneTimeBtn = document.getElementById('supportTypeOneTime');
    const monthlyBtn = document.getElementById('supportTypeMonthly');
    const currencyEl = document.getElementById('supportCurrency');
    const amountEl = document.getElementById('supportAmount');
    const checkoutBtn = document.getElementById('supportCheckoutBtn');
    const errorEl = document.getElementById('supportError');
    const minHintEl = document.getElementById('supportMinHint');

    if (!oneTimeBtn || !monthlyBtn || !currencyEl || !amountEl || !checkoutBtn || !errorEl || !minHintEl) {
        return;
    }

    let supportType = 'one_time';

    function setSupportType(type) {
        supportType = type;
        const activeClasses = [
            'bg-blue-50',
            'text-blue-700',
            'border-blue-400',
            'ring-2',
            'ring-blue-400',
            'shadow-sm',
            'dark:bg-blue-900/30',
            'dark:text-blue-200',
            'dark:border-blue-500',
            'dark:ring-blue-500'
        ];
        const inactiveClasses = [
            'bg-white',
            'text-gray-900',
            'border-gray-300',
            'dark:bg-gray-800',
            'dark:text-gray-100',
            'dark:border-gray-600'
        ];

        if (type === 'one_time') {
            oneTimeBtn.classList.remove(...inactiveClasses);
            oneTimeBtn.classList.add(...activeClasses);
            monthlyBtn.classList.remove(...activeClasses);
            monthlyBtn.classList.add(...inactiveClasses);
        } else {
            monthlyBtn.classList.remove(...inactiveClasses);
            monthlyBtn.classList.add(...activeClasses);
            oneTimeBtn.classList.remove(...activeClasses);
            oneTimeBtn.classList.add(...inactiveClasses);
        }
    }

    function minAmount(currency) {
        if (currency === 'pln') return 5;
        if (currency === 'eur') return 1;
        if (currency === 'usd') return 1;
        return 1;
    }

    function updateMinHint() {
        const currency = currencyEl.value;
        const min = minAmount(currency);
        minHintEl.textContent = `Minimum: ${min} ${currency.toUpperCase()}`;
    }

    function showError(msg) {
        errorEl.textContent = msg;
        errorEl.classList.remove('hidden');
    }

    function hideError() {
        errorEl.textContent = '';
        errorEl.classList.add('hidden');
    }

    oneTimeBtn.addEventListener('click', function () {
        setSupportType('one_time');
    });

    monthlyBtn.addEventListener('click', function () {
        setSupportType('monthly');
    });

    currencyEl.addEventListener('change', function () {
        updateMinHint();
    });

    setSupportType('one_time');
    try {
        currencyEl.value = 'usd';
    } catch (e) {
    }
    updateMinHint();

    checkoutBtn.addEventListener('click', async function () {
        hideError();

        const currency = currencyEl.value;
        const amount = Number(amountEl.value);
        const min = minAmount(currency);

        if (!amount || Number.isNaN(amount) || amount <= 0) {
            showError('Please enter a valid amount');
            return;
        }

        if (amount < min) {
            showError(`Minimum amount is ${min} ${currency.toUpperCase()}`);
            return;
        }

        const csrf = getCookie('csrftoken');
        if (!csrf) {
            showError('CSRF token not found. Please refresh the page.');
            return;
        }

        checkoutBtn.disabled = true;
        const originalText = checkoutBtn.textContent;
        checkoutBtn.textContent = 'Redirecting...';

        try {
            const resp = await fetch(window.SUPPORT_CHECKOUT_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf
                },
                body: JSON.stringify({
                    support_type: supportType,
                    currency: currency,
                    amount: amount
                })
            });

            const data = await resp.json();
            if (!resp.ok) {
                showError(data && data.error ? data.error : 'Failed to create checkout session');
                return;
            }

            if (!data.checkout_url) {
                showError('No checkout URL returned');
                return;
            }

            window.location.href = data.checkout_url;
        } catch (e) {
            showError('Request failed. Please try again.');
        } finally {
            checkoutBtn.disabled = false;
            checkoutBtn.textContent = originalText;
        }
    });
})();
