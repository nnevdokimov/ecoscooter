function sendMessage(appealId) {
    var messageText = document.getElementById('message-text').value;
    if (messageText.trim()) {
        fetch(`/send_message/${appealId}`, {
            method: 'POST',
            body: JSON.stringify({ message: messageText }),
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Вывод всплывающего окна с подтверждением
                alert('Сообщение успешно отправлено!');
                // Перенаправление на страницу со списком обращений
                window.location.href = '/';
            }
        })
        .catch(error => {
            console.error('Ошибка: ', error);
            alert('Произошла ошибка при отправке сообщения.');
        });
    }
}

function addPromocode(appealId) {
    // Отключаем кнопку, чтобы предотвратить повторное нажатие
    var promoButton = document.getElementById('add-promo-button');
    promoButton.disabled = true;
    promoButton.textContent = 'Добавление...';

    fetch(`/add_promocode/${appealId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Информируем пользователя о добавлении промокода
            var promoInfo = document.createElement('div');
            promoInfo.textContent = 'Промокод добавлен: ' + data.promo_code;
            document.querySelector('.promo-container').appendChild(promoInfo);

            // Делаем кнопку серой и неактивной
            promoButton.style.backgroundColor = '#ccc';
            promoButton.style.color = '#666';
            promoButton.textContent = 'Промокод добавлен';
        } else {
            // В случае ошибки снова активируем кнопку
            promoButton.disabled = false;
            promoButton.textContent = 'Добавить промокод';
            alert('Произошла ошибка при добавлении промокода.');
        }
    })
    .catch(error => {
        console.error('Ошибка: ', error);
        alert('Ошибка при выполнении запроса.');
        // В случае ошибки запроса снова активируем кнопку
        promoButton.disabled = false;
        promoButton.textContent = 'Добавить промокод';
    });
}

