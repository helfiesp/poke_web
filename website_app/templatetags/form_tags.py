from django import template
from django.forms.widgets import Widget
from django.urls import reverse
from website_app.models import product, category
from django.shortcuts import render, get_object_or_404


register = template.Library()

@register.filter
def get_category_count(category_name):
    if not category_name:
        return 0
    try:
        category_obj = category.objects.get(name__iexact=category_name)  # Case-insensitive match
        return product.objects.filter(category=category_obj, enabled=True).count()
    except category.DoesNotExist:
        return 0

@register.filter
def fetch_category_id(category_name):
    if not category_name:
        return 0
    try:
        category_obj = category.objects.get(name__iexact=category_name)  # Case-insensitive match
        return category_obj.id
    except category.DoesNotExist:
        return 0

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except Exception:
            return ''

@register.filter
def tostring(text):
    return str(text)


@register.simple_tag
def get_category_breadcrumbs(category):
    breadcrumbs = []
    while category is not None:
        breadcrumbs.insert(0, category)
        category = category.parent
    return breadcrumbs

@register.filter(name='stock_url')
def stock_url(value):
    return "http://schema.org/InStock" if value > 0 else "http://schema.org/OutOfStock"


@register.filter
def fetch_item(item):
    item = get_object_or_404(product, pk=item)
    return item

@register.filter
def fetch_item_name(item):
    item = get_object_or_404(product, pk=item)
    return item.title

@register.filter
def fetch_item_image(item):
    item = get_object_or_404(product, pk=item)
    try:
        # Assuming the item model has a related field 'images' which can be accessed directly
        return item.images.all()[0].image.url
    except (AttributeError, IndexError):
        # Default image if no image is found or if there are any errors in accessing the image
        return 'path/to/default/image.jpg'
