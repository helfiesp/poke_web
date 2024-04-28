// Reuse the generateCartItemHtml function for both cart and checkout displays
function generateCartItemHtml(item) {
    let priceHtml = '';
    // Use the individual prices without multiplying by quantity
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
    refreshCheckoutDisplay();

    // Reference the order summary section where products are displayed
    const orderSummarySection = document.querySelector('.order-summary-section');
    if (orderSummarySection) {
        orderSummarySection.addEventListener('click', function(event) {
            const target = event.target;
            // Check if the clicked element is a quantity button or remove item button
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
});

function refreshCheckoutDisplay() {
    fetch('/get-cart-data/')
        .then(response => response.json())
        .then(data => {
            const orderSummarySection = document.querySelector('.order-summary-section');
            if (orderSummarySection) {
                // Clear existing items, but not the summary totals
                let itemContainers = orderSummarySection.querySelectorAll('.cart-item');
                itemContainers.forEach(itemContainer => itemContainer.remove());

                data.cart_items.forEach(item => {
                    // Append HTML for each cart item
                    orderSummarySection.innerHTML += generateCartItemHtml(item);
                });

                // Update the displayed total price
                updateTotalPriceDisplay(data.total_price);
            } else {
                console.error('Order summary section element is missing');
            }
        })
        .catch(error => console.error('Error fetching cart data:', error));
}

function updateTotalPriceDisplay(totalPrice) {
    const totalPriceElement = document.querySelector('.summary-totals .total .price');
    if (totalPriceElement) {
        totalPriceElement.textContent = `NOK kr ${totalPrice}`;
    } else {
        console.error('Total price element not found');
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


// Function to toggle the display of delivery and pickup options
function toggleDeliveryOptions(isDelivery) {
    // Select the shipping options and pickup address div elements
    var shippingOptions = document.getElementById('shipping-options');
    var pickupAddress = document.getElementById('pickup-address');

    // Display the appropriate div based on the selected delivery option
    if (isDelivery) {
        shippingOptions.style.display = 'block'; // Show shipping options for delivery
        pickupAddress.style.display = 'none'; // Hide pickup address for delivery
    } else {
        shippingOptions.style.display = 'none'; // Hide shipping options for pickup
        pickupAddress.style.display = 'block'; // Show pickup address for pickup
    }
}

// Add event listeners to radio buttons for when they change
document.addEventListener('DOMContentLoaded', function() {
    var deliveryRadioButton = document.getElementById('delivery');
    var pickupRadioButton = document.getElementById('pickup');
    
    deliveryRadioButton.addEventListener('change', function() {
        toggleDeliveryOptions(this.checked);
    });
    
    pickupRadioButton.addEventListener('change', function() {
        toggleDeliveryOptions(!this.checked);
    });
});