function generateCartItemHtml(item) {
    let priceHtml = '';
    let itemTotalPrice = item.price * item.quantity;
    let itemTotalNormalPrice = item.normal_price * item.quantity;
    let itemTotalSalePrice = item.sale_price ? item.sale_price * item.quantity : null;

    // Check if there is a sale price
    if (item.sale_price && item.sale_price < item.normal_price) {
        // Sale price exists and is less than normal price, so display both with normal price struck through
        priceHtml = `<p class="cart-item-price">
                        <span class="sale-price">${itemTotalSalePrice.toFixed(2)} kr</span>
                        <span class="normal-price struck">${itemTotalNormalPrice.toFixed(2)}</span>
                     </p>`;
    } else {
        // No sale price, so just display normal price
        priceHtml = `<p class="cart-item-price">
                        ${itemTotalNormalPrice.toFixed(2)} kr
                     </p>`;
    }

    return `
    <div class="cart-item" data-product-id="${item.id}">
        <div class="cart-item-image">
            <img src="${item.image_url}" alt="${item.title}">
        </div>
        <div class="cart-item-info">
            <p class="cart-item-title">${item.title}</p>
            ${priceHtml} <!-- Insert the price HTML here -->
        </div>
        <div class="cart-item-quantity">
            <button class="quantity-btn remove" data-product-id="${item.id}" data-action="remove">-</button>
            <span class="quantity-text" data-product-id="${item.id}">${item.quantity}</span>
            <button class="quantity-btn add" data-product-id="${item.id}" data-action="add">+</button>
        </div>
        <button class="remove-item" data-product-id="${item.id}">Fjern</button>
    </div>
    `;
}



function refreshCartDisplay() {
    fetch('/get-cart-data/')
        .then(response => response.json())
        .then(data => {
            const cartContainer = document.querySelector('.cart-items');
            const cartFooter = document.querySelector('.cart-footer'); // Select the cart footer to show/hide
            cartContainer.innerHTML = ''; // Clear current cart contents

            let totalItems = 0; // Initialize total items count
            if (data.cart_items.length > 0) {
                data.cart_items.forEach(item => {
                    cartContainer.innerHTML += generateCartItemHtml(item);
                    totalItems += item.quantity; // Sum up total items
                });
                document.querySelector('span.total-price').textContent = data.total_price + ' NOK';
                cartFooter.style.display = 'block'; // Show footer if items are present
            } else {
                cartContainer.innerHTML = '<p>Det er ingen varer i handlekurven.</p>'; // Display message if no items
                document.querySelector('span.total-price').textContent = '0 NOK'; // Set total price to 0
                cartFooter.style.display = 'none'; // Hide footer if no items
            }

            // Update cart item count display
            const cartCountSpan = document.querySelector('.cart-count');
            if (totalItems > 0) {
                cartCountSpan.style.display = 'block';
                cartCountSpan.textContent = totalItems; // Display total number of items
            } else {
                cartCountSpan.style.display = 'none'; // Hide if no items
                const closeCartBtn = document.getElementById('close-cart-btn');
                if (closeCartBtn) {
                    closeCartBtn.click(); // Close the cart automatically
                }
            }
        })
        .catch(error => console.error('Error fetching cart data:', error));
}
function updateCartItem(productId, action, removeAll=false) {
    let bodyData = { 'action': action };

    // Determine if the action is to completely remove the item
    if (removeAll) {
        bodyData['remove_all'] = true;  // Tell the server to remove the item entirely
    }

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
            refreshCartDisplay(); // Refresh the cart to reflect changes
        }
    })
    .catch(error => {
        console.error('Error updating cart item:', error);
    });
}


document.addEventListener('DOMContentLoaded', function() {
    refreshCartDisplay();

    // Fetching elements for event handling
    const cartIcon = document.getElementById('cart-icon');
    const cartOverlay = document.getElementById('cart-overlay');

    // Function to toggle the visibility of the cart overlay
    function toggleCart() {
        if (cartOverlay.style.display === 'block') {
            cartOverlay.style.display = 'none';
        } else {
            cartOverlay.style.display = 'block';
        }
    }

// Update event listeners for the 'Remove' button
const cartContainer = document.querySelector('.cart'); // Stable parent container
cartContainer.addEventListener('click', function(event) {
    const target = event.target;
    if (target.classList.contains('quantity-btn')) {
        const productId = target.dataset.productId;
        const action = target.dataset.action; // 'add' or 'remove' for quantity adjustment
        updateCartItem(productId, action);
        event.preventDefault();
    } else if (target.classList.contains('remove-item')) {
        const productId = target.dataset.productId;
        updateCartItem(productId, 'remove', true); // Pass true to indicate complete removal
        event.preventDefault();
    }
});
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            fetch(this.action, {
                method: 'POST',
                body: new FormData(this),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.querySelector('[name=csrfmiddlewaretoken]').value,
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    refreshCartDisplay(); // Refresh the entire cart display after adding an item
                }
            })
            .catch(error => {
                console.error('Error adding item to cart:', error);
            });
        });
    });

    var cartBtn = document.querySelector('.account-icon img[src$="shopping-cart.png"]');
    var closeCartBtn = document.getElementById('close-cart-btn');

    function toggleCart() {
        if (cartOverlay.classList.contains('show')) {
            cartOverlay.classList.remove('show');
            document.querySelector('.cart').classList.remove('show');
            setTimeout(function() {
                cartOverlay.style.display = 'none';
                document.querySelector('.cart').style.display = 'none';
            }, 500); // matches CSS transition-duration
        } else {
            cartOverlay.style.display = 'block';
            document.querySelector('.cart').style.display = 'block';
            cartOverlay.classList.add('show');
            document.querySelector('.cart').classList.add('show');
        }
    }

    function closeCart(event) {
        if (event.target === cartOverlay || event.target === closeCartBtn || event.target.classList.contains('close-cart-btn')) {
            cartOverlay.classList.remove('show');
            document.querySelector('.cart').classList.remove('show');
        }
    }

    if (cartBtn) {
        cartBtn.addEventListener('click', toggleCart);
    }

    if (closeCartBtn) {
        closeCartBtn.addEventListener('click', closeCart);
    }

    window.addEventListener('click', closeCart);
});
