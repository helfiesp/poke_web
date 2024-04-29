// Reuse the generateCartItemHtml function for both cart and checkout displays
function generateCartItemHtml(item) {
    let priceHtml = '';
    let itemNormalPrice = item.normal_price;
    let itemSalePrice = item.sale_price;

    if (item.sale_price && item.sale_price < item.normal_price) {
        priceHtml = `<p class="cart-item-price">
                        <span class="sale-price">${itemSalePrice.toFixed(2)} kr</span>
                        <span class="normal-price struck">${itemNormalPrice.toFixed(2)} kr</span>
                     </p>`;
    } else {
        priceHtml = `<p class="cart-item-price">${itemNormalPrice.toFixed(2)} kr</p>`;
    }

    return `
    <div class="cart-item" data-product-id="${item.id}">
        <div class="cart-item-image">
            <img src="${item.image_url}" alt="${item.title}">
        </div>
        <div class="cart-item-info">
            <p class="cart-item-title">${item.title}</p>
            ${priceHtml}
        </div>
        <div class="cart-item-quantity">
            <button class="quantity-btn remove" data-product-id="${item.id}" data-action="remove">-</button>
            <span class="quantity-text">${item.quantity}</span>
            <button class="quantity-btn add" data-product-id="${item.id}" data-action="add">+</button>
        </div>
        <button class="remove-item" data-product-id="${item.id}">Fjern</button>
        <input type="hidden" name="item_id[]" value="${item.id}">
        <input type="hidden" name="item_quantity[]" value="${item.quantity}">
        <input type="hidden" name="item_price[]" value="${itemNormalPrice}">
        <input type="hidden" name="item_sale_price[]" value="${itemSalePrice || ''}">
    </div>`;
}

document.addEventListener('DOMContentLoaded', function() {
    // Refresh the checkout display and then execute further actions in a callback
    refreshCheckoutDisplay(() => {
        const totalPriceElement = document.querySelector('.summary-totals .total .price');
        let initialTotalPrice = parseFloat(totalPriceElement.textContent.replace('NOK kr ', '')) || 0;
        const orderSummarySection = document.querySelector('.order-summary-section');
        if (orderSummarySection) {
            orderSummarySection.addEventListener('click', function(event) {
                const target = event.target;
                if (target.classList.contains('quantity-btn') || target.classList.contains('remove-item')) {
                    const productId = target.dataset.productId;
                    const action = target.dataset.action || 'remove';
                    const removeAll = target.classList.contains('remove-item');
                    updateCartItem(productId, action, removeAll);
                    event.preventDefault();
                }
            });
        } else {
            console.error('Order summary section not found');
        }

        console.log(initialTotalPrice)
        document.querySelectorAll('input[name="shipping_option"]').forEach(option => {
            option.addEventListener('change', function() {
                updateTotalPriceDisplay(initialTotalPrice);
            });
        });

        const deliveryRadioButton = document.getElementById('delivery');
        const pickupRadioButton = document.getElementById('pickup');

        deliveryRadioButton.addEventListener('change', function() {
            toggleDeliveryOptions(this.checked);
        });

        pickupRadioButton.addEventListener('change', function() {
            toggleDeliveryOptions(!this.checked);
        });

        });
});

function refreshCheckoutDisplay(callback) {
    fetch('/get-cart-data/')
    .then(response => response.json())
    .then(data => {
        const orderSummarySection = document.querySelector('.order-summary-section');
        if (orderSummarySection) {
            let itemContainers = orderSummarySection.querySelectorAll('.cart-item');
            itemContainers.forEach(itemContainer => itemContainer.remove());
            data.cart_items.forEach(item => {
                orderSummarySection.innerHTML += generateCartItemHtml(item);
            });
            if(data.total_price !== undefined) {
                updateTotalPriceDisplay(data.total_price);
            } else {
                console.error('Total price data missing');
                updateTotalPriceDisplay(0);
            }
            // Call the callback after everything has been updated
            if (callback) callback();
        } else {
            console.error('Order summary section element is missing');
        }
    })
    .catch(error => {
        console.error('Error fetching cart data:', error);
    });
}

function updateTotalPriceDisplay(totalPrice) {
    const totalPriceElement = document.querySelector('.summary-totals .total .price');
    if (totalPriceElement && totalPrice !== undefined) {
        totalPriceElement.textContent = `NOK kr ${totalPrice.toFixed(2)}`;
        updateShippingDisplay(totalPrice);
    } else {
        console.error('Total price element not found or totalPrice is undefined');
    }
}

function updateCartItem(productId, action, removeAll = false) {
    let bodyData = { 'action': action, 'remove_all': removeAll };
    fetch('/update-cart/' + productId + '/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify(bodyData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            refreshCheckoutDisplay(); // Refresh the display to reflect changes
        }
    })
    .catch(error => console.error('Error updating cart item:', error));
}

function fetchTotalPrice() {
    // Returns a promise that resolves to the total price
    return fetch('/get-cart-data/')
    .then(response => response.json())
    .then(data => {
        if(data.total_price !== undefined) {
            return data.total_price; // Return the total price so it can be used in another function
        } else {
            console.error('Total price data missing');
            return 0; // Return 0 if the total price is not defined
        }
    })
    .catch(error => {
        console.error('Error fetching cart data:', error);
        return 0; // Return 0 in case of an error
    });
}

function toggleDeliveryOptions(isDelivery) {
    const shippingOptions = document.getElementById('shipping-options');
    const pickupAddress = document.getElementById('pickup-address');
    shippingOptions.style.display = isDelivery ? 'block' : 'none';
    pickupAddress.style.display = isDelivery ? 'none' : 'block';
}


function updateShippingDisplay() {
    // Fetch the latest total price first
    fetchTotalPrice().then(totalPrice => {
        const totalPriceElement = document.querySelector('.summary-totals .total .price');
        const shippingOptions = document.querySelectorAll('input[name="shipping_option"]');
        const shippingCostDisplay = document.querySelector('.summary-totals .shipping .price');

        // Update the total price display to reflect the latest total
        totalPriceElement.textContent = `NOK kr ${totalPrice.toFixed(2)}`;
        
        shippingOptions.forEach(option => {
            const priceElement = option.nextElementSibling.querySelector('.radio-label-text');
            const price = parseFloat(option.dataset.price || 0);
            const freeShippingLimit = parseFloat(option.dataset.freeShippingLimit || Infinity);
            
            if (totalPrice >= freeShippingLimit) {
                priceElement.textContent = 'GRATIS';
            } else {
                priceElement.textContent = `${price.toFixed(2)} kr`;
            }
        });

        const selectedShippingOption = document.querySelector('input[name="shipping_option"]:checked');
        if (selectedShippingOption) {
            const selectedPriceText = selectedShippingOption.nextElementSibling.querySelector('.radio-label-text').textContent;
            shippingCostDisplay.textContent = selectedPriceText;
            
            // Recalculate the new total with the latest total price and the current shipping cost
            const shippingCost = selectedPriceText === 'GRATIS' ? 0 : parseFloat(selectedPriceText.replace(' kr', ''));
            const newTotalPrice = totalPrice + shippingCost; // Use the latest fetched total price
            totalPriceElement.textContent = `NOK kr ${newTotalPrice.toFixed(2)}`;
        }
    }).catch(error => {
        console.error('Error updating shipping display:', error);
    });
}

function getSelectedShippingCost() {
    const selectedShippingOption = document.querySelector('input[name="shipping_option"]:checked + label .radio-label-text');
    return selectedShippingOption ? selectedShippingOption.textContent : 'Fraktalternativ ikke valgt';
}

