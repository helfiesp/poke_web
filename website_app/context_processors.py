from . import models

def base_info(request):
    products = models.product.objects.all().order_by('-date_added')
    categories = models.category.objects.all()
    text_areas = models.text_areas.objects.first()
    footer_textareas = models.footer_textareas.objects.first()
    business_information = models.business_information.objects.first()
    recent_products = models.product.objects.filter(enabled=True).order_by('-date_added')[:8]
    bestsellers = models.product.objects.filter(enabled=True, bestseller=True).order_by('-date_added')[:8]

    # New variable that filters specific categories
    front_categories = models.category.objects.filter(name__in=['pokemon', 'japansk', 'engelsk'])

    return {
        'all_products': products,
        'all_categories': categories,
        'text_areas_all': text_areas,
        'footer_textareas': footer_textareas,
        'business_information': business_information,
        'recent_products': recent_products,
        'bestsellers': bestsellers,
        'front_categories': front_categories,  # Add to the return dictionary
    }


def cart_context(request):
    cart = request.session.get('cart', {})
    product_ids = [int(pid) for pid in cart.keys()]
    products = models.product.objects.filter(id__in=product_ids)
    cart_items = []
    total_price = 0

    for product in products:
        current_price = product.sale_price if product.sale_price is not None else product.price
        # Fetch the first image based on the order or just the first available
        first_image = product.images.order_by('order').first()
        image_url = first_image.image.url if first_image else None
        item = {
            'string_id': product.string_id,
            'id': product.id,
            'title': product.title,
            'subtitle': product.subtitle,
            'normal_price': product.price,
            'sale_price': product.sale_price,
            'price': current_price,
            'quantity': cart[str(product.id)],
            'total_item_price': current_price * cart[str(product.id)],
            'image_url': image_url,
        }
        cart_items.append(item)
        total_price += item['total_item_price']

    return {
        'cart_items': cart_items,
        'total_price': total_price
    }