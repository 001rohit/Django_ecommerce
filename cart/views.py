from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render,redirect
from product.models import *
from .models import *
from django.core.exceptions import ObjectDoesNotExist
# Create your views here.

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    product_variation = []
    if request.method == 'POST':
        for item in request.POST:
            key = item
            value = request.POST.get(key)
            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                print(variation)
                product_variation.append(variation)
            except:
                pass 

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except (TypeError,Cart.DoesNotExist):
        cart = Cart.objects.create(
            cart_id = _cart_id(request)
        )
    cart.save()  
    
    # implementing variation with the cart functionality
    is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
          
    if is_cart_item_exists:

        cart_item = CartItem.objects.filter(product=product, cart=cart)
        # existing variation -> database
        # current variation -> product_variation
        # item_id -> database
        
        # existing variation list
        ex_var_list = []
        # cart item id list
        id = []
        
        # check current variation inside the existing variation - increase quantity for cart_item
        for item in cart_item:
            # print(item)
            existing_variation = item.variation.all()
            ex_var_list.append(list(existing_variation)) # existing_variation into list
            id.append(item.id) # appending item id in list
        
        # print(ex_var_list)
        # print(ex_var_list[1])
        # print(product_variation)
        
        if product_variation in ex_var_list:
            # increase the cart item qunatity
            
            # id from the list
            index = ex_var_list.index(product_variation)
            item_id = id[index]
            item = CartItem.objects.get(product=product, id=item_id)
            item.quantity += 1
            item.save()
            
        else:
            # item creation
            item = CartItem.objects.create(product=product, quantity=1, cart=cart)
            
            # create new cart item
            if len(product_variation) > 0:
                item.variation.clear()
                item.variation.add(*product_variation)

            # cart_item.quantity += 1
            item.save()
    else:
        cart_item = CartItem.objects.create(product = product, quantity = 1, cart = cart)
        if len(product_variation) > 0:
            cart_item.variation.clear()
            cart_item.variation.add(*product_variation)
        cart_item.save()
    # return HttpResponse(cart_item.quantity)
    # close()
    return redirect('cart')

def remove_cart(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id = product_id)
    
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
            
        else:
            cart_item.delete()
            
    except:
        pass
        
    return redirect('cart')

def remove_cart_item(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id = product_id)
    cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')
        
def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        cart = Cart.objects.get(cart_id = _cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        
        tax = (2 * total)/100
        grand_total = total + tax
    except ObjectDoesNotExist:
        pass

    context = {
        'total':total,
        'quantity':quantity,
        'cart_items':cart_items,
        'tax':tax,
        'grand_total':grand_total,
    }
          
    return render(request, 'cart.html', context)