from django.shortcuts import render, redirect
from cart.models import *
from .forms import OrderForm
import datetime
from .models import *
import json
from django.http import JsonResponse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

import stripe
from django.conf import settings
from django.urls import reverse

def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered = False, order_number= body['orderID'])
    # Store transaction details inside PAYMENT model
    payment = Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid = order.order_total,
        status = body['status'],
    )
    payment.save()
    
    # Update ORDER model 
    order.payment = payment
    order.is_ordered = True
    order.save()
    
    
    # Move the cart items to the Order Product table
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order_id = order.id
        order_product.payment = payment
        order_product.user_id = request.user.id
        order_product.product_id = item.product_id
        order_product.quantity = item.quantity
        order_product.product_price = item.product.price
        order_product.ordered = True
        # ManytoManyField needs to be saved first
        order_product.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        order_product = OrderProduct.objects.get(id=order_product.id)
        order_product.variations.set(product_variation)
        order_product.save()


    # Decrement the quantity of the available stock

    product = Product.objects.get(id=item.product_id)
    product.stock -= item.quantity
    product.save()

    # CLEAR the cart 
    
    CartItem.objects.filter(user=request.user).delete()

    # SEND order EMAIL to customer
    
    mail_subject = 'Thank you for your order!'
    message = render_to_string('orders/order_received_email.html', {
        'user': request.user,
        'order': order,
    })

    to_email = request.user.email 
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    # SEND order number and transaction id to sendData method via JSON1

    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }

    return JsonResponse(data)



def place_order(request, total=0, quantity=0):
    current_user = request.user
    # if cart count is zero, then redirect to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store') 
    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity   
    tax = (2 * total)/100
    grand_total = total + tax
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside the Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number 202407032
            yr = int(datetime.date.today().strftime('%Y'))
            mt = int(datetime.date.today().strftime('%m'))
            dt = int(datetime.date.today().strftime('%d'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime('%Y%m%d') 
            order_number = current_date + str(data.id)  # 20210525
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            
            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }
            return render(request, 'orders/payments.html', context)
            
            
    else:
        return redirect('checkout')
    

    



stripe.api_key = settings.STRIPE_SECRET_KEY

def checkout_session(request):

    products = [
        {
            "product_name": "Apple Macbook Pro 16",
            "product_image": "https://dghyt15qon7us.cloudfront.net/images/productTheme/devices/small/16994358911333051.jpg",
            "qty": 1,
            "price": 100  # Price in cents
        },
        {
            "product_name": "Apple iPhone 15",
            "product_image": "https://dghyt15qon7us.cloudfront.net/images/productTheme/devices/small/0.37064300%2017125747411333074.jpg",
            "qty": 1,
            "price": 200  # Price in cents
        },
        {
            "product_name": "Ultimate Screen Protector",
            "product_image": "https://30minutesfix.com/assets/images/repair-part.png",
            "qty": 1,
            "price": 300  # Price in cents
        }
    ]

    line_items = []
    for product in products:
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': product['product_name'],
                   #'images': [product['product_image']],
                },
                'unit_amount': product['price'],
            },
            'quantity': product['qty'],
        })
    print(line_items)
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri(reverse('checkout_success')) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri(reverse('checkout_failure')),
    )

    return JsonResponse({'id': session.id})

def checkout_success(request):
    session_id = request.GET.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    return render(request, 'payments/payment_success.html', {'session': session})

def checkout_failure(request):
    return render(request, 'payments/payment_fail.html')

def show_payment_form(request):
    stripe_public_key = settings.STRIPE_PUBLISHABLE_KEY
    return render(request, 'payments/payment_checkout_page.html', {'stripe_public_key': stripe_public_key})
