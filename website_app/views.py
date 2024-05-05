from django.shortcuts import render
from django.db.models import Q, F, FloatField, ExpressionWrapper, Case, When
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from . import models
from . import forms
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
import base64
import requests
from django.contrib import messages
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.forms import UserCreationForm
from .context_processors import cart_context
import re
from weasyprint import HTML
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.http import HttpResponse
from datetime import timedelta
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, get_user_model
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import F, Case, When, Value, IntegerField
from django.db.models.functions import Cast
import os
from django.http import FileResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings


def apply_sort_and_pagination(request, base_queryset, default_sort='newly_added'):
    # Annotate the queryset with discount_percentage and effective_price
    queryset = base_queryset.annotate(
        discount_percentage=Case(
            When(
                sale_price__isnull=False,
                sale_price__lt=F('price'),
                then=ExpressionWrapper(
                    (F('price') - F('sale_price')) * 100.0 / F('price'),
                    output_field=FloatField()
                )
            ),
            default=None,
            output_field=FloatField()
        ),
        effective_price=Coalesce('sale_price', 'price')
    )

    sort = request.GET.get('sort', default_sort)
    per_page = request.GET.get('per_page', 4)

    try:
        per_page = max(int(per_page), 1)  # Ensure at least 1 item per page and handle possible ValueError
    except ValueError:
        per_page = 4

    # Applying sorting based on the request
    if sort == 'price_low_high':
        queryset = queryset.order_by('effective_price')
    elif sort == 'price_high_low':
        queryset = queryset.order_by('-effective_price')
    elif sort == 'name_a_z':
        queryset = queryset.order_by('title')
    elif sort == 'name_z_a':
        queryset = queryset.order_by('-title')
    elif sort == 'most_discounted':
        queryset = queryset.filter(sale_price__isnull=False, sale_price__lt=F('price'))
        queryset = queryset.order_by('-discount_percentage')
    else:  # Default sort, including 'newly_added'
        queryset = queryset.order_by('-date_added')


    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)

    try:
        paginated_queryset = paginator.page(page_number)
    except PageNotAnInteger:
        paginated_queryset = paginator.page(1)
    except EmptyPage:
        paginated_queryset = paginator.page(paginator.num_pages)

    return paginated_queryset, sort, per_page


def error_404_view(request, exception):
    return render(request, 'error/404.html', status=404)

def error_500_view(request):
    return render(request, 'error/500.html', status=500)
    
def index(request):
    return render(request, 'index.html')

def fetch_admin_alerts():
    # Calculate the date 1 day ago from now
    alert_interval = 90
    days_ago = timezone.now() - timedelta(days=alert_interval)

    # Query to find products not updated in the last day and return only their id and title
    alerts = models.product.objects.filter(date_edited__isnull=True, date_added__lt=days_ago) | \
             models.product.objects.filter(date_edited__lt=days_ago) \
             .values('id', 'title')  # Use .values() to specify which fields to include

    return list(alerts), alert_interval



@login_required(login_url='/admin')
def administration(request):
    admin_alerts = fetch_admin_alerts()
    context = {
        'alerts': admin_alerts[0],
        'alert_interval': admin_alerts[1],
    }
    return render(request, 'admin/admin_base.html', context)

def categories(request):
    return render(request, 'categories.html')

def sale_catalogue(request):
    return render(request, 'sale_catalogue.html')

def all_products(request):
    products, sort, per_page = apply_sort_and_pagination(request, models.product.objects.all())
    context = {
        'products': products,  # This now contains the paginated and sorted products
        'current_sort': sort,
        'per_page': per_page
    }

    return render(request, 'products.html', context)

def about_us(request):
    about_us_text = models.business_information.objects.values_list('about_us_text', flat=True).first()
    context = {
        'about_us':about_us_text.replace("\n", "<br>"),
    }
    return render(request, 'about_us.html', context)

def contact(request):
    return render(request, 'contact.html')

def get_all_subcategories(main_category):
    subcategories = [main_category]
    for subcategory in models.category.objects.filter(parent=main_category):
        subcategories.extend(get_all_subcategories(subcategory))
    return subcategories

def category_search(request, category_string_id):
    # Using string_id to directly fetch the category
    main_category = get_object_or_404(models.category, string_id__iexact=category_string_id.replace(" > ", "/").lower())

    # Assuming the function get_all_subcategories is defined to fetch all subcategories
    subcategories = get_all_subcategories(main_category)
    # Fetch products linked to these subcategories and are enabled
    products = models.product.objects.filter(category__in=subcategories, enabled=True)
    # Assuming apply_sort_and_pagination is defined and used here to handle sorting and pagination
    products_page, sort, per_page = apply_sort_and_pagination(request, products)

    context = {
        'category': main_category,
        'products': products_page,
        'current_sort': sort,
        'per_page': per_page,
        'query': True,
    }

    return render(request, 'products.html', context)

def supplier_search(request, supplier_name):
    # Fetch the supplier
    supplier = get_object_or_404(models.supplier, name=supplier_name)

    # Fetch products that belong to the supplier
    products = models.product.objects.filter(
        supplier=supplier.name,  # Use supplier's name to filter products
        enabled=True
    )

    # Apply sorting and pagination
    products_page, sort, per_page = apply_sort_and_pagination(request, products)

    context = {
        'supplier': supplier,
        'products': products_page,
        'current_sort': sort,
        'per_page': per_page,
        'query': True,
    }

    # Render the template with the products for the supplier
    return render(request, 'products.html', context)

def general_search(request):
    query = request.GET.get('query', '')
    sort = request.GET.get('sort', 'default_sort_option')
    per_page = request.GET.get('per_page', '4')  # Default to showing 4 items per row

    products = models.product.objects.filter(
        Q(title__icontains=query) | 
        Q(subtitle__icontains=query) | 
        Q(description__icontains=query) |
        Q(category__name__icontains=query),
        enabled=True
    ).distinct()


    # Your existing logic for sorting
    sort_options = {
        'newly_added': 'date_added',
        'price_low_high': 'price',
        'price_high_low': '-price',
        'name_a_z': 'title',
        'name_z_a': '-title',
        'most_discounted': 'discount_percentage',
    }

    # Adjusting the sort logic to handle discount percentage
    if sort == 'most_discounted':
        products = products.annotate(
            discount_percentage=Case(
                # Ensure division by zero is handled
                When(price__gt=0, sale_price__isnull=False, then=(
                    1 - Cast(F('sale_price'), output_field=IntegerField()) / Cast(F('price'), output_field=IntegerField())
                ) * 100),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-discount_percentage')
    elif sort in sort_options:
        products = products.order_by(sort_options[sort])

    context = {
        'products': products,
        'per_page': per_page,
        'query': query,
    }
    
    return render(request, 'products.html', context)

def fetch_product_image(string_id):
    product = get_object_or_404(models.product, string_id=string_id)
    product_images = product.images.exclude(image__isnull=True).exclude(image__exact='')
    for product_image in product_images:
        if product_image.order == 0:
            return product_image.image
            

def product_page(request, string_id):
    product = get_object_or_404(models.product, string_id=string_id)
    quantity_range = list(range(1, product.instock + 1))
    # Filter out images with empty values
    product_images = product.images.exclude(image__isnull=True).exclude(image__exact='')

    context = {'product': product, 'product_images': product_images, 'quantity_range':quantity_range}
    return render(request, 'product_page.html', context)


def handle_custom_image_order(image_order_combined_json, item_instance, uploaded_images,new_entry=None):
    image_order_combined = json.loads(image_order_combined_json)
    uploaded_images_dict = {image.name: image for image in uploaded_images}

    # Track which images have been processed to identify any that need to be removed
    processed_image_ids = []

    model = models.product_image
    for item in image_order_combined:
        filename = item.get('filename')
        order = item.get('order')
        image_id = item.get('id', None)  # This assumes your JSON includes IDs for existing images
        if image_id:
            try:
                img = model.objects.get(id=image_id, product=item_instance)
                
                img.order = order
                img.save()
                processed_image_ids.append(img.id)
            except product_image.DoesNotExist:
                pass  # Handle case where image doesn't exist if necessary
        else:
            # Create new images for those uploaded
            image_file = uploaded_images_dict.get(filename)
            if image_file:
                new_img = model.objects.create(
                        product=item_instance, 
                        image=image_file, 
                        order=order)
                processed_image_ids.append(new_img.id)
    # Optionally, remove any images not included in the processed list
    model.objects.filter(product=item_instance).exclude(id__in=processed_image_ids).delete()



@login_required(login_url='/admin')
def add_product(request):
    categories = models.category.objects.all()
    suppliers = models.supplier.objects.all()
    if request.method == 'POST':
        form = forms.product_form(request.POST, request.FILES)
        formset = forms.product_image_formset(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            # Extract title and price from the form to check if the product already exists
            title = form.cleaned_data['title']
            price = form.cleaned_data['price']

            # Check if a product with the same title and price already exists
            existing_products = models.product.objects.filter(title=title, price=price)

            if existing_products.exists():
                existing_product_id = existing_products.first().id
                # If the product exists, return a JSON response indicating failure
                return JsonResponse({"success": False, "errors":'ERRORS', "redirect_url": reverse('edit_product', kwargs={'product_id': existing_product_id})})

            product_instance = form.save(commit=False) 
            enabled = request.POST.get('enabled')
            if enabled:
                product_instance.enabled = True
            bestseller = request.POST.get('bestseller')
            if bestseller:
                product_instance.bestseller = True
            product_instance.product_url = "https://testing.pokelageret.no/product/{}".format(product_instance.string_id)
            product_instance.save()


            # Update inventory records
            purchase_price = int(request.POST.get('stock_price', 0))
            stock_quantity = int(request.POST.get('instock', 0))

            # Create Inventory instance
            inventory_instance = models.Inventory(product=product_instance, purchase_price=purchase_price, stock_quantity=stock_quantity)
            inventory_instance.save()

            # Record Price History
            price_history_instance = models.PriceHistory(product=product_instance, purchase_price=purchase_price)
            price_history_instance.save()

            # Record Stock History
            stock_history_instance = models.StockHistory(product=product_instance, stock_quantity=stock_quantity, reason='Initial stock entry')
            stock_history_instance.save()

            image_order_combined_json = request.POST.get('image_order_combined')
            if image_order_combined_json:
                handle_custom_image_order(image_order_combined_json, product_instance, request.FILES.getlist('images'))


            formset.instance = product_instance
            formset.save()
            return JsonResponse({"success": True, "redirect_url": reverse('products')})
        else:
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
            return JsonResponse({"success": False, "errors": form.errors})
    else:
        form = forms.product_form()
        formset = forms.product_image_formset()
        context = {
            'form': form,
            'formset': formset,
            'categories':categories,
            'suppliers': suppliers,
        }
        return render(request, 'admin/add_product.html', context)


@login_required(login_url='/admin')
def edit_product(request, product_id):
    product_instance = get_object_or_404(models.product, id=product_id)
    categories = models.category.objects.all()
    suppliers = models.supplier.objects.all()
    if request.method == 'POST':
        form = forms.product_form(request.POST, request.FILES, instance=product_instance)
        formset = forms.product_image_formset(request.POST, request.FILES, queryset=product_instance.images.all())
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Save product instance
                product_instance = form.save(commit=False)
                enabled = request.POST.get('enabled')
                if enabled:
                    product_instance.enabled = True
                bestseller = request.POST.get('bestseller')
                if bestseller:
                    product_instance.bestseller = True
                product_instance.product_url = "https://testing.pokelageret.no/product/{}".format(product_instance.string_id)
                product_instance.save()

                # Update the remaining images
                formset.save()

                # Handle inventory updates
                current_inventory = models.Inventory.objects.get(product=product_instance)
                new_stock_quantity = int(request.POST.get('instock', current_inventory.stock_quantity))
                new_purchase_price = int(request.POST.get('stock_price', current_inventory.purchase_price))

                # Check and update inventory if changes are made
                if new_stock_quantity != current_inventory.stock_quantity:
                    current_inventory.stock_quantity = new_stock_quantity
                    models.StockHistory.objects.create(product=product_instance, stock_quantity=new_stock_quantity, reason='Stock updated via edit')

                if new_purchase_price != current_inventory.purchase_price:
                    current_inventory.purchase_price = new_purchase_price
                    models.PriceHistory.objects.create(product=product_instance, purchase_price=new_purchase_price)

                current_inventory.save()

                image_order_combined_json = request.POST.get('image_order_combined')
                if image_order_combined_json:
                    handle_custom_image_order(image_order_combined_json, product_instance, request.FILES.getlist('images'))

            return JsonResponse({"success": True, "redirect_url": reverse('edit_product', kwargs={'product_id': product_instance.id})})
        else:
            return JsonResponse({"success": False, "errors": form.errors, "formset_errors": formset.errors})
    else:
        form = forms.product_form(instance=product_instance)
        formset = forms.product_image_formset(queryset=product_instance.images.all())
        return render(request, 'admin/edit_product.html', {
            'form': form,
            'formset': formset,
            'product': product_instance,
            'categories': categories,
            'suppliers': suppliers,
        })



@require_POST
@login_required(login_url='/admin')
def delete_product_image(request, image_id):
    image = get_object_or_404(models.product_image, id=image_id)
    image.delete()
    return JsonResponse({"success": True, "redirect_url": reverse('edit_product', kwargs={'product_id': image.product.id})})

@login_required(login_url='/admin')
def delete_product(request, product_id):
    product = get_object_or_404(models.product, id=product_id)
    product.delete()
    return redirect('products')

@login_required(login_url='/admin')
def add_category(request):
    all_categories = models.category.objects.all()
    if request.method == 'POST':
        form = forms.category_form(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            string_id = str(category.get_full_path()).replace(" > ", "/").replace(" ", "_").lower()
            category.string_id = string_id
            category.save()

            if request.FILES:
                category.image = request.FILES['category_image']
            category.save()
            return redirect('update_categories')  # Make sure 'home' is the correct named URL for redirection
        else:
            return HttpResponse(json.dumps(form.errors), content_type="application/json")
    else:

        form = forms.category_form()

    return render(request, 'admin/add_category.html', {'category_form': form, 'categories':all_categories})


@login_required(login_url='/admin')
def add_supplier(request):
    if request.method == 'POST':
        form = forms.supplier_form(request.POST, request.FILES)
        if form.is_valid():
            supplier = form.save(commit=False)
            try:
                supplier.image = request.FILES['supplier_image']
            except:
                pass
            supplier.save()
            return redirect('hjem')  # Redirect to the index page or wherever you want
        else:
            print("Form Errors:", form.errors)
            return HttpResponse(json.dumps(form.errors), content_type="application/json")
    else:
        form = forms.category_form()

    return render(request, 'admin/add_supplier.html', {'supplier_form': form})

@login_required(login_url='/admin')
def product_list_and_update(request, product_id=None):
    if request.method == 'POST':
        product = get_object_or_404(models.product, pk=product_id)
        form = forms.product_form(request.POST, instance=product)
        if form.is_valid():
            product_instance = form.save(commit=False)
            product_instance.date_edited = timezone.now()
            product_instance.save()
            form.save_m2m()
            return redirect('update_products')
        else:
            print(form.errors)
    else:
        products = models.product.objects.all().order_by('id')
        all_categories = models.category.objects.all()
        return render(request, 'admin/update_products.html', {
            'products': products,
            'all_categories': all_categories,  # Add this line
            'admin': True,
            'suppliers': models.supplier.objects.all()
        })



@login_required(login_url='/admin')
def category_list_and_update(request, category_id=None):
    if request.method == 'POST':
        # If a category_id is provided, fetch the existing instance; otherwise, create a new one
        category = get_object_or_404(models.category, pk=category_id) if category_id else None
        form = forms.category_form(request.POST, request.FILES, instance=category)

        if form.is_valid():
            category_instance = form.save(commit=False)
            string_id = str(category_instance.get_full_path()).replace(" > ", "/").replace(" ", "_").lower()
            category.string_id = string_id
            category.save()
            category_instance.save()
            return redirect('update_categories')  # Assuming 'update_categories' is the correct redirect URL
        else:
            # If the form is not valid, render the page again with the form errors
            categories = models.category.objects.all()
            return render(request, 'admin/update_categories.html', {
                'categories': categories,
                'form': form,
                'admin': True
            })
    else:
        categories = models.category.objects.all()
        form = forms.category_form()  # Provide a blank form for creating new categories
        return render(request, 'admin/update_categories.html', {
            'categories': categories,
            'form': form,
            'admin': True
        })

@login_required(login_url='/admin')
def text_areas_list_and_update(request, text_area_id=None, footer_text_area_id=None, business_info_id=None):
    context = {
        'text_areas': models.text_areas.objects.all(),
        'footer_text_areas': models.footer_textareas.objects.all(),
        'business_information': models.business_information.objects.all(),  # Add this line
        'admin': True
    }

    if request.method == 'POST':
        print(request.POST)
        if text_area_id:
            text_area = get_object_or_404(models.text_areas, pk=text_area_id)
            form = forms.text_areas_form(request.POST, instance=text_area)
            if form.is_valid():
                form.save()
                return redirect('update_text_areas')  # Make sure this is the correct URL name
            else:
                context['text_area_form'] = form  # Include form with errors in the context
        elif "front_page_header" in request.POST:
            form = forms.text_areas_form(request.POST)
            if form.is_valid():
                form.save()
                return redirect('update_text_areas')  # Make sure this is the correct URL name
            else:
                context['text_area_form'] = form  # Include form with errors in the context


        elif footer_text_area_id:
            footer_area = get_object_or_404(models.footer_textareas, pk=footer_text_area_id)
            footer_form = forms.footer_text_areas_form(request.POST, instance=footer_area)
            if footer_form.is_valid():
                footer_form.save()
                return redirect('update_footer_text_areas')  # Make sure this is the correct URL name
            else:
                context['footer_text_area_form'] = footer_form  # Include form with errors in the context

        # Handling for business information
        elif business_info_id:
            business_info = get_object_or_404(models.business_information, pk=business_info_id)
            business_info_form = forms.business_information_form(request.POST, instance=business_info)
            if business_info_form.is_valid():
                business_info_form.save()
                return redirect('business_information')  # Redirect to appropriate URL
            else:
                context['business_info_form'] = business_info_form  # Include form with errors in the context
        elif 'street_address' in request.POST:  # Or any other unique field in the business information form
            business_info_form = forms.business_information_form(request.POST)
            if business_info_form.is_valid():
                business_info_form.save()
                return redirect('business_information')  # Redirect to appropriate URL
            else:
                context['business_info_form'] = business_info_form  # Include form with errors in the context

        # If no forms were valid, fall through to render

    # Render is called if it's a GET request or if a POST request is not valid
    return render(request, 'admin/update_text_areas.html', context)


@login_required(login_url='/admin')
def business_information_update(request, business_info_id=None):
    if request.method == 'POST':
        if business_info_id:
            # Update existing business information
            business_info_instance = get_object_or_404(models.business_information, pk=business_info_id)
            business_info_form = forms.business_information_form(request.POST, instance=business_info_instance)
        else:
            # Create new business information
            business_info_form = forms.business_information_form(request.POST)

        if business_info_form.is_valid():
            business_info_form.save()
            return redirect('update_business_info')

    else:
        business_info_form = forms.business_information_form()
        if business_info_id:
            # If an ID is provided, populate the form with that instance
            business_info_instance = get_object_or_404(models.business_information, pk=business_info_id)
            business_info_form = forms.business_information_form(instance=business_info_instance)

    # Get all instances of business information to display
    business_info_list = models.business_information.objects.all()
    
    return render(request, 'admin/update_text_areas.html', {
        'business_info_form': business_info_form,
        'business_info_list': business_info_list,
        'admin': True
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('administration')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('administration')  # Redirect to the user's home page after login
        else:
            # Return the form with errors
            return render(request, 'login.html', {'form': form})
    else:
        form = AuthenticationForm()
        return render(request, 'login.html', {'form': form})

def add_customer(request, customer_id=None):

    all_customers = models.customers.objects.all()  # Fetch all customers
    customers_dict = {str(customer.id): {
        'name': customer.name,
        'zip_code': customer.zip_code,
        'street_address': customer.street_address,
        'email': customer.email,
        'phone_number': customer.phone_number
    } for customer in all_customers}
    customers_json = json.dumps(customers_dict)

    if request.method == 'POST':

        form = forms.customer_form(request.POST)
        if form.is_valid():
            new_customer = form.save()
            # Redirect to the same page with the newly added customer selected
            return HttpResponseRedirect(reverse('add_customer') + f'?customer={new_customer.id}')
    else:
        if customer_id:
            return HttpResponseRedirect(reverse('add_customer') + f'?customer={customer_id}')
        form = forms.customer_form()

    selected_customer = request.GET.get('customer', '')

    return render(request, 'admin/customer_form.html', {
        'form': form,
        'all_customers': all_customers,
        'selected_customer': selected_customer,
        'customers_json': customers_json,
    })



def customer_detail(request, customer_id):
    customer = get_object_or_404(models.customers, id=customer_id)
    customer_orders = models.orders.objects.filter(customer=customer).order_by('-date_added')

    if request.method == 'POST':
        form = forms.customer_form(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customer_detail', customer_id=customer.id)
    else:
        form = forms.customer_form(instance=customer)
    context = {
        'customer': customer,
        'form': form,
        'orders': customer_orders  # Pass the orders to the template
    }
    return render(request, 'admin/customer_detail.html', context)


def add_order(request, customer_id):
    customer = get_object_or_404(models.customers, id=customer_id)
    products = models.product.objects.all().order_by('-date_added')

# Manually construct a list of dictionaries for each product
    products_list = [{
        'id': product.id,
        'name': product.title,
        'price': product.price,
    } for product in products]
    
    # Serialize this list to a JSON string
    products_json = json.dumps(products_list)

    if request.method == 'POST':
        form = forms.order_form(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.customer = customer

            # Regular expression to match the pattern 'products[index][field]' in POST keys
            pattern = re.compile(r'^products\[(\d+)\]\[(\w+)\]$')

            # Dictionary to hold the items details, indexed by item number
            items_details = {}

            for key, value in request.POST.items():
                match = pattern.match(key)
                if match:
                    index, field = match.groups()
                    index = int(index)  # Convert index to integer
                    
                    if index not in items_details:
                        items_details[index] = {}
                    items_details[index][field] = value
            
            # Convert the dictionary of items to a list, to maintain order
            items_list = [item for _, item in sorted(items_details.items())]
            order.remaining = int(request.POST.get('price')) - int(request.POST.get('paid'))
            order.a_paid = int(request.POST.get('paid'))
            order.items = json.dumps(items_list)  # Save serialized items list
            order.save()
            return redirect(reverse('order_confirmation', args=[order.order_number]))

        else:
            # Form is not valid; render form with validation errors
            return render(request, 'admin/order_form.html', {'form': form, 'customer': customer, 'products_json':products_json})
    else:
        form = forms.order_form()

    return render(request, 'admin/order_form.html', {'form': form, 'customer': customer, 'products_json':products_json})

def all_orders(request):
    all_orders = models.orders.objects.all().order_by('-date_added')
    return render(request, 'admin/all_orders.html', {'orders': all_orders})


def pdf_exists_for_order(order_number):
    # Define the path to the 'orders' directory within 'files' in your BASE_DIR
    orders_dir = os.path.join(settings.BASE_DIR, 'files', 'orders')
    
    # Define the full file path where the PDF should be saved
    file_path = os.path.join(orders_dir, f'order_{order_number}.pdf')
    
    # Return True if the PDF file exists, False otherwise
    return os.path.exists(file_path)

def order_detail(request, order_number):
    order = get_object_or_404(models.orders, order_number=order_number)
    items = prep_items(json.loads(order.items))
    delivery_info = json.loads(order.delivery_info)
    # Call the helper function to check if the PDF exists for this order
    pdf_file_exists = pdf_exists_for_order(order_number)
    payment_method = json.loads(order.payment_info)["payment_method"]

    # Pass the result to the template context
    return render(request, 'admin/order_detail.html', {
        'order': order,
        'items': items,
        'pdf_exists': pdf_file_exists,
        'delivery_info': delivery_info,
        'payment_method': payment_method
    })

def update_order(request, order_number):
    order = get_object_or_404(models.orders, order_number=order_number)
    if request.method == 'POST':
        form = forms.order_form(request.POST, instance=order)
        if form.is_valid():
            order = form.save(commit=False)
            
            # Process item details just like in add_order, adjusting for any changes in POST structure
            pattern = re.compile(r'^product_(\d+)$')  # Adjust this regex based on your POST data keys for items
            items_details = []

            if 'total_price' in request.POST and request.POST['total_price']:
                order.price = request.POST['total_price']

            # We need to find the highest index to know how many items we're updating
            max_index = 0
            for key in request.POST:
                match = pattern.match(key)
                if match:
                    max_index = max(max_index, int(match.group(1)))
            
            # Now we create a list of item details
            for index in range(1, max_index + 1):
                try:
                    item = {
                        'product': request.POST[f'product_{index}'],
                        'product_info': request.POST[f'info_{index}'],
                        'amount': int(request.POST[f'amount_{index}']),
                        'legs': request.POST[f'legs_{index}'],
                        'fabric': request.POST[f'fabric_{index}'],
                        'price': request.POST[f'price_{index}']
                    }
                    items_details.append(item)
                except (ValueError, KeyError):
                    # Handle the case where some item details are missing
                    # You might want to add some error handling or logging here
                    continue
 
            order.remaining = int(request.POST.get('total_price')) - int(request.POST.get('paid'))
            order.items = json.dumps(items_details)
            order.save()
            return redirect('order_detail', order_number=order.order_number)  # Adjust the redirect as needed
        else:
            # If the form is not valid, render the same order detail page with validation errors
            items = json.loads(order.items)
            return render(request, 'admin/order_detail.html', {'form': form, 'order': order, 'items': items})
    else:
        # Pre-populate the form with the order details for GET request
        form = forms.order_form(instance=order)
        items = json.loads(order.items)
        return render(request, 'admin/order_detail.html', {'form': form, 'order': order, 'items': items})

@login_required
@require_POST
def remove_order(request, order_number):
    try:
        order = models.orders.objects.get(order_number=order_number)
        order.deleted = not order.deleted  # Toggle the deleted status
        order.save()
        return redirect('order_detail', order_number=order.order_number)
    except models.orders.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


@login_required
@require_POST
def complete_order(request, order_number):
    try:
        order = models.orders.objects.get(order_number=order_number)
        order.completed = not order.completed
        order.save()
        return redirect('all_orders')
    except models.orders.DoesNotExist:
        # Handle the error or redirect as appropriate
        return redirect('all_orders')


def show_order_pdf(request, order_number):
    # Define the path to the 'orders' directory within 'files' in your BASE_DIR
    orders_dir = os.path.join(settings.BASE_DIR, 'files', 'orders')
    
    # Define the full file path where the PDF should be saved
    file_path = os.path.join(orders_dir, f'order_{order_number}.pdf')
    
    # Check if the PDF file exists
    if os.path.exists(file_path):
        # Open the PDF file and return it in the response
        pdf_file = open(file_path, 'rb')
        response = FileResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="order_{order_number}_confirmation.pdf"'
        return response
    else:
        # If the PDF does not exist, raise 404 not found
        raise Http404("PDF file does not exist")

def order_confirmation(request, order_number):
    # Fetch the order and customer from the database using order ID
    order = get_object_or_404(models.orders, pk=order_number)
    customer = get_object_or_404(models.customers, id=order.customer.id)
    
    # Assuming order.items is a JSON string; parse it into a Python dictionary
    item_details = json.loads(order.items) if order.items else []
    product_total = sum(int(item["price"]) * int(item["amount"]) for item in item_details)
    if order.delivery_price:
        product_total += int(order.delivery_price)

    # Fetch the business information
    business_info = models.business_information.objects.first()
    
    # Prepare the context for rendering
    context = {
        'order': order,
        'customer': customer,
        'item_details': item_details,
        'product_total': product_total,
        'business_information': business_info,
    }

    # Render the HTML template to a string
    html_string = render_to_string('admin/order_confirmation.html', context)

    # Generate PDF from the rendered HTML string
    html = HTML(string=html_string)
    pdf = html.write_pdf()

    # Define the path to the 'orders' directory within 'files' in your PROJECT_ROOT
    orders_dir = os.path.join(settings.BASE_DIR, 'files', 'orders')
    os.makedirs(orders_dir, exist_ok=True)  # Create the directory if it doesn't exist

    # Define the full file path where the PDF will be saved
    file_path = os.path.join(orders_dir, f'order_{order_number}.pdf')

    # Write the PDF data to the file
    with open(file_path, 'wb') as pdf_file:
        pdf_file.write(pdf)

    # Open the PDF file and return it in the response
    pdf_file = open(file_path, 'rb')
    response = FileResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="order_{order_number}_confirmation.pdf"'

    return response



def get_cart_data(request):
    cart_data = cart_context(request)  # Assuming this gathers all cart data
    return JsonResponse({
        'cart_items': [
            {    
                'string_id': item['string_id'],
                'id': item['id'],
                'title': item['title'],
                'price': item['price'],
                'normal_price': item['normal_price'],
                'sale_price': item['sale_price'],
                'quantity': item['quantity'],
                'image_url': item['image_url'],
            } for item in cart_data['cart_items']
        ],
        'total_price': cart_data['total_price']
    })

def get_cart_total(request):
    cart_data = cart_context(request) 
    total_price = cart_data['total_price']
    return JsonResponse({'total': total_price})

@require_POST
def add_to_cart_ajax(request, product_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
    # Get the product or return a 404 error if not found
    product = get_object_or_404(models.product, pk=product_id)
    # Read quantity from the request, default to 1 if not set
    cart = request.session.get('cart', {})
    cart[product_id] = cart.get(product_id, 0) + 1

    request.session['cart'] = cart  # Save the updated cart to the session
    return JsonResponse({'status': 'ok'})

def add_to_cart(request, product_id):
    if request.method == 'POST':
        # Fetch the product or return a 404 error if not found
        product = get_object_or_404(models.product, pk=product_id)

        # Try to get the quantity from POST data and convert it to an integer
        try:
            quantity = int(request.POST.get('quantity', 0))
        except ValueError:
            # Handle the case where the quantity is not an integer
            return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)

        # Validate quantity (must be at least 1 and not exceed product.instock)
        if quantity < 1 or quantity > product.instock:
            return JsonResponse({'status': 'error', 'message': 'Invalid quantity'}, status=400)

        # Get the cart from the session, or initialize a new one if none exists
        cart = request.session.get('cart', {})

        # Add the quantity of the product to the cart or update it
        if product_id in cart:
            # Update existing quantity in the cart, but do not exceed the stock
            cart[product_id] = min(cart[product_id] + quantity, product.instock)
        else:
            # Add new product with the specified quantity
            cart[product_id] = quantity
        
        # Save the updated cart in the session
        request.session['cart'] = cart
        
        # Return appropriate response based on the type of request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        else:
            return redirect('hjem')  # Redirect to a cart view or homepage

@require_POST
def update_cart(request, product_id):
    data = json.loads(request.body)
    cart = request.session.get('cart', {})
    if data['action'] == 'add':
        instock = get_object_or_404(models.product, pk=product_id).instock
        if not cart.get(product_id, 0) >= instock:
            cart[product_id] = cart.get(product_id, 0) + 1
    elif data['action'] == 'remove':
        if 'remove_all' in data and data['remove_all']:
            cart.pop(product_id, None)  # Remove the item completely if flagged
        else:
            # Decrement the quantity by one unless it's the last item
            if cart[product_id] > 1:
                cart[product_id] -= 1
            else:
                cart.pop(product_id, None)  # Remove item if only one left

    request.session['cart'] = cart
    return JsonResponse({'status': 'ok'})


def fetch_checkout_data(request):
    item_data = sort_purchased_items(request)  # This function processes item data
    customer = None
    new_order = models.orders()
    if customer:
        new_order.customer = customer
    new_order.items = json.dumps(item_data)  # Assuming this is structured correctly

    # Calculate price and related fields
    total_price = sum(item['quantity'] * (item['purchase_price'] if item['purchase_price'] else item['normal_price']) for item in item_data)
    new_order.price = total_price
    new_order.paid = float('0.00')  # This could be set based on your payment processing logic
    new_order.remaining = total_price - new_order.paid
    new_order.status = 'processing'  # Default, or set based on logic

    new_order.save()
    return new_order.order_number

def checkout(request):
    options = models.shipping_options.objects.all()
    customer_instance = None
    form = None

    if request.user.is_authenticated:
        customer_instance, created = models.customers.objects.get_or_create(user=request.user)
        form = forms.CustomerForm(request.POST or None, instance=customer_instance)
    else:
        # For non-authenticated users, create a new customer instance if form is submitted
        form = forms.CustomerForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            customer_instance = form.save(commit=False)
            if not request.user.is_authenticated:
                # For guest users, do any additional handling as needed
                customer_instance.save()
            else:
                # For authenticated users, link the customer instance with the user
                customer_instance.user = request.user
                customer_instance.save()

            # Proceed with order creation
            order_response = create_order(request, customer_instance)
            if order_response['status'] == 'success':
                messages.success(request, 'Order created successfully with number: {}'.format(order_response['order_number']))
                return redirect('order_success', order_number=order_response['order_number'])
            else:
                messages.error(request, order_response['message'])
                return redirect('checkout')
        else:
            print(request.POST)
            print(form.errors)

    return render(request, 'checkout.html', {
        'shipping_options': options,
        'form': form,
        'customer':customer_instance,
    })

def create_order(request, customer_instance):
    data = request.POST
    with transaction.atomic():
        item_info = [
            {
                'item_id': item_id,
                'quantity': quantity,
                'sale_price': sale_price if sale_price else price
            } for item_id, quantity, price, sale_price in zip(
                data.getlist('item_id[]'),
                data.getlist('item_quantity[]'),
                data.getlist('item_price[]'),
                data.getlist('item_sale_price[]')
            )
        ]
        total_price = sum(float(item['sale_price']) * int(item['quantity']) for item in item_info)
        delivery_price = Decimal('0.00')  # Set default delivery price, potentially updated based on options

        # Build delivery information based on selected delivery option
        delivery_info = {
            'delivery_option': data.get('delivery_option')
        }
        if delivery_info['delivery_option'] == 'delivery':
            shipping_option_id = data.get('shipping_option', '')
            if shipping_option_id:
                shipping_option = models.shipping_options.objects.get(id=shipping_option_id)
                delivery_price = Decimal(shipping_option.price if shipping_option.price is not None else '0.00')
            else:
                delivery_price = Decimal('0.00')
        else:
            delivery_price = Decimal('0.00')

        # Assuming total_price is originally a float, convert it to Decimal
        total_price = Decimal(str(total_price))

        order = models.orders.objects.create(
            customer=customer_instance,
            items=json.dumps(item_info),
            delivery_info=json.dumps(delivery_info),
            price=total_price + delivery_price,  # Both are Decimals now
            remaining=total_price + delivery_price,  # Both are Decimals now
            delivery_price=delivery_price,
            payment_info=json.dumps({
                'payment_method': data.get('payment_method')
            }),
            status='processing'
        )
        if data.get("payment_method") == "faktura":
            send_order_confirmation(order)
        return {'status': 'success', 'message': 'Order created successfully.', 'order_number': order.order_number}

@require_POST
def order_detail_send_order(request, order_number, action):
    order = models.orders.objects.get(order_number=order_number)
    data = json.loads(request.body)
    items_to_update = {item['item_id'] for item in data.get('items', [])}  # Create a set of item_ids
    # Assume order.items is already deserialized into a list of dictionaries
    updated_items = []
    items_updated = False

    for item in json.loads(order.items):
        if item['item_id'] in items_to_update:
            item['sent'] = True
            items_updated = True
        updated_items.append(item)

    if items_updated:
        with transaction.atomic():
            order.items = json.dumps(updated_items)  # Assuming the field can be directly assigned like this
            order.save()

    if action == 'send' or action == 'pickup':
        send_order_sent(order)
        return JsonResponse({'status': 'Order sent'})
    else:
        return JsonResponse({'status': 'Invalid action'}, status=400)

def send_order_sent(order):
    subject = 'Din ordre {} er sendt fra oss'.format(order.order_number)
    items = prep_items(json.loads(order.items))

    context = {
        'order': order,
        'items': items,
    }
    message = render_to_string('emails/order_sent.html', context)
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [order.customer.email]

    # Send email using the HTML message body
    send_mail(subject, message, email_from, recipient_list, html_message=message)

def prep_items(items):
    for item in items:
        product = models.product.objects.filter(id=item["item_id"]).first()
        item["title"] = product.title
        item["id"] = product.id
        item["product_total"] = int(item["sale_price"]) * int(item["quantity"])
        item["price_pre_discount"] = product.price
        item["price_pre_discount_total"] = int(product.price) * int(item["quantity"])
        item["money_saved"] = int(item["price_pre_discount_total"]) - int(item["product_total"])
    return items

def send_order_confirmation(order):
    subject = 'Ordrebekreftelse fra Pokelageret - Ordrenummer {}'.format(order.order_number)
    items = prep_items(json.loads(order.items))

    context = {
        'order': order,
        'items': items,
        'payment_details': json.loads(order.payment_info),  # Assuming 'payment_info' is a JSON string
        'item_total': sum(item['product_total'] for item in items)
    }
    message = render_to_string('emails/order_confirmation.html', context)
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [order.customer.email]

    # Send email using the HTML message body
    send_mail(subject, message, email_from, recipient_list, html_message=message)

def sort_purchased_items(request):
    item_ids = request.POST.getlist('item_id[]')
    item_quantities = request.POST.getlist('item_quantity[]')
    item_prices = request.POST.getlist('item_price[]')
    item_sale_prices = request.POST.getlist('item_sale_price[]')

    items = []
    for i, item_id in enumerate(item_ids):
        items.append({
            'id': item_id,
            'quantity': int(item_quantities[i]),
            'normal_price': float(item_prices[i]),
            'purchase_price': float(item_sale_prices[i]) if item_sale_prices[i] else None
        })
    return items

def get_or_create_customer(first_name, last_name, phone, email, address, postal_code, city):
    # Combine first and last name into a full name if needed
    full_name = f"{first_name} {last_name}"
    
    try:
        # Attempt to get or create the customer based on unique fields
        customer, created = models.customers.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone,
            defaults={
                'email': email,
                'address': address,
                'postal_code': postal_code,
                'city': city
            }
        )
        
        if not created:
            # If the customer was found, check for any changes in the other details
            updated = False
            if customer.email != email:
                customer.email = email
                updated = True
            if customer.address != address:
                customer.address = address
                updated = True
            if customer.postal_code != postal_code:
                customer.postal_code = postal_code
                updated = True
            if customer.city != city:
                customer.city = city
                updated = True
            
            if updated:
                customer.save()  # Save only if there are updates

    except IntegrityError as e:
        # Handle the possible integrity error if unique constraints are violated
        raise ValueError("A customer with the given details already exists or other integrity issues.")
    
    return customer

def order_success(request, order_number):
    try:
        order = models.orders.objects.get(order_number=order_number)
        items = json.loads(order.items)
        item_total = 0
        for item in items:
            product = models.product.objects.filter(id=item["item_id"]).first()
            item["title"] = product.title
            item_total += Decimal(item["sale_price"])
        payment_details = json.loads(order.payment_info)
    except models.orders.DoesNotExist:
        # Handle missing order scenario
        return render(request, 'error.html', {'message': 'Order not found.'})

    return render(request, 'admin/order_confirmation.html', {'payment_details': payment_details, 'items':items, 'order': order, 'item_total':item_total})

def klarna_push_notification(request):
    if request.method == 'POST':
        # Process the notification (you might want to log it, or update order status in your database)
        print("Received push notification:", request.body)
        return HttpResponse("OK", status=200)
    return HttpResponse("Method Not Allowed", status=405)

def build_shipping_options(order_price):
    # Define the base shipping options
    shipping_options = [
        {
            "id": "1",
            "type": "postal",
            "carrier": "posten",
            "name": "Pakke til postkassen",
            "price": 6900,
            "tax_rate": 0,
            "tax_amount": 0,  # Should be recalculated if price changes
            "delivery_time": {
                "interval": {
                    "earliest": 4,
                    "latest": 6
                }
            },
            "class": "standard"
        },
        {
            "id": "2",
            "type": "postal",
            "carrier": "posten",
            "name": "Pakke til hentested",
            "price": 12900,
            "tax_rate": 0,
            "tax_amount": 0,  # Should be recalculated if price changes
            "delivery_time": {
                "interval": {
                    "earliest": 1,
                    "latest": 3
                }
            },
            "class": "standard"
        }
    ]

    # Adjust shipping prices based on order price
    if order_price > 2999:
        # Both shipping options free
        for option in shipping_options:
            option['price'] = 0
            option['tax_amount'] = 0  # Adjust tax_amount accordingly
    elif order_price > 999:
        # Only the first shipping option free
        shipping_options[0]['price'] = 0
        shipping_options[0]['tax_amount'] = 0  # Adjust tax_amount accordingly

    return shipping_options


def retrieve_klarna_order(klarna_order_id):
    url = f"https://api.playground.klarna.com/checkout/v3/orders/{klarna_order_id}"
    credentials = f"{settings.KLARNA_API_USERNAME}:{settings.KLARNA_API_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    headers = {'Authorization': f'Basic {encoded_credentials}'}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        order_details = response.json()
        print(order_details)
        return order_details
    else:
        # Handle error: log it, send notification, etc.
        print(f"Failed to retrieve order from Klarna: {response.text}")
        return None

def generate_klarna_customer_info(request):
    pass

def klarna_checkout(request):
    customer_instance = None
    form = None

    if request.user.is_authenticated:
        customer_instance, created = models.customers.objects.get_or_create(user=request.user)
        form = forms.CustomerForm(request.POST or None, instance=customer_instance)
    else:
        # For non-authenticated users, create a new customer instance if form is submitted
        form = forms.CustomerForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            customer_instance = form.save(commit=False)
            if not request.user.is_authenticated:
                # For guest users, do any additional handling as needed
                customer_instance.save()
            else:
                # For authenticated users, link the customer instance with the user
                customer_instance.user = request.user
                customer_instance.save()

            # Proceed with order creation
            order_response = create_order(request, customer_instance)

            order_number = order_response['order_number']
            items_ids = request.POST.getlist('item_id[]')
            quantities = request.POST.getlist('item_quantity[]')
            prices = request.POST.getlist('item_price[]')
            sale_prices = request.POST.getlist('item_sale_price[]')
            delivery_method = request.POST.get('delivery_option')
            shipping_option = request.POST.get('shipping_option')
            selected_shipping_option = None
            if shipping_option:
                selected_shipping_option = models.shipping_options.objects.filter(pk=shipping_option).first()

            order_lines = []
            total_amount = 0
            total_tax_amount = 0

            for i, item_id in enumerate(items_ids):
                price = float(sale_prices[i]) if sale_prices[i] else float(prices[i])
                quantity = int(quantities[i])

                # Convert price to minor units (assuming input prices are in major units)
                price_in_cents = round(price * 100)
                
                # Price is assumed to be excluding tax already, calculate tax based on this
                unit_price_excl_tax = int(price_in_cents / 1.25)
                tax_amount_per_unit = int(price_in_cents * 0.25)  # 25% of the exclusive price
                total_tax_amount_for_item = (price_in_cents - unit_price_excl_tax) * quantity
                total_price_excl_tax = unit_price_excl_tax * quantity
                total_amount_incl_tax = total_price_excl_tax + total_tax_amount_for_item
                product_name = None
                product = models.product.objects.filter(pk=item_id).first()
                if product:
                    product_name = product.title
                order_lines.append({
                    "type": "physical",
                    "name": product_name,
                    "quantity": quantity,
                    "unit_price": price_in_cents,
                    "product_url": product.product_url,
                    "image_url": "https://testing.pokelageret.no/media/{}".format(fetch_product_image(product.string_id)),
                    "tax_rate": 2500,
                    "total_amount": total_amount_incl_tax, 
                    "total_tax_amount": total_tax_amount_for_item,
                })

                total_amount += total_amount_incl_tax
                total_tax_amount += total_tax_amount_for_item

            if delivery_method == 'delivery' and selected_shipping_option:
                # Assuming the shipping price from the database is inclusive of tax
                shipping_cost_in_cents = round(float(selected_shipping_option.price) * 100)
                shipping_cost_excl_tax = int(shipping_cost_in_cents / 1.25)  # Calculate price exclusive of tax
                shipping_tax_amount = shipping_cost_in_cents - shipping_cost_excl_tax

                order_lines.append({
                    "type": "shipping_fee",
                    "name": selected_shipping_option.title,
                    "quantity": 1,
                    "unit_price": shipping_cost_in_cents,
                    "tax_rate": 2500,  # 25%
                    #"image_url": fetch_product_image(product_instance.string_id),
                    "total_amount": shipping_cost_in_cents,
                    "total_tax_amount": shipping_tax_amount,
                })
                total_amount += shipping_cost_in_cents
                total_tax_amount += shipping_tax_amount

            url = "https://api.playground.klarna.com/checkout/v3/orders"
            credentials = f"{settings.KLARNA_API_USERNAME}:{settings.KLARNA_API_PASSWORD}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "purchase_country": "NO",
                "purchase_currency": "NOK",
                "locale": "nb",
                "order_amount": total_amount,
                "order_tax_amount": total_tax_amount,
                "order_lines": order_lines,
                "merchant_urls": {
                    "terms": "https://testing.pokelageret.no",
                    "checkout": "https://testing.pokelageret.no/checkout",
                    "confirmation": f"https://testing.pokelageret.no/confirmation/{order_number}/",
                    "push": "https://testing.pokelageret.no/klarna/push/"
                }, 
                "billing_address": {
                    "email": request.POST.get('email'),  # Replace with your customer's email
                    "postal_code": request.POST.get('postal_code'),  # Replace with your customer's postal code
                    "given_name": request.POST.get('first_name'),  # Replace with your customer's first name
                    "family_name": request.POST.get('last_name'),  # Replace with your customer's last name
                    "street_address": request.POST.get('address'),  # Replace with your customer's street address
                    "city": request.POST.get('city'),  # Replace with your customer's city
                    "phone": request.POST.get('phone'),  # Replace with your customer's phone number
                    "country": "NO",  # Replace with your customer's country code if different
                },
            }
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 201:
                klarna_order = response.json()
                order_id = klarna_order["order_id"]
                return render(request, "klarna_checkout.html", {'html_snippet': klarna_order['html_snippet']})
            else:
                return render(request, "error/checkout_error.html", {"post_data":request.POST, "error": response.text})

    return render(request, "checkout.html")

def manage_shipping_option(request, id=None):
    if request.method == 'POST':
        # Extract data from POST request
        data = {
            'title': request.POST.get('title', ''),
            'subtitle': request.POST.get('subtitle', ''),
            'description': request.POST.get('description', ''),
            'company': request.POST.get('company', ''),
            'max_weight': request.POST.get('max_weight', None),
            'price': request.POST.get('price', None),
            'free_shipping_limit': request.POST.get('free_shipping_limit', None)
        }
        
        if id:
            # Update existing shipping option
            shipping_option = get_object_or_404(models.shipping_options, pk=id)
            for field, value in data.items():
                setattr(shipping_option, field, value)
        else:
            # Create a new shipping option
            shipping_option = models.shipping_options(**data)

        # Handle image separately to account for file uploads
        shipping_option.image = request.FILES.get('image', None)

        # Save the object to database
        shipping_option.save()
        
        return redirect('hjem')  # Assuming you have a listing URL
    else:
        # Prepare context data for template
        shipping_option = models.shipping_options.objects.filter(pk=id).first() if id else None
        return render(request, 'admin/shipping_options.html', {'shipping_option': shipping_option})


@login_required
def user_settings(request):
    return render(request, 'settings/user_settings.html')

@login_required
def user_settings_contact(request):
    return render(request, 'settings/user_settings_contact.html')

@login_required
def user_settings_address(request):
    return render(request, 'settings/user_settings_address.html')

@login_required
def update_user_info(request):
    return render(request, 'users/user_settings.html')

@login_required
def user_home(request):
    user = request.user
    if user.is_authenticated:
        try:
            customer = models.customers.objects.get(user=request.user)
            user_orders = models.orders.objects.filter(customer=customer).order_by('-date_added')
            # Process orders to add item counts
            for order in user_orders:
                items = json.loads(order.items)
                item_count = sum(int(item['quantity']) for item in items)  # Summing up the 'amount' field from each item
                order.item_count = item_count  # Attach the count to the order object
        except models.customers.DoesNotExist:
            user_orders = []
        context = {
            'orders': user_orders,
            'full_name': user.get_full_name(),
            'email': user.email,
            'last_login': user.last_login,

        }
        return render(request, 'users/user_orders.html', context)

    else:
        return redirect('login')


def register(request):
    if request.method == 'POST':
        form = forms.CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('hjem')  # Adjust this to your home URL name
        else:
            return render(request, 'users/register.html', {'form': form})
    else:
        form = forms.CustomUserCreationForm()
        return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('user_home')
        else:
            return render(request, 'users/login.html', {'form': form})
    else:
        form = AuthenticationForm()
        return render(request, 'users/login.html', {'form': form})

@login_required
def user_details(request):
    user = request.user
    try:
        customer_instance = models.customers.objects.get(user=user)
    except models.customers.DoesNotExist:
        customer_instance = models.customers(user=user)  # Create a new instance if not exists

    if request.method == 'POST':
        print(request.POST)
        form = forms.CustomerForm(request.POST, instance=customer_instance)
        if form.is_valid():
            print("VALID")
            form.save()
            return redirect('user_home')  # Redirect to the user home page or confirmation page
        else:
            print(form.errors)
    else:
        form = forms.CustomerForm(instance=customer_instance)

    return render(request, 'users/user_details.html', {'form': form})