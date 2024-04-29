"""
URL configuration for pgmobler project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from website_app import views
from django.conf.urls.static import static
from pokelageret import settings
from django.contrib.auth import views as auth_views
from django.conf.urls import handler404, handler500

handler404 = 'website_app.views.error_404_view'
handler500 = 'website_app.views.error_500_view'

urlpatterns = [
    path('login/', views.login_view, name='login'), 
    path('', views.index, name='hjem'),
    path('categories', views.categories, name='categories'),
    path('sale_catalogue', views.sale_catalogue, name='sale_catalogue'),
    path('categories/<str:category_name>', views.category_search, name='category_search'),
    path('products/supplier/<str:supplier_name>', views.supplier_search, name='supplier_search'),

    path('products', views.general_search, name='products'),


    path('product/<str:string_id>/', views.product_page, name='product_page'),
    path('product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('product/edit/image/delete/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
    path('product/<int:product_id>/edit/delete/', views.delete_product, name='delete_product'),

    # ADMIN STUFF
    path('administration', views.administration, name='administration'),

    path('products/add', views.add_product, name='add_product'),
    path('products/edit/', views.product_list_and_update, name='update_products'),
    path('products/edit/<int:product_id>/', views.product_list_and_update, name='update_products_id'),

    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/', views.category_list_and_update, name='update_categories'),
    path('categories/edit/<int:category_id>/', views.category_list_and_update, name='update_categories_id'),

    path('text_areas/edit/', views.text_areas_list_and_update, name='update_text_areas'),
    path('text_areas/edit/<int:text_area_id>/', views.text_areas_list_and_update, name='update_text_areas_id'),
    path('text_areas/create/', views.text_areas_list_and_update, name='create_text_area'),

    path('footer_textareas/edit/', views.text_areas_list_and_update, name='update_footer_text_areas'),
    path('footer_textareas/edit/<int:footer_text_area_id>/', views.text_areas_list_and_update, name='update_footer_textareas_id'),
    path('footer_textareas/create/', views.text_areas_list_and_update, name='create_footer_text_area'),

    path('business_information/', views.text_areas_list_and_update, name='business_information'),
    path('business_information/create/', views.text_areas_list_and_update, name='create_business_information'),
    path('business_information/edit/<int:business_info_id>/', views.text_areas_list_and_update, name='update_business_information'),


    path('suppliers/add/', views.add_supplier, name='add_supplier'),

    path('order/<int:customer_id>/', views.add_order, name='add_order'),

    path('add-customer/', views.add_customer, name='add_customer'),
    path('customer/<int:customer_id>/', views.customer_detail, name='customer_detail'),

    path('orders/', views.all_orders, name='all_orders'),
    path('order-detail/<int:order_number>/', views.order_detail, name='order_detail'),
    path('order-detail/<int:order_number>/confirmation', views.order_confirmation, name='order_confirmation'),
    path('order-detail/<int:order_number>/show-pdf/', views.show_order_pdf, name='show_order_pdf'),
    path('order-detail/<int:order_number>/complete', views.complete_order, name='complete_order'),

    path('order-detail/<int:order_number>/update', views.update_order, name='update_order'),

    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<product_id>/', views.update_cart, name='update_cart'),
    path('get-cart-total/', views.get_cart_total, name='get-cart-total'),
    path('get-cart-data/', views.get_cart_data, name='get-cart-data'),

    path('checkout', views.checkout, name='checkout'),
    path('klarna-checkout/', views.klarna_checkout, name='klarna_checkout'),

    path('order-success/<str:order_number>/', views.order_success, name='order_success'),


    path('shipping_option/', views.manage_shipping_option, name='new_shipping_option'),
    path('shipping_option/<int:id>/', views.manage_shipping_option, name='edit_shipping_option'),

    # KLARNA
    #path('terms/', views.terms_and_conditions, name='terms'),
    #path('checkout_update/', views.checkout_update, name='checkout_update'),
    path('confirmation/<int:order_number>/', views.order_success, name='order_success'),
    path('klarna/push/', views.klarna_push_notification, name='klarna_push_notification'),


    # END OF ADMIN STUFF

    path('about_us', views.about_us, name='about_us'),
    path('contact', views.contact, name='contact'),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

