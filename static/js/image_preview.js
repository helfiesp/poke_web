
document.addEventListener('DOMContentLoaded', function() {
    const previewContainer = document.getElementById('image-preview-container');
    const fileInput = document.getElementById('id_images');
    let dragSrcEl = null;
    let currentEditingId = null; 
    const existingPreviews = previewContainer.querySelectorAll('.image-preview');


    // Function to update the order of images
    function updateImageOrder() {
        const imagePreviews = previewContainer.querySelectorAll('.image-preview');
        imagePreviews.forEach((preview, index) => {
            let orderInput = preview.querySelector('.image-order');
            if (!orderInput) {
                orderInput = document.createElement('input');
                orderInput.type = 'hidden';
                orderInput.classList.add('image-order');
                orderInput.name = 'image_order';
                preview.appendChild(orderInput);
            }
            orderInput.value = index;
        });

    }
    function handleDragStart(e) {
        dragSrcEl = this;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', null); // for Firefox compatibility
        this.classList.add('dragging');
    }

    function handleDragOver(e) {
        e.preventDefault(); // Necessary for allowing a drop.
        e.dataTransfer.dropEffect = 'move';
    }

    function handleDragEnter(e) {
        this.classList.add('over');
    }

    function handleDragLeave(e) {
        this.classList.remove('over');
    }

    function handleDrop(e) {
        e.preventDefault();
        if (dragSrcEl !== this) {
            previewContainer.insertBefore(dragSrcEl, this);
            updateImageOrder();
        }
        this.classList.remove('over');
    }

    function handleDragEnd(e) {
        this.classList.remove('dragging');
        let images = previewContainer.querySelectorAll('.image-preview');
        images.forEach(function (img) {
            img.classList.remove('over');
        });
    }

    function enableDragAndDropForImages() {
        let images = previewContainer.querySelectorAll('.image-preview');
        images.forEach(function(img) {
            img.setAttribute('draggable', true);
            img.addEventListener('dragstart', handleDragStart, false);
            img.addEventListener('dragenter', handleDragEnter, false);
            img.addEventListener('dragover', handleDragOver, false);
            img.addEventListener('dragleave', handleDragLeave, false);
            img.addEventListener('drop', handleDrop, false);
            img.addEventListener('dragend', handleDragEnd, false);
        });
    }

// Function to append buttons to the previewWrapper

// Function to append overlays to the previewWrapper
function appendOverlaysToPreview(previewWrapper, file, imageId) { 
    const overlayLeft = document.createElement('div');
    overlayLeft.classList.add('overlay', 'overlay-left');
    overlayLeft.addEventListener('click', function() {
        const prev = previewWrapper.previousElementSibling;
        if (prev) {
            previewContainer.insertBefore(previewWrapper, prev);
            updateImageOrder();
        }
    });

    const overlayRight = document.createElement('div');
    overlayRight.classList.add('overlay', 'overlay-right');
    overlayRight.addEventListener('click', function() {
        const next = previewWrapper.nextElementSibling;
        if (next) {
            previewContainer.insertBefore(next, previewWrapper);
            updateImageOrder();
        }
    });

    const removeButton = createRemoveButton(previewWrapper);

    previewWrapper.appendChild(overlayLeft);
    previewWrapper.appendChild(overlayRight);
    previewWrapper.appendChild(removeButton);

}

function createRemoveButton(previewWrapper) {
    const removeButton = document.createElement('button');
    removeButton.textContent = 'X';
    removeButton.classList.add('remove-image');
    removeButton.addEventListener('click', function() {
        previewWrapper.remove();
        updateImageOrder();
    });
    return removeButton;
}

    // Function to handle new image file input
    fileInput.addEventListener('change', function() {
        Array.from(this.files).forEach((file, index) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                const previewWrapper = document.createElement('div');
                previewWrapper.classList.add('image-preview');
                const img = document.createElement('img');
                img.src = e.target.result;
                img.setAttribute('data-filename', file.name);
                appendOverlaysToPreview(previewWrapper, file);

                const orderInput = document.createElement('input');
                orderInput.type = 'hidden';
                orderInput.classList.add('image-order');
                orderInput.name = 'image_order';
                orderInput.value = index;

                previewWrapper.appendChild(img);
                previewWrapper.appendChild(orderInput);
                previewContainer.appendChild(previewWrapper);

                enableDragAndDropForImages();

                updateImageOrder();

            };
            reader.readAsDataURL(file);
        });
    });

    // Initialize functionality for existing image previews (if any)
    existingPreviews.forEach(function(previewWrapper) {
        const imageId = previewWrapper.dataset.imageId; // Assuming data-image-id attribute is set
        appendOverlaysToPreview(previewWrapper, null, imageId);
        enableDragAndDropForImages(); // Call to enable DnD for existing images
    });

    updateImageOrder(); // Initial call to ensure existing images are correctly ordered
});


document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('product-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(form); // Initialize FormData with the form itself


        // Handling file inputs for new images
        const fileInput = document.getElementById('id_images');
        Array.from(fileInput.files).forEach((file, index) => {
            formData.append('images', file, file.name);
        });

        // Preparing the image_order_combined JSON string
        let imageOrderCombined = [];
        document.querySelectorAll('.image-preview').forEach((preview, index) => {
            const img = preview.querySelector('img');
            const filename = img.getAttribute('data-filename');
            const id = preview.getAttribute('data-image-id'); // Assuming existing images have this attribute

            const imageInfo = { filename: filename, order: index };
            if (id) {
                imageInfo.id = id;
            }
            imageOrderCombined.push(imageInfo);
        });

        // Append the image_order_combined as a JSON string
        formData.append('image_order_combined', JSON.stringify(imageOrderCombined));

        // Handling image text inputs for new images
        document.querySelectorAll('.image-preview').forEach((preview, index) => {
            const img = preview.querySelector('img');
            const filename = img.getAttribute('data-filename'); // Use the image's filename to associate text
            const imageId = preview.getAttribute('data-image-id') || filename; // Use data-image-id if available, otherwise use filename
        }); // It seems like you have an unfinished code block here, please ensure it's completed or removed if not necessary

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            // Always check if the response is ok (status 200-299)
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();  // Now we can safely parse the response as JSON
        })
        .then(data => {
            if (data.success) {
                // Redirect to the given URL
                window.location.href = data.redirect_url;
            } else {
                // Handle errors here
                console.error('Form errors:', data.errors);
            }
        })
        .catch(error => {
            // Handle any errors that fell through
            console.error('Error:', error);
        });

        function updateFileList(fileInput, fileToRemove) {
            const dt = new DataTransfer();
            Array.from(fileInput.files).forEach(file => {
                if (file !== fileToRemove) {
                    dt.items.add(file);
                }
            });
            fileInput.files = dt.files;
        }

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

    }); // This was correctly placed, ending the 'submit' event listener
}); // This was correctly placed, ending the 'DOMContentLoaded' event listener