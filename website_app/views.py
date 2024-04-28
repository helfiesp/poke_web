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

from .context_processors import cart_context
import re
from weasyprint import HTML
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

def category_search(request, category_name):
    # Fetch the main category
    main_category = get_object_or_404(models.category, name__iexact=category_name)

    # Fetch all subcategories of the main category recursively, including the main category itself
    subcategories = get_all_subcategories(main_category)

    # Fetch products that belong to the main category or any of its subcategories
    products = models.product.objects.filter(category__in=subcategories, enabled=True)

    # Apply sorting and pagination
    # (Ensure that 'apply_sort_and_pagination' function is implemented)
    products_page, sort, per_page = apply_sort_and_pagination(request, products)

    context = {
        'category': main_category,
        'products': products_page,
        'current_sort': sort,      
        'per_page': per_page,      
        'query': True,
    }

    # Render the template with the products for the category and its subcategories
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

def product_page(request, string_id):
    product = get_object_or_404(models.product, string_id=string_id)

    # Filter out images with empty values
    product_images = product.images.exclude(image__isnull=True).exclude(image__exact='')

    context = {'product': product, 'product_images': product_images}
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
                print("EXISTS")
                return JsonResponse({"success": False, "errors":'ERRORS', "redirect_url": reverse('edit_product', kwargs={'product_id': existing_product_id})})

            product_instance = form.save(commit=False) 
            enabled = request.POST.get('enabled')
            if enabled:
                product_instance.enabled = True
            bestseller = request.POST.get('bestseller')
            if bestseller:
                product_instance.bestseller = True
            product_instance.save()


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
                product_instance.save()

                # Update the remaining images
                formset.save()

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
    if request.method == 'POST':
        form = forms.category_form(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            if request.FILES:
                category.image = request.FILES['category_image']
            category.save()
            return redirect('hjem')  # Redirect to the index page or wherever you want
        else:
            print("Form Errors:", form.errors)
            return HttpResponse(json.dumps(form.errors), content_type="application/json")
    else:
        form = forms.category_form()

    return render(request, 'admin/add_category.html', {'category_form': form})


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
        category = get_object_or_404(models.category, pk=category_id)
        form = forms.category_form(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category_instance = form.save(commit=False)
            category_instance.save()
            return redirect('update_categories')
    else:
        categories = models.category.objects.all()
        return render(request, 'admin/update_categories.html', {'categories': categories, 'admin':True })

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
    items = json.loads(order.items)  # Assuming items is stored as a JSON string
    delivery_info = json.loads(order.delivery_info)
    # Call the helper function to check if the PDF exists for this order
    pdf_file_exists = pdf_exists_for_order(order_number)

    # Pass the result to the template context
    return render(request, 'admin/order_detail.html', {
        'order': order,
        'items': items,
        'pdf_exists': pdf_file_exists,
        'delivery_info': delivery_info,
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

def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(models.product, pk=product_id)
        cart = request.session.get('cart', {})
        cart[product_id] = cart.get(product_id, 0) + 1
        request.session['cart'] = cart
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        else:
            return redirect('hjem')  # Name of the URL to view the cart

@require_POST
def update_cart(request, product_id):
    data = json.loads(request.body)
    cart = request.session.get('cart', {})

    if data['action'] == 'add':
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

def checkout(request):
    if request.method == 'POST':
        # Extract data from request.POST
        delivery_option = request.POST.get('delivery_option')
        shipping_option = request.POST.get('shipping_option')
        extra_info = request.POST.get('extra_info', '')
        payment_method = request.POST.get('payment_method')
        item_data = sort_purchased_items(request)  # This function processes item data

        # Same extraction logic
        customer = get_or_create_customer(
                request.POST.get('first_name'),
                request.POST.get('last_name'),
                request.POST.get('phone'),
                request.POST.get('contact_email'),
                request.POST.get('address'),
                request.POST.get('postal_code'),
                request.POST.get('city')
            )
        # Manually create an order instance
        new_order = models.orders()
        new_order.customer = customer
        new_order.delivery_info = json.dumps({'delivery_type': delivery_option, 'shipping_option': shipping_option})
        new_order.payment_info = json.dumps({'payment_method': payment_method})
        new_order.extra_info = extra_info
        new_order.items = json.dumps(item_data)  # Assuming this is structured correctly

        # Calculate price and related fields
        total_price = sum(item['quantity'] * (item['purchase_price'] if item['purchase_price'] else item['normal_price']) for item in item_data)
        new_order.price = total_price
        new_order.paid = float('0.00')  # This could be set based on your payment processing logic
        new_order.remaining = total_price - new_order.paid
        new_order.delivery_price = float('0.00')  # Adjust if needed
        new_order.status = 'processing'  # Default, or set based on logic

        # Save the new order
        new_order.save()
        return redirect('order_success', order_number=new_order.order_number)
    else:
        return render(request, 'checkout.html')

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
        payment_details = json.loads(order.payment_info)
    except models.orders.DoesNotExist:
        # Handle missing order scenario
        return render(request, 'error.html', {'message': 'Order not found.'})

    return render(request, 'admin/order_confirmation.html', {'payment_details': payment_details, 'items':items, 'order': order})

def klarna_push_notification(request):
    if request.method == 'POST':
        # Process the notification (you might want to log it, or update order status in your database)
        print("Received push notification:", request.body)
        return HttpResponse("OK", status=200)
    return HttpResponse("Method Not Allowed", status=405)


def klarna_checkout(request):
    if request.method == 'POST':
        items_ids = request.POST.getlist('item_id[]')
        quantities = request.POST.getlist('item_quantity[]')
        prices = request.POST.getlist('item_price[]')
        sale_prices = request.POST.getlist('item_sale_price[]')

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
            
            order_lines.append({
                "type": "physical",
                "reference": str(item_id),
                "name": "Item " + str(item_id),
                "quantity": quantity,
                "unit_price": price_in_cents,
                "tax_rate": 2500,
                "total_amount": total_amount_incl_tax,  # total excl tax
                "total_tax_amount": total_tax_amount_for_item,
            })

            total_amount += total_amount_incl_tax
            total_tax_amount += total_tax_amount_for_item
            print(order_lines)
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
            "locale": "no-NO",
            "order_amount": total_amount,
            "order_tax_amount": total_tax_amount,
            "order_lines": order_lines,
            "merchant_urls": {
                "terms": "http://example.com/terms.html",
                "checkout": "http://example.com/checkout.html",
                "confirmation": "http://example.com/thank_you.html",
                "push": "http://16.16.255.122:8000/klarna/push"
            }
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 201:
            klarna_order = response.json()
            return redirect(klarna_order['html_snippet'])
        else:
            print(response.text)
            return render(request, "checkout_error.html", {"error": response.text})

    return render(request, "checkout_page.html")