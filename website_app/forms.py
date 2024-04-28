from django import forms
from .models import product, product_image, category, text_areas, footer_textareas, business_information, supplier, orders, customers
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

class product_form(forms.ModelForm):
    class Meta:
        model = product
        fields = ['title', 'subtitle', 'category', 'description', 'price', 'sale_price', 'material', 'color', 'height', 'width', 'depth','length', 'instock', 'more_information', 'supplier', 'enabled', 'bestseller']

product_image_formset = inlineformset_factory(
    product, product_image,
    fields=('image',),
    extra=3,
    can_delete=True
)


class category_form(forms.ModelForm):
    class Meta:
        model = category
        fields = ['name', 'parent', 'image'] 


class supplier_form(forms.ModelForm):
    class Meta:
        model = supplier
        fields = ['name', 'image'] 

class text_areas_form(forms.ModelForm):
    class Meta:
        model = text_areas
        fields = [
            'front_page_header', 'front_page_subtitle', 'front_page_button_text',
            'recent_product_header', 'recent_product_text',
            'bestseller_header', 'bestseller_text',
            'nav_item_1', 'nav_item_2', 'nav_item_3', 'nav_item_4',
            'purchase_button_1', 'purchase_button_2',
            'product_desc_item_1', 'product_desc_item_2', 'product_desc_item_3', 'sale_catalogue'
        ]

class footer_text_areas_form(forms.ModelForm):
    class Meta:
        model = footer_textareas
        fields = [
            'footer_header_1', 'footer_header_1_subtitle',
            'footer_header_2',
            'footer_header_3', 'footer_header_3_subtitle_1', 'footer_header_3_subtitle_2',
            'footer_header_4', 'footer_header_4_subtitle_1', 'footer_header_4_subtitle_2',
            'footer_header_5', 'footer_header_5_subtitle_1', 'footer_header_5_subtitle_2',
        ]

class business_information_form(forms.ModelForm):
    class Meta:
        model = business_information
        fields = [
            'street_address', 'zip_code',
            'zip_code_area',
            'main_email', 'secondary_email', 'main_phone',
            'secondary_phone', 'about_us_text',
        ]

class CustomerForm(forms.ModelForm):
    class Meta:
        model = customers
        fields = ['first_name', 'last_name', 'address', 'postal_code', 'city', 'email', 'phone_number']
        labels = {
            'first_name': 'Fornavn',
            'last_name': 'Etternavn',
            'address': 'Gateadresse',
            'postal_code': 'Postkode',
            'city': 'By',
            'email': 'E-post',
            'phone_number': 'Telefonnummer'
        }

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        phone_number = cleaned_data.get('phone_number')

        # Check for existing customers with the same first name, last name, and phone number, excluding the current instance if it exists
        existing_customer = customers.objects.filter(
            first_name=first_name, 
            last_name=last_name, 
            phone_number=phone_number
        ).exclude(pk=self.instance.pk if self.instance else None)

        if existing_customer.exists():
            raise ValidationError("A customer with this first name, last name, and phone number already exists.")

        return cleaned_data

class OrderForm(forms.ModelForm):
    # Custom fields for contact and delivery details
    contact_email = forms.EmailField(required=True)
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'cols': 20, 'rows': 2}), required=True)
    payment_method = forms.ChoiceField(choices=[('card', 'Card'), ('paypal', 'Paypal')], required=True)

    # Override the init method if needed to customize form initialization
    # def __init__(self, *args, **kwargs):
    #     super(OrderForm, self).__init__(*args, **kwargs)
    #     # Initialize form fields here if needed

    class Meta:
        model = orders
        fields = ['delivery_info', 'extra_info', 'price', 'paid', 'remaining', 'delivery_price', 'status']
        # You might want to add or remove fields based on your requirements

    # Override the save method to customize saving behavior
    def save(self, commit=True):
        order = super(OrderForm, self).save(commit=False)
        # Set additional fields here or process data
        if commit:
            order.save()
        return order

    # Custom validation methods as needed
    def clean(self):
        cleaned_data = super().clean()